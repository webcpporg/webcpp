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
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent


def run(command: list[str], *, cwd: Path, env: dict[str, str], log: Path) -> None:
    print('+ ' + shlex.join(command), flush=True)
    with log.open('w') as stream:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=600)
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
    if not candidate.is_file():
        raise RuntimeError(f'configured compiler has no C driver: {candidate}')
    return candidate.absolute()


def main() -> None:
    arguments = sys.argv[1:]
    if len(arguments) == 1:
        arguments = shlex.split(Path(arguments[0]).read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--platform', choices=('darwin', 'linux', 'wasi'), required=True)
    parser.add_argument('--threading', choices=('single', 'multi'), required=True)
    parser.add_argument('--cc', required=True)
    parser.add_argument('--ar', default='')
    parser.add_argument('flags', nargs=argparse.REMAINDER)
    args = parser.parse_args(arguments)
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    pin = json.loads((HERE / 'pin.json').read_text())
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'],
                                       text=True).strip()
    if revision != pin['commit']:
        raise RuntimeError('OpenSSL checkout differs from tools/openssl/pin.json; '
                           'update the submodule')
    subprocess.run(['git', '-C', str(source), 'diff', '--exit-code', 'HEAD', '--'],
                   check=True, stdout=subprocess.DEVNULL)
    compiler = c_driver(args.cc)
    flags = args.flags[1:] if args.flags[:1] == ['--'] else args.flags
    flags += ['-ffunction-sections', '-fdata-sections']
    archiver = args.ar or str(compiler.with_name('llvm-ar') if args.platform == 'wasi' else 'ar')
    env = os.environ.copy()
    for variable in ('CPATH', 'CPLUS_INCLUDE_PATH', 'C_INCLUDE_PATH', 'CPPFLAGS',
                     'CFLAGS', 'CXXFLAGS', 'LDFLAGS', 'LD_LIBRARY_PATH',
                     'OPENSSL_CONF', 'OPENSSL_MODULES', 'CROSS_COMPILE'):
        env.pop(variable, None)
    env.setdefault('SOURCE_DATE_EPOCH', subprocess.check_output(
        ['git', '-C', str(source), 'show', '-s', '--format=%ct', 'HEAD'], text=True).strip())
    options = ['--openssldir=/etc/ssl', 'no-shared', 'no-tests', 'no-apps', 'no-docs', 'no-module',
               '--libdir=lib', 'threads' if args.threading == 'multi' else 'no-threads']
    if args.platform == 'wasi':
        if '--target=wasm32-wasip3' not in flags:
            raise RuntimeError('WASIp3 OpenSSL requires --target=wasm32-wasip3 '
                               'in the configured C flags')
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
        target = ['--config=' + str(HERE / 'wasip3.conf'), 'webcpp-wasip3']
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
    env.update(CC=shlex.quote(str(compiler)), AR=shlex.quote(archiver),
               RANLIB=shlex.quote(archiver) + ' s', CFLAGS=shlex.join(flags))
    record = {'pin': pin, 'platform': args.platform, 'threading': args.threading,
              'compiler': str(compiler), 'archiver': archiver, 'flags': flags,
              'configure': target + options}
    started = time.monotonic()
    # Do not use a potentially space-containing TMPDIR for upstream make.
    temporary_root = Path(tempfile.gettempdir())
    if any(character.isspace() for character in str(temporary_root)):
        temporary_root = Path('/tmp')
    with tempfile.TemporaryDirectory(prefix='webcpp-openssl-', dir=temporary_root) as temporary:
        scratch = Path(temporary)
        # Configure canonicalizes source symlinks. A real, unmodified copy is
        # needed to keep spaces in the user's checkout out of its Makefiles.
        shutil.copytree(source, scratch / 'source', symlinks=True,
                        ignore=shutil.ignore_patterns('.git'))
        build = scratch / 'build'
        build.mkdir()
        install = scratch / 'install'
        # External config is reached through the same space-free staging area.
        (scratch / 'wasip3.conf').symlink_to(HERE / 'wasip3.conf')
        actual_target = (['--config=' + str(scratch / 'wasip3.conf'), 'webcpp-wasip3']
                         if args.platform == 'wasi' else target)
        run(['perl', str(scratch / 'source/Configure'), *actual_target, *options,
             '--prefix=' + str(install)], cwd=build, env=env, log=output / 'configure.log')
        run(['make', '-j' + str(min(8, os.cpu_count() or 1)), 'build_libs'],
            cwd=build, env=env, log=output / 'build.log')
        run(['make', 'install_dev'], cwd=build, env=env, log=output / 'install.log')
        # Copy headers before archives: consumers cannot compile against a
        # different configuration while the new archives are being produced.
        shutil.copytree(install / 'include', output / 'include', dirs_exist_ok=True)
        for name in ('libssl.a', 'libcrypto.a'):
            staged = output / (name + '.new')
            shutil.copyfile(install / 'lib' / name, staged)
            staged.replace(output / name)
    record['seconds'] = time.monotonic() - started
    record['sha256'] = {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                        for name in ('libssl.a', 'libcrypto.a')}
    (output / 'build.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'OpenSSL {pin["version"]}: {args.platform}/{args.threading} built from source '
          f'in {record["seconds"]:.1f}s', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, OSError) as error:
        sys.exit(f'OpenSSL build: {error}')
