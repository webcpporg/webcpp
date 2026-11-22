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
example is not there, and so does a function of the capability table without a default that a
backend of the order hash2, xkcp, blake3, sodium has (one that none has, as kbkdf, has none), or
with a default outside that order (bcrypt given botan, kbkdf given openssl). Every
function's default is the capability table's, `hash2` for HKDF whatever the measurements say. A
family's tag (spec 2.15) names a default of the order hash2, xkcp, blake3, sodium, or none, and
one without its cell fails; a partial cell says what it refuses. A tag of `digests` or `macs`
sits in its namespace's chapter. A backend of the asynchronous family alone (backends::webcrypto)
is named so in every table, with its targets as the guide spells them, and is never a default; a
row of an unknown kind fails. Each backend's constant-time statements are one bullet. llms.txt's
defaults are the capability table's, not a text written once.
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
    """A library with the real capability table, guide and public headers, and an example file
    for each use case."""
    library = scratch / 'hash'
    (library / 'doc').mkdir(parents=True)
    (library / 'example').mkdir()
    shutil.copytree(LIBRARY / 'include', library / 'include')
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


def test_a_function_without_a_backend_of_the_order_has_no_default(scratch: Path) -> None:
    """A function that no backend of the order hash2, xkcp, blake3, sodium has (kbkdf, on
    backends::openssl alone) has no default (design D34), and its backends say that the call
    names one; given a backend of the order, it must name its default."""
    library = scratch_library(scratch)
    kbkdf = write_ok(library)['generated/backends-kbkdf.adoc']
    expect('`kbkdf` has no default backend: the call names one of its backends' in kbkdf, kbkdf)

    def hash2_cell(table: dict) -> None:
        family_row(table, 'kbkdf')['backends']['hash2'] = a_cell(4)
    edit_capabilities(library, hash2_cell)
    done = run(library, '--write')
    expect(done.returncode == 1, 'a function of hash2 without a default was rendered')
    expect('the function kbkdf has no default, though hash2' in done.stderr, done.stderr)


def family_row(table: dict, name: str) -> dict:
    for algorithm in table['algorithms']:
        for function in algorithm['functions']:
            if function['name'] == name:
                return function
    raise AssertionError(f'no row {name}')


def test_a_function_s_default_is_of_the_order(scratch: Path) -> None:
    """No measurement or backend outside the order decides a function's default (designs D33 and
    D34): bcrypt, which botan alone has, keeps none; given botan as its default, or kbkdf given
    openssl, each is refused, as a family's tag is."""
    library = scratch_library(scratch)

    def outside_the_order(table: dict) -> None:
        family_row(table, 'bcrypt')['default'] = 'botan'
        family_row(table, 'kbkdf')['default'] = 'openssl'
    edit_capabilities(library, outside_the_order)
    done = run(library, '--write')
    expect(done.returncode == 1, 'a function default outside the order was rendered')
    expect('the function bcrypt has the default botan, which is not one of hash2, xkcp, blake3, '
           'sodium' in done.stderr, done.stderr)
    expect('the function kbkdf has the default openssl' in done.stderr, done.stderr)


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


def test_a_default_without_its_cell_fails_and_a_partial_cell_is_said(scratch: Path) -> None:
    # Every default has its engine once increments 2 to 7 have landed (ruling R84): a family's
    # default without its cell is a fault of the data, not a cell to come. The partial cells are
    # hash2's and backends::webcrypto's.
    library = scratch_library(scratch)
    files = write_ok(library)
    blake2 = files['generated/backends-blake2.adoc']
    expect('`hash2` (partial: an output under 64 bytes' in blake2, blake2)
    expect('| hash2 (partial: a tag under 32 bytes' in files['backends.adoc'],
           'the backends chapter does not say what the partial cell refuses')
    expect('`webcrypto` (asynchronous family only) (partial: an info longer than 1,024 bytes'
           in files['generated/backends-hkdf.adoc'], files['generated/backends-hkdf.adoc'])
    expect('| webcrypto (asynchronous family only) (partial: an iteration count above 2^32 - 1'
           in files['backends.adoc'], 'webcrypto\'s PBKDF2 limits are not said')

    def drop_cell(table: dict) -> None:
        family_row(table, 'digests::blake2b')['backends'].pop('sodium', None)
    edit_capabilities(library, drop_cell)
    done = run(library, '--write')
    expect(done.returncode == 1, 'a default without its cell was rendered')
    expect('the tag digests::blake2b has the default sodium, which has no cell of it'
           in done.stderr, done.stderr)


def test_a_tag_sits_in_its_namespace_s_chapter(scratch: Path) -> None:
    # A tag of macs is a MAC, listed with the MACs and under llms.txt's MAC section; a tag of
    # digests with the digests.
    library = scratch_library(scratch)
    files = write_ok(library)
    expect('macs::blake2b_mac' in files['generated/compare-macs.adoc'], 'keyed BLAKE2b')
    expect('macs::blake2b_mac' not in files['generated/compare-digests.adoc'],
           'keyed BLAKE2b among the digests')
    macs = files['llms.txt'].split('## Message authentication')[1].split('\n## ')[0]
    expect('webcpp::hash::macs::blake2s_mac' in macs, macs)

    def misplace(table: dict) -> None:
        kmac = next(a for a in table['algorithms'] if a['name'] == 'kmac')
        sha2 = next(a for a in table['algorithms'] if a['name'] == 'md5_sha1_sha2')
        row = next(f for f in kmac['functions'] if f['name'] == 'macs::kmac_128')
        kmac['functions'].remove(row)
        sha2['functions'].append(row)
    edit_capabilities(library, misplace)
    done = run(library, '--write')
    expect(done.returncode == 1, 'a tag of macs among the digests was rendered')
    expect('the tag macs::kmac_128 is in the chapter digests, not macs' in done.stderr,
           done.stderr)


def test_an_asynchronous_backend_is_never_a_default(scratch: Path) -> None:
    library = scratch_library(scratch)

    def webcrypto_default(table: dict) -> None:
        family_row(table, 'hkdf')['default'] = 'webcrypto'
        family_row(table, 'pbkdf2')['kind'] = 'fixture'
    edit_capabilities(library, webcrypto_default)
    done = run(library, '--write')
    expect(done.returncode == 1, 'an asynchronous-only default was rendered')
    expect('the function hkdf has the default webcrypto, which only the asynchronous family '
           'takes' in done.stderr, done.stderr)
    expect('pbkdf2 has the unknown kind fixture' in done.stderr, done.stderr)


def test_an_asynchronous_backend_s_targets_are_spelled(scratch: Path) -> None:
    library = scratch_library(scratch)

    def two_targets(table: dict) -> None:
        webcrypto = next(b for b in table['backends'] if b['name'] == 'webcrypto')
        webcrypto['targets'] = ['native', 'wasip2', 'emscripten']
    edit_capabilities(library, two_targets)
    hkdf = write_ok(library)['generated/backends-hkdf.adoc']
    expect('serves the asynchronous family alone, on native, wasip2 and Emscripten, where' in hkdf,
           hkdf)


def test_llms_txt_s_defaults_are_the_table_s(scratch: Path) -> None:
    """Each clause whole, its template position the header's: argon2id's and scrypt's backend is
    their only template argument, hkdf's and pbkdf2's the second, after the hmac."""
    library = scratch_library(scratch)
    llms = write_ok(library)['llms.txt']
    expect('By default, hkdf_extract, hkdf_expand, hkdf and pbkdf2 run on backends::hash2 unless '
           'the call names another of its backends as its second template argument; '
           'blake2b_subkey runs on backends::sodium alone; kbkdf, sskdf and x963kdf have no '
           'default backend, and the call names one of its backends as its second template '
           'argument; argon2id and scrypt run on backends::sodium unless the call names another '
           'of its backends as its only template argument; bcrypt and bcrypt_pbkdf have no '
           'default backend, and the call names backends::botan as its only template argument. '
           'The families' in llms, llms.split('\n\n')[1])

    def scrypt_alone(table: dict) -> None:
        family_row(table, 'scrypt')['backends'].pop('openssl')
        family_row(table, 'scrypt')['backends'].pop('botan')
    edit_capabilities(library, scrypt_alone)
    llms = write_ok(library)['llms.txt']
    expect('; blake2b_subkey and scrypt run on backends::sodium alone; ' in llms,
           llms.split('\n\n')[1])
    expect('; argon2id runs on backends::sodium unless the call names another of its backends as '
           'its only template argument; ' in llms, llms.split('\n\n')[1])


def test_a_backend_s_position_is_its_header_s(scratch: Path) -> None:
    """The template argument a call names its backend as is read from the header that declares
    the template: every generated sentence follows a moved parameter, and a header that does not
    declare it fails."""
    library = scratch_library(scratch)
    files = write_ok(library)
    expect('The default of `argon2id`: `sodium` on every target, whatever the program links; '
           '`botan`, `openssl` only where the call names it, as its only template argument '
           '(<<hash-default-backend>>).' in files['generated/backends-argon2id.adoc'],
           files['generated/backends-argon2id.adoc'])
    expect('The default of `scrypt`: `sodium` on every target, whatever the program links; '
           '`botan`, `openssl` only where the call names it, as its only template argument '
           '(<<hash-default-backend>>).' in files['generated/backends-scrypt.adoc'],
           files['generated/backends-scrypt.adoc'])
    expect('The default of `kdfs::argon2i` and `kdfs::argon2id`: `sodium` on every target, '
           'whatever the program links; `botan`, `openssl` only where the call names it, as its '
           'second template argument (<<hash-default-backend>>).'
           in files['generated/backends-argon2.adoc'], files['generated/backends-argon2.adoc'])
    expect('The default of `pbkdf2`: `hash2` on every target, whatever the program links; '
           '`botan`, `openssl` only where the call names it, as its second template argument '
           '(<<hash-default-backend>>).' in files['generated/backends-pbkdf2.adoc'],
           files['generated/backends-pbkdf2.adoc'])
    header = library / 'include/webcpp/hash/scrypt.hpp'
    text = header.read_text(encoding='utf-8')
    moved = 'template <class Fixture = void, class Backend = default_backend<kdfs::scrypt>>'
    expect('template <class Backend = default_backend<kdfs::scrypt>>' in text, text)
    header.write_text(text.replace('template <class Backend = default_backend<kdfs::scrypt>>',
                                   moved, 1), encoding='utf-8')
    files = write_ok(library)
    expect('`botan`, `openssl` only where the call names it, as its second template argument'
           in files['generated/backends-scrypt.adoc'], files['generated/backends-scrypt.adoc'])
    expect('argon2id runs on backends::sodium unless the call names another of its backends as '
           'its only template argument; scrypt runs on backends::sodium unless the call names '
           'another of its backends as its second template argument;' in files['llms.txt'],
           files['llms.txt'].split('\n\n')[1])
    header.write_text(text.replace('scrypt(', 'scrypt_gone(').replace('scrypt (', 'gone ('),
                      encoding='utf-8')
    done = run(library, '--write')
    expect(done.returncode == 1, 'a header without the template was rendered')
    expect('webcpp/hash/scrypt.hpp declares no template scrypt with a Backend parameter'
           in done.stderr, done.stderr)


def edit_capabilities(library: Path, edit: Callable[[dict], None]) -> None:
    """Rewrites the scratch library's capability table through `edit`."""
    path = library / 'doc/capabilities.json'
    table = json.loads(path.read_text(encoding='utf-8'))
    edit(table)
    path.write_text(json.dumps(table, indent=4) + '\n', encoding='utf-8')


def a_cell(since: int) -> dict:
    return {'since': since, 'hmacs': None,
            'constant_time': {'value': 'not stated', 'source': 'fixture'}}


def test_a_default_names_only_its_functions_backends(scratch: Path) -> None:
    """An algorithm whose functions have different backends: the sentence of each default
    names, as the backends a call may name instead, those of its own functions alone; functions
    with one default and the same other backends share a sentence."""
    library = scratch_library(scratch)

    def blake2(table: dict) -> None:
        rows = {f['name']: f for a in table['algorithms'] for f in a['functions']}
        rows['digests::blake2b']['default'] = 'sodium'
        rows['digests::blake2b']['backends'] = {'hash2': a_cell(2), 'sodium': a_cell(2)}
        rows['digests::blake2s_256']['backends'] = {'hash2': a_cell(2), 'openssl': a_cell(4)}
        rows['macs::blake2s_mac']['backends'] = {'hash2': a_cell(2)}
        rows['blake2s_256']['backends'] = {'hash2': a_cell(1)}
    edit_capabilities(library, blake2)
    files = write_ok(library)
    blake2_mac = files['generated/backends-blake2-mac.adoc']
    expect('The default of `macs::blake2s_mac`: `hash2` on every target, whatever the program '
           'links (<<hash-default-backend>>).' in blake2_mac, blake2_mac)
    blake2_file = files['generated/backends-blake2.adoc']
    expect('The default of `digests::blake2s_256`: `hash2` on every target, whatever the '
           'program links; `openssl` only where the call names it' in blake2_file, blake2_file)
    expect('The default of `digests::blake2b`: `sodium` on every target, whatever the program '
           'links; `hash2` only where the call names it' in blake2_file, blake2_file)
    hkdf = files['generated/backends-hkdf.adoc']
    expect('`bearssl`' not in hkdf.split('The default of `hkdf_extract`')[1].split('\n')[0],
           hkdf)


def test_a_tag_without_a_default_is_not_said_a_type(scratch: Path) -> None:
    """An algorithm whose one row is a family's tag without a default says that the call names
    a backend, and not that types take none."""
    library = scratch_library(scratch)

    def lone_tag(table: dict) -> None:
        table['algorithms'].append({
            'name': 'fixture_lone', 'macro': 'FIXTURE_LONE', 'tag': None, 'chapter': 'digests',
            'standard': 'a fixture', 'functions': [{
                'name': 'digests::fixture_lone', 'kind': 'digest',
                'header': 'webcpp/hash/digest.hpp', 'default': None,
                'backends': {'openssl': a_cell(4)}}]})
    edit_capabilities(library, lone_tag)
    guide_path = library / 'doc/guide.json'
    guide = json.loads(guide_path.read_text(encoding='utf-8'))
    guide['functions']['digests::fixture_lone'] = dict(guide['functions']['digests::sha2_256'])
    guide_path.write_text(json.dumps(guide, indent=4) + '\n', encoding='utf-8')
    lone = write_ok(library)['generated/backends-fixture-lone.adoc']
    expect('`digests::fixture_lone` has no default backend: the call names one of its backends'
           in lone, lone)
    expect('the types take no backend' not in lone, lone)


def test_each_backend_s_constant_time_sources_are_together(scratch: Path) -> None:
    # One bullet per backend and value, in the table's order of backends, its sources under it
    # when it has several; and one bullet per backend in an algorithm's table.
    library = scratch_library(scratch)
    files = write_ok(library)
    chapter = files['backends.adoc']
    listed = [line.split(':')[0] for line in
              chapter.split("What each backend's upstream states, and where:")[1].splitlines()
              if line.startswith('* ')]
    order = [b['name'] for b in json.loads(
        (library / 'doc/capabilities.json').read_text(encoding='utf-8'))['backends']]
    expect(listed == sorted(listed, key=lambda b: order.index(b[2:])), '\n'.join(listed))
    # A backend whose cells state two values (botan: "no" for Streebog and Whirlpool, "not
    # stated" elsewhere) has one bullet for each.
    stated = [line.split('.')[0] for line in
              chapter.split("What each backend's upstream states, and where:")[1].splitlines()
              if line.startswith('* ')]
    expect(len(stated) == len(set(stated)), '\n'.join(stated))
    expect('* openssl: not stated.\n** ' in chapter, 'openssl\'s sources are not under it')
    for name, text in files.items():
        if not name.startswith('generated/backends-'):
            continue
        bullets = [line.split(':')[0] for line in
                   text.split('What each backend states on constant time')[1].splitlines()
                   if line.startswith('* ')]
        expect(len(bullets) == len(set(bullets)), f'{name}: {bullets}')


def test_an_asynchronous_backend_is_said(scratch: Path) -> None:
    # backends::webcrypto serves the asynchronous family alone (its "asynchronous_only" field):
    # every table names it with that note, and a synchronous call never names it.
    library = scratch_library(scratch)
    files = write_ok(library)
    backends = files['backends.adoc']
    expect('| webcrypto\n| the JavaScript runtime' in backends, backends)
    expect('| asynchronous family only (async.hpp)' in backends, backends)
    expect('| every function of its cells' in backends, backends)
    expect('| hkdf\n| webcrypto (asynchronous family only)' in backends, backends)
    hkdf = files['generated/backends-hkdf.adoc']
    expect('| `webcrypto` (asynchronous family only)' in hkdf, hkdf)
    expect('`bearssl`, `botan`, `openssl`, `sodium` only where the call names it' in hkdf, hkdf)
    expect('`webcrypto` serves the asynchronous family alone, on Emscripten, where the type of '
           'its asynchronous call names it (<<hash-async-webcrypto>>).' in hkdf, hkdf)
    digests = files['generated/backends-md5-sha1-sha2.adoc']
    expect('`webcrypto` serves the asynchronous family alone' in digests, digests)
    expect('webcrypto, asynchronous family only (/webcpp/asio//asio; emscripten)'
           in files['llms.txt'], 'llms.txt does not say webcrypto is asynchronous only')
    expect('backends::webcrypto, the browser\'s WebCrypto, serves that form alone'
           in files['llms.txt'], 'llms.txt does not name the asynchronous form')
    table = json.loads((library / 'doc/capabilities.json').read_text(encoding='utf-8'))
    for backend in table['backends']:
        backend.pop('asynchronous_only', None)
    (library / 'doc/capabilities.json').write_text(json.dumps(table), encoding='utf-8')
    plain = write_ok(library)['backends.adoc']
    expect('asynchronous family only' not in plain, 'a note without its field')


def test_an_exceptions_only_backend_is_said(scratch: Path) -> None:
    # backends::botan has no cell in a build without exceptions (its "exceptions_only" field):
    # every table and llms.txt name it with "with exceptions only", and without the field nothing
    # does.
    library = scratch_library(scratch)
    files = write_ok(library)
    backends = files['backends.adoc']
    expect('| botan\n| Botan 3.14.1' in backends, backends)
    expect('| every function of its cells, with exceptions only' in backends, backends)
    expect('| digests::whirlpool\n| botan (with exceptions only)' in backends, backends)
    expect('botan, with exceptions only (/third_party//botan; ' in files['llms.txt'],
           'llms.txt does not say botan is with exceptions only')
    table = json.loads((library / 'doc/capabilities.json').read_text(encoding='utf-8'))
    for backend in table['backends']:
        backend.pop('exceptions_only', None)
    (library / 'doc/capabilities.json').write_text(json.dumps(table), encoding='utf-8')
    plain = write_ok(library)
    expect('with exceptions only' not in plain['backends.adoc'], 'a note without its field')
    expect('with exceptions only' not in plain['llms.txt'], 'a note without its field')


def test_without_measurements_the_tables_say_so(scratch: Path) -> None:
    library = scratch_library(scratch)
    files = write_ok(library)
    expect('Fastest natively' not in files['generated/compare-digests.adoc'],
           'a measured column without measurements')
    expect('does not have yet' in files['generated/compare-digests.adoc'],
           'the comparison table does not say its measurements are missing')
    expect('measurements.adoc' not in files, 'measurements.adoc without its data')
    hkdf = files['generated/backends-hkdf.adoc']
    expect('The default of `hkdf_extract` and `hkdf_expand`: `hash2` on every target' in hkdf
           and 'The default of `hkdf`: `hash2` on every target' in hkdf,
           f'the backends of HKDF do not name the default: {hkdf}')
    expect('`bearssl`, `botan`, `openssl`, `sodium` only where the call names it' in hkdf, hkdf)
    expect('The default of `argon2id`: `sodium` on every target'
           in files['generated/backends-argon2id.adoc'], 'Argon2id\'s default')
    expect('One backend, `hash2`: the types take no backend.'
           in files['generated/backends-non-cryptographic.adoc'], 'a type\'s backend')
    backends = files['backends.adoc']
    expect('| pbkdf2\n| hash2' in backends and '| scrypt\n| sodium' in backends,
           'backends.adoc does not list the defaults')
    expect('Backends: hash2 (/webcpp/hash//hash' in files['llms.txt'], 'llms.txt has no backends')
    expect('hkdf_extract, hkdf_expand, hkdf and pbkdf2 run on backends::hash2 unless the call '
           'names another of its backends as its second template argument' in files['llms.txt'],
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
    test_a_default_without_its_cell_fails_and_a_partial_cell_is_said,
    test_a_tag_sits_in_its_namespace_s_chapter,
    test_an_asynchronous_backend_is_never_a_default,
    test_an_asynchronous_backend_s_targets_are_spelled,
    test_llms_txt_s_defaults_are_the_table_s,
    test_a_backend_s_position_is_its_header_s,
    test_a_default_names_only_its_functions_backends,
    test_a_tag_without_a_default_is_not_said_a_type,
    test_a_function_without_a_backend_of_the_order_has_no_default,
    test_a_function_s_default_is_of_the_order,
    test_each_backend_s_constant_time_sources_are_together,
    test_an_asynchronous_backend_is_said,
    test_an_exceptions_only_backend_is_said,
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
