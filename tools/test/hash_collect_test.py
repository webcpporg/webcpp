#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks that libs/hash/bench/collect.py, which measures bench/pbkdf2_sha512 and bench/timing and
renders doc/performance.adoc, builds its page only from release builds: a program whose build
directory, b2's bench/<toolset>/<variant>/..., names another variant, or does not say, is refused
before anything runs or is written, the guard's `--timing` program as the throughput's; one at
variant=release is taken (it gets as far as running); `--timing` alone stores the guard's cost
beside the data's throughput, which it keeps, with UTC's date, and the page renders it; `--exe`
alone keeps the data's guard, and replaces data it cannot keep, saying so, with UTC's date;
`--provisional` marks the guard's figures and the page says so, a measurement without it clears the
mark, and it is refused without `--timing`; `--timing` without data, a timing line that is not the
form collect.py reads and a "timing_guard" that is not the form it writes are refused with a
message, not a traceback, before anything is written; and `--render-only` refuses data whose build,
or whose guard's build, is not variant=release, before it writes the page, and renders the committed
data as the committed page. Run with the names of some cases to run only those."""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLLECT = ROOT / 'libs/hash/bench/collect.py'
DATA = ROOT / 'libs/hash/doc/measurements.throughput.json'
PAGE = ROOT / 'libs/hash/doc/performance.adoc'
# A stand-in's body that fails when run, after saying so.
FAILS = 'echo "the stand-in ran" >&2\nexit 3\n'


def run(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(COLLECT), *map(str, args)], cwd=ROOT,
                          capture_output=True, text=True, check=False, timeout=120)


def program(scratch: Path, variant: str, body: str = FAILS,
            name: str = 'pbkdf2_sha512') -> Path:
    """A stand-in of bench/<name> where b2 builds it at variant, which runs body (by default, it
    fails)."""
    path = (scratch / 'bin/libs/hash/bench/clang-darwin-21' / variant
            / 'cxxstd-20-iso/optimization-speed' / name)
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


def test_a_program_not_built_at_variant_release_is_refused(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    for variant in ('debug', 'profile'):
        exe = program(scratch / variant, variant)
        done = run('--exe', f'native={exe}', '--data', data, '--page', page)
        expect(done, 1, f'native={exe} was built at variant={variant}',
               'only from release builds')
        if 'the stand-in ran' in done.stderr or data.exists() or page.exists():
            raise AssertionError(f'{variant}: the program ran or a file was written')
    stray = scratch / 'stray/pbkdf2_sha512'
    stray.parent.mkdir()
    stray.write_text('')
    done = run('--exe', f'wasip2={stray}', '--data', data, '--page', page)
    expect(done, 1, f'wasip2={stray}', 'bench/<toolset>/<variant>', 'only from release builds')


def test_a_program_built_at_variant_release_is_measured(scratch: Path) -> None:
    exe = program(scratch, 'release')
    done = run('--exe', f'native={exe}', '--data', scratch / 'data.json', '--page',
               scratch / 'page.adoc')
    # Past the check, collect.py runs it, and stops on its failure.
    expect(done, 1, 'native: --list exit 3', 'the stand-in ran')


def test_a_timing_program_not_built_at_variant_release_is_refused(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    data.write_text(DATA.read_text())
    for variant in ('debug', 'profile'):
        exe = program(scratch / variant, variant, FAILS, 'timing')
        done = run('--timing', exe, '--data', data, '--page', page)
        expect(done, 1, f'timing={exe} was built at variant={variant}',
               'only from release builds')
        if 'the stand-in ran' in done.stderr or page.exists():
            raise AssertionError(f'{variant}: the program ran or the page was written')
        if data.read_text() != DATA.read_text():
            raise AssertionError(f'{variant}: the data was rewritten')


GUARD = {'dit': True, 'clear': 12.345, 'set': 0.678, 'disengaged': -0.04,
         'clear_fastest': 11.25, 'clear_slowest': 19.75, 'set_fastest': 0.25, 'set_slowest': 1.75,
         'disengaged_fastest': -0.25, 'disengaged_slowest': 0.375, 'iterations': 10000000,
         'runs': 5, 'target': 'native', 'compiler': 'clang'}


def timing_program(scratch: Path, line: str = json.dumps(GUARD)) -> Path:
    """A stand-in of bench/timing at variant=release whose --measure prints line."""
    return program(scratch, 'release', 'if [ "$1" = --measure ]; then '
                   f"echo '{line}'; else exit 3; fi\n", 'timing')


def test_the_guard_is_measured_kept_beside_the_throughput_and_rendered(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    committed = json.loads(DATA.read_text())
    data.write_text(json.dumps(committed))
    before = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    expect(run('--timing', timing_program(scratch), '--data', data, '--page', page), 0)
    written = json.loads(data.read_text())
    guard = written['timing_guard']
    stored = {key: guard[f'{key}_ns'] for key in GUARD if isinstance(GUARD[key], float)}
    if stored != {key: value for key, value in GUARD.items() if isinstance(value, float)} or \
            guard['dit'] is not True or guard['build'] != committed['build'] or \
            guard['provisional'] is not False:
        raise AssertionError(f'the guard was not stored as measured: {guard}')
    utc = {datetime.datetime.now(datetime.timezone.utc).date().isoformat(), before}
    if guard['date'] not in utc:
        raise AssertionError(f"the guard's date {guard['date']} is not UTC's {utc}")
    if {key: value for key, value in written.items() if key != 'timing_guard'} != \
            {key: value for key, value in committed.items() if key != 'timing_guard'}:
        raise AssertionError('the throughput was not kept')
    text = page.read_text()
    if 'provisional' in text:
        raise AssertionError(f'the page says provisional without --provisional:\n{text}')
    for expected in ('[#hash-performance-timing]', '<<hash-backends-dit>>', '| 12.3', '| 11.2',
                     '| 19.8', '| 0.7', '| 0.2', '| 1.8', '| 0.0', '| 0.4',
                     'The guard sets DIT on this machine', '10,000,000 guards'):
        if expected not in text:
            raise AssertionError(f'{expected!r} is not on the page:\n{text}')
    if text.index('[#hash-performance-pbkdf2]') > text.index('[#hash-performance-timing]'):
        raise AssertionError('the guard is not rendered after the throughput')


def throughput_program(scratch: Path) -> Path:
    """A stand-in of bench/pbkdf2_sha512 at variant=release with one variant, hash2, whose key is
    right."""
    line = json.dumps({'key_correct': True, 'median_ms': 900.0, 'runs_ms': [899.0, 901.0],
                       'compiler': 'clang', 'iterations': 1000000})
    return program(scratch, 'release', 'if [ "$1" = --list ]; then echo hash2; '
                   f"else echo '{line}'; fi\n")


def test_the_throughput_alone_keeps_the_guard_or_replaces_bad_data(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    committed = json.loads(DATA.read_text())
    data.write_text(json.dumps(committed))
    exe = throughput_program(scratch)
    utc = {datetime.datetime.now(datetime.timezone.utc).date().isoformat()}
    expect(run('--exe', f'native={exe}', '--invocations', '1', '--data', data, '--page', page), 0)
    written = json.loads(data.read_text())
    if written['timing_guard'] != committed['timing_guard']:
        raise AssertionError("a measurement of the throughput alone did not keep the guard")
    utc.add(datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    if written['date'] not in utc or [c['median_ms'] for c in written['cases']] != [900.0]:
        raise AssertionError(f'the throughput was not stored as measured, with UTC\'s date: '
                             f'{written["date"]}, {written["cases"]}')
    # Data it cannot keep, of another build or not JSON, is replaced, and the message says so.
    for bad in (json.dumps({**committed, 'build': 'variant=debug'}), 'not json'):
        data.write_text(bad)
        done = run('--exe', f'native={exe}', '--invocations', '1', '--data', data, '--page',
                   page)
        expect(done, 0, 'the guard is not kept')
        if 'timing_guard' in json.loads(data.read_text()) or 'Traceback' in done.stderr:
            raise AssertionError(f'bad data was not replaced cleanly:\n{done.stderr}')


def test_provisional_marks_the_guard_and_a_measurement_without_it_clears_it(
        scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    data.write_text(DATA.read_text())
    exe = timing_program(scratch)
    expect(run('--timing', exe, '--provisional', '--data', data, '--page', page), 0)
    if json.loads(data.read_text())['timing_guard']['provisional'] is not True:
        raise AssertionError('--provisional did not mark the guard')
    text = page.read_text()
    if text.count('NOTE: these figures are provisional') != 1 or \
            text.index('NOTE: these figures are provisional') < \
            text.index('[#hash-performance-timing]'):
        raise AssertionError(f'the page does not mark the guard alone:\n{text}')
    expect(run('--timing', exe, '--data', data, '--page', page), 0)
    if json.loads(data.read_text())['timing_guard']['provisional'] is not False or \
            'provisional' in page.read_text():
        raise AssertionError('a measurement without --provisional kept the mark')
    before = data.read_text()
    done = run('--render-only', '--provisional', '--data', data, '--page', scratch / 'other.adoc')
    expect(done, 1, '--provisional marks the guard\'s figures: give it with --timing')
    if data.read_text() != before or (scratch / 'other.adoc').exists():
        raise AssertionError('--provisional without --timing wrote a file')


def test_timing_alone_without_data_is_refused_with_a_message(scratch: Path) -> None:
    exe = program(scratch, 'release', FAILS, 'timing')
    data, page = scratch / 'missing.json', scratch / 'page.adoc'
    done = run('--timing', exe, '--data', data, '--page', page)
    expect(done, 1, f'collect.py: {data} does not exist')
    if 'Traceback' in done.stderr or 'the stand-in ran' in done.stderr:
        raise AssertionError(f'a traceback, or the program ran:\n{done.stderr}')
    if data.exists() or page.exists():
        raise AssertionError('a file was written')


def test_a_timing_line_or_guard_of_another_form_is_refused_with_a_message(scratch: Path) -> None:
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
    for change, named in ((lambda g: g.pop('set_ns'), 'data.timing_guard.set_ns (missing)'),
                          (lambda g: g.update(dit='yes'), 'data.timing_guard.dit'),
                          (lambda g: g.update(provisional=None), 'data.timing_guard.provisional')):
        broken = json.loads(json.dumps(committed))
        change(broken['timing_guard'])
        data.write_text(json.dumps(broken))
        done = run('--render-only', '--data', data, '--page', page)
        expect(done, 1, 'not the data collect.py writes', named)
        if 'Traceback' in done.stderr or page.exists():
            raise AssertionError(f'{named}: a traceback, or the page was written:\n{done.stderr}')


def test_render_only_refuses_data_not_built_at_variant_release(scratch: Path) -> None:
    committed = json.loads(DATA.read_text())
    page = scratch / 'page.adoc'
    for build in ('variant=debug optimization=speed', None):
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
    data = json.loads(json.dumps(committed))
    data['timing_guard']['build'] = 'variant=debug'
    path = scratch / 'data.json'
    path.write_text(json.dumps(data))
    done = run('--render-only', '--data', path, '--page', page)
    expect(done, 1, "timing guard was measured with build variant=debug",
           'only from release builds')
    if page.exists():
        raise AssertionError("the guard's debug build: the page was written")
    path.write_text(json.dumps(committed))
    expect(run('--render-only', '--data', path, '--page', page), 0)
    if page.read_text() != PAGE.read_text():
        raise AssertionError('the committed data does not render the committed page')


CASES: list[Callable[[Path], None]] = [
    test_a_program_not_built_at_variant_release_is_refused,
    test_a_program_built_at_variant_release_is_measured,
    test_a_timing_program_not_built_at_variant_release_is_refused,
    test_the_throughput_alone_keeps_the_guard_or_replaces_bad_data,
    test_the_guard_is_measured_kept_beside_the_throughput_and_rendered,
    test_provisional_marks_the_guard_and_a_measurement_without_it_clears_it,
    test_timing_alone_without_data_is_refused_with_a_message,
    test_a_timing_line_or_guard_of_another_form_is_refused_with_a_message,
    test_render_only_refuses_data_not_built_at_variant_release,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'hash_collect_test: no case named {", ".join(sorted(unknown))}', file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp hash collect ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('hash_collect_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
