#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Build pinned static WebRTC dependencies against B2's exact OpenSSL provider."""
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

from source import check_checkout, stage_source

HERE = Path(__file__).resolve().parent


def run(command: list[str], directory: Path, env: dict[str, str], log: Path) -> None:
    """Keep bounded upstream diagnostics outside the disposable source/build tree."""
    print('+ ' + shlex.join(command), flush=True)
    try:
        with log.open('w') as stream:
            result = subprocess.run(command, cwd=directory, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=1800)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f'command timed out; full log: {log}') from error
    if result.returncode:
        print(log.read_text(errors='replace')[-14000:], file=sys.stderr)
        raise RuntimeError(f'command failed ({result.returncode}); full log: {log}')


def provider(root: Path, windows: bool) -> dict:
    """Require the source-built threaded provider, never a discovered system library."""
    record = json.loads((root / 'build.json').read_text())
    expected = json.loads((HERE.parent / 'openssl/pin.json').read_text())
    if record['pin'] != expected or record['threading'] != 'multi':
        raise RuntimeError('libdatachannel requires the pinned OpenSSL built with threading=multi')
    names = ('libssl.lib', 'libcrypto.lib') if windows else ('libssl.a', 'libcrypto.a')
    for name in names:
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != record['sha256'][name]:
            raise RuntimeError(f'OpenSSL provider differs from its build record: {name}')
    return record


def build(args: argparse.Namespace) -> None:
    source, output, openssl = args.source.resolve(), args.output.resolve(), args.openssl.resolve()
    pin = json.loads((HERE / 'pin.json').read_text())
    check_checkout(source, pin)
    if args.headers_only:
        # The same verified staging boundary protects analysis and full builds.
        # Headers alone cannot publish archives or their successful build record.
        with tempfile.TemporaryDirectory(prefix='webcpp-libdatachannel-headers-') as temporary:
            staged = Path(temporary) / 'source'
            stage_source(source, staged, pin)
            shutil.copytree(staged / 'include/rtc', output / 'include/rtc',
                            dirs_exist_ok=True, copy_function=shutil.copyfile)
        return
    windows = args.platform == 'windows'
    ssl = provider(openssl, windows)
    output.mkdir(parents=True, exist_ok=True)
    driver = shutil.which(args.cxx)
    if driver is None:
        raise RuntimeError(f'configured C++ compiler is missing: {args.cxx}')
    cxx = Path(driver).absolute()
    cc = cxx.with_name(cxx.name.replace('clang++', 'clang').replace('g++', 'gcc'))
    if not cc.is_file() and cxx.is_symlink():
        resolved = cxx.resolve()
        cc = resolved.with_name(resolved.name.replace('clang++', 'clang').replace('g++', 'gcc'))
    if not cc.is_file():
        raise RuntimeError(f'configured compiler has no C driver: {cc}')
    arguments = args.flags[1:] if args.flags[:1] == ['--'] else args.flags
    separator = arguments.index('--cxx-flags')
    cflags, flags = arguments[:separator], arguments[separator + 1:]
    # Upstream WebRTC uses exceptions and RTTI internally even when a consumer
    # only uses Trystero's exception-free timer, sealer or WebSocket adapters.
    flags = [flag for flag in flags if flag not in ('-fno-exceptions', '-fno-rtti',
             '-D_HAS_EXCEPTIONS=0', '/D_HAS_EXCEPTIONS=0', '/GR-')]
    flags += ['/EHsc', '/GR', '/Gy', '/Gw'] if windows else [
        '-fexceptions', '-frtti', '-ffunction-sections', '-fdata-sections']
    # C dependencies receive B2's compile.c settings, without unrelated C++ ABI
    # or language options. Both languages retain their explicit runtime flags.
    cflags += ['/Gy', '/Gw'] if windows else ['-ffunction-sections', '-fdata-sections']
    quote = subprocess.list2cmdline if windows else shlex.join
    env = os.environ.copy()
    for variable in ('CPATH', 'CPLUS_INCLUDE_PATH', 'C_INCLUDE_PATH', 'CPPFLAGS',
                     'CFLAGS', 'CXXFLAGS', 'LDFLAGS', 'LD_LIBRARY_PATH', 'CL', '_CL_',
                     'OPENSSL_ROOT_DIR', 'OPENSSL_ROOT', 'CMAKE_PREFIX_PATH',
                     'CMAKE_TOOLCHAIN_FILE',
                     'CMAKE_GENERATOR', 'CC', 'CXX'):
        env.pop(variable, None)
    env.setdefault('SOURCE_DATE_EPOCH', str(pin['source_date_epoch']))
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='webcpp-libdatachannel-') as temporary:
        scratch = Path(temporary)
        stage_source(source, scratch / 'source', pin)
        # Upstream's macOS workaround constructs ROOT/lib paths. Supply an
        # isolated prefix with exactly the already-verified B2 provider bytes.
        ssl_prefix = scratch / 'openssl'
        (ssl_prefix / 'lib').mkdir(parents=True)
        shutil.copytree(openssl / 'include', ssl_prefix / 'include')
        names = ('libssl.lib', 'libcrypto.lib') if windows else ('libssl.a', 'libcrypto.a')
        for name in names:
            shutil.copyfile(openssl / name, ssl_prefix / 'lib' / name)
        configuration = 'Debug' if args.variant == 'debug' else 'Release'
        generator = 'NMake Makefiles' if windows else 'Unix Makefiles'
        command = ['cmake', '-S', str(scratch / 'source'), '-B', str(scratch / 'build'),
                   '-G', generator, '-DCMAKE_C_COMPILER=' + str(cc),
                   '-DCMAKE_CXX_COMPILER=' + str(cxx),
                   '-DCMAKE_BUILD_TYPE=' + configuration,
                   '-DCMAKE_C_FLAGS=' + quote(cflags), '-DCMAKE_CXX_FLAGS=' + quote(flags),
                   '-DCMAKE_C_FLAGS_DEBUG=', '-DCMAKE_CXX_FLAGS_DEBUG=',
                   '-DCMAKE_C_FLAGS_RELEASE=', '-DCMAKE_CXX_FLAGS_RELEASE=',
                   '-DCMAKE_POLICY_DEFAULT_CMP0091=NEW', '-DCMAKE_MSVC_RUNTIME_LIBRARY=',
                   '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
                   '-DBUILD_SHARED_LIBS=OFF', '-DBUILD_SHARED_DEPS_LIBS=OFF',
                   '-DPREFER_SYSTEM_LIB=OFF', '-DUSE_SYSTEM_SRTP=OFF',
                   '-DUSE_SYSTEM_JUICE=OFF', '-DUSE_SYSTEM_USRSCTP=OFF', '-DUSE_SYSTEM_PLOG=OFF',
                   '-DUSE_GNUTLS=OFF', '-DUSE_MBEDTLS=OFF', '-DUSE_NICE=OFF',
                   '-DNO_WEBSOCKET=ON', '-DNO_EXAMPLES=ON', '-DNO_TESTS=ON', '-DNO_MEDIA=OFF',
                   '-DOPENSSL_USE_STATIC_LIBS=TRUE', '-DOPENSSL_ROOT_DIR=' + str(ssl_prefix),
                   '-DOPENSSL_INCLUDE_DIR=' + str(ssl_prefix / 'include'),
                   '-DOPENSSL_SSL_LIBRARY=' + str(ssl_prefix / 'lib' / names[0]),
                   '-DOPENSSL_CRYPTO_LIBRARY=' + str(ssl_prefix / 'lib' / names[1]),
                   '-DCMAKE_INSTALL_PREFIX=' + str(scratch / 'install'),
                   '-DCMAKE_INSTALL_LIBDIR=lib']
        if windows and any(flag.lower() == '/zi' for flag in flags):
            command += ['-DCMAKE_PROJECT_libdatachannel_INCLUDE=' + str(HERE / 'msvc.cmake'),
                        '-DWEBCPP_SYMBOL_DIRECTORY=' + str(output)]
        run(command, scratch, env, output / 'configure.log')
        run(['cmake', '--build', str(scratch / 'build'), '--target', 'datachannel',
             '--parallel', str(min(4, os.cpu_count() or 1))], scratch, env, output / 'build.log')
        # Each static archive remains separate. OpenSSL is never inserted in
        # these archives, so B2 gives the final link one ssl/crypto pair.
        archives = {}
        for library in ('datachannel', 'juice', 'usrsctp', 'srtp2'):
            name = library + '.lib' if windows else 'lib' + library + '.a'
            matches = list((scratch / 'build').rglob(name))
            if len(matches) != 1:
                raise RuntimeError(f'expected one built {name}, found {matches}')
            archives[name] = matches[0]
        shutil.copytree(scratch / 'source/include/rtc', output / 'include/rtc',
                        dirs_exist_ok=True, copy_function=shutil.copyfile)
        for name, archive in archives.items():
            shutil.copyfile(archive, output / (name + '.new'))
            (output / (name + '.new')).replace(output / name)
        record = {'pin': pin, 'platform': args.platform, 'variant': args.variant,
                  'compiler': str(cxx), 'flags': flags, 'c_flags': cflags, 'openssl': str(openssl),
                  'openssl_sha256': ssl['sha256'], 'seconds': time.monotonic() - started,
                  'sha256': {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                             for name in archives}}
        (output / 'build.json').write_text(json.dumps(record, indent=2) + '\n')
        print(f'libdatachannel {pin["version"]}: static provider built in '
              f'{record["seconds"]:.1f}s', flush=True)


def main() -> None:
    arguments = sys.argv[1:]
    if len(arguments) == 1:
        arguments = shlex.split(Path(arguments[0]).read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--openssl', type=Path, required=True)
    parser.add_argument('--platform', choices=('darwin', 'linux', 'windows'), required=True)
    parser.add_argument('--cxx', required=True)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--headers-only', action='store_true')
    parser.add_argument('flags', nargs=argparse.REMAINDER)
    build(parser.parse_args(arguments))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, OSError, KeyError, ValueError) as error:
        sys.exit(f'libdatachannel build: {error}')
