#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Build the pinned upstream OpenSSL sources for a B2-selected C toolchain.

The temporary upstream build has space-free paths because OpenSSL's generated
Makefiles do not support all checkout paths B2 supports. Only the finished
archives and matching headers enter B2's variant directory. No download or
system OpenSSL lookup takes place here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

from source import check_checkout, stage_source

HERE = Path(__file__).resolve().parent


def run(command: list[str], *, cwd: Path, env: dict[str, str], log: Path,
        timeout: float = 600) -> None:
    print('+ ' + shlex.join(command), flush=True)
    try:
        with log.open('w') as stream:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        print(log.read_text(errors='replace')[-14000:], file=sys.stderr)
        raise RuntimeError(f'command timed out after {timeout:g}s; full log: {log}') from error
    if result.returncode:
        print(log.read_text(errors='replace')[-14000:], file=sys.stderr)
        raise RuntimeError(f'command failed ({result.returncode}); full log: {log}')


def c_driver(command: str) -> Path:
    # B2 configures its C++ driver. Use the C driver from that exact installation,
    # not PATH's unrelated compiler. Custom wrappers must expose a C sibling.
    found = shutil.which(command)
    if not found:
        raise RuntimeError(f'cannot find configured compiler {command!r}')
    driver = Path(found)
    name = driver.name.replace('clang++', 'clang').replace('g++', 'gcc')
    candidate = driver.with_name(name)
    if not candidate.is_file() and driver.is_symlink():
        # CI and package managers may expose only a C++ symlink. Follow it to
        # its installation, preserving a wrapper's C sibling when one exists.
        driver = driver.resolve()
        name = driver.name.replace('clang++', 'clang').replace('g++', 'gcc')
        candidate = driver.with_name(name)
    if not candidate.is_file():
        raise RuntimeError(f'configured compiler has no C driver: {candidate}')
    return candidate.absolute()


def windows_target(compiler: Path, flags: list[str], scratch: Path, env: dict[str, str]) -> str:
    """Select upstream's architecture from the compiler B2 actually configured."""
    probe = scratch / 'architecture.c'
    probe.write_text('#if defined(_MSC_VER) && defined(_WIN32)\n'
                     '#if defined(_M_ARM64)\nWEBCPP_OPENSSL_ARM64\n'
                     '#elif defined(_M_X64)\nWEBCPP_OPENSSL_X64\n'
                     '#elif defined(_M_IX86)\nWEBCPP_OPENSSL_X86\n'
                     '#endif\n#endif\n')
    result = subprocess.check_output([str(compiler), *flags, '/nologo', '/EP', '/TC', str(probe)],
                                     env=env, text=True)
    for marker, target in (('WEBCPP_OPENSSL_ARM64', 'VC-WIN64-ARM'),
                           ('WEBCPP_OPENSSL_X64', 'VC-WIN64A'),
                           ('WEBCPP_OPENSSL_X86', 'VC-WIN32')):
        if marker in result.split():
            return target
    raise RuntimeError('OpenSSL recipe requires an x86, x64 or ARM64 MSVC target')


def windows_perl(env: dict[str, str]) -> str:
    """Find native Perl even when a Git Bash or MSYS Perl precedes it on PATH."""
    for directory in env.get('PATH', '').split(os.pathsep):
        perl = shutil.which('perl', path=directory)
        if not perl:
            continue
        platform = subprocess.check_output([perl, '-e', 'print $^O'], env=env, text=True)
        if platform.strip() == 'MSWin32':
            return perl
    raise RuntimeError('MSVC OpenSSL requires native Windows Perl (for example Strawberry Perl) '
                       'on PATH; a Git Bash or MSYS Perl cannot generate nmake files')


def suite_result(log: str, recipes: list[str]) -> dict:
    """Reject empty or partial TAP runs, retaining upstream's configuration skips."""
    # Upstream runs preparation recipes first, with a separate TAP summary.
    # A non-FIPS build legitimately skips that phase with Tests=0.
    summaries = list(re.finditer(r'Files=(\d+), Tests=(\d+)', log))
    summary = summaries[-1] if summaries else None
    missing = [name for name in recipes if name not in log]
    if ('All tests successful.' not in log or not summary or int(summary[2]) == 0
            or not recipes or missing):
        raise RuntimeError('upstream suite did not report a complete passing run; '
                           f'missing recipes: {missing}')
    return {'result': 'passed', 'selection': 'alltests', 'recipes': len(recipes),
            'files': int(summary[1]), 'tests': int(summary[2])}


def main() -> None:
    arguments = sys.argv[1:]
    if len(arguments) == 1:
        arguments = shlex.split(Path(arguments[0]).read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--platform', choices=('darwin', 'linux', 'wasi', 'windows'), required=True)
    parser.add_argument('--threading', choices=('single', 'multi'), required=True)
    parser.add_argument('--cc', required=True)
    parser.add_argument('--ar', default='')
    parser.add_argument('--variant', default='release')
    parser.add_argument('--test', action='store_true',
                        help='run the complete native upstream suite before publishing libraries')
    parser.add_argument('--headers-only', action='store_true',
                        help='generate public headers without building archives or running tests')
    parser.add_argument('flags', nargs=argparse.REMAINDER)
    args = parser.parse_args(arguments)
    if args.headers_only and args.test:
        raise RuntimeError('header preparation cannot certify an upstream test run')
    if args.test and args.platform == 'wasi':
        raise RuntimeError('the OpenSSL upstream test harness requires native executables; '
                           'WASI uses the separately declared TLS integration tests')
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name in ('build.json', 'upstream-tests.json'):
        (output / name).unlink(missing_ok=True)
    pin = json.loads((HERE / 'pin.json').read_text())
    check_checkout(source, pin)
    # Verify the source before probing or invoking any configured build tool.
    # A broken toolchain must never mask a corrupted source archive.
    temporary_root = Path(tempfile.gettempdir())
    if any(character.isspace() for character in str(temporary_root)):
        if sys.platform == 'win32':
            raise RuntimeError('OpenSSL needs a writable TEMP directory without spaces')
        temporary_root = Path('/tmp')
    with tempfile.TemporaryDirectory(prefix='webcpp-openssl-', dir=temporary_root) as temporary:
        scratch = Path(temporary)
        stage_source(source, scratch / 'source', pin)
        build_source(args, output, pin, scratch)


def build_source(args: argparse.Namespace, output: Path, pin: dict, scratch: Path) -> None:
    """Build verified sources, then publish archives and headers to B2 together."""
    compiler = c_driver(args.cc)
    flags = args.flags[1:] if args.flags[:1] == ['--'] else args.flags
    windows = args.platform == 'windows'
    flags += ['/Gy', '/Gw'] if windows else ['-ffunction-sections', '-fdata-sections']
    archiver = args.ar or str(compiler.with_name('llvm-ar') if args.platform == 'wasi' else 'ar')
    env = os.environ.copy()
    for variable in ('CPATH', 'CPLUS_INCLUDE_PATH', 'C_INCLUDE_PATH', 'CPPFLAGS',
                     'CFLAGS', 'CXXFLAGS', 'LDFLAGS', 'LD_LIBRARY_PATH',
                     'OPENSSL_CONF', 'OPENSSL_MODULES', 'CROSS_COMPILE', 'CL', '_CL_',
                     'MAKEFLAGS', 'MFLAGS', 'TESTS', 'EXE_SHELL', 'TOP', 'SRCTOP', 'BLDTOP',
                     'BIN_D', 'TEST_D', 'RESULT_D', 'STOPTEST', 'FIPS_MODE'):
        env.pop(variable, None)
    for variable in list(env):
        if variable.startswith(('HARNESS_', 'OPENSSL_TEST_')):
            env.pop(variable)
    env.setdefault('SOURCE_DATE_EPOCH', str(pin['source_date_epoch']))
    # Native ordinary and tested builds use the same library configuration.
    # Only the opt-in action builds the upstream apps and test executables.
    options = ['no-shared', 'no-docs', 'no-module',
               '--libdir=lib', 'threads' if args.threading == 'multi' else 'no-threads']
    # MSVC's /MDd and /MTd define _DEBUG themselves. Upstream --debug would
    # force it even when the user explicitly selects runtime-debugging=off.
    if args.variant == 'debug' and not windows:
        options += ['--debug']
    if not windows:
        options += ['--openssldir=/etc/ssl']
    if args.platform == 'wasi':
        options += ['no-tests', 'no-apps']
        wasi_targets = [target for target in ('wasip2', 'wasip3')
                        if f'--target=wasm32-{target}' in flags]
        if len(wasi_targets) != 1:
            raise RuntimeError('WASI OpenSSL requires exactly one --target=wasm32-wasip2 '
                               'or --target=wasm32-wasip3 in the configured C flags')
        wasi_target = wasi_targets[0]
        if wasi_target == 'wasip2' and args.threading != 'single':
            raise RuntimeError('WASIp2 OpenSSL requires threading=single; '
                               'the pinned SDK has no WASIp2 thread backend')
        sdk = compiler.parent.parent
        if args.threading == 'multi':
            sysroots = [flag.split('=', 1)[1] for flag in flags if flag.startswith('--sysroot=')]
            coop = (Path(sysroots[-1]) if sysroots
                    else sdk / 'share/wasi-sysroot/experimental-coop-threads')
            if not (coop / 'lib/wasm32-wasip3/libc.a').is_file():
                raise RuntimeError('WASIp3 threading=multi requires '
                                   'the cooperative wasi-sdk sysroot')
            flags += [f'--sysroot={coop}', '-pthread']
            options += ['no-thread-pool']
        flags += [f'-D_WASI_EMULATED_{name}' for name in
                  ('SIGNAL', 'PROCESS_CLOCKS', 'MMAN', 'GETPID')]
        options += ['--with-rand-seed=getrandom', 'no-asm', 'no-dso', 'no-ui-console',
                    'no-afalgeng', 'no-quic', '-DOPENSSL_NO_UNIX_SOCK']
        target = ['--config=' + str(HERE / 'wasip3.conf'), 'webcpp-' + wasi_target]
    elif windows:
        native = windows_target(compiler, flags, scratch, env)
        target = ['--config=' + str(HERE / 'msvc.conf'), native + '-webcpp']
        # A deterministic portable C profile needs only the MSVC toolchain,
        # including ml64 for upstream's x64 uplink shim, and no separate NASM.
        options += ['no-asm']
        archiver = args.ar or 'link'
    else:
        triple = subprocess.check_output([str(compiler), *flags, '-dumpmachine'],
                                         text=True).strip()
        macros = subprocess.check_output([str(compiler), *flags, '-dM', '-E', '-x', 'c', '-'],
                                         input='', text=True)
        if args.platform == 'darwin' and '#define __APPLE__ 1' not in macros:
            raise RuntimeError('B2 target-os=darwin disagrees with the configured C compiler')
        if args.platform == 'linux' and '#define __linux__ 1' not in macros:
            raise RuntimeError('B2 target-os=linux disagrees with the configured C compiler')
        arch = next((name for macro, name in (('__aarch64__', 'aarch64'),
                    ('__arm64__', 'arm64'), ('__x86_64__', 'x86_64'), ('__i386__', 'i386'))
                    if f'#define {macro} 1' in macros), 'unsupported')
        supported = {('darwin', 'arm64'): 'darwin64-arm64-cc',
                     ('darwin', 'aarch64'): 'darwin64-arm64-cc',
                     ('darwin', 'x86_64'): 'darwin64-x86_64-cc',
                     ('linux', 'aarch64'): 'linux-aarch64',
                     ('linux', 'x86_64'): 'linux-x86_64',
                     ('linux', 'i386'): 'linux-x86', ('linux', 'i686'): 'linux-x86'}
        if (args.platform, arch) not in supported:
            raise RuntimeError(f'OpenSSL recipe has no reviewed native target for {triple}')
        target = [supported[args.platform, arch]]
    # Inherit compiler options from B2 but not webcpp's C++ warning policy.
    if windows:
        # The upstream nmake template quotes tool paths itself.
        env.update(CC=str(compiler), AR=archiver, CFLAGS=subprocess.list2cmdline(flags))
        env['ARFLAGS'] = '/lib /nologo'
    else:
        env.update(CC=shlex.quote(str(compiler)), AR=shlex.quote(archiver),
                   CFLAGS=shlex.join(flags))
        env['RANLIB'] = shlex.quote(archiver) + ' s'
    record = {'pin': pin, 'platform': args.platform, 'threading': args.threading,
              'variant': args.variant,
              'compiler': str(compiler), 'archiver': archiver, 'flags': flags,
              'configure': target + options}
    started = time.monotonic()
    build = scratch / 'build'
    build.mkdir()
    install = scratch / 'install'
    actual_target = target
    if args.platform == 'wasi':
        # Copying also works when symlink creation needs Windows privileges.
        shutil.copyfile(HERE / 'wasip3.conf', scratch / 'wasip3.conf')
        actual_target = ['--config=' + str(scratch / 'wasip3.conf'), target[-1]]
    elif windows:
        shutil.copyfile(HERE / 'msvc.conf', scratch / 'msvc.conf')
        actual_target = ['--config=' + str(scratch / 'msvc.conf'), target[-1]]
    perl = windows_perl(env) if windows else 'perl'
    run([perl, str(scratch / 'source/Configure'), *actual_target, *options,
         '--prefix=' + str(install)], cwd=build, env=env, log=output / 'configure.log')
    make = ['nmake', '/nologo'] if windows else ['make']
    jobs = [] if windows else ['-j2']
    if args.headers_only:
        run([*make, *jobs, 'build_generated'], cwd=build, env=env,
            log=output / 'headers.log')
        headers = copy_headers(scratch / 'source', build, output / 'include/openssl', windows)
        # This is B2's header-producing action. Even unchanged headers must
        # become newer than its prerequisites, without disturbing mapped bytes.
        for header in headers:
            header.touch()
        print(f'OpenSSL {pin["version"]}: {args.platform}/{args.threading} headers generated '
              f'in {time.monotonic() - started:.1f}s', flush=True)
        return
    # nmake builds one translation unit at a time. Windows CI exceeded ten
    # minutes while still compiling normally; retain a bounded thirty-minute
    # budget for this phase. Parallel Make retains the shorter budget.
    run([*make, *jobs, 'build_libs'], cwd=build, env=env, log=output / 'build.log',
        timeout=1800 if windows else 600)
    suite = None
    if args.test:
        env['HARNESS_JOBS'] = '2'
        run([*make, *jobs, 'test', 'TESTS=alltests'], cwd=build, env=env,
            log=output / 'upstream-tests.log', timeout=2400)
        log = (output / 'upstream-tests.log').read_text(errors='replace')
        recipes = sorted(path.name for path in (scratch / 'source/test/recipes').glob('*.t'))
        try:
            suite = suite_result(log, recipes)
        except RuntimeError as error:
            raise RuntimeError(f'{error}; full log: {output / "upstream-tests.log"}') from error
    if windows:
        # Upstream install_dev requires an external PDB even with B2's /Z7
        # embedded symbols or debug-symbols=off. Stage exactly its public and
        # generated headers and archives, without the unrelated exporters.
        copy_headers(scratch / 'source', build, install / 'include/openssl', windows)
        (install / 'lib').mkdir()
        for name in ('libssl.lib', 'libcrypto.lib'):
            shutil.copyfile(build / name, install / 'lib' / name)
        symbols = build / 'ossl_static.pdb'
        if symbols.is_file():
            shutil.copyfile(symbols, output / symbols.name)
    else:
        run([*make, 'install_dev'], cwd=build, env=env, log=output / 'install.log')
    # Headers were already prepared with this configuration. Keep identical
    # files untouched: consumers can be compiling with them during this action.
    # Publish any changed headers atomically before making archives available.
    shutil.copytree(install / 'include', output / 'include', dirs_exist_ok=True,
                    copy_function=publish_header)
    names = ('libssl.lib', 'libcrypto.lib') if windows else ('libssl.a', 'libcrypto.a')
    for name in names:
        staged = output / (name + '.new')
        shutil.copyfile(install / 'lib' / name, staged)
        staged.replace(output / name)
    record['seconds'] = time.monotonic() - started
    record['sha256'] = {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                        for name in names}
    (output / 'build.json').write_text(json.dumps(record, indent=2) + '\n')
    if suite:
        suite.update(pin=pin['commit'], configure=record['configure'], sha256=record['sha256'])
        (output / 'upstream-tests.json').write_text(json.dumps(suite, indent=2) + '\n')
        print(f'OpenSSL upstream suite passed: {suite["files"]} recipes, '
              f'{suite["tests"]} tests', flush=True)
    print(f'OpenSSL {pin["version"]}: {args.platform}/{args.threading} built from source '
          f'in {record["seconds"]:.1f}s', flush=True)


def copy_headers(source: Path, build: Path, output: Path, windows: bool) -> list[Path]:
    """Publish the public headers in upstream install_dev's source/generated order."""
    output.mkdir(parents=True, exist_ok=True)
    headers = {}
    for directory in (source / 'include/openssl', build / 'include/openssl'):
        for header in directory.glob('*.h'):
            if not header.name.startswith('__DECC_'):
                headers[header.name] = header
    if windows:
        headers['applink.c'] = source / 'ms/applink.c'
    for name, header in headers.items():
        publish_header(header, output / name)
    return [output / name for name in headers]


def publish_header(source: str | Path, destination: str | Path) -> str:
    """Replace changed headers without truncating files a compiler may have mapped."""
    source, destination = Path(source), Path(destination)
    if destination.is_file() and source.read_bytes() == destination.read_bytes():
        return str(destination)
    with tempfile.NamedTemporaryFile(prefix=f'.{destination.name}.',
                                     dir=destination.parent, delete=False) as stream:
        staged = Path(stream.name)
    try:
        # Retain source permissions, but give changed build outputs a fresh
        # timestamp rather than the checkout's potentially older timestamp.
        shutil.copy(source, staged)
        staged.replace(destination)
    finally:
        staged.unlink(missing_ok=True)
    return str(destination)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, OSError) as error:
        sys.exit(f'OpenSSL build: {error}')
