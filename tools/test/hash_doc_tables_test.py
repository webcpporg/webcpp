#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks tools/hash/doc_tables.py, the generated tables of webcpp::hash's guide, on a copy of
the real library's doc/capabilities.json and doc/guide.json in a scratch library. `--write`
renders the comparison table of every chapter, the backends of every algorithm, the decision
table, the includes of the measured chapters and llms.txt, the same bytes each time; `--check`
passes on what it wrote, and fails naming `python3 tools/hash/doc_tables.py --write` when a
generated file was edited by hand, is missing or is left over. A guide that lacks a function of
the capability table, or describes one it does not have, fails, and so does a use case whose
example is not there. Without doc/measurements.json the tables say so and carry no measured
column; with it (a fixture in its shape) they carry the throughput and the size, and the default
of `hkdf_extract` on Emscripten follows the step's own measured order, not HKDF's, as
detail/ranking.hpp does. The includes of the measured chapters name only those present. And
`--check` passes on the real library's committed files. Run with the names of some cases to run
only those."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / 'tools/hash/doc_tables.py'
LIBRARY = ROOT / 'libs/hash'
WRITE = 'python3 tools/hash/doc_tables.py --write'


def run(library: Path, mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOL), mode, '--library', str(library)],
                          capture_output=True, text=True, check=False)


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def scratch_library(scratch: Path) -> Path:
    """A library with the real capability table and guide, and an example file for each use
    case."""
    library = scratch / 'hash'
    (library / 'doc').mkdir(parents=True)
    (library / 'example').mkdir()
    for name in ('capabilities.json', 'guide.json'):
        shutil.copy(LIBRARY / 'doc' / name, library / 'doc' / name)
    guide = json.loads((library / 'doc/guide.json').read_text(encoding='utf-8'))
    for case in guide['use_cases']:
        (library / 'example' / case['example']).write_text('// fixture\n', encoding='utf-8')
    return library


def written(library: Path) -> dict[str, str]:
    doc = library / 'doc'
    files = {str(p.relative_to(doc)): p.read_text(encoding='utf-8')
             for p in (doc / 'generated').glob('*.adoc')}
    files['llms.txt'] = (doc / 'llms.txt').read_text(encoding='utf-8')
    return files


def write_ok(library: Path) -> dict[str, str]:
    done = run(library, '--write')
    expect(done.returncode == 0, f'--write failed: {done.stderr}')
    return written(library)


def measurements(library: Path) -> dict:
    """doc/measurements.json's shape (tools/hash/measure.py), for HKDF's three operations and
    sha2_256: HKDF is smallest on BearSSL, then sodium, then hash2; each step alone is smallest
    on hash2, then sodium (an order of its own, which HKDF's must not replace)."""
    records = []
    whole = {'hash2': 3000, 'sodium': 2000, 'bearssl': 1000, 'openssl': 9000}
    step = {'hash2': 1500, 'sodium': 2000, 'openssl': 9000}
    for operation, sizes in (('hkdf', whole), ('hkdf_extract', step),
                             ('hkdf_expand', step)):
        for backend in sizes:
            for target in ('native', 'wasip2', 'wasip3', 'emscripten'):
                if backend == 'openssl' and target == 'emscripten':
                    continue
                records.append({'operation': operation, 'hmac': 'hmac_sha2_256',
                                'backend': backend, 'target': target,
                                'size_bytes': sizes[backend],
                                'throughput': {'median_ns': 1000.0 + sizes[backend],
                                               'min_ns': 1.0, 'max_ns': 2.0},
                                'throughput_absent': None})
    records.append({'operation': 'sha2_256', 'hmac': None, 'backend': 'hash2',
                    'target': 'native', 'size_bytes': 33776,
                    'throughput': {'median_ns': 1757469.0, 'min_ns': 1.0, 'max_ns': 2.0},
                    'throughput_absent': None})
    records.append({'operation': 'sha2_256', 'hmac': None, 'backend': 'hash2',
                    'target': 'emscripten', 'size_bytes': 19235,
                    'throughput': None, 'throughput_absent': 'fixture'})
    orders = []
    for operation, sizes in (('hkdf', whole), ('hkdf_extract', step),
                             ('hkdf_expand', step)):
        for target in ('native', 'wasip2', 'wasip3', 'emscripten'):
            have = [r['backend'] for r in records
                    if r['operation'] == operation and r['target'] == target]
            orders.append({'operation': operation, 'hmac': 'hmac_sha2_256', 'target': target,
                           'by_size': sorted(have, key=lambda b: sizes[b]),
                           'by_throughput': sorted(have, key=lambda b: sizes[b]),
                           'throughput_from': target})
    data = {'date': '2026-11-15', 'machine': {'cpu': 'Fixture CPU'}, 'loaded': True,
            'records': records, 'orders': orders}
    (library / 'doc/measurements.json').write_text(json.dumps(data), encoding='utf-8')
    return data


def test_write_is_deterministic(scratch: Path) -> None:
    library = scratch_library(scratch)
    first = write_ok(library)
    second = write_ok(library)
    expect(first == second, 'two --write runs differ')
    for chapter in ('digests', 'macs', 'kdfs', 'password-hashing', 'non-cryptographic'):
        expect(f'generated/compare-{chapter}.adoc' in first, f'no comparison table of {chapter}')
    expect('generated/backends-hkdf.adoc' in first, 'no backends of HKDF')
    expect('generated/choose.adoc' in first, 'no decision table')
    expect('generated/measured.adoc' in first, 'no includes of the measured chapters')
    for text in first.values():
        expect(chr(0x2014) not in text, 'an em dash in a generated file')


def test_check_passes_on_what_write_wrote(scratch: Path) -> None:
    library = scratch_library(scratch)
    write_ok(library)
    done = run(library, '--check')
    expect(done.returncode == 0, f'--check failed: {done.stderr}')


def test_a_hand_edit_fails(scratch: Path) -> None:
    library = scratch_library(scratch)
    write_ok(library)
    path = library / 'doc/generated/compare-digests.adoc'
    path.write_text(path.read_text(encoding='utf-8') + 'edited\n', encoding='utf-8')
    done = run(library, '--check')
    expect(done.returncode == 1, 'a hand edit passed --check')
    expect('compare-digests.adoc differs' in done.stderr and WRITE in done.stderr,
           f'the fault does not name the file and the command: {done.stderr}')


def test_a_missing_or_left_over_file_fails(scratch: Path) -> None:
    library = scratch_library(scratch)
    write_ok(library)
    (library / 'doc/llms.txt').unlink()
    (library / 'doc/generated/backends-gone.adoc').write_text('x\n', encoding='utf-8')
    done = run(library, '--check')
    expect(done.returncode == 1, 'a missing and a left-over file passed --check')
    expect('doc/llms.txt is missing' in done.stderr, done.stderr)
    expect('backends-gone.adoc is left over' in done.stderr, done.stderr)
    write_ok(library)
    expect(not (library / 'doc/generated/backends-gone.adoc').exists(),
           '--write left a file no data renders')


def test_the_guide_covers_the_capability_table(scratch: Path) -> None:
    library = scratch_library(scratch)
    path = library / 'doc/guide.json'
    guide = json.loads(path.read_text(encoding='utf-8'))
    del guide['functions']['blake3']
    guide['functions']['sha4_256'] = guide['functions']['sha2_256']
    path.write_text(json.dumps(guide), encoding='utf-8')
    done = run(library, '--write')
    expect(done.returncode == 1, 'an incomplete guide was rendered')
    expect('no entry for blake3' in done.stderr, done.stderr)
    expect('describes sha4_256' in done.stderr, done.stderr)


def test_a_use_case_names_an_example_that_is_there(scratch: Path) -> None:
    library = scratch_library(scratch)
    (library / 'example/hkdf.cpp').unlink()
    done = run(library, '--write')
    expect(done.returncode == 1, 'a use case with no example was rendered')
    expect('example/hkdf.cpp, which is not there' in done.stderr, done.stderr)


def test_without_measurements_the_tables_say_so(scratch: Path) -> None:
    library = scratch_library(scratch)
    files = write_ok(library)
    expect('Fastest natively' not in files['generated/compare-digests.adoc'],
           'a measured column without measurements')
    expect('does not have yet' in files['generated/compare-digests.adoc'],
           'the comparison table does not say its measurements are missing')
    expect('detail/ranking.hpp' in files['generated/backends-hkdf.adoc'],
           'the backends of HKDF do not say which order applies')
    expect('Backends: hash2 (/webcpp/hash//hash' in files['llms.txt'], 'llms.txt has no backends')


def test_with_measurements_the_tables_carry_them(scratch: Path) -> None:
    library = scratch_library(scratch)
    measurements(library)
    files = write_ok(library)
    digests = files['generated/compare-digests.adoc']
    expect('Fastest natively' in digests, 'no measured column')
    expect('569 MiB/s (hash2)' in digests, 'sha2_256 throughput: 1 MiB in 1.757 ms')
    expect('19,235 bytes (hash2)' in digests, 'sha2_256 size on Emscripten')
    hkdf = files['generated/backends-hkdf.adoc']
    # Each step on Emscripten: its own order hash2, sodium; HKDF's would give sodium, hash2.
    for name in ('hkdf_extract', 'hkdf_expand'):
        rows = hkdf.split(f'default backend of `{name}`')[1].split('|===')[1]
        emscripten = rows.split('| emscripten')[1].split('\n\n')[0]
        expect('| hash2, sodium\n| hash2, sodium\n| hash2, sodium\n| hash2' in emscripten,
               f'{name} on Emscripten does not follow its own order: {emscripten!r}')
    expect('own orders' in hkdf and '`hmac_sha2_512`' in hkdf,
           'HKDF\'s note does not say that another hmac has its own orders')
    expect('hmac_sha2_256' not in files['generated/backends-argon2id.adoc'],
           'Argon2id\'s note names an hmac it does not have')
    expect('a loaded, shared machine' in digests, 'the note hides that the machine was loaded')
    expect('libsodium 1.0.22: its headers state constant time' in hkdf,
           'the constant-time column does not give its source')
    whole = hkdf.split('default backend of `hkdf`')[1].split('|===')[1]
    native = whole.split('| native')[1].split('\n\n')[0]
    expect('| bearssl, sodium, hash2, openssl' in native, f'hkdf natively: {native!r}')


def test_no_table_is_a_matrix(scratch: Path) -> None:
    # The page scrolls a table of eight columns or more, a matrix, in its box rather than stack
    # it (tools/doc/postprocess.mjs, MATRIX), at 1440px too. A chapter's comparison is two tables
    # instead, what each function is and how to choose it, each led by the name and each under
    # eight columns, with the measured columns or without them.
    library = scratch_library(scratch)
    for measured in (False, True):
        if measured:
            measurements(library)
        files = write_ok(library)
        for name, text in files.items():
            for table in text.split('|===')[1::2]:
                header = table.strip().split('\n')[0]
                expect(header.count('| ') < 8, f'{name} ({measured}): a matrix: {header}')
        digests = files['generated/compare-digests.adoc']
        headers = [table.strip().split('\n')[0] for table in digests.split('|===')[1::2]]
        expect(len(headers) == 2 and all(h.startswith('| Name |') for h in headers), str(headers))
        expect('Security' in headers[0] and 'Choose it when' in headers[1], str(headers))
        expect(('Fastest natively' in headers[1]) == measured, str(headers))


def test_measured_chapters_are_included_when_present(scratch: Path) -> None:
    library = scratch_library(scratch)
    (library / 'doc/performance.adoc').write_text('x\n', encoding='utf-8')
    files = write_ok(library)
    measured = files['generated/measured.adoc']
    expect('include::../performance.adoc[]' in measured, 'performance.adoc not included')
    expect('include::../backends.adoc[]' not in measured, 'an absent chapter is included')
    expect('`doc/backends.adoc` (tools/hash/measure.py --capabilities)' in measured,
           'the absent chapter is not named')
    for name in ('backends.adoc', 'measurements.adoc', 'allocation.adoc'):
        (library / 'doc' / name).write_text('x\n', encoding='utf-8')
    measured = write_ok(library)['generated/measured.adoc']
    expect('NOTE' not in measured, 'a note with every chapter present')
    expect(measured.index('backends.adoc') < measured.index('measurements.adoc')
           < measured.index('performance.adoc') < measured.index('allocation.adoc'),
           'the measured chapters are out of order')


def test_the_real_library_s_files_are_its_data_s(scratch: Path) -> None:
    del scratch
    done = run(LIBRARY, '--check')
    expect(done.returncode == 0, f'the committed files are stale: {done.stderr}')


CASES: list[Callable[[Path], None]] = [
    test_write_is_deterministic,
    test_check_passes_on_what_write_wrote,
    test_a_hand_edit_fails,
    test_a_missing_or_left_over_file_fails,
    test_the_guide_covers_the_capability_table,
    test_a_use_case_names_an_example_that_is_there,
    test_without_measurements_the_tables_say_so,
    test_with_measurements_the_tables_carry_them,
    test_no_table_is_a_matrix,
    test_measured_chapters_are_included_when_present,
    test_the_real_library_s_files_are_its_data_s,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'hash_doc_tables_test: no case named {", ".join(sorted(unknown))}',
              file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp hash doc tables ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('hash_doc_tables_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
