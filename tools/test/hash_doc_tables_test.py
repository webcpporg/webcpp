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
example is not there, and so does a function of the capability table without a default. Every
function's default is the capability table's, `hash2` for HKDF whatever the measurements say. A
family's tag (spec 2.15) names a default of the order hash2, xkcp, blake3, sodium, or none, and
one whose cell comes in a later increment is said so; a partial cell says what it refuses.
Without doc/measurements.json the tables say so, carry no measured column and render no
measurements.adoc; with it (a fixture in its shape) they carry the throughput and the size, and
measurements.adoc renders it as the dated reference that decides nothing; a hand edit of the
data, which its digest tells, fails. The includes of the measured chapters name only those
present. And `--check` passes on the real library's committed files. Run with the names of some
cases to run only those."""

from __future__ import annotations

import hashlib
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
    for name in ('backends.adoc', 'measurements.adoc'):
        if (doc / name).is_file():
            files[name] = (doc / name).read_text(encoding='utf-8')
    return files


def write_ok(library: Path) -> dict[str, str]:
    done = run(library, '--write')
    expect(done.returncode == 0, f'--write failed: {done.stderr}')
    return written(library)


def digest_of(data: dict) -> str:
    body = {k: v for k, v in data.items() if k != 'digest'}
    return 'sha256:' + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def measurements(library: Path) -> dict:
    """doc/measurements.json's shape, for HKDF's three operations and sha2_256: HKDF is smallest
    and fastest on BearSSL, then sodium, then hash2, which must not move its default."""
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
    data = {'date': '2026-11-15',
            'machine': {'cpu': 'Fixture CPU', 'cores': 2, 'memory_gib': 4, 'os': 'Fixture OS'},
            'loaded': True, 'load_average_before_after': [[9.0, 8.0, 7.0], [6.0, 5.0, 4.0]],
            'toolchains': {'native': 'Fixture clang'},
            'runtimes': {'wasip2': 'Fixture wasmtime', 'emscripten': 'Fixture node'},
            'native_toolchain': {}, 'workloads': {'hkdf': 'one derivation'},
            'rules': {'size': 'fixture sizes', 'throughput': 'fixture throughput'},
            'records': records}
    data['digest'] = digest_of(data)
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


def test_every_function_names_its_default(scratch: Path) -> None:
    library = scratch_library(scratch)
    path = library / 'doc/capabilities.json'
    table = json.loads(path.read_text(encoding='utf-8'))
    for algorithm in table['algorithms']:
        for function in algorithm['functions']:
            if function['name'] == 'pbkdf2':
                function['default'] = None
            if function['name'] == 'sha2_256':
                function['default'] = 'hash2'
    path.write_text(json.dumps(table), encoding='utf-8')
    done = run(library, '--write')
    expect(done.returncode == 1, 'a function without a default was rendered')
    expect('the function pbkdf2 has no default' in done.stderr, done.stderr)
    expect('the type sha2_256 has a default' in done.stderr, done.stderr)


def family_row(table: dict, name: str) -> dict:
    for algorithm in table['algorithms']:
        for function in algorithm['functions']:
            if function['name'] == name:
                return function
    raise AssertionError(f'no row {name}')


def test_a_family_default_is_of_the_order_or_none(scratch: Path) -> None:
    library = scratch_library(scratch)
    path = library / 'doc/capabilities.json'
    table = json.loads(path.read_text(encoding='utf-8'))
    family_row(table, 'digests::sha2_256')['default'] = 'openssl'
    family_row(table, 'macs::hmac<digests::sha2_256>')['default'] = None
    path.write_text(json.dumps(table), encoding='utf-8')
    done = run(library, '--write')
    expect(done.returncode == 1, 'a family default outside the order was rendered')
    expect('the tag digests::sha2_256 has the default openssl' in done.stderr, done.stderr)
    expect('hmac<digests::sha2_256>' not in done.stderr, f'none is a default: {done.stderr}')

    family_row(table, 'digests::sha2_256')['default'] = 'hash2'
    path.write_text(json.dumps(table), encoding='utf-8')
    files = write_ok(library)
    hmac = files['generated/backends-hmac.adoc']
    expect('`macs::hmac<digests::sha2_256>` has no default backend: the call names one' in hmac,
           hmac)
    expect('| macs::hmac<digests::sha2_256>\n| none: the call names its backend'
           in files['backends.adoc'], 'the default backends do not say none')


def test_a_later_default_and_a_partial_cell_are_said(scratch: Path) -> None:
    library = scratch_library(scratch)
    files = write_ok(library)
    shake = files['generated/backends-sha3-shake.adoc']
    expect('The default of `digests::shake_128` is `xkcp`, whose cell comes with a later '
           'increment' in shake, shake)
    expect('`hash2` (partial: an output past 32 bytes, one Boost.Hash2 result)' in shake, shake)
    expect('| hash2 (partial: an output past 64 bytes' in files['backends.adoc'],
           'the backends chapter does not say what the partial cell refuses')


def test_without_measurements_the_tables_say_so(scratch: Path) -> None:
    library = scratch_library(scratch)
    files = write_ok(library)
    expect('Fastest natively' not in files['generated/compare-digests.adoc'],
           'a measured column without measurements')
    expect('does not have yet' in files['generated/compare-digests.adoc'],
           'the comparison table does not say its measurements are missing')
    expect('measurements.adoc' not in files, 'measurements.adoc without its data')
    hkdf = files['generated/backends-hkdf.adoc']
    expect('The default of `hkdf_extract`, `hkdf_expand` and `hkdf`: `hash2` on every target'
           in hkdf, f'the backends of HKDF do not name the default: {hkdf}')
    expect('`bearssl`, `openssl`, `sodium` only where the call names it' in hkdf, hkdf)
    expect('The default of `argon2id`: `sodium` on every target'
           in files['generated/backends-argon2id.adoc'], 'Argon2id\'s default')
    expect('One backend, `hash2`: the types take no backend.'
           in files['generated/backends-non-cryptographic.adoc'], 'a type\'s backend')
    backends = files['backends.adoc']
    expect('| pbkdf2\n| hash2' in backends and '| scrypt\n| sodium' in backends,
           'backends.adoc does not list the defaults')
    expect('Backends: hash2 (/webcpp/hash//hash' in files['llms.txt'], 'llms.txt has no backends')
    expect('Every key derivation runs on backends::hash2' in files['llms.txt'],
           'llms.txt does not say the default')


def test_with_measurements_the_tables_carry_them(scratch: Path) -> None:
    library = scratch_library(scratch)
    measurements(library)
    files = write_ok(library)
    digests = files['generated/compare-digests.adoc']
    expect('Fastest natively' in digests, 'no measured column')
    expect('569 MiB/s (hash2)' in digests, 'sha2_256 throughput: 1 MiB in 1.757 ms')
    expect('19,235 bytes (hash2)' in digests, 'sha2_256 size on Emscripten')
    expect('a reference measured on 2026-11-15 on Fixture CPU that decides nothing' in digests,
           'the measured columns are not labelled as the reference')
    expect('a loaded, shared machine' in digests, 'the note hides that the machine was loaded')
    hkdf = files['generated/backends-hkdf.adoc']
    # BearSSL is the smallest and the fastest HKDF of the fixture: the default stays hash2.
    expect('`hkdf`: `hash2` on every target' in hkdf, 'the measurements moved a default')
    expect('libsodium 1.0.22: its headers state constant time' in hkdf,
           'the constant-time column does not give its source')
    page = files['measurements.adoc']
    expect('A reference measured once, on 2026-11-15, that decides nothing' in page,
           'measurements.adoc is not labelled as the dated reference')
    expect('`backends::hash2`' in page and 'header-only' in page,
           'measurements.adoc does not say why hash2 is the default')
    expect('WARNING: the machine was shared and loaded' in page, 'the load is hidden')
    expect('| hkdf\n| hmac_sha2_256\n| bearssl\n| 1000\n| 1000\n| 1000\n| 1000' in page,
           'the size table')
    expect('| 569 MiB/s (500000000 to 1000000000)' in page, 'the throughput table')
    expect('orders' not in page.lower(), 'measurements.adoc still shows the orders')


def test_a_hand_edit_of_the_measurements_fails(scratch: Path) -> None:
    library = scratch_library(scratch)
    data = measurements(library)
    data['records'][0]['size_bytes'] = 1
    (library / 'doc/measurements.json').write_text(json.dumps(data), encoding='utf-8')
    done = run(library, '--write')
    expect(done.returncode == 1, 'measurements edited by hand were rendered')
    expect('its digest does not match its content' in done.stderr, done.stderr)


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
    expect('include::../backends.adoc[]' in measured, 'backends.adoc, always rendered, is left out')
    expect('include::../measurements.adoc[]' not in measured, 'an absent chapter is included')
    expect('`doc/measurements.adoc` (this tool, from doc/measurements.json)' in measured,
           'the absent chapter is not named')
    measurements(library)
    (library / 'doc/allocation.adoc').write_text('x\n', encoding='utf-8')
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
    test_every_function_names_its_default,
    test_a_family_default_is_of_the_order_or_none,
    test_a_later_default_and_a_partial_cell_are_said,
    test_without_measurements_the_tables_say_so,
    test_with_measurements_the_tables_carry_them,
    test_a_hand_edit_of_the_measurements_fails,
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
