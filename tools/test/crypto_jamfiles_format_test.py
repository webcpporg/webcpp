#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks the rules of user_jamfiles.py, which crypto_jamfiles_test.py and hash_jamfiles_test.py
share, without building anything: what an outcome file may say, what a run that builds nothing
is, and how a failure's lines are matched (whole lines).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import crypto_jamfiles_test
import harness
import user_jamfiles as jamfiles

TEST = Path(__file__).resolve().parent / 'crypto_jamfiles_test.py'


def parse(text: str, target: str = 'native') -> jamfiles.Outcome:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'case.outcome'
        path.write_text(text)
        return jamfiles.outcome(path, target)


def refused(text: str, *words: str) -> None:
    try:
        parse(text)
    except jamfiles.OutcomeError as error:
        assert all(word in str(error) for word in words), (text, str(error))
        return
    raise AssertionError(f'accepted: {text!r}')


def test_a_good_outcome_is_read():
    result = parse('[all]\ntargets: native wasip2\nbuild: succeeds\nrun: app\nok\n'
                   '[wasip3]\nwasip3 only\n')
    assert (result.targets, result.succeeds, result.run, result.lines) == (
        ['native', 'wasip2'], True, 'app', ['ok']), result
    assert parse('[all]\nbuild: succeeds\nrun: app\nok\n[native]\nnative\n').lines == [
        'ok', 'native']


def test_the_format_is_enforced():
    refused('[everything]\nbuild: fails\nx\n', 'no block')
    refused('build: fails\nx\n', 'before the first')
    refused('[all]\nbuild: succeed\n', 'succeeds or fails')
    refused('[all]\nbuild: fails\nx\nrun: app\n', 'run: after build: fails')
    refused('[all]\nbuild: succeeds\nx\n', 'no run:')
    refused('[all]\nbuild: fails\n', 'no line to find')
    refused('[all]\nrun: app\nx\n', 'no build:')
    refused('[all]\ntargets: native vax\nbuild: fails\nx\n', 'no target')
    refused('[all]\nbuild: fails\nx\nargument: y\n', 'no directive')
    refused('[wasip3]\nbuilds: fails\n[all]\nbuild: fails\nx\n', 'no directive')


def test_line_states_a_literal_output_line():
    lines = parse('[all]\nbuild: fails\nline: error: x\nline:\nline: # c\nline: [x]\n'
                  'line: line: y\n').lines
    assert lines == ['error: x', '', '# c', '[x]', 'line: y'], lines
    refused('[all]\nbuild: fails\nerror: x\n', 'no directive')


def test_a_leftover_option_is_a_usage_error():
    for arguments in (['--targt', 'hello'], ['--target', 'native', '--target', 'native']):
        result = run(*arguments)
        assert result.returncode == 2, (arguments, result)


def test_contains_matches_part_of_a_line():
    assert parse('[all]\nbuild: fails\ncontains: part\n').contains == ['part']
    refused('[all]\nbuild: succeeds\nrun: app\ncontains: x\n', 'contains:')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        case = root / 'c'
        case.mkdir()
        original = harness.run_b2
        harness.run_b2 = lambda *_a, **_k: subprocess.CompletedProcess(
            [], 1, '/some/path/c.cpp:7:2: error: "boom"\n')
        try:
            for text, faults in (('boom', 0), ('/other', 1)):
                (case / 'c.outcome').write_text(f'[all]\nbuild: fails\ncontains: {text}\n')
                assert len(jamfiles.run_target(root, 'native', [case])) == faults, text
        finally:
            harness.run_b2 = original


def test_not_contains_forbids_a_text_in_every_line():
    assert parse('[all]\nbuild: fails\ncontains: a\nnot-contains: b\n'
                 'not-contains: c unless d\n').forbidden == [('b', None), ('c', 'd')]
    refused('[all]\nbuild: succeeds\nrun: app\nnot-contains: x\n', 'not-contains:')
    refused('[all]\nbuild: fails\ncontains: a\nnot-contains:\n', 'names nothing')
    refused('[all]\nbuild: fails\ncontains: a\nnot-contains: x unless \n', 'unless')
    refused('[all]\nbuild: fails\nnot-contains: x\n', 'no line to find')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        case = root / 'c'
        case.mkdir()
        original = harness.run_b2
        harness.run_b2 = lambda *_a, **_k: subprocess.CompletedProcess(
            [], 1, 'undefined reference to `canary\'\nundefined reference to `other\'\n')
        try:
            for directive, faults in (('not-contains: unrelated', 0),
                                      ('not-contains: undefined reference unless canary', 1),
                                      ('not-contains: undefined reference unless canary or other',
                                       2),
                                      ('not-contains: reference to `other', 1),
                                      ('not-contains: undefined reference', 2)):
                (case / 'c.outcome').write_text(
                    f'[all]\nbuild: fails\ncontains: canary\n{directive}\n')
                found = jamfiles.run_target(root, 'native', [case])
                assert len(found) == faults, (directive, found)
        finally:
            harness.run_b2 = original


def test_same_as_keeps_copies_identical():
    with tempfile.TemporaryDirectory() as directory:
        cases = Path(directory)
        (cases / 'a').mkdir()
        (cases / 'b').mkdir()
        (cases / 'a' / 'app.cpp').write_text('int main() {}\n')
        (cases / 'b' / 'app.cpp').write_text('int main() {}\n')
        outcome = cases / 'b' / 'b.outcome'
        outcome.write_text('[all]\nsame-as: a/app.cpp app.cpp\nbuild: succeeds\n')
        assert jamfiles.same_as_faults(cases / 'b', cases) == []
        (cases / 'b' / 'app.cpp').write_text('int main() { return 1; }\n')
        faults = jamfiles.same_as_faults(cases / 'b', cases)
        assert len(faults) == 1 and 'a/app.cpp' in faults[0], faults
        outcome.write_text('[all]\nsame-as: a/missing.cpp app.cpp\nbuild: succeeds\n')
        assert jamfiles.same_as_faults(cases / 'b', cases), 'a missing copy is a fault'
        outcome.write_text('[all]\nsame-as: a/app.cpp\nbuild: succeeds\n')
        assert jamfiles.same_as_faults(cases / 'b', cases), 'one name is a fault'
    assert parse('[all]\nsame-as: a/app.cpp app.cpp\nbuild: succeeds\n').succeeds


def test_a_native_block_applies_by_architecture():
    text = ('[all]\nbuild: fails\n[native-arm64]\ncontains: arm\n'
            '[native-x86_64]\ncontains: x86\n')
    expected = {'arm64': ['arm'], 'x86_64': ['x86']}.get(jamfiles.ARCHITECTURE, [])
    assert parse(text).contains == expected, (jamfiles.ARCHITECTURE, parse(text))
    assert parse('[all]\ntargets: wasip2\nbuild: fails\nx\n[native-arm64]\ncontains: arm\n',
                 'wasip2').contains == []


def test_a_library_not_checked_out_is_named():
    result = subprocess.run(
        [sys.executable, '-c', 'import sys, user_jamfiles; sys.exit(user_jamfiles.main('
         '"t", user_jamfiles.harness.FIXTURES, ("no_such_library",), {}, []))'],
        capture_output=True, text=True, check=False, cwd=TEST.parent)
    assert result.returncode == 2, result
    assert ('libs/no_such_library is not checked out' in result.stderr
            and 'git submodule update --init libs/no_such_library' in result.stderr), result


def test_every_case_directory_is_read():
    cases = jamfiles.case_directories(crypto_jamfiles_test.CASES)
    assert {c.name for c in cases} >= {'hello', 'broken'}, cases


def run(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TEST), *arguments], capture_output=True,
                          text=True, check=False)


def test_a_run_that_builds_nothing_fails():
    unknown = run('nonexistent_case')
    assert unknown.returncode != 0 and 'no case named' in unknown.stderr, unknown
    nothing = run('--target', 'wasip3', 'hello')
    assert nothing.returncode != 0 and 'nothing was tested' in nothing.stderr, nothing
    assert run('--target').returncode == 2
    assert run('--target', 'vax').returncode == 2


def test_a_failure_line_is_matched_whole():
    printed = ['user/c/c.cpp:7:2: error: "boom"', '    7 | #error "boom"   ']
    original = harness.run_b2

    def fake(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 1, '\n'.join(printed) + '\n')

    harness.run_b2 = fake
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / 'c'
            case.mkdir()
            for line, faults in (('    7 | #error "boom"', 0), ('"boom"', 1),
                                 ('7:2: error: "boom"', 1)):
                (case / 'c.outcome').write_text(f'[all]\nbuild: fails\n{line}\n')
                assert len(jamfiles.run_target(root, 'native', [case])) == faults, line
    finally:
        harness.run_b2 = original


def main() -> int:
    for name, case in sorted(globals().items()):
        if name.startswith('test_'):
            case()
            print(f'{name}: ok')
    print('crypto_jamfiles_format_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
