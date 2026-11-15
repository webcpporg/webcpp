#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks tools/hash/measure.py, webcpp::hash's measured table (spec section 4.2), on a fixture
library: a capability table of four backends and five functions, and measurements made up for
it. `--write --measured` renders doc/measurements.json, doc/measurements.adoc,
detail/ranking.hpp, detail/overrides.hpp, doc/backends.adoc and test/measure/cells.jam, the same
bytes each time; `--check` passes on what it wrote, and fails naming
`python3 tools/hash/measure.py --write` when the size order of a row changes, when a throughput
median moves more than 10 percent past the one ahead of it (spec 4.2's rule alone, ruling R33: a
first measurement orders by the medians, and the runs' spread plays no part), when a generated
file or the data was edited by hand, and when a program of a cell is missing on a target (a lane
that built nothing); a median that moves by under 10 percent changes nothing. Each key
derivation operation has its own ranking (hkdf_extract and hkdf_expand beside hkdf); every order
names every backend with a tag, so that the per-operation default (ruling R23) always finds
one; the portable order is hash2, sodium, bearssl (ruling R3). Native orders measured with
another native toolchain are not compared, said in one line, while WebAssembly's are (ruling
R34). `--capabilities` renders the capability table (ruling R13); `--overrides`, run on the real
library, gives detail/overrides.hpp byte for byte; and `--check` passes on the real library's
committed data, without a build. Run with the names of some cases to run only those."""

from __future__ import annotations

import copy
import functools
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MEASURE = ROOT / 'tools/hash/measure.py'
LIBRARY = ROOT / 'libs/hash'
WRITE = 'python3 tools/hash/measure.py --write'

TARGETS = ('native', 'wasip2', 'wasip3', 'emscripten')
ALL = list(TARGETS)
NOT_EMSCRIPTEN = ['native', 'wasip2', 'wasip3']

# The outputs of --write, relative to the library.
OUTPUTS = (
    'doc/measurements.json',
    'doc/measurements.adoc',
    'doc/backends.adoc',
    'include/webcpp/hash/detail/ranking.hpp',
    'include/webcpp/hash/detail/overrides.hpp',
    'test/measure/cells.jam',
)

STATED = {'value': 'not stated', 'source': 'the fixture states nothing.'}


def cell(hmacs: list[str] | None) -> dict[str, Any]:
    return {'since': 1, 'hmacs': hmacs, 'constant_time': STATED}


def capabilities() -> dict[str, Any]:
    """A capability table in the layout of doc/capabilities.json, version 2: SHA-256 on hash2;
    HKDF's three functions on hash2, libsodium, OpenSSL and (whole) BearSSL; PBKDF2 on hash2
    and OpenSSL; Argon2id on libsodium."""
    hmacs = ['hmac_sha2_256', 'hmac_sha2_512']

    def backend(name: str, tag: str | None, targets: Sequence[str], portable: bool) -> dict:
        return {'name': name, 'tag': tag, 'macro': name.upper(), 'library': f'{name} 1.0',
                'licence': 'BSL-1.0', 'targets': list(targets),
                'jamfile': '/webcpp/hash//hash' if name == 'hash2' else f'/third_party//{name}',
                'portable': portable}

    def function(name: str, tag: str | None, kind: str, cells: dict) -> dict:
        return {'name': name, 'kind': kind, 'tag': tag, 'header': f'webcpp/hash/{name}.hpp',
                'backends': cells}

    hkdf_steps = {'hash2': cell(hmacs), 'sodium': cell(hmacs), 'openssl': cell(hmacs)}
    return {
        'about': 'the fixture', 'version': 2, 'layout': {},
        'targets': ALL,
        'backends': [
            backend('hash2', 'backends::hash2', ALL, True),
            backend('xkcp', None, ALL, True),
            backend('sodium', 'backends::sodium', ALL, True),
            backend('bearssl', 'backends::bearssl', ALL, True),
            backend('openssl', 'backends::openssl', NOT_EMSCRIPTEN, False),
        ],
        'hmacs': hmacs + ['other'],
        'algorithms': [
            {'name': 'sha2', 'macro': 'SHA2', 'tag': None, 'chapter': 'digests',
             'standard': 'FIPS 180-4', 'overridable': False,
             'functions': [function('sha2_256', None, 'type', {'hash2': cell(None)})]},
            {'name': 'hkdf', 'macro': 'HKDF', 'tag': 'kdfs::hkdf', 'chapter': 'kdfs',
             'standard': 'RFC 5869', 'overridable': True,
             'functions': [
                 function('hkdf_extract', 'kdfs::hkdf_extract', 'function', hkdf_steps),
                 function('hkdf_expand', 'kdfs::hkdf_expand', 'function',
                          copy.deepcopy(hkdf_steps)),
                 function('hkdf', 'kdfs::hkdf', 'function',
                          {'hash2': cell(hmacs), 'sodium': cell(hmacs),
                           'bearssl': cell(hmacs), 'openssl': cell(hmacs)})]},
            {'name': 'pbkdf2', 'macro': 'PBKDF2', 'tag': 'kdfs::pbkdf2', 'chapter': 'kdfs',
             'standard': 'RFC 8018', 'overridable': True,
             'functions': [function('pbkdf2', 'kdfs::pbkdf2', 'function',
                                    {'hash2': cell(hmacs), 'openssl': cell(hmacs)})]},
            {'name': 'argon2id', 'macro': 'ARGON2ID', 'tag': 'kdfs::argon2id',
             'chapter': 'password_hashing', 'standard': 'RFC 9106', 'overridable': True,
             'functions': [function('argon2id', 'kdfs::argon2id', 'function',
                                    {'sodium': cell(None)})]},
        ],
    }


# Made-up sizes and times per backend: hash2 the smallest, OpenSSL the fastest natively.
SIZES = {'hash2': 20000, 'sodium': 30000, 'bearssl': 40000, 'openssl': 900000}
TIMES = {'hash2': 1000.0, 'sodium': 1500.0, 'bearssl': 2000.0, 'openssl': 400.0}


def throughput(median: float, spread: float = 0.02) -> dict[str, Any]:
    runs = [median * (1 - spread), median, median * (1 + spread)]
    return {'repetitions': 1, 'invocations': 1, 'runs_per_invocation': 3,
            'invocation_medians_ns': [median], 'median_ns': median,
            'min_ns': min(runs), 'max_ns': max(runs)}


@functools.cache
def result_of(operation: str, hmac: str | None) -> str:
    """The value Python computes for the operation, as measure.py checks it, else one made up;
    measure.py is loaded once, and each value computed once."""
    python_value = measure_module()['python_value']
    return python_value(operation, hmac) or f'{operation}-{hmac}'.encode().hex()


@functools.cache
def measure_module() -> dict[str, Any]:
    """measure.py's names, loaded once."""
    return runpy.run_path(str(MEASURE))


def measured(table: dict[str, Any]) -> dict[str, Any]:
    """Measurements of every cell of the table on every target of its backend, as the fixture's
    SIZES and TIMES say, every result the same per operation and hmac."""
    records = []
    targets_of = {b['name']: b['targets'] for b in table['backends']}
    for algorithm in table['algorithms']:
        for function in algorithm['functions']:
            for name, c in function['backends'].items():
                hmacs = [h for h in ('hmac_sha2_256', 'hmac_sha2_512')
                         if c['hmacs'] and h in c['hmacs']] or [None]
                for hmac in hmacs:
                    for target in targets_of[name]:
                        scale = 1 if target == 'native' else 2
                        records.append({
                            'operation': function['name'], 'hmac': hmac, 'backend': name,
                            'target': target, 'size_bytes': SIZES[name] * scale,
                            'result': result_of(function['name'], hmac),
                            'throughput': throughput(TIMES[name] * scale)})
    return {
        'date': '2026-11-15',
        'machine': {'cpu': 'fixture', 'cores': 18, 'memory_gib': 128, 'os': 'fixture'},
        'load_average_before_after': [[30.0, 30.0, 30.0], [31.0, 30.0, 30.0]],
        'loaded': True,
        'toolchains': {t: f'{t} compiler 1.0' for t in TARGETS},
        'runtimes': {'wasip2': 'wasmtime 1', 'wasip3': 'wasmtime 1', 'emscripten': 'node 1'},
        'strip': 'strip',
        'records': records,
    }


def library(scratch: Path, name: str = 'hash') -> Path:
    directory = scratch / name
    (directory / 'doc').mkdir(parents=True)
    (directory / 'include/webcpp/hash/detail').mkdir(parents=True)
    (directory / 'test/measure').mkdir(parents=True)
    (directory / 'doc/capabilities.json').write_text(json.dumps(capabilities(), indent=4) + '\n')
    return directory


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(MEASURE), *args], cwd=ROOT, capture_output=True,
                          text=True, check=False)


def passes(done: subprocess.CompletedProcess[str]) -> None:
    if done.returncode != 0:
        raise AssertionError(f'exit {done.returncode}\n{done.stdout}{done.stderr}')


def fails(done: subprocess.CompletedProcess[str], *texts: str, status: int = 1) -> None:
    if done.returncode != status:
        raise AssertionError(f'exit {done.returncode}, not {status}\n{done.stdout}{done.stderr}')
    for text in texts:
        if text not in done.stderr:
            raise AssertionError(f'{text!r} is not in the error:\n{done.stderr}')


def write_measured(scratch: Path, data: dict[str, Any], name: str = 'measured.json') -> Path:
    path = scratch / name
    path.write_text(json.dumps(data, indent=2) + '\n')
    return path


def written(directory: Path, data: dict[str, Any], scratch: Path) -> None:
    passes(run('--library', str(directory), '--write', '--measured',
               str(write_measured(scratch, data, f'{directory.name}.json'))))


def changed(data: dict[str, Any], keep: Callable[[dict], bool],
            change: Callable[[dict], None]) -> dict[str, Any]:
    data = copy.deepcopy(data)
    for record in data['records']:
        if keep(record):
            change(record)
    return data


def row(operation: str, hmac: str | None, target: str) -> Callable[[dict], bool]:
    return lambda r: (r['operation'], r['hmac'], r['target']) == (operation, hmac, target)


def test_write_renders_deterministically(scratch: Path) -> None:
    data = measured(capabilities())
    one, two = library(scratch, 'one'), library(scratch, 'two')
    written(one, data, scratch)
    written(two, data, scratch)
    for output in OUTPUTS:
        a, b = (one / output).read_bytes(), (two / output).read_bytes()
        if a != b:
            raise AssertionError(f'{output} differs between two writes of the same data')
    ranking = (one / 'include/webcpp/hash/detail/ranking.hpp').read_text()
    expected = ('struct ranking<kdfs::hkdf, hmac_sha2_512> {', 'Generated by',
                'backend_list<backends::openssl, backends::hash2, backends::sodium, '
                'backends::bearssl>', 'WEBCPP_TARGET_EMSCRIPTEN')
    for text in expected:
        if text not in ranking:
            raise AssertionError(f'{text!r} is not in ranking.hpp:\n{ranking}')
    table = json.loads((one / 'doc/measurements.json').read_text())
    keys = {(r['operation'], r['hmac'], r['backend'], r['target']) for r in table['records']}
    if ('pbkdf2', 'hmac_sha2_512', 'openssl', 'wasip3') not in keys:
        raise AssertionError('measurements.json lacks a record of its measured data')
    page = (one / 'doc/measurements.adoc').read_text()
    for text in ('WARNING: the machine was shared and loaded', '| hkdf_extract',
                 'The default of each key derivation'):
        if text not in page:
            raise AssertionError(f'{text!r} is not in measurements.adoc')
    cells = (one / 'test/measure/cells.jam').read_text()
    for text in ('measure-cell hkdf_bearssl_hmac_sha2_256 : hkdf_bearssl.cpp\n',
                 'measure-cell pbkdf2_openssl_hmac_sha2_512 : pbkdf2_openssl.cpp\n'
                 '  : /third_party//openssl : hmac_sha2_512 : native wasip2 wasip3 ;\n',
                 'measure-cell sha2_256_hash2 : sha2_256_hash2.cpp\n'
                 '  : : : native wasip2 wasip3 emscripten ;\n'):
        if text not in cells:
            raise AssertionError(f'{text!r} is not in cells.jam:\n{cells}')


def test_check_passes_on_its_own_write(scratch: Path) -> None:
    data = measured(capabilities())
    directory = library(scratch)
    written(directory, data, scratch)
    passes(run('--library', str(directory), '--check', '--measured',
               str(write_measured(scratch, data))))


def test_check_fails_when_a_size_order_changes(scratch: Path) -> None:
    data = measured(capabilities())
    directory = library(scratch)
    written(directory, data, scratch)

    def smaller(record: dict) -> None:
        if record['backend'] == 'sodium':
            record['size_bytes'] = 100

    again = changed(data, row('hkdf', 'hmac_sha2_256', 'wasip3'), smaller)
    fails(run('--library', str(directory), '--check', '--measured',
              str(write_measured(scratch, again))),
          'hkdf over hmac_sha2_256 on wasip3', 'by size', WRITE)


def test_throughput_moving_under_ten_percent_keeps_the_order(scratch: Path) -> None:
    data = measured(capabilities())
    for record in data['records']:
        if record['operation'] == 'pbkdf2' and record['target'] == 'native':
            record['throughput'] = throughput(1000.0 if record['backend'] == 'openssl'
                                              else 1200.0)
    directory = library(scratch)
    written(directory, data, scratch)
    table = json.loads((directory / 'doc/measurements.json').read_text())
    order = next(o for o in table['orders'] if (o['operation'], o['hmac'], o['target'])
                 == ('pbkdf2', 'hmac_sha2_256', 'native'))
    if order['by_throughput'] != ['openssl', 'hash2']:
        raise AssertionError(f'the first order is {order["by_throughput"]}')

    def faster(median: float) -> Callable[[dict], None]:
        def change(record: dict) -> None:
            if record['backend'] == 'hash2':
                record['throughput'] = throughput(median)
        return change

    # hash2 now 5 percent faster than OpenSSL: noise, the order stays.
    a_little = changed(data, row('pbkdf2', 'hmac_sha2_256', 'native'), faster(952.0))
    passes(run('--library', str(directory), '--check', '--measured',
               str(write_measured(scratch, a_little))))
    # 25 percent faster, the spreads apart: the order changes.
    much = changed(data, row('pbkdf2', 'hmac_sha2_256', 'native'), faster(750.0))
    fails(run('--library', str(directory), '--check', '--measured',
              str(write_measured(scratch, much))),
          'pbkdf2 over hmac_sha2_256 on native', 'by throughput', WRITE)


def test_the_spread_plays_no_part_in_an_order(scratch: Path) -> None:
    # Ruling R33: spec 4.2's rule alone. A first measurement orders by the medians, however
    # close (OpenSSL 5 percent faster leads); a committed order changes when a median is more
    # than 10 percent below the one ahead of it, however wide the runs' spread.
    data = measured(capabilities())
    for record in data['records']:
        if record['operation'] == 'pbkdf2' and record['target'] == 'native':
            record['throughput'] = throughput(1000.0 if record['backend'] == 'openssl'
                                              else 1050.0)
    directory = library(scratch)
    written(directory, data, scratch)
    table = json.loads((directory / 'doc/measurements.json').read_text())
    order = next(o for o in table['orders'] if (o['operation'], o['hmac'], o['target'])
                 == ('pbkdf2', 'hmac_sha2_256', 'native'))
    if order['by_throughput'] != ['openssl', 'hash2']:
        raise AssertionError(f'the medians do not order a first measurement: {order}')

    def noisy(record: dict) -> None:
        if record['backend'] == 'hash2':
            record['throughput'] = throughput(800.0, spread=0.5)

    again = changed(data, row('pbkdf2', 'hmac_sha2_256', 'native'), noisy)
    fails(run('--library', str(directory), '--check', '--measured',
              str(write_measured(scratch, again))),
          'pbkdf2 over hmac_sha2_256 on native', 'by throughput', WRITE)


def test_each_operation_has_its_own_ranking(scratch: Path) -> None:
    # hkdf_extract's default reads its own row (spec 4.1's smallest per operation): libsodium's
    # extract program is the smaller on emscripten while whole HKDF's order puts hash2 first.
    data = measured(capabilities())

    def sodium_smaller(record: dict) -> None:
        if record['backend'] == 'sodium':
            record['size_bytes'] = 100

    data = changed(data, lambda r: (r['operation'], r['target']) == ('hkdf_extract',
                                                                      'emscripten'),
                   sodium_smaller)
    directory = library(scratch)
    written(directory, data, scratch)
    ranking = ' '.join((directory / 'include/webcpp/hash/detail/ranking.hpp').read_text()
                       .split())
    emscripten = ranking.split('#elif defined(WEBCPP_TARGET_EMSCRIPTEN)')[1].split('#else')[0]
    for text in ('struct ranking<kdfs::hkdf_extract, Hmac> { /** The smallest program first. */ '
                 'using by_size = backend_list<backends::sodium, backends::hash2',
                 'struct ranking<kdfs::hkdf_expand, hmac_sha2_512> {',
                 'struct ranking<kdfs::hkdf, Hmac> { /** The smallest program first. */ '
                 'using by_size = backend_list<backends::hash2'):
        if text not in emscripten:
            raise AssertionError(f'{text!r} is not in ranking.hpp on emscripten:\n{emscripten}')


def test_another_native_toolchain_compares_no_native_order(scratch: Path) -> None:
    # Ruling R34: the native orders hold for the toolchain that measured them. Measured with
    # another, a native order that differs is said in one line and not compared; a WebAssembly
    # order still is.
    data = measured(capabilities())
    data['native_toolchain'] = {'compiler': 'A 1', 'os': 'Darwin', 'processor': 'arm64',
                                'strip': '/usr/bin/strip'}
    directory = library(scratch)
    written(directory, data, scratch)

    def smaller(record: dict) -> None:
        if record['backend'] == 'openssl':
            record['size_bytes'] = 1

    other = changed(data, row('hkdf', 'hmac_sha2_256', 'native'), smaller)
    other['native_toolchain'] = {'compiler': 'B 2', 'os': 'Linux', 'processor': 'x86_64',
                                 'strip': '/usr/bin/strip'}
    done = run('--library', str(directory), '--check', '--measured',
               str(write_measured(scratch, other)))
    passes(done)
    if 'measured with A 1 on Darwin arm64' not in done.stdout or 'B 2 on Linux' not in done.stdout:
        raise AssertionError(f'no line says the native orders are not compared:\n{done.stdout}')
    fails(run('--library', str(directory), '--check', '--measured',
              str(write_measured(scratch, changed(other, row('hkdf', 'hmac_sha2_256', 'wasip2'),
                                                  smaller)))),
          'hkdf over hmac_sha2_256 on wasip2', 'by size', WRITE)
    same = copy.deepcopy(other)
    same['native_toolchain'] = data['native_toolchain']
    fails(run('--library', str(directory), '--check', '--measured',
              str(write_measured(scratch, same))),
          'hkdf over hmac_sha2_256 on native', 'by size', WRITE)


def test_a_hand_edit_fails(scratch: Path) -> None:
    data = measured(capabilities())
    directory = library(scratch)
    written(directory, data, scratch)
    measured_file = str(write_measured(scratch, data))
    for output in OUTPUTS[1:]:
        path = directory / output
        original = path.read_text()
        path.write_text(original.replace('hash2', 'hash3', 1))
        fails(run('--library', str(directory), '--check', '--measured', measured_file),
              output, WRITE)
        path.write_text(original)
    path = directory / 'doc/measurements.json'
    original = path.read_text()
    path.write_text(original.replace('"size_bytes": 20000', '"size_bytes": 20001', 1))
    fails(run('--library', str(directory), '--check', '--measured', measured_file),
          'doc/measurements.json', 'edited by hand', WRITE)
    path.write_text(original)
    passes(run('--library', str(directory), '--check', '--measured', measured_file))


def test_a_missing_program_fails(scratch: Path) -> None:
    data = measured(capabilities())
    directory = library(scratch)
    written(directory, data, scratch)
    lists = scratch / 'lists'
    lists.mkdir()
    programs = []
    for target in TARGETS:
        for optimization in ('space', 'speed'):
            names = [f'{optimization}-{r["operation"]}_{r["backend"]}'
                     + (f'_{r["hmac"]}' if r['hmac'] else '')
                     for r in data['records'] if r['target'] == target]
            if (target, optimization) == ('wasip2', 'space'):
                names = [n for n in names if 'hkdf_sodium_hmac_sha2_512' not in n]
            suffix = '.wasm' if target in ('wasip2', 'wasip3') else (
                '.js' if target == 'emscripten' else '')
            path = lists / f'measure-programs-{target}-{optimization}.txt'
            path.write_text(''.join(f'{lists}/{name}{suffix}\n' for name in names))
            programs.append(str(path))
    fails(run('--library', str(directory), '--check', '--programs', *programs),
          'space-hkdf_sodium_hmac_sha2_512 on wasip2', 'built nothing')
    # A target whose list is missing altogether.
    fails(run('--library', str(directory), '--check', '--programs', *programs[2:]),
          'native', 'built nothing')


def test_every_order_names_every_backend(scratch: Path) -> None:
    data = measured(capabilities())
    for record in data['records']:
        if record['operation'] == 'hkdf' and record['backend'] == 'bearssl':
            record['size_bytes'] = 1
            record['throughput'] = throughput(1.0)
    directory = library(scratch)
    written(directory, data, scratch)
    ranking = (directory / 'include/webcpp/hash/detail/ranking.hpp').read_text()
    orders = [line for line in ranking.splitlines() if 'backend_list<' in line
              or line.strip().startswith('backends::')]
    joined = ' '.join(ranking.split())
    if 'using portable_order = backend_list<backends::hash2, backends::sodium, ' \
       'backends::bearssl>;' not in joined:
        raise AssertionError(f'the portable order is not hash2, sodium, bearssl:\n{ranking}')
    lists = [part.split('>;')[0] for part in joined.split('= backend_list<')[1:]]
    if not orders or not lists:
        raise AssertionError('ranking.hpp holds no order')
    for order in lists:
        named = {b.strip() for b in order.split(',')}
        if order.startswith('backends::hash2, backends::sodium, backends::bearssl') and \
           len(named) == 3:
            continue  # portable_order
        wanted = {'backends::hash2', 'backends::sodium', 'backends::bearssl',
                  'backends::openssl'}
        if named != wanted:
            raise AssertionError(f'an order names {sorted(named)}, not every backend')
    if 'backend_list<backends::bearssl, backends::hash2' not in joined:
        raise AssertionError('BearSSL, the smallest and fastest, leads no order of HKDF')


def test_capabilities_renders_the_table(scratch: Path) -> None:
    directory = library(scratch)
    passes(run('--library', str(directory), '--capabilities'))
    page = (directory / 'doc/backends.adoc').read_text()
    for text in ('| hkdf_extract', '| argon2id', 'not stated', 'emscripten', 'openssl',
                 'Generated by'):
        if text not in page:
            raise AssertionError(f'{text!r} is not in backends.adoc:\n{page}')
    first = page
    passes(run('--library', str(directory), '--capabilities'))
    if (directory / 'doc/backends.adoc').read_text() != first:
        raise AssertionError('--capabilities renders differently twice')


def test_the_real_library_s_generated_files_are_its_data_s(_: Path) -> None:
    # Review Focus 9 without the lane: every generated file of libs/hash is what its committed
    # data and capability table render, and the data's digest holds (no b2, no program).
    passes(run('--library', str(LIBRARY), '--check', '--measured',
               str(LIBRARY / 'doc/measurements.json')))


def test_overrides_regenerate_the_committed_file(scratch: Path) -> None:
    directory = scratch / 'hash'
    (directory / 'include/webcpp/hash/detail').mkdir(parents=True)
    (directory / 'doc').mkdir()
    shutil.copy(LIBRARY / 'doc/capabilities.json', directory / 'doc/capabilities.json')
    passes(run('--library', str(directory), '--overrides'))
    ours = (directory / 'include/webcpp/hash/detail/overrides.hpp').read_text()
    committed = (LIBRARY / 'include/webcpp/hash/detail/overrides.hpp').read_text()
    if ours != committed:
        raise AssertionError('--overrides does not give the committed detail/overrides.hpp')


def test_usage_errors_exit_2(scratch: Path) -> None:
    directory = library(scratch)
    fails(run('--library', str(directory)), 'one of', status=2)
    fails(run('--library', str(directory), '--check', '--measured', 'a', '--programs', 'b'),
          '--measured and --programs', status=2)
    fails(run('--library', str(scratch / 'nowhere'), '--capabilities'),
          'capabilities.json', status=2)


CASES = [
    test_write_renders_deterministically,
    test_check_passes_on_its_own_write,
    test_check_fails_when_a_size_order_changes,
    test_throughput_moving_under_ten_percent_keeps_the_order,
    test_the_spread_plays_no_part_in_an_order,
    test_each_operation_has_its_own_ranking,
    test_another_native_toolchain_compares_no_native_order,
    test_a_hand_edit_fails,
    test_a_missing_program_fails,
    test_every_order_names_every_backend,
    test_capabilities_renders_the_table,
    test_the_real_library_s_generated_files_are_its_data_s,
    test_overrides_regenerate_the_committed_file,
    test_usage_errors_exit_2,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'hash_measure_test: no case named {", ".join(sorted(unknown))}', file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp hash measure ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('hash_measure_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
