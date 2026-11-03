#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Build and run local OpenSSL integration profiles; never starts CI.

Requires B2's user config, Python with TLS 1.3, and an OpenSSL 3 CLI solely for
fresh server certificates. WASMTIME selects a runtime supporting WASIp3 threads.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--profile', choices=('all', 'native', 'wasi'), default='all')
parser.add_argument('--user-config', type=Path, default=ROOT / '.local/user-config.jam')
parser.add_argument('--fresh', action='store_true')
args = parser.parse_args()
env = os.environ.copy()
for key in ('CPATH', 'CPLUS_INCLUDE_PATH', 'C_INCLUDE_PATH'):
    env.pop(key, None)
records = []
output = ROOT / '.local/openssl-integration'
output.mkdir(parents=True, exist_ok=True)


def run(command, timeout=90):
    print('+ ' + shlex.join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), cwd=ROOT, env=env, check=True, timeout=timeout)


for target, threads, exceptions in (
        ('native', 'single', 'on'), ('native', 'single', 'off'),
        ('native', 'multi', 'on'), ('native', 'multi', 'off'),
        ('wasi', 'single', 'on'), ('wasi', 'single', 'off'),
        ('wasi', 'multi', 'off')):
    if args.profile not in ('all', target):
        continue
    profile = f'{target}-{threads}-eh-{exceptions}'
    directory = output / profile
    options = ['b2', '--user-config=' + str(args.user_config.resolve()),
               '--build-dir=' + str(directory),
               'toolset=' + ('clang' if target == 'native' else 'clang-wasip3'),
               'variant=release', 'threading=' + threads, 'exception-handling=' + exceptions]
    if args.fresh:
        options.append('-a')
    names = ['tls_client']
    if target == 'wasi':
        names.append('entropy')
    if threads == 'multi':
        names.append('threads')
    started = time.monotonic()
    run(options + ['tools/openssl/test//' + name for name in names], timeout=600)
    build_seconds = time.monotonic() - started
    suffix = '.wasm' if target == 'wasi' else ''
    programs = {}
    for name in names:
        matches = list(directory.rglob(name + suffix))
        if len(matches) != 1:
            raise RuntimeError(f'expected one {name} binary, found {matches}')
        programs[name] = matches[0]
    run([sys.executable, HERE / 'tls.py', programs['tls_client']], timeout=180)
    launcher = [] if target == 'native' else [env.get('WASMTIME', 'wasmtime'), 'run',
        '-S', 'p3', '-W', 'component-model-async=y', '-W', 'component-model-threading=y',
        '-W', 'timeout=15s']
    if 'entropy' in programs:
        for _ in range(3):
            run(launcher + [programs['entropy']])
        run(launcher + [programs['entropy'], 'fail-entropy'])
    if 'threads' in programs:
        run(launcher + [programs['threads']])
    if target == 'native' and sys.platform == 'darwin':
        linked = subprocess.check_output(['otool', '-L', str(programs['tls_client'])], text=True)
        if any(name in linked for name in ('libssl', 'libcrypto')):
            raise RuntimeError('client linked a host OpenSSL dynamic library: ' + linked)
        print(linked, flush=True)
    records.append({'profile': profile, 'build_seconds': build_seconds,
                    'programs': {key: str(value) for key, value in programs.items()},
                    'tls_cases': 6, 'entropy_cases': 4 if target == 'wasi' else 0,
                    'thread_case': threads == 'multi', 'passed': True})
    (output / (args.profile + '-results.json')).write_text(json.dumps(records, indent=2) + '\n')
    print('PASS ' + profile, flush=True)
