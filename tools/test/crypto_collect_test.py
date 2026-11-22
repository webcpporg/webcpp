#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks that libs/crypto/bench/collect.py, which measures bench/throughput and bench/timing and
renders doc/performance.adoc, builds its page only from release builds: a program whose build
directory, b2's bench/<toolset>/<variant>/..., names another variant, or does not say, is refused
before anything runs or is written, the guard's `--timing` program as the throughput's; one at
variant=release is taken (it gets as far as running); a cell whose operation is not the one
doc/tables/crypto.json states for its family is refused; a further operation the program lists
after its family and backend is measured by that name, stated as the family's "sized_operations"
entry and rendered after the family's fixed operation, and one crypto.json does not state is
refused; `--timing` alone stores the guard's cost
beside the data's throughput, which it keeps, and the page renders it, with UTC's date; `--timing`
without data is refused with a message; `--provisional` marks each part, the throughput and the
guard, on its own, numbers unchanged, a measurement clears only the mark of the part it measured,
and the page says the figures are provisional above each table whose part is marked; data that is
not what collect.py writes, and a program's line that is not the form it reads, are refused with a
message, not a traceback; and `--render-only` refuses data whose build, or whose guard's build, is
not variant=release, before it writes the page, and renders the committed data as the committed
page; and the page always states the load it was measured under, warning above half the cores.
Run with the names of some cases to run only those."""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLLECT = ROOT / 'libs/crypto/bench/collect.py'
DATA = ROOT / 'libs/crypto/doc/performance.json'
PAGE = ROOT / 'libs/crypto/doc/performance.adoc'


def run(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(COLLECT), *map(str, args)], cwd=ROOT,
                          capture_output=True, text=True, check=False, timeout=120)


def program(scratch: Path, variant: str, script: str, name: str = 'throughput') -> Path:
    """A stand-in of bench/<name> where b2 builds it at variant, running script."""
    path = scratch / 'bin/libs/crypto/bench/clang-darwin-21' / variant / 'cxxstd-20-iso' / name
    path.parent.mkdir(parents=True)
    path.write_text('#!/bin/sh\n' + script)
    path.chmod(0o755)
    return path


def expect(done: subprocess.CompletedProcess[str], status: int, *texts: str) -> None:
    if done.returncode != status:
        raise AssertionError(f'exit {done.returncode}, not {status}\n{done.stdout}{done.stderr}')
    for text in texts:
        if text not in done.stderr:
            raise AssertionError(f'{text!r} is not in the error:\n{done.stderr}')


FAILS = 'echo "the stand-in ran" >&2\nexit 3\n'


def test_a_program_not_built_at_variant_release_is_refused(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    for variant in ('debug', 'profile'):
        exe = program(scratch / variant, variant, FAILS)
        done = run('--exe', f'native={exe}', '--data', data, '--page', page)
        expect(done, 1, f'native={exe} was built at variant={variant}',
               'only from release builds')
        if 'the stand-in ran' in done.stderr or data.exists() or page.exists():
            raise AssertionError(f'{variant}: the program ran or a file was written')
    stray = scratch / 'stray/throughput'
    stray.parent.mkdir()
    stray.write_text('')
    done = run('--exe', f'wasip2={stray}', '--data', data, '--page', page)
    expect(done, 1, f'wasip2={stray}', 'bench/<toolset>/<variant>', 'only from release builds')


def test_a_program_built_at_variant_release_is_measured(scratch: Path) -> None:
    exe = program(scratch, 'release', FAILS)
    done = run('--exe', f'native={exe}', '--data', scratch / 'data.json', '--page',
               scratch / 'page.adoc')
    # Past the check, collect.py runs it, and stops on its failure.
    expect(done, 1, 'native --list: exit 3', 'the stand-in ran')


def test_an_operation_crypto_json_does_not_state_is_refused(scratch: Path) -> None:
    line = json.dumps({'family': 'x25519', 'backend': 'sodium', 'operation': 'something else',
                       'target': 'native', 'compiler': 'clang', 'repetitions': 1,
                       'runs_us': [1.0], 'median_us': 1.0})
    exe = program(scratch, 'release', 'if [ "$1" = --list ]; then echo "x25519 sodium"; '
                  f"else echo '{line}'; fi\n")
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    done = run('--exe', f'native={exe}', '--invocations', '1', '--data', data, '--page', page)
    expect(done, 1, "native x25519 sodium measures 'something else', and crypto.json states "
           "'agreement of a secret key and a public key'")
    if data.exists() or page.exists():
        raise AssertionError('a file was written')


def test_a_further_operation_is_measured_by_its_name(scratch: Path) -> None:
    def line(operation: str, median: float) -> str:
        return json.dumps({'family': 'p256', 'backend': 'bearssl', 'operation': operation,
                           'target': 'native', 'compiler': 'clang', 'repetitions': 1,
                           'runs_us': [median], 'median_us': median})
    fixed = line('ECDSA signature of a 32-byte SHA-256 digest', 20.0)
    further = line("x coordinate of the ECDH shared point with a peer's public key", 40.0)
    # The stand-in answers the further operation only when it is named after the backend; its
    # lines are files, since the operation's text holds a quote.
    (scratch / 'fixed.json').write_text(fixed + '\n')
    (scratch / 'further.json').write_text(further + '\n')
    exe = program(scratch, 'release',
                  'if [ "$1" = --list ]; then printf "p256 bearssl ecdh_x\\np256 bearssl\\n"; '
                  f'elif [ "$3" = ecdh_x ]; then cat "{scratch}/further.json"; '
                  f'elif [ "$3" = --runs ]; then cat "{scratch}/fixed.json"; else exit 3; fi\n')
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    done = run('--exe', f'native={exe}', '--invocations', '1', '--data', data, '--page', page)
    expect(done, 0)
    measured = {case['operation']: case['median_us']
                for case in json.loads(data.read_text())['cases']}
    if measured != {'ECDSA signature of a 32-byte SHA-256 digest': 20.0,
                    "x coordinate of the ECDH shared point with a peer's public key": 40.0}:
        raise AssertionError(f'measured {measured}')
    text = page.read_text()
    first = text.index('| P-256: ECDSA signature of a 32-byte SHA-256 digest')
    second = text.index("| P-256: x coordinate of the ECDH shared point with a peer's public key")
    if first > second:
        raise AssertionError('the further operation is rendered before the fixed one')
    unknown = program(scratch / 'unknown', 'release',
                      'if [ "$1" = --list ]; then echo "p256 bearssl recover"; else exit 3; fi\n')
    done = run('--exe', f'native={unknown}', '--invocations', '1', '--data',
               scratch / 'other.json', '--page', scratch / 'other.adoc')
    expect(done, 1, "native lists p256 bearssl recover, and crypto.json's family p256 has no "
           'sized operation recover')


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


GUARD_LINE = json.dumps({'dit': True, 'clear': 12.345, 'set': 0.678, 'clear_fastest': 11.25,
                         'clear_slowest': 19.75, 'set_fastest': 0.25, 'set_slowest': 1.75,
                         'iterations': 10000000, 'runs': 5, 'target': 'native',
                         'compiler': 'clang'})


def timing_program(scratch: Path, line: str = GUARD_LINE) -> Path:
    """A stand-in of bench/timing at variant=release whose --measure prints line."""
    return program(scratch, 'release', 'if [ "$1" = --measure ]; then '
                   f"echo '{line}'; else exit 3; fi\n", 'timing')


def throughput_program(scratch: Path) -> Path:
    """A stand-in of bench/throughput at variant=release with one cell, X25519 on libsodium, which
    states crypto.json's operation."""
    line = json.dumps({'family': 'x25519', 'backend': 'sodium',
                       'operation': 'agreement of a secret key and a public key',
                       'target': 'native', 'compiler': 'clang', 'repetitions': 1,
                       'runs_us': [30.0, 31.0], 'median_us': 30.5})
    return program(scratch, 'release', 'if [ "$1" = --list ]; then echo "x25519 sodium"; '
                   f"else echo '{line}'; fi\n")


def both_marked() -> dict:
    """The committed data with both parts marked provisional."""
    committed = json.loads(DATA.read_text())
    committed['provisional'] = True
    committed['timing_guard']['provisional'] = True
    return committed


def test_the_guard_is_measured_kept_beside_the_throughput_and_rendered(scratch: Path) -> None:
    exe = timing_program(scratch)
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    committed = both_marked()
    data.write_text(json.dumps(committed))
    before = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    expect(run('--timing', exe, '--data', data, '--page', page), 0)
    written = json.loads(data.read_text())
    guard = written['timing_guard']
    stored = (guard['clear_ns'], guard['clear_fastest_ns'], guard['clear_slowest_ns'],
              guard['set_ns'], guard['set_fastest_ns'], guard['set_slowest_ns'], guard['dit'],
              guard['build'])
    if stored != (12.345, 11.25, 19.75, 0.678, 0.25, 1.75, True, 'variant=release'):
        raise AssertionError(f'the guard was not stored as measured: {guard}')
    # Every date is UTC's, as the constant-time lane's are (a day's edge decides it, so either of
    # the dates around the run is taken only when the clock crossed midnight while it ran).
    utc = {datetime.datetime.now(datetime.timezone.utc).date().isoformat()}
    if guard['date'] not in utc | {before}:
        raise AssertionError(f"the guard's date {guard['date']} is not UTC's {utc}")
    if written['cases'] != committed['cases'] or written['date'] != committed['date']:
        raise AssertionError('the throughput was not kept')
    # The guard was measured again, so its mark is cleared; the throughput was not, so its mark
    # survives, and the page still says so above the throughput alone.
    if 'provisional' in guard:
        raise AssertionError("a measurement of the guard without --provisional kept its mark")
    if written.get('provisional') is not True:
        raise AssertionError("a measurement of the guard alone cleared the throughput's mark")
    text = page.read_text()
    if text.count('NOTE: these figures are provisional') != 1 or \
            text.index('NOTE: these figures are provisional') > \
            text.index('[#crypto-performance-timing]'):
        raise AssertionError(f'the page does not mark the throughput alone:\n{text}')
    for expected in ('[#crypto-performance-timing]', '<<crypto-backends-dit>>', '| 12.3',
                     '| 11.2', '| 19.8', '| 0.7', '| 0.2', '| 1.8',
                     'The guard sets DIT on this machine', '10,000,000 guards'):
        if expected not in text:
            raise AssertionError(f'{expected!r} is not on the page:\n{text}')


def test_the_throughput_measured_alone_keeps_the_guards_mark(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    data.write_text(json.dumps(both_marked()))
    exe = throughput_program(scratch)
    expect(run('--exe', f'native={exe}', '--invocations', '1', '--data', data, '--page', page), 0)
    written = json.loads(data.read_text())
    if 'provisional' in written:
        raise AssertionError("a measurement of the throughput without --provisional kept its mark")
    if written['timing_guard'].get('provisional') is not True:
        raise AssertionError("a measurement of the throughput alone cleared the guard's mark")
    text = page.read_text()
    if text.count('NOTE: these figures are provisional') != 1 or \
            text.index('NOTE: these figures are provisional') < \
            text.index('[#crypto-performance-timing]'):
        raise AssertionError(f'the page does not mark the guard alone:\n{text}')
    # With --provisional, the measurement marks its own part, and the guard's stays marked.
    expect(run('--exe', f'native={exe}', '--invocations', '1', '--provisional', '--data', data,
               '--page', page), 0)
    written = json.loads(data.read_text())
    if written.get('provisional') is not True or \
            written['timing_guard'].get('provisional') is not True:
        raise AssertionError(f'--provisional did not mark the throughput: {written}')
    if page.read_text().count('NOTE: these figures are provisional') != 2:
        raise AssertionError(f'the page does not mark both tables:\n{page.read_text()}')


def test_the_guard_measured_with_provisional_is_marked(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    committed = json.loads(DATA.read_text())
    committed.pop('provisional', None)
    committed['timing_guard'].pop('provisional', None)
    data.write_text(json.dumps(committed))
    expect(run('--timing', timing_program(scratch), '--provisional', '--data', data, '--page',
               page), 0)
    written = json.loads(data.read_text())
    if written['timing_guard'].get('provisional') is not True or 'provisional' in written:
        raise AssertionError(f'--timing --provisional did not mark the guard alone: {written}')
    text = page.read_text()
    if text.count('NOTE: these figures are provisional') != 1 or \
            text.index('NOTE: these figures are provisional') < \
            text.index('[#crypto-performance-timing]'):
        raise AssertionError(f'the page does not mark the guard alone:\n{text}')


def test_timing_alone_without_data_is_refused_with_a_message(scratch: Path) -> None:
    exe = program(scratch, 'release', FAILS, 'timing')
    data, page = scratch / 'missing.json', scratch / 'page.adoc'
    done = run('--timing', exe, '--data', data, '--page', page)
    expect(done, 1, f'collect.py: {data} cannot be read')
    if 'Traceback' in done.stderr or 'the stand-in ran' in done.stderr:
        raise AssertionError(f'a traceback, or the program ran:\n{done.stderr}')
    if data.exists() or page.exists():
        raise AssertionError('a file was written')


def test_provisional_marks_the_data_and_the_page_says_so(scratch: Path) -> None:
    committed = json.loads(DATA.read_text())
    committed.pop('provisional', None)
    committed['timing_guard'].pop('provisional', None)
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    data.write_text(json.dumps(committed))
    expect(run('--render-only', '--data', data, '--page', page), 0)
    if 'provisional' in page.read_text() or json.loads(data.read_text()) != committed:
        raise AssertionError('render-only without --provisional marked something')
    expect(run('--render-only', '--provisional', '--data', data, '--page', page), 0)
    marked = json.loads(data.read_text())
    if marked.pop('provisional', None) is not True or \
            marked['timing_guard'].pop('provisional', None) is not True or marked != committed:
        raise AssertionError('--provisional did not mark both parts alone, numbers unchanged')
    if page.read_text().count('NOTE: these figures are provisional') != 2:
        raise AssertionError(f'the page does not say it above both tables:\n{page.read_text()}')


def refused(done: subprocess.CompletedProcess[str], page: Path, *texts: str) -> None:
    """Checks that collect.py stopped with its own message, not a traceback, before the page."""
    expect(done, 1, 'collect.py: ', *texts)
    if 'Traceback' in done.stderr:
        raise AssertionError(f'a traceback, not a message:\n{done.stderr}')
    if page.exists():
        raise AssertionError('the page was written')


def test_data_collect_py_does_not_write_is_refused_with_a_message(scratch: Path) -> None:
    committed = json.loads(DATA.read_text())
    page = scratch / 'page.adoc'

    def without(*path: str | int) -> dict:
        data = json.loads(json.dumps(committed))
        parent = data
        for key in path[:-1]:
            parent = parent[key]
        del parent[path[-1]]
        return data

    def replaced(value: object, *path: str | int) -> dict:
        data = json.loads(json.dumps(committed))
        parent = data
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = value
        return data

    for data, named in (
            ([committed], 'not a JSON object'),
            (without('cases'), 'data.cases (missing)'),
            (without('machine', 'cpu'), 'data.machine.cpu (missing)'),
            (without('cases', 3, 'median_us'), 'data.cases[3].median_us (missing)'),
            (replaced('fast', 'cases', 0, 'median_us'), 'data.cases[0].median_us'),
            (replaced('nothing', 'cases', 0, 'family'), "data.cases[0].family ('nothing'"),
            (replaced([[1.0], [1.0], [1.0]], 'load_average_before_after'),
             'data.load_average_before_after'),
            (without('timing_guard', 'clear_ns'), 'data.timing_guard.clear_ns (missing)'),
            (replaced('yes', 'timing_guard', 'dit'), 'data.timing_guard.dit'),
            (replaced('0.5', 'timing_guard', 'set_fastest_ns'),
             'data.timing_guard.set_fastest_ns')):
        path = scratch / 'data.json'
        path.write_text(json.dumps(data))
        refused(run('--render-only', '--data', path, '--page', page), page, named)
        # --timing alone reads the same data, and refuses it before it runs the program.
        refused(run('--timing', timing_program(scratch / named.split(' ')[0].replace('.', '_')
                                               .replace('[', '_').replace(']', '_')),
                    '--data', path, '--page', page), page, named)


def test_a_timing_program_of_another_form_is_refused_with_a_message(scratch: Path) -> None:
    committed = json.loads(DATA.read_text())
    old = json.loads(GUARD_LINE)
    for key in ('clear_fastest', 'clear_slowest', 'set_fastest', 'set_slowest'):
        del old[key]
    for index, (line, named) in enumerate((
            (json.dumps(old), 'line.clear_fastest (missing)'),
            ('not json', 'a line that is not JSON'),
            ('[1, 2]', 'line (not an object)'),
            ('', 'line (not an object)'))):
        data, page = scratch / 'data.json', scratch / 'page.adoc'
        data.write_text(json.dumps(committed))
        refused(run('--timing', timing_program(scratch / str(index), line), '--data', data,
                    '--page', page), page, named)
        if json.loads(data.read_text()) != committed:
            raise AssertionError(f'{named}: the data was rewritten')


def test_render_only_refuses_data_not_built_at_variant_release(scratch: Path) -> None:
    committed = json.loads(DATA.read_text())
    page = scratch / 'page.adoc'
    for build in ('variant=debug', None):
        data = dict(committed)
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
        raise AssertionError('the guard of a debug build: the page was written')
    path = scratch / 'data.json'
    path.write_text(json.dumps(committed))
    expect(run('--render-only', '--data', path, '--page', page), 0)
    if page.read_text() != PAGE.read_text():
        raise AssertionError('the committed data does not render the committed page')


def test_the_page_states_the_load_and_warns_above_half_the_cores(scratch: Path) -> None:
    # The page always prints the load averages it was measured under, and warns when the larger
    # 1-minute load exceeds half the cores: a shared machine's spread, not its figures.
    committed = json.loads(DATA.read_text())
    page = scratch / 'page.adoc'
    cores = committed['machine']['cores']
    for one_minute, warned in ((cores / 2 + 1, True), (cores / 2 - 1, False)):
        data = json.loads(json.dumps(committed))
        data['load_average_before_after'] = [[one_minute, 1.0, 1.0], [1.0, 1.0, 1.0]]
        # The guard's measurement states its own load, and warns by the same rule.
        data['timing_guard']['load_average_before_after'] = [[1.0, 1.0, 1.0],
                                                             [one_minute, 1.0, 1.0]]
        path = scratch / 'data.json'
        path.write_text(json.dumps(data))
        expect(run('--render-only', '--data', path, '--page', page), 0)
        text = page.read_text()
        stated = text.count('minute load averages were')
        if stated != 2 or text.count('WARNING') != (2 if warned else 0):
            raise AssertionError(f'{one_minute} on {cores} cores:\n{text}')


CASES: list[Callable[[Path], None]] = [
    test_a_program_not_built_at_variant_release_is_refused,
    test_a_program_built_at_variant_release_is_measured,
    test_an_operation_crypto_json_does_not_state_is_refused,
    test_a_further_operation_is_measured_by_its_name,
    test_a_timing_program_not_built_at_variant_release_is_refused,
    test_the_guard_is_measured_kept_beside_the_throughput_and_rendered,
    test_the_throughput_measured_alone_keeps_the_guards_mark,
    test_the_guard_measured_with_provisional_is_marked,
    test_timing_alone_without_data_is_refused_with_a_message,
    test_provisional_marks_the_data_and_the_page_says_so,
    test_data_collect_py_does_not_write_is_refused_with_a_message,
    test_a_timing_program_of_another_form_is_refused_with_a_message,
    test_render_only_refuses_data_not_built_at_variant_release,
    test_the_page_states_the_load_and_warns_above_half_the_cores,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'crypto_collect_test: no case named {", ".join(sorted(unknown))}', file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp crypto collect ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('crypto_collect_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
