# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""The user's Jamfiles as fixtures (CODING-GUIDELINES.md chapter 8), shared by
crypto_jamfiles_test.py and hash_jamfiles_test.py: the outcome file's format, the build of a
case with b2 as a user runs it, the run of its program, and the command line of a test.

A test names its directory of cases under tools/test/fixtures, the libraries of libs/ its
scratch superproject holds, and the cases it leaves out until code they need is merged. Each
target gets one scratch superproject, with those libraries and the cases in its user/; every case
of a target shares one build directory, so each C library is compiled once per target."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import harness

TOOLSETS = {'native': [], 'wasip2': ['toolset=clang-wasip2'], 'wasip3': ['toolset=clang-wasip3'],
            'emscripten': ['toolset=emscripten']}
SYSTEM = {'Linux': 'linux', 'Darwin': 'darwin', 'Windows': 'windows'}[platform.system()]
# The machine's architecture, as a native block names it.
ARCHITECTURE = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x86_64',
                'amd64': 'x86_64'}.get(platform.machine().lower(), platform.machine().lower())

BLOCKS = {'all', 'native', 'native-linux', 'native-darwin', 'native-windows', 'native-arm64',
          'native-x86_64', 'wasip2', 'wasip3', 'emscripten'}


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
    applying = {'all', target} | ({'native', 'native-' + SYSTEM, 'native-' + ARCHITECTURE}
                                  if target == 'native' else set())
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


def same_as_faults(case: Path, cases_directory: Path) -> list[str]:
    """Each `same-as: <case>/<file> <file>` of case's outcome file whose two files are not
    byte-identical: the file of another case of cases_directory, and case's own copy of it. A
    fixture's program is a copy, never a symbolic link (a checkout on Windows reads a link as a
    text file), and this keeps the copies from drifting."""
    faults: list[str] = []
    for number, raw in enumerate((case / f'{case.name}.outcome').read_text().splitlines(), 1):
        if not raw.startswith('same-as:'):
            continue
        names = raw[len('same-as:'):].split()
        where = f'{case.name}.outcome:{number}'
        if len(names) != 2:
            faults.append(f'{where}: same-as: names <case>/<file> and <file>, not {names}')
            continue
        original, copy = cases_directory / names[0], case / names[1]
        if not original.is_file() or not copy.is_file():
            faults.append(f'{where}: {names[0]} or {case.name}/{names[1]} does not exist')
        elif original.read_bytes() != copy.read_bytes():
            faults.append(f'{where}: {case.name}/{names[1]} is not a copy of {names[0]}')
    return faults


def case_directories(cases_directory: Path) -> list[Path]:
    """Every directory of cases_directory, each with its one outcome file named after it, and
    every outcome file read for every target (so each line of each block is checked), else an
    OutcomeError."""
    cases = sorted(p for p in cases_directory.iterdir() if p.is_dir())
    for case in cases:
        found = sorted(p.name for p in case.glob('*.outcome'))
        if found != [case.name + '.outcome']:
            raise OutcomeError(f'{case.name}: the outcome files are {found}; '
                               f'the one is {case.name}.outcome')
        if not (case / 'Jamfile').is_file():
            raise OutcomeError(f'{case.name}: no Jamfile')
        for target in TOOLSETS:
            outcome(case / f'{case.name}.outcome', target)
        faults = same_as_faults(case, cases_directory)
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


def selected(cases: list[Path], names: list[str], target: str,
             not_yet: dict[str, str]) -> list[Path]:
    """The cases to build for target: the named ones, else every one that is not in not_yet,
    each that its outcome file's targets line names target for."""
    return [case for case in cases
            if (case.name in names if names else case.name not in not_yet)
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


def main(label: str, cases_directory: Path, libraries: tuple[str, ...],
         not_yet: dict[str, str], argv: list[str],
         check: Callable[[list[Path]], list[str]] | None = None) -> int:
    """The command line of a test of label: [--target <name>] [case ...]. It builds the cases of
    cases_directory in scratch superprojects that hold libs/<library> for each of libraries, and
    prints `<label>_test: ok` or each fault and `<label>_test: failed`. check, given the cases,
    returns the faults found without b2, before any build."""
    targets = list(TOOLSETS)
    if '--target' in argv:
        position = argv.index('--target')
        if position + 1 >= len(argv) or argv[position + 1] not in TOOLSETS:
            print(f'{label}: --target takes one of {list(TOOLSETS)}', file=sys.stderr)
            return 2
        targets = [argv[position + 1]]
        argv = argv[:position] + argv[position + 2:]
    names = [a for a in argv if not a.startswith('--')]
    if len(names) != len(argv):
        print(f'{label}: no option {[a for a in argv if a.startswith("--")]}; '
              'the one is --target <name>', file=sys.stderr)
        return 2
    absent = [name for name in libraries
              if not (harness.ROOT / 'libs' / name / 'build.jam').is_file()]
    if absent:
        for name in absent:
            print(f'{label}: libs/{name} is not checked out: it holds no build.jam. Check it out '
                  f'with `git submodule update --init libs/{name}`.', file=sys.stderr)
        return 2
    try:
        cases = case_directories(cases_directory)
    except OutcomeError as error:
        print(f'{label}: {error}', file=sys.stderr)
        return 2
    missing = [n for n in names if n not in {c.name for c in cases}]
    if missing:
        print(f'{label}: no case named {missing}', file=sys.stderr)
        return 2
    faults: list[str] = check(cases) if check is not None else []
    if not names:
        for case, reason in not_yet.items():
            print(f'left out until {reason}: {case}')
    built = 0
    for target in targets if not faults else []:
        chosen = selected(cases, names, target, not_yet)
        if not chosen:
            continue
        built += len(chosen)
        started = time.monotonic()
        root = harness.scratch_superproject()
        try:
            harness.copy_integration_libraries(root, *libraries)
            shutil.copytree(cases_directory, root / 'user', ignore=harness.built)
            if target == 'emscripten':
                harness.link_emsdk(root)
            elif target.startswith('wasi'):
                harness.link_wasi_tools(root)
            faults += run_target(root, target, chosen)
        finally:
            shutil.rmtree(root)
        print(f'{target}: {len(chosen)} cases in {time.monotonic() - started:.0f} s')
    if not built and not faults:
        faults.append(f'no case was built for {targets}; nothing was tested')
    for fault in faults:
        print(f'{label}: {fault}', file=sys.stderr)
    print(f'{label}_test: ' + ('failed' if faults else 'ok'))
    return 1 if faults else 0
