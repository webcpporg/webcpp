#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks tools/variants/variants.py: a manifest names each variant's script relative to itself and
the size of its .wasm, in sorted keys and four spaces; an artifact without its script or its .wasm
is refused before anything is written; a table lists each program with its sizes and their ratio,
in the file and on the standard output; a manifest that is not one is refused, naming it; and a
table is written only from release builds: given another variant, or none, it is refused before
anything is written. The sizes of linked programs (webcpp.program-sizes) are each program's raw and
gzip -9n bytes and their excess over the baseline's: a native executable stripped, a WASI program's
.wasm, an Emscripten program's .wasm and its .js; a program not among the files given, a baseline
not among the programs, and a build at another variant than release are refused before anything is
written; their Markdown table is the JSON's, and it too refuses data not built at release. Run with
the names of some cases to run only those."""

from __future__ import annotations

import gzip
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

VARIANTS = Path(__file__).resolve().parent / 'variants.py'


def scripts(root: Path) -> tuple[Path, Path]:
    """A jspi and an asyncify artifact as b2 lays them out, each with its .wasm."""
    jspi = root / 'page-60-d-jspi.js'
    asyncify = root / 'webcpp-suspend-asyncify/page-60-d-asyncify.js'
    for script, size in ((jspi, 102988), (asyncify, 297636)):
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text('// glue\n')
        script.with_suffix('.wasm').write_bytes(b'\0' * size)
    return jspi, asyncify


def variants(*arguments: Path | str) -> subprocess.CompletedProcess[str]:
    """variants.py run with arguments, as the build runs it."""
    return subprocess.run([sys.executable, str(VARIANTS), *map(str, arguments)],
                          capture_output=True, text=True, check=False, timeout=120)


def test_manifest_names_each_artifact_from_its_own_directory(root: Path) -> None:
    jspi, asyncify = scripts(root)
    out = root / 'page.variants.json'
    result = variants('manifest', '--out', out, '--jspi', jspi, '--asyncify', asyncify)
    assert result.returncode == 0, result.stderr
    assert json.loads(out.read_text()) == {
        'asyncify': {'bytes': 297636, 'script': 'webcpp-suspend-asyncify/page-60-d-asyncify.js'},
        'jspi': {'bytes': 102988, 'script': 'page-60-d-jspi.js'}}
    assert out.read_text().startswith('{\n    "asyncify": {\n'), out.read_text()


def test_manifest_refuses_an_artifact_without_its_wasm(root: Path) -> None:
    jspi, asyncify = scripts(root)
    asyncify.with_suffix('.wasm').unlink()
    result = variants('manifest', '--out', root / 'page.variants.json', '--jspi', jspi,
                      '--asyncify', asyncify)
    assert result.returncode == 1, result.returncode
    assert f'{asyncify.with_suffix(".wasm")} does not exist' in result.stderr, result.stderr
    assert not (root / 'page.variants.json').exists()


def test_manifest_refuses_an_artifact_without_its_script(root: Path) -> None:
    jspi, asyncify = scripts(root)
    jspi.unlink()
    result = variants('manifest', '--out', root / 'page.variants.json', '--jspi', jspi,
                      '--asyncify', asyncify)
    assert result.returncode == 1, result.returncode
    assert f'{jspi} does not exist' in result.stderr, result.stderr
    assert not (root / 'page.variants.json').exists()


def test_table_lists_each_program_with_its_ratio(root: Path) -> None:
    jspi, asyncify = scripts(root)
    manifest = root / 'page.variants.json'
    variants('manifest', '--out', manifest, '--jspi', jspi, '--asyncify', asyncify)
    out = root / 'sizes.md'
    result = variants('table', '--variant', 'release', '--out', out, manifest)
    assert result.returncode == 0, result.stderr
    table = ('| program | jspi | asyncify | asyncify / jspi |\n'
             '| --- | ---: | ---: | ---: |\n'
             '| page | 102,988 | 297,636 | 2.89 |\n')
    assert out.read_text() == table and result.stdout == table, (out.read_text(), result.stdout)


def test_table_refuses_a_manifest_that_is_not_one(root: Path) -> None:
    bad = root / 'bad.variants.json'
    bad.write_text('{"jspi": {}}\n')
    result = variants('table', '--variant', 'release', '--out', root / 'sizes.md', bad)
    assert result.returncode == 1 and f'{bad}: ' in result.stderr, result.stderr


def test_table_refuses_a_build_that_is_not_release(root: Path) -> None:
    # Published sizes are those of release builds: webcpp.size-table requires <variant>release
    # and gives the table's variant, which variants.py refuses to be any other.
    jspi, asyncify = scripts(root)
    manifest = root / 'page.variants.json'
    variants('manifest', '--out', manifest, '--jspi', jspi, '--asyncify', asyncify)
    out = root / 'sizes.md'
    for variant in ('debug', 'profile'):
        result = variants('table', '--variant', variant, '--out', out, manifest)
        assert result.returncode == 1, (variant, result.returncode, result.stderr)
        assert (f'variants.py: a size table is built only from release builds, not '
                f'variant={variant}') in result.stderr, result.stderr
        assert not out.exists(), variant
    result = variants('table', '--out', out, manifest)
    assert result.returncode == 2 and '--variant' in result.stderr, result.stderr
    assert not out.exists()


def gzipped(data: bytes) -> int:
    """What gzip -9n gives: no name and no time stamp in its header."""
    return len(gzip.compress(data, compresslevel=9, mtime=0))


def linked(root: Path, target: str, sizes: dict[str, int]) -> list[Path]:
    """Programs as webcpp.link's <name>-program files on target, each of the bytes given: on WASI
    its .wasm, on emscripten its .js and the .wasm beside it; natively a copy of the Python
    interpreter, an executable strip can shorten, whatever the size given."""
    paths = []
    for name, size in sizes.items():
        if target == 'native':
            path = root / f'{name}-program'
            shutil.copyfile(sys.executable, path)
        elif target == 'emscripten':
            path = root / f'{name}-program.js'
            path.write_bytes(b'// glue\n' * (size // 8))
            path.with_suffix('.wasm').write_bytes(bytes(range(256)) * (size // 256))
        else:
            path = root / f'{name}-program.wasm'
            path.write_bytes(bytes(range(256)) * (size // 256))
        paths.append(path)
    return paths


def program_sizes(root: Path, target: str, *programs: Path, variant: str = 'release',
                  names: tuple[str, ...] = ('baseline', 'sealed'),
                  baseline: str = 'baseline') -> subprocess.CompletedProcess[str]:
    """variants.py programs run as webcpp.program-sizes runs it."""
    return variants('programs', '--variant', variant, '--target', target, '--toolset', 'clang',
                    '--baseline', baseline, '--names', *names, '--out', root / 'p.sizes.json',
                    '--', *programs)


def test_programs_size_each_wasm_against_the_baseline(root: Path) -> None:
    programs = linked(root, 'wasip2', {'baseline': 2560, 'sealed': 25600})
    # A library object a project's requirements append to the make is not a program.
    stray = root / 'libsodium.a'
    stray.write_bytes(b'x' * 100)
    result = program_sizes(root, 'wasip2', *programs, stray)
    assert result.returncode == 0, result.stderr
    read = json.loads((root / 'p.sizes.json').read_text())
    base, sealed = (p.read_bytes() for p in programs)
    assert read == {
        'variant': 'release', 'target': 'wasip2', 'toolset': 'clang', 'baseline': 'baseline',
        'programs': [
            {'program': 'baseline', 'file': 'wasm', 'bytes': 2560, 'gzip': gzipped(base),
             'over_baseline': 0, 'gzip_over_baseline': 0},
            {'program': 'sealed', 'file': 'wasm', 'bytes': 25600, 'gzip': gzipped(sealed),
             'over_baseline': 23040, 'gzip_over_baseline': gzipped(sealed) - gzipped(base)}]}, read


def test_programs_size_emscripten_s_wasm_and_its_glue(root: Path) -> None:
    programs = linked(root, 'emscripten', {'baseline': 2560, 'sealed': 5120})
    result = program_sizes(root, 'emscripten', *programs)
    assert result.returncode == 0, result.stderr
    rows = json.loads((root / 'p.sizes.json').read_text())['programs']
    assert [(r['program'], r['file'], r['bytes'], r['over_baseline']) for r in rows] == [
        ('baseline', 'js', 2560, 0), ('baseline', 'wasm', 2560, 0),
        ('sealed', 'js', 5120, 2560), ('sealed', 'wasm', 5120, 2560)], rows


def test_programs_strip_a_native_executable(root: Path) -> None:
    if not shutil.which('strip'):
        raise AssertionError('strip is not on PATH: a native size is that of a stripped program')
    programs = linked(root, 'native', {'baseline': 0, 'sealed': 0})
    result = program_sizes(root, 'native', *programs)
    assert result.returncode == 0, result.stderr
    rows = json.loads((root / 'p.sizes.json').read_text())['programs']
    copy = root / 'stripped'
    shutil.copyfile(programs[0], copy)
    subprocess.run(['strip', str(copy)], check=True, capture_output=True)
    stripped = copy.read_bytes()
    assert [(r['file'], r['bytes'], r['gzip'], r['over_baseline']) for r in rows] == [
        ('executable', len(stripped), gzipped(stripped), 0),
        ('executable', len(stripped), gzipped(stripped), 0)], rows
    # The program itself is never changed.
    assert programs[0].read_bytes() == Path(sys.executable).read_bytes()


def test_programs_refuse_a_program_not_given(root: Path) -> None:
    programs = linked(root, 'wasip2', {'baseline': 256})
    result = program_sizes(root, 'wasip2', *programs)
    assert result.returncode == 1, result.returncode
    assert 'variants.py: sealed is not among the programs given' in result.stderr, result.stderr
    assert not (root / 'p.sizes.json').exists()
    result = program_sizes(root, 'wasip2', *programs, names=('sealed',))
    assert result.returncode == 1, result.returncode
    assert 'the baseline baseline is not among the programs named' in result.stderr, result.stderr


def test_programs_are_sized_only_from_release_builds(root: Path) -> None:
    programs = linked(root, 'wasip2', {'baseline': 256, 'sealed': 512})
    for variant in ('debug', 'profile'):
        result = program_sizes(root, 'wasip2', *programs, variant=variant)
        assert result.returncode == 1, (variant, result.returncode)
        assert (f'variants.py: a size table is built only from release builds, not '
                f'variant={variant}') in result.stderr, result.stderr
        assert not (root / 'p.sizes.json').exists(), variant


def test_programs_table_is_the_json_s(root: Path) -> None:
    programs = linked(root, 'wasip2', {'baseline': 2560, 'sealed': 25600})
    program_sizes(root, 'wasip2', *programs)
    out = root / 'p.sizes.md'
    result = variants('programs-table', '--out', out, root / 'p.sizes.json')
    assert result.returncode == 0, result.stderr
    read = json.loads((root / 'p.sizes.json').read_text())['programs']
    table = ('Linked programs on wasip2, built with clang at variant=release, against the '
             'baseline baseline.\n\n'
             '| program | file | bytes | gzip -9n | over baseline | gzip -9n over baseline |\n'
             '| --- | --- | ---: | ---: | ---: | ---: |\n'
             f'| baseline | wasm | 2,560 | {read[0]["gzip"]:,} | 0 | 0 |\n'
             f'| sealed | wasm | 25,600 | {read[1]["gzip"]:,} | 23,040 | '
             f'{read[1]["gzip_over_baseline"]:,} |\n')
    assert out.read_text() == table and result.stdout == table, (out.read_text(), result.stdout)


def test_programs_table_refuses_data_not_built_at_release(root: Path) -> None:
    programs = linked(root, 'wasip2', {'baseline': 256, 'sealed': 512})
    program_sizes(root, 'wasip2', *programs)
    data = json.loads((root / 'p.sizes.json').read_text())
    for variant in ('debug', None):
        if variant is None:
            del data['variant']
        else:
            data['variant'] = variant
        (root / 'p.sizes.json').write_text(json.dumps(data))
        result = variants('programs-table', '--out', root / 'p.sizes.md', root / 'p.sizes.json')
        assert result.returncode == 1, (variant, result.returncode)
        assert 'a size table is built only from release builds' in result.stderr, result.stderr
        assert not (root / 'p.sizes.md').exists(), variant


CASES: list[Callable[[Path], None]] = [
    test_manifest_names_each_artifact_from_its_own_directory,
    test_manifest_refuses_an_artifact_without_its_wasm,
    test_manifest_refuses_an_artifact_without_its_script,
    test_table_lists_each_program_with_its_ratio,
    test_table_refuses_a_manifest_that_is_not_one,
    test_table_refuses_a_build_that_is_not_release,
    test_programs_size_each_wasm_against_the_baseline,
    test_programs_size_emscripten_s_wasm_and_its_glue,
    test_programs_strip_a_native_executable,
    test_programs_refuse_a_program_not_given,
    test_programs_are_sized_only_from_release_builds,
    test_programs_table_is_the_json_s,
    test_programs_table_refuses_data_not_built_at_release,
]


def main(argv: list[str]) -> int:
    """Runs every case, or those argv names, each in a directory of its own."""
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'variants_test: no case named {", ".join(sorted(unknown))}', file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp variants ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('variants_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
