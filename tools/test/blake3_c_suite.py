#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Runs BLAKE3's own C test on webcpp's build of BLAKE3, on every target.

BLAKE3's c/test.py runs c/blake3, a program built inside the submodule, where webcpp builds
nothing; and a library's test Jamfile may not declare b2's raw exe. So this test of the tools
builds the fixture tools/test/fixtures/blake3_c_suite, c/main.c linked with /third_party//blake3
(with BLAKE3_TESTING, so that one run checks each instruction set the machine has), on a scratch
superproject for each target, and runs it over every case of test_vectors/test_vectors.json as
c/test.py does: the input of a case is i % 251 for each i below input_len, on standard input;
the program runs with no argument, with --length <n>, with --keyed <hex of the key> and with
--derive-key <context>, each also with the output's whole length, and every line it prints is
compared with the file's. Natively the program runs directly, on wasip2 and wasip3 through
tools/boost/asio-wasip<n>/run.sh, on Emscripten through node. It prints
"blake3 c suite: <target>: <n> cases ok" per target, or the first difference, and exits non-zero
on a difference. Run with --target <name> to run one target."""

from __future__ import annotations

import concurrent.futures
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import harness

FIXTURE = 'tools/test/fixtures/blake3_c_suite'
VECTORS = harness.ROOT / 'third_party/libs/blake3/test_vectors/test_vectors.json'
TOOLSETS = {'native': [], 'wasip2': ['toolset=clang-wasip2'], 'wasip3': ['toolset=clang-wasip3'],
            'emscripten': ['toolset=emscripten']}
WINDOWS = platform.system() == 'Windows'

# The programs of a target run at once, each a process of its own.
WORKERS = 8


class Difference(Exception):
    """A line the program printed that is not the file's, or a run that failed."""


def node() -> str:
    """The node the emscripten toolset of user-config.jam runs, this checkout's
    .local/emscripten/node, else the one on PATH."""
    local = harness.ROOT / '.local/emscripten/node'
    return str(local) if local.exists() else 'node'


def program_command(build_dir: Path, target: str) -> list[str]:
    """The command that runs blake3_main, which the build made under build_dir, as its lane runs
    a program."""
    suffix = {'native': '.exe' if WINDOWS else '', 'wasip2': '.wasm', 'wasip3': '.wasm',
              'emscripten': '.js'}[target]
    found = [p for p in build_dir.rglob('blake3_main' + suffix) if p.is_file()]
    if len(found) != 1:
        raise AssertionError(f'the build made {len(found)} files named blake3_main{suffix}')
    if target == 'emscripten':
        return [node(), str(found[0])]
    if target.startswith('wasi'):
        return [str(harness.ROOT / f'tools/boost/asio-{target}/run.sh'), str(found[0])]
    return [str(found[0])]


def make_input(length: int) -> bytes:
    """c/test.py's input: the bytes i % 251 for each i below length."""
    return bytes(i % 251 for i in range(length))


def runs(vectors: dict) -> list[tuple[str, list[str], bytes, str]]:
    """Every run of the suite, c/test.py's six per case: its name, the program's arguments, its
    input, and the line each of its output lines must equal."""
    key = vectors['key'].encode().hex()
    context = vectors['context_string']
    result = []
    for case in vectors['cases']:
        length = case['input_len']
        data = make_input(length)
        for mode, arguments in (('hash', []), ('keyed_hash', ['--keyed', key]),
                                ('derive_key', ['--derive-key', context])):
            expected = case[mode]
            result.append((f'{mode}({length})', arguments, data, expected[:64]))
            result.append((f'{mode}_xof({length})',
                           arguments + ['--length', str(len(expected) // 2)], data, expected))
    return result


def run_one(command: list[str], name: str, arguments: list[str], data: bytes,
            expected: str) -> None:
    """Runs the program once and raises Difference unless it succeeds and every line it prints
    is expected."""
    ran = subprocess.run(command + arguments, input=data, capture_output=True, check=False)
    if ran.returncode != 0:
        raise Difference(f'{name}: {" ".join(arguments)} exited {ran.returncode}: '
                         f'{ran.stderr.decode(errors="replace")[-2000:]}')
    lines = ran.stdout.decode(errors='replace').split()
    if not lines:
        raise Difference(f'{name}: {" ".join(arguments)} printed nothing')
    for line in lines:
        if line != expected:
            raise Difference(f'{name}: {expected} != {line}')


def run_target(target: str, vectors: dict) -> int:
    """Builds the fixture for target on a scratch superproject, runs the suite with it and returns
    the number of cases; raises Difference at the first difference."""
    root = harness.scratch_superproject()
    try:
        harness.copy_integration_libraries(root, 'config', 'hash')
        if target == 'emscripten':
            harness.link_emsdk(root)
        elif target.startswith('wasi'):
            harness.link_wasi_tools(root)
        build_dir = root / 'bin' / f'blake3-{target}'
        built = harness.run_b2(root, '-j4', f'--build-dir={build_dir}', *TOOLSETS[target],
                               FIXTURE)
        if built.returncode != 0:
            raise Difference(f'the build failed:\n{built.stdout[-4000:]}')
        command = program_command(build_dir, target)
        with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
            futures = [pool.submit(run_one, command, *run) for run in runs(vectors)]
            for future in futures:
                future.result()
        return len(vectors['cases'])
    finally:
        shutil.rmtree(root)


def main(argv: list[str]) -> int:
    targets = list(TOOLSETS)
    if argv:
        if len(argv) != 2 or argv[0] != '--target' or argv[1] not in TOOLSETS:
            print(f'blake3 c suite: the one option is --target <one of {list(TOOLSETS)}>',
                  file=sys.stderr)
            return 2
        targets = [argv[1]]
    vectors = json.loads(VECTORS.read_text())
    for target in targets:
        try:
            cases = run_target(target, vectors)
        except Difference as difference:
            print(f'blake3 c suite: {target}: {difference}')
            return 1
        print(f'blake3 c suite: {target}: {cases} cases ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
