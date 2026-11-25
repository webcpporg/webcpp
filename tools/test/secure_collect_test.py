#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks that libs/secure/bench/collect.py, which measures bench/timing and renders
doc/performance.adoc, builds its page only from release builds: a program whose build directory,
b2's bench/<toolset>/<variant>/..., names another variant, or does not say, is refused before it
runs or anything is written; one at variant=release is measured, its figures stored with UTC's date
and the load averages and rendered, whether the data existed or not (an older measurement is
replaced); a program that fails, and a line or a data file that is not the form collect.py reads,
are refused with a message, not a traceback, before anything is written; `--render-only` refuses
data whose build is not variant=release, before it writes the page, and renders the committed data
as the committed page; and exactly one of `--timing` and `--render-only` is given. Run with the
names of some cases to run only those."""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLLECT = ROOT / 'libs/secure/bench/collect.py'
DATA = ROOT / 'libs/secure/doc/measurements.json'
PAGE = ROOT / 'libs/secure/doc/performance.adoc'
# A stand-in's body that fails when run, after saying so.
FAILS = 'echo "the stand-in ran" >&2\nexit 3\n'


def run(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(COLLECT), *map(str, args)], cwd=ROOT,
                          capture_output=True, text=True, check=False, timeout=120)


def program(scratch: Path, variant: str, body: str = FAILS) -> Path:
    """A stand-in of bench/timing where b2 builds it at variant, which runs body (by default, it
    fails)."""
    path = (scratch / 'bin/libs/secure/bench/clang-darwin-21' / variant
            / 'cxxstd-20-iso' / 'timing')
    path.parent.mkdir(parents=True)
    path.write_text('#!/bin/sh\n' + body)
    path.chmod(0o755)
    return path


def expect(done: subprocess.CompletedProcess[str], status: int, *texts: str) -> None:
    if done.returncode != status:
        raise AssertionError(f'exit {done.returncode}, not {status}\n{done.stdout}{done.stderr}')
    for text in texts:
        if text not in done.stderr:
            raise AssertionError(f'{text!r} is not in the error:\n{done.stderr}')


GUARD = {'dit': True, 'clear': 12.345, 'set': 0.678, 'disengaged': -0.04,
         'clear_fastest': 11.25, 'clear_slowest': 19.75, 'set_fastest': 0.25, 'set_slowest': 1.75,
         'disengaged_fastest': -0.25, 'disengaged_slowest': 0.375, 'iterations': 10000000,
         'runs': 5, 'target': 'native', 'compiler': 'clang'}


def timing_program(scratch: Path, line: str = json.dumps(GUARD)) -> Path:
    """A stand-in of bench/timing at variant=release whose --measure prints line."""
    return program(scratch, 'release', 'if [ "$1" = --measure ]; then '
                   f"echo '{line}'; else exit 3; fi\n")


def test_a_program_not_built_at_variant_release_is_refused(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    for variant in ('debug', 'profile'):
        exe = program(scratch / variant, variant)
        done = run('--timing', exe, '--data', data, '--page', page)
        expect(done, 1, f'timing={exe} was built at variant={variant}',
               'only from release builds')
        if 'the stand-in ran' in done.stderr or data.exists() or page.exists():
            raise AssertionError(f'{variant}: the program ran or a file was written')
    stray = scratch / 'stray/timing'
    stray.parent.mkdir()
    stray.write_text('')
    done = run('--timing', stray, '--data', data, '--page', page)
    expect(done, 1, f'timing={stray}', 'bench/<toolset>/<variant>', 'only from release builds')


def test_the_committed_data_is_not_replaced_by_a_refused_program(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    data.write_text(DATA.read_text())
    exe = program(scratch, 'debug')
    expect(run('--timing', exe, '--data', data, '--page', page), 1, 'only from release builds')
    if data.read_text() != DATA.read_text() or page.exists():
        raise AssertionError('the data was rewritten or the page written')


def test_a_program_built_at_variant_release_is_measured_stored_and_rendered(
        scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    before = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    # The data need not exist, and an older measurement is replaced.
    for existing in (None, DATA.read_text()):
        if existing is not None:
            data.write_text(existing)
        expect(run('--timing', timing_program(scratch / str(existing is None)), '--data', data,
                   '--page', page), 0)
        written = json.loads(data.read_text())
        stored = {key: written[f'{key}_ns'] for key in GUARD if isinstance(GUARD[key], float)}
        if stored != {key: value for key, value in GUARD.items() if isinstance(value, float)} or \
                written['dit'] is not True or written['build'] != 'variant=release' or \
                written['iterations'] != GUARD['iterations'] or written['runs'] != 5:
            raise AssertionError(f'the guard was not stored as measured: {written}')
        utc = {datetime.datetime.now(datetime.timezone.utc).date().isoformat(), before}
        if written['date'] not in utc:
            raise AssertionError(f"the date {written['date']} is not UTC's {utc}")
        loads = written['load_average_before_after']
        if len(loads) != 2 or any(len(load) != 3 for load in loads):
            raise AssertionError(f'the load averages are not two triples: {loads}')
        text = page.read_text()
        for expected in ('[#secure-performance]', '<<secure-guard>>', '| 12.3', '| 11.2', '| 19.8',
                         '| 0.7', '| 0.2', '| 1.8', '| 0.0', '| 0.4', 'load averages were',
                         'The guard sets DIT on this machine', '10,000,000 guards'):
            if expected not in text:
                raise AssertionError(f'{expected!r} is not on the page:\n{text}')
        if 'provisional' in text:
            raise AssertionError(f'the page says provisional:\n{text}')


def test_a_machine_without_dit_says_the_rows_are_noise(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    line = json.dumps({**GUARD, 'dit': False})
    expect(run('--timing', timing_program(scratch, line), '--data', data, '--page', page), 0)
    if 'does not set DIT on this machine' not in page.read_text():
        raise AssertionError('the page does not say the guard sets nothing here')


def test_a_program_that_fails_is_refused_with_a_message(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    exe = program(scratch, 'release')
    done = run('--timing', exe, '--data', data, '--page', page)
    expect(done, 1, 'timing --measure: exit 3', 'the stand-in ran')
    if 'Traceback' in done.stderr or data.exists() or page.exists():
        raise AssertionError(f'a traceback, or a file was written:\n{done.stderr}')


def test_a_timing_line_or_data_of_another_form_is_refused_with_a_message(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    lines = {
        'not json': 'line (not JSON)',
        json.dumps({key: value for key, value in GUARD.items() if key != 'disengaged'}):
            'line.disengaged (missing)',
        json.dumps({**GUARD, 'clear': 'fast'}): 'line.clear',
        json.dumps({**GUARD, 'dit': 1}): 'line.dit',
    }
    for index, (line, named) in enumerate(lines.items()):
        data.write_text(DATA.read_text())
        done = run('--timing', timing_program(scratch / str(index), line), '--data', data,
                   '--page', page)
        expect(done, 1, 'not the form collect.py reads', named)
        if 'Traceback' in done.stderr or page.exists() or data.read_text() != DATA.read_text():
            raise AssertionError(f'{line}: a traceback, or a file was written:\n{done.stderr}')
    committed = json.loads(DATA.read_text())
    for change, named in ((lambda d: d.pop('set_ns'), 'data.set_ns (missing)'),
                          (lambda d: d.update(dit='yes'), 'data.dit'),
                          (lambda d: d.update(machine=3), 'data.machine (not an object)'),
                          (lambda d: d.update(load_average_before_after=[]),
                           'data.load_average_before_after (not a list, or empty)')):
        broken = json.loads(json.dumps(committed))
        change(broken)
        data.write_text(json.dumps(broken))
        done = run('--render-only', '--data', data, '--page', page)
        expect(done, 1, 'not the data collect.py writes', named)
        if 'Traceback' in done.stderr or page.exists():
            raise AssertionError(f'{named}: a traceback, or the page was written:\n{done.stderr}')
    data.write_text('not json')
    expect(run('--render-only', '--data', data, '--page', page), 1, 'cannot be read')
    expect(run('--render-only', '--data', scratch / 'missing.json', '--page', page), 1,
           'cannot be read')


def test_render_only_refuses_data_not_built_at_variant_release(scratch: Path) -> None:
    committed = json.loads(DATA.read_text())
    page = scratch / 'page.adoc'
    for build in ('variant=debug', 'variant=release optimization=speed', None):
        data = json.loads(json.dumps(committed))
        if build is None:
            del data['build']
        else:
            data['build'] = build
        path = scratch / 'data.json'
        path.write_text(json.dumps(data))
        done = run('--render-only', '--data', path, '--page', page)
        expect(done, 1, 'only from release builds')
        if page.exists():
            raise AssertionError(f'{build}: the page was written')
    path = scratch / 'data.json'
    path.write_text(json.dumps(committed))
    expect(run('--render-only', '--data', path, '--page', page), 0)
    if page.read_text() != PAGE.read_text():
        raise AssertionError('the committed data does not render the committed page')


def test_the_load_note_states_only_the_loads_and_only_at_two_or_more(scratch: Path) -> None:
    committed = json.loads(DATA.read_text())
    for loads, noted in (([[4.5, 4.0, 3.0], [1.0, 1.0, 1.0]], True),
                         ([[1.0, 1.0, 1.0], [2.0, 1.0, 1.0]], True),
                         ([[0.5, 1.0, 1.0], [1.99, 1.0, 1.0]], False)):
        data, page = scratch / 'data.json', scratch / 'page.adoc'
        data.write_text(json.dumps({**committed, 'load_average_before_after': loads}))
        expect(run('--render-only', '--data', data, '--page', page), 0)
        text = page.read_text()
        note = [line for line in text.splitlines() if line.startswith('NOTE:')]
        if bool(note) != noted:
            raise AssertionError(f'{loads}: the note is {"absent" if noted else "present"}')
        if noted:
            for expected in (f'{loads[0][0]:.2f} before and {loads[1][0]:.2f}', 'below 2',
                             "upper bound of an idle machine's"):
                if expected not in ' '.join(text.split()):
                    raise AssertionError(f'{expected!r} is not in the note:\n{text}')
            for claim in ('system tasks', 'no build', 'core was free', 'idle by that rule'):
                if claim in text:
                    raise AssertionError(f'the page claims a cause, {claim!r}:\n{text}')


def test_exactly_one_of_timing_and_render_only_is_given(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    data.write_text(DATA.read_text())
    exe = timing_program(scratch)
    for arguments in ((), ('--timing', exe, '--render-only')):
        done = run(*arguments, '--data', data, '--page', page)
        expect(done, 1, 'give --timing to measure, or --render-only to render')
        if data.read_text() != DATA.read_text() or page.exists():
            raise AssertionError(f'{arguments}: a file was written')


CASES: list[Callable[[Path], None]] = [
    test_a_program_not_built_at_variant_release_is_refused,
    test_the_committed_data_is_not_replaced_by_a_refused_program,
    test_a_program_built_at_variant_release_is_measured_stored_and_rendered,
    test_a_machine_without_dit_says_the_rows_are_noise,
    test_a_program_that_fails_is_refused_with_a_message,
    test_a_timing_line_or_data_of_another_form_is_refused_with_a_message,
    test_render_only_refuses_data_not_built_at_variant_release,
    test_the_load_note_states_only_the_loads_and_only_at_two_or_more,
    test_exactly_one_of_timing_and_render_only_is_given,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'secure_collect_test: no case named {", ".join(sorted(unknown))}', file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp secure collect ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('secure_collect_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
