#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks that libs/hash/bench/allocation_collect.py, which collects the counting programs' records
into doc/measurements.allocation.json and renders doc/allocation.adoc, builds its table only from
release builds: an output of a program whose build directory, b2's
bench/<name>.test/<toolset>/<variant>/..., names another variant (the lanes' test/ directories
included), or does not say, is refused before anything is written; one at variant=release is
taken and the data records the build and the toolset; backends::botan's records give one row per
operation and target; `--render-only` and `--check` refuse data whose build is not
variant=release. Run with the names of some cases to run only those."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLLECT = ROOT / 'libs/hash/bench/allocation_collect.py'
DATA = ROOT / 'libs/hash/doc/measurements.allocation.json'
PAGE = ROOT / 'libs/hash/doc/allocation.adoc'

RECORDS = (
    'record operation=counter c_counted=1\n'
    'record operation=argon2id backend=sodium new=0 c=3 counted=1\n'
    'record operation=hkdf backend=openssl new=0 hmac=hmac_sha2_256 call=1 openssl=7\n'
    'record operation=hkdf backend=openssl new=0 hmac=hmac_sha2_512 call=1 openssl=5\n'
    'record operation=hkdf backend=openssl new=0 hmac=hmac_sha2_512 call=2 openssl=4\n'
)


def run(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(COLLECT), *map(str, args)], cwd=ROOT,
                          capture_output=True, text=True, check=False, timeout=120)


def lane(scratch: Path, project: str, variant: str) -> Path:
    """A build directory with the output of a counting program, where b2 puts it at variant."""
    base = (scratch / 'bin/libs/hash' / project / 'allocation_release.test' / 'clang-darwin-21'
            / variant)
    out = base / 'cxxstd-20-iso/allocation_release.output'
    out.parent.mkdir(parents=True)
    out.write_text(RECORDS)
    return scratch / 'bin'


def expect(done: subprocess.CompletedProcess[str], status: int, *texts: str) -> None:
    if done.returncode != status:
        raise AssertionError(f'exit {done.returncode}, not {status}\n{done.stdout}{done.stderr}')
    for text in texts:
        if text not in done.stdout + done.stderr:
            raise AssertionError(f'{text!r} is not in the output:\n{done.stdout}{done.stderr}')


def test_an_output_not_built_at_variant_release_is_refused(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    page.write_text(PAGE.read_text())
    for project, variant in (('bench', 'debug'), ('bench', 'profile'), ('test', 'debug'),
                             ('test', 'release')):
        path = lane(scratch / f'{project}-{variant}', project, variant)
        done = run('--lane', f'native={path}', '--data', data, '--page', page)
        expect(done, 1, 'only from release builds')
        if data.exists() or page.read_text() != PAGE.read_text():
            raise AssertionError(f'{project}/{variant}: a file was written')
    stray = scratch / 'stray'
    stray.mkdir()
    (stray / 'allocation.output').write_text(RECORDS)
    expect(run('--lane', f'wasip2={stray}', '--data', data, '--page', page), 1,
           'bench/<name>.test/<toolset>/<variant>', 'only from release builds')


def test_an_output_built_at_variant_release_is_collected(scratch: Path) -> None:
    path = lane(scratch, 'bench', 'release')
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    page.write_text(PAGE.read_text())
    expect(run('--lane', f'native={path}', '--data', data, '--page', page), 0)
    written = json.loads(data.read_text())
    if written.get('build') != 'variant=release':
        raise AssertionError(f'the data states build {written.get("build")}')
    if written.get('toolsets') != {'native': 'clang-darwin-21'}:
        raise AssertionError(f'the data states toolsets {written.get("toolsets")}')
    expect(run('--check', '--data', data, '--page', page), 0)


BOTAN_RECORDS = (
    'record operation=counter c_counted=1\n'
    'record operation=digest_of tag=digests::md5 backend=botan target=native call=1 new=1 c=2 '
    'counted=1\n'
    'record operation=digest_of tag=digests::md5 backend=botan target=native call=2 new=1 c=2 '
    'counted=1\n'
    'record operation=digest_of tag=digests::sm3 backend=botan target=native call=1 new=4 c=13 '
    'counted=1\n'
    'record operation=digest_of tag=digests::sm3 backend=botan target=native call=2 new=4 c=13 '
    'counted=1\n'
    'record operation=argon2id tag=kdfs::argon2id backend=botan target=native call=1 new=6 c=9 '
    'counted=1\n'
    'record operation=argon2id tag=kdfs::argon2id backend=botan target=native call=2 new=5 c=8 '
    'counted=1\n'
    'record operation=scrypt tag=kdfs::scrypt backend=botan target=native call=1 new=3 c=0 '
    'counted=0\n'
    'record operation=scrypt tag=kdfs::scrypt backend=botan target=native call=2 new=3 c=0 '
    'counted=0\n'
)


def test_botan_s_records_give_one_row_per_operation(scratch: Path) -> None:
    """backends::botan's records, one per call of each tag, become one row per operation and
    target: the range over its tags, and a steady call's counts where they differ; a record whose
    C library is not counted (MSVC's) says so; Botan's argon2id is not libsodium's."""
    base = (scratch / 'bin/libs/hash/bench/allocation_botan_release.test/clang-darwin-21/release'
            / 'cxxstd-20-iso')
    base.mkdir(parents=True)
    (base / 'allocation_botan_release.output').write_text(BOTAN_RECORDS)
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    page.write_text(PAGE.read_text())
    expect(run('--lane', f'native={scratch / "bin"}', '--data', data, '--page', page), 0)
    table = page.read_text()
    for row in ('| `digest_of` | `botan` | native | 1 to 4 | Botan: 2 to 13 C library calls '
                "(operator new's included), over its 2 algorithms; the same in a steady call",
                '| `argon2id` | `botan` | native | 6 | Botan: 9 C library calls (operator '
                "new's included), of kdfs::argon2id; a steady call: 5 operator new, 8 C library "
                'calls',
                '| `scrypt` | `botan` | native | 3 | Botan: C library not counted, of '
                'kdfs::scrypt; the same in a steady call'):
        if row not in table:
            raise AssertionError(f'{row!r} is not in the table:\n{table}')
    if '| `argon2id` | `sodium`' in table:
        raise AssertionError(f"Botan's argon2id was rendered as libsodium's:\n{table}")
    expect(run('--check', '--data', data, '--page', page), 0)


def test_render_only_and_check_refuse_data_not_built_at_variant_release(scratch: Path) -> None:
    committed = json.loads(DATA.read_text())
    page = scratch / 'page.adoc'
    page.write_text(PAGE.read_text())
    for build in ('variant=debug', None):
        data = dict(committed)
        if build is None:
            data.pop('build', None)
        else:
            data['build'] = build
        path = scratch / 'data.json'
        path.write_text(json.dumps(data))
        for flag in ('--render-only', '--check'):
            expect(run(flag, '--data', path, '--page', page), 1, 'only from release builds')
        if page.read_text() != PAGE.read_text():
            raise AssertionError(f'{build}: the page was written')


def test_the_committed_data_is_from_release_builds_and_renders_the_page(scratch: Path) -> None:
    committed = json.loads(DATA.read_text())
    if committed.get('build') != 'variant=release':
        raise AssertionError(f'the committed data states build {committed.get("build")}')
    expect(run('--check', '--data', DATA, '--page', PAGE), 0)


CASES: list[Callable[[Path], None]] = [
    test_an_output_not_built_at_variant_release_is_refused,
    test_an_output_built_at_variant_release_is_collected,
    test_botan_s_records_give_one_row_per_operation,
    test_render_only_and_check_refuse_data_not_built_at_variant_release,
    test_the_committed_data_is_from_release_builds_and_renders_the_page,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'hash_allocation_collect_test: no case named {", ".join(sorted(unknown))}',
              file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp hash allocation ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('hash_allocation_collect_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
