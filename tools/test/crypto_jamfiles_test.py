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
import re
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

# Cases whose outcome needs code that is not merged yet: a run without names leaves them out
# (and says so), a run that names one builds it. Each entry names what it waits for. The
# integrator empties it when the code it waits for is merged, and then rewrites the lines of those
# cases' outcome files as b2's whole output lines (a line: directive, if need be).
NOT_YET: dict[str, str] = {}

BLOCKS = {'all', 'native', 'native-linux', 'native-darwin', 'native-windows', 'wasip2', 'wasip3',
          'emscripten'}


class OutcomeError(Exception):
    """An outcome file or a case directory that does not follow the format."""


def launcher(target: str) -> Path:
    """The script the lanes run a WASI program with (tools/ci/matrix.py, wasm_lane)."""
    return harness.ROOT / f'tools/boost/asio-{target}/run.sh'


@dataclass
class Outcome:
    """What an outcome file says for one target."""
    targets: list[str] = field(default_factory=lambda: ['native'])
    succeeds: bool | None = None
    run: str | None = None
    lines: list[str] = field(default_factory=list)
    contains: list[str] = field(default_factory=list)
    # (text, allowed): no line of b2's output contains text, unless it also contains allowed
    # (none: not even then).
    forbidden: list[tuple[str, str | None]] = field(default_factory=list)
    arguments: list[str] = field(default_factory=list)


def outcome(path: Path, target: str) -> Outcome:
    """The blocks of path that apply to target on this system, read into an Outcome. Every line
    of the file is checked, whether its block applies or not, and so is the outcome that results
    when target is one the case is built for (checked)."""
    applying = {'all', target} | ({'native', 'native-' + SYSTEM} if target == 'native' else set())
    result = Outcome()
    block = None
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        where = f'{path.name}:{number}'
        if not raw.strip() or raw.startswith('#'):
            continue
        if raw.startswith('[') and raw.endswith(']'):
            block = raw[1:-1]
            if block not in BLOCKS:
                raise OutcomeError(f'{where}: no block [{block}]; the blocks are {sorted(BLOCKS)}')
            continue
        if block is None:
            raise OutcomeError(f'{where}: a line before the first [block]: {raw!r}')
        directive = re.match(r'([a-z]+(?:-[a-z]+)?):(?: |$)', raw)
        key, value = (directive.group(1), raw[directive.end():]) if directive else ('', raw)
        if key and key not in ('targets', 'build', 'run', 'arguments', 'line', 'contains',
                               'not-contains', 'same-as'):
            raise OutcomeError(f'{where}: no directive {key}: (a line of one lowercase word and '
                               f'a colon is reserved for them): {raw!r}')
        if key in ('targets', 'arguments', 'not-contains') and not value.split():
            raise OutcomeError(f'{where}: {key}: names nothing')
        if key == 'targets':
            unknown = [t for t in value.split() if t not in TOOLSETS]
            if unknown:
                raise OutcomeError(
                    f'{where}: no target {unknown}; the targets are {list(TOOLSETS)}')
        elif key == 'build' and value not in ('succeeds', 'fails'):
            raise OutcomeError(f'{where}: build: is succeeds or fails, not {value!r}')
        elif key == 'run' and not value:
            raise OutcomeError(f'{where}: run: names no program')
        if block not in applying or key == 'same-as':
            continue
        if key == 'targets':
            result.targets = value.split()
        elif key == 'build':
            result.succeeds = value == 'succeeds'
        elif key == 'run':
            result.run = value
        elif key == 'arguments':
            result.arguments += value.split()
        elif key == 'contains':
            result.contains.append(value)
        elif key == 'not-contains':
            text, separator, allowed = value.partition(' unless ')
            if not text.strip() or (separator and not allowed.strip()):
                raise OutcomeError(f'{where}: not-contains: needs a text, then ` unless <text>` '
                                   f'if any line may hold it: {raw!r}')
            result.forbidden.append((text.strip(), allowed.strip() or None))
        else:
            result.lines.append(value if key == 'line' else raw)
    if target in result.targets:
        checked(path, target, result)
    return result


def checked(path: Path, target: str, result: Outcome) -> None:
    """Raises an OutcomeError naming path and target unless result is coherent: a build is said
    to succeed or fail; a failure has lines to find and no program to run; a success that
    prints lines has a program."""
    if result.succeeds is None:
        raise OutcomeError(f'{path.name} on {target}: no build: line')
    if not result.succeeds and result.run is not None:
        raise OutcomeError(f'{path.name} on {target}: run: after build: fails')
    if result.succeeds and (result.contains or result.forbidden):
        raise OutcomeError(f'{path.name} on {target}: contains: or not-contains: after build: '
                           'succeeds')
    if not result.succeeds and not result.lines and not result.contains:
        raise OutcomeError(f'{path.name} on {target}: build: fails with no line to find')
    if result.succeeds and result.run is None and result.lines:
        raise OutcomeError(f'{path.name} on {target}: lines after build: succeeds, with no run:')


def same_as_faults(case: Path, cases: Path = CASES) -> list[str]:
    """Each `same-as: <case>/<file> <file>` of case's outcome file whose two files are not
    byte-identical: the file of another case, and case's own copy of it. A fixture's program is
    a copy, never a symbolic link (a checkout on Windows reads a link as a text file), and this
    keeps the copies from drifting."""
    faults: list[str] = []
    for number, raw in enumerate((case / f'{case.name}.outcome').read_text().splitlines(), 1):
        if not raw.startswith('same-as:'):
            continue
        names = raw[len('same-as:'):].split()
        where = f'{case.name}.outcome:{number}'
        if len(names) != 2:
            faults.append(f'{where}: same-as: names <case>/<file> and <file>, not {names}')
            continue
        original, copy = cases / names[0], case / names[1]
        if not original.is_file() or not copy.is_file():
            faults.append(f'{where}: {names[0]} or {case.name}/{names[1]} does not exist')
        elif original.read_bytes() != copy.read_bytes():
            faults.append(f'{where}: {case.name}/{names[1]} is not a copy of {names[0]}')
    return faults


def case_directories() -> list[Path]:
    """Every directory of CASES, each with its one outcome file named after it, and every
    outcome file read for every target (so each line of each block is checked), else an
    OutcomeError."""
    cases = sorted(p for p in CASES.iterdir() if p.is_dir())
    for case in cases:
        found = sorted(p.name for p in case.glob('*.outcome'))
        if found != [case.name + '.outcome']:
            raise OutcomeError(f'{case.name}: the outcome files are {found}; '
                               f'the one is {case.name}.outcome')
        if not (case / 'Jamfile').is_file():
            raise OutcomeError(f'{case.name}: no Jamfile')
        for target in TOOLSETS:
            outcome(case / f'{case.name}.outcome', target)
        faults = same_as_faults(case)
        if faults:
            raise OutcomeError('; '.join(faults))
    return cases


def program_command(build_dir: Path, case: str, name: str, target: str) -> list[str]:
    """The command that runs the program name that the build of case made under build_dir, as its
    lane runs one."""
    suffix = {'native': '.exe' if SYSTEM == 'windows' else '', 'wasip2': '.wasm',
              'wasip3': '.wasm', 'emscripten': '.js'}[target]
    found = [p for p in build_dir.rglob(name + suffix)
             if p.is_file() and f'user/{case}/' in p.relative_to(build_dir).as_posix()]
    if len(found) != 1:
        raise AssertionError(f'the build made {len(found)} files named {name}{suffix}')
    if target == 'emscripten':
        return ['node', str(found[0])]
    if target.startswith('wasi'):
        return [str(launcher(target)), str(found[0])]
    return [str(found[0])]


def selected(cases: list[Path], names: list[str], target: str) -> list[Path]:
    """The cases to build for target: the named ones, else every one that is not in NOT_YET,
    each that its outcome file's targets line names target for."""
    return [case for case in cases
            if (case.name in names if names else case.name not in NOT_YET)
            and target in outcome(case / f'{case.name}.outcome', target).targets]


def run_target(root: Path, target: str, cases: list[Path]) -> list[str]:
    """Builds each of cases for target in root and returns the faults, one line each."""
    faults: list[str] = []
    build_dir = root / 'bin' / f'user-{target}'
    for case in cases:
        expected = outcome(case / f'{case.name}.outcome', target)
        scratch = root / 'scratch' / case.name
        scratch.mkdir(parents=True, exist_ok=True)
        arguments = [a.replace('@scratch', str(scratch)) for a in expected.arguments]
        # No testing.launcher: a user's exe is run by this test, not by b2.
        built = harness.run_b2(root, '-j3', f'--build-dir={build_dir}', *TOOLSETS[target],
                               *arguments, f'user/{case.name}')
        output = built.stdout
        if (built.returncode == 0) != expected.succeeds:
            faults.append(f'{case.name} on {target}: the build '
                          f'{"succeeded" if built.returncode == 0 else "failed"}\n{output[-3000:]}')
            continue
        if not expected.succeeds:
            printed = {line.rstrip() for line in output.splitlines()}
            faults += [f'{case.name} on {target}: b2 printed no line {line!r}'
                       for line in expected.lines if line.rstrip() not in printed]
            faults += [f'{case.name} on {target}: no line of b2 contains {text!r}'
                       for text in expected.contains
                       if not any(text in line for line in printed)]
            faults += [f'{case.name} on {target}: b2 printed {line!r}, which contains {text!r}'
                       f'{"" if allowed is None else f" and not {allowed!r}"}'
                       for text, allowed in expected.forbidden for line in sorted(printed)
                       if text in line and (allowed is None or allowed not in line)]
            continue
        if expected.run is not None:
            try:
                command = program_command(build_dir, case.name, expected.run, target)
            except AssertionError as error:
                faults.append(f'{case.name} on {target}: {error}')
                continue
            ran = subprocess.run(command, capture_output=True, text=True, check=False)
            printed = ran.stdout.replace('\r\n', '\n').splitlines()
            if ran.returncode != 0 or printed != expected.lines:
                faults.append(f'{case.name} on {target}: {expected.run} exited {ran.returncode} '
                              f'and printed {printed!r}; the outcome says {expected.lines!r}')
    return faults


def main(argv: list[str]) -> int:
    targets = list(TOOLSETS)
    if '--target' in argv:
        position = argv.index('--target')
        if position + 1 >= len(argv) or argv[position + 1] not in TOOLSETS:
            print(f'crypto_jamfiles: --target takes one of {list(TOOLSETS)}', file=sys.stderr)
            return 2
        targets = [argv[position + 1]]
        argv = argv[:position] + argv[position + 2:]
    names = [a for a in argv if not a.startswith('--')]
    if len(names) != len(argv):
        print(f'crypto_jamfiles: no option {[a for a in argv if a.startswith("--")]}; '
              'the one is --target <name>', file=sys.stderr)
        return 2
    try:
        cases = case_directories()
    except OutcomeError as error:
        print(f'crypto_jamfiles: {error}', file=sys.stderr)
        return 2
    missing = [n for n in names if n not in {c.name for c in cases}]
    if missing:
        print(f'crypto_jamfiles: no case named {missing}', file=sys.stderr)
        return 2
    if not names and NOT_YET:
        for case, reason in NOT_YET.items():
            print(f'left out until {reason}: {case}')
    faults: list[str] = []
    built = 0
    for target in targets:
        chosen = selected(cases, names, target)
        if not chosen:
            continue
        built += len(chosen)
        started = time.monotonic()
        root = harness.scratch_superproject()
        try:
            harness.copy_integration_libraries(root, 'config', 'crypto')
            shutil.copytree(CASES, root / 'user', ignore=harness.built)
            if target == 'emscripten':
                harness.link_emsdk(root)
            elif target.startswith('wasi'):
                harness.link_wasi_tools(root)
            faults += run_target(root, target, chosen)
        finally:
            shutil.rmtree(root)
        print(f'{target}: done in {time.monotonic() - started:.0f} s')
    if not built:
        faults.append(f'no case was built for {targets}; nothing was tested')
    for fault in faults:
        print(f'crypto_jamfiles: {fault}', file=sys.stderr)
    print('crypto_jamfiles_test: ' + ('failed' if faults else 'ok'))
    return 1 if faults else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
