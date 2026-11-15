#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Builds every fixture of tools/test/fixtures/hash_jamfiles, a Jamfile as a user of webcpp::hash
writes it (b2's raw exe), with b2 as a user runs it, and checks its outcome file: the build's
status, the lines a failure prints, and a program's output (CODING-GUIDELINES.md chapter 8). The
cases are each line of the library's spec 5.1, one program with every C library, and each stop of
the build: the canaries at link time on every target, and the messages raised on Emscripten.

The outcome files, their format and the build of a case are crypto_jamfiles_test.py's, read
through it: one scratch superproject per target, with libs/config, libs/hash, libs/crypto (whose
canary /third_party//bearssl compiles) and the fixtures in it; every case of a target shares one
build directory, so each C library is compiled once per target. Run with the names of some cases
to run only those, and with --target <name> to run one target."""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

import crypto_jamfiles_test as jamfiles
import harness

CASES = harness.FIXTURES / 'hash_jamfiles'

# Cases whose outcome needs code that is not merged yet, as crypto_jamfiles_test.py's NOT_YET:
# a run without names leaves them out (and says so), a run that names one builds it.
NOT_YET: dict[str, str] = {}


def case_directories() -> list[Path]:
    """Every directory of CASES, each with its one outcome file named after it and a Jamfile,
    and every outcome file read for every target, else a jamfiles.OutcomeError."""
    cases = sorted(p for p in CASES.iterdir() if p.is_dir())
    for case in cases:
        found = sorted(p.name for p in case.glob('*.outcome'))
        if found != [case.name + '.outcome']:
            raise jamfiles.OutcomeError(f'{case.name}: the outcome files are {found}; '
                                        f'the one is {case.name}.outcome')
        if not (case / 'Jamfile').is_file():
            raise jamfiles.OutcomeError(f'{case.name}: no Jamfile')
        for target in jamfiles.TOOLSETS:
            jamfiles.outcome(case / f'{case.name}.outcome', target)
    return cases


def selected(cases: list[Path], names: list[str], target: str) -> list[Path]:
    """The cases to build for target: the named ones, else every one that is not in NOT_YET,
    each that its outcome file's targets line names target for."""
    return [case for case in cases
            if (case.name in names if names else case.name not in NOT_YET)
            and target in jamfiles.outcome(case / f'{case.name}.outcome', target).targets]


def main(argv: list[str]) -> int:
    targets = list(jamfiles.TOOLSETS)
    if '--target' in argv:
        position = argv.index('--target')
        if position + 1 >= len(argv) or argv[position + 1] not in jamfiles.TOOLSETS:
            print(f'hash_jamfiles: --target takes one of {targets}', file=sys.stderr)
            return 2
        targets = [argv[position + 1]]
        argv = argv[:position] + argv[position + 2:]
    names = [a for a in argv if not a.startswith('--')]
    if len(names) != len(argv):
        print(f'hash_jamfiles: no option {[a for a in argv if a.startswith("--")]}; '
              'the one is --target <name>', file=sys.stderr)
        return 2
    try:
        cases = case_directories()
    except jamfiles.OutcomeError as error:
        print(f'hash_jamfiles: {error}', file=sys.stderr)
        return 2
    missing = [n for n in names if n not in {c.name for c in cases}]
    if missing:
        print(f'hash_jamfiles: no case named {missing}', file=sys.stderr)
        return 2
    if not names:
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
            harness.copy_integration_libraries(root, 'config', 'hash', 'crypto')
            shutil.copytree(CASES, root / 'user', ignore=harness.built)
            if target == 'emscripten':
                harness.link_emsdk(root)
            elif target.startswith('wasi'):
                harness.link_wasi_tools(root)
            faults += jamfiles.run_target(root, target, chosen)
        finally:
            shutil.rmtree(root)
        print(f'{target}: {len(chosen)} cases in {time.monotonic() - started:.0f} s')
    if not built:
        faults.append(f'no case was built for {targets}; nothing was tested')
    for fault in faults:
        print(f'hash_jamfiles: {fault}', file=sys.stderr)
    print('hash_jamfiles_test: ' + ('failed' if faults else 'ok'))
    return 1 if faults else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
