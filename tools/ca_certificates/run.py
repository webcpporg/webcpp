#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Run the embedded-trust Release matrix locally, without CI or CA file mounts."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('all', 'native', 'wasi'), default='all')
    parser.add_argument('--user-config', type=Path, help='B2 user-config.jam override')
    parser.add_argument('--fresh', action='store_true')
    args = parser.parse_args()
    env = os.environ.copy()
    for key in ('CPATH', 'CPLUS_INCLUDE_PATH', 'C_INCLUDE_PATH'):
        env.pop(key, None)
    records = []
    directory = ROOT / '.local/ca-integration'
    directory.mkdir(exist_ok=True)
    for target, threads, exceptions in (
            ('native', 'single', 'on'), ('native', 'single', 'off'),
            ('native', 'multi', 'on'), ('native', 'multi', 'off'),
            ('wasi', 'single', 'on'), ('wasi', 'single', 'off'),
            ('wasi', 'multi', 'off')):
        if args.profile not in ('all', target):
            continue
        name = f'{target}-{threads}-eh-{exceptions}'
        build = directory / name
        command = ['b2', '--build-dir=' + str(build), 'variant=release',
                   'toolset=' + ('clang-wasip3' if target == 'wasi' else 'clang'),
                   'threading=' + threads, 'exception-handling=' + exceptions,
                   'tools/openssl/test//tls_client_embedded',
                   'libs/asio/test//tls_client_context']
        config = args.user_config or ROOT / '.local/user-config.jam'
        if args.user_config or config.is_file():
            command.append('--user-config=' + str(config.resolve()))
        if args.fresh:
            command.append('-a')
        if target == 'wasi':
            launcher = env.get('WASMTIME', 'wasmtime')
            command.append('testing.launcher=' + launcher + ' run -S p3'
                           ' -W component-model-async=y -W component-model-threading=y'
                           ' -W timeout=15s')
        print('+ ' + shlex.join(command), flush=True)
        subprocess.run(command, cwd=ROOT, env=env, check=True, timeout=600)
        suffix = '.wasm' if target == 'wasi' else ''
        binaries = list(build.rglob('tls_client_embedded' + suffix))
        if len(binaries) != 1:
            raise RuntimeError(f'expected one embedded TLS client, found {binaries}')
        command = [sys.executable, str(ROOT / 'tools/openssl/test/tls.py'),
                   str(binaries[0]), '--embedded']
        print('+ ' + shlex.join(command), flush=True)
        subprocess.run(command, cwd=ROOT, env=env, check=True, timeout=180)
        records.append({'profile': name, 'tls_cases': 8, 'malformed_der_cases': 2, 'passed': True})
        (directory / (args.profile + '-results.json')).write_text(
            json.dumps(records, indent=2) + '\n')
        print('PASS ' + name, flush=True)


if __name__ == '__main__':
    main()
