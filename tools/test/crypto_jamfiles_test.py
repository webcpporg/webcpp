#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Builds every fixture of tools/test/fixtures/crypto_jamfiles, a Jamfile as a user of
webcpp::crypto writes it (b2's raw exe), with b2 as a user runs it, and checks its outcome file:
the build's status, the lines a failure prints, and a program's output (CODING-GUIDELINES.md
chapter 8). One scratch superproject per target, with libs/crypto and the fixtures in it; every
case of a target shares one build directory, so BearSSL's 295 files are compiled once per
target. Run with the names of some cases to run only those, and with --target <name> to run one
target."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import harness

CASES = harness.FIXTURES / 'crypto_jamfiles'
TOOLSETS = {'native': [], 'wasip2': ['toolset=clang-wasip2'], 'wasip3': ['toolset=clang-wasip3'],
            'emscripten': ['toolset=emscripten']}
SYSTEM = {'Linux': 'linux', 'Darwin': 'darwin', 'Windows': 'windows'}[platform.system()]

# Cases whose outcome needs code that is not merged yet; a run without names leaves them out,
# a run that names one builds it. Each entry names what it waits for.
NOT_YET = {
    'has_openssl_on_emscripten': 'the refusal in config.hpp (Task 6)',
    'default_openssl_on_emscripten': 'the refusal in config.hpp (Task 6)',
}


def launcher(target: str) -> Path:
    """The script the lanes run a WASI program with (tools/ci/matrix.py, wasm_lane)."""
    return harness.ROOT / f'tools/boost/asio-{target}/run.sh'


@dataclass
class Outcome:
    """What an outcome file says for one target."""
    targets: list[str] = field(default_factory=lambda: ['native'])
    succeeds: bool = True
    run: str | None = None
    lines: list[str] = field(default_factory=list)
    arguments: list[str] = field(default_factory=list)


def outcome(path: Path, target: str) -> Outcome:
    """The blocks of path that apply to target on this system, read into an Outcome."""
    applying = {'all', target} | ({'native', 'native-' + SYSTEM} if target == 'native' else set())
    result = Outcome()
    block = None
    for raw in path.read_text().splitlines():
        if not raw.strip() or raw.startswith('#'):
            continue
        if raw.startswith('[') and raw.endswith(']'):
            block = raw[1:-1]
            continue
        if block is None:
            raise SystemExit(f'{path}: a line before the first [block]: {raw!r}')
        if block not in applying:
            continue
        key, _, value = raw.partition(': ')
        if key == 'targets':
            result.targets = value.split()
        elif key == 'build':
            result.succeeds = value == 'succeeds'
        elif key == 'run':
            result.run = value
        elif key == 'arguments':
            result.arguments += value.split()
        else:
            result.lines.append(raw)
    return result


def program_command(build_dir: Path, case: str, name: str, target: str) -> list[str]:
    """The command that runs the program name that the build of case made under build_dir, as its
    lane runs one."""
    suffix = {'native': '.exe' if SYSTEM == 'windows' else '', 'wasip2': '.wasm',
              'wasip3': '.wasm', 'emscripten': '.js'}[target]
    found = [p for p in build_dir.rglob(name + suffix)
             if p.is_file() and f'user/{case}/' in p.relative_to(build_dir).as_posix() + '/']
    if len(found) != 1:
        raise AssertionError(f'the build made {len(found)} files named {name}{suffix}')
    if target == 'emscripten':
        return ['node', str(found[0])]
    if target.startswith('wasi'):
        return [str(launcher(target)), str(found[0])]
    return [str(found[0])]


def selected(names: list[str], target: str) -> list[Path]:
    """The case directories to build for target: the named ones, else every one that is not in
    NOT_YET, each that its outcome file's targets line names target for."""
    cases = []
    for case in sorted(p.parent for p in CASES.glob('*/*.outcome')):
        if (names and case.name not in names) or (not names and case.name in NOT_YET):
            continue
        if target in outcome(next(case.glob('*.outcome')), target).targets:
            cases.append(case)
    return cases


def run_target(root: Path, target: str, cases: list[Path]) -> list[str]:
    """Builds each of cases for target in root and returns the faults, one line each."""
    faults: list[str] = []
    build_dir = root / 'bin' / f'user-{target}'
    for case in cases:
        expected = outcome(next(case.glob('*.outcome')), target)
        scratch = root / 'scratch' / case.name
        scratch.mkdir(parents=True, exist_ok=True)
        arguments = [a.replace('@scratch', str(scratch)) for a in expected.arguments]
        launch = [f'testing.launcher={launcher(target)}'] if target.startswith('wasi') else []
        built = harness.run_b2(root, f'--build-dir={build_dir}', *TOOLSETS[target], *launch,
                               *arguments, f'user/{case.name}')
        output = built.stdout
        if (built.returncode == 0) != expected.succeeds:
            faults.append(f'{case.name} on {target}: the build '
                          f'{"succeeded" if built.returncode == 0 else "failed"}\n{output[-3000:]}')
            continue
        if not expected.succeeds:
            faults += [f'{case.name} on {target}: b2 did not print: {line}'
                       for line in expected.lines if line not in output]
            continue
        if expected.run is not None:
            command = program_command(build_dir, case.name, expected.run, target)
            ran = subprocess.run(command, capture_output=True, text=True, check=False)
            printed = ran.stdout.replace('\r\n', '\n').splitlines()
            if ran.returncode != 0 or printed != expected.lines:
                faults.append(f'{case.name} on {target}: {expected.run} exited {ran.returncode} '
                              f'and printed {printed!r}; the outcome says {expected.lines!r}')
    return faults


def main(argv: list[str]) -> int:
    targets = list(TOOLSETS)
    if '--target' in argv:
        targets = [argv[argv.index('--target') + 1]]
        argv = [a for a in argv if a not in ('--target', targets[0])]
        if targets[0] not in TOOLSETS:
            raise SystemExit(f'crypto_jamfiles: no target {targets[0]}; '
                             f'the targets are {list(TOOLSETS)}')
    names = [a for a in argv if not a.startswith('--')]
    faults: list[str] = []
    for target in targets:
        cases = selected(names, target)
        if not cases:
            continue
        started = time.monotonic()
        root = harness.scratch_superproject()
        try:
            harness.copy_integration_libraries(root, 'crypto')
            shutil.copytree(CASES, root / 'user', ignore=harness.built)
            if target == 'emscripten':
                harness.link_emsdk(root)
            elif target.startswith('wasi'):
                harness.link_wasi_tools(root)
            faults += run_target(root, target, cases)
        finally:
            shutil.rmtree(root)
        print(f'{target}: done in {time.monotonic() - started:.0f} s')
    for fault in faults:
        print(f'crypto_jamfiles: {fault}', file=sys.stderr)
    print('crypto_jamfiles_test: ' + ('failed' if faults else 'ok'))
    return 1 if faults else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
