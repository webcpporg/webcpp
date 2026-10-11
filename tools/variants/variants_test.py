#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks tools/variants/variants.py: a manifest names each variant's script relative to itself and
the size of its .wasm, in sorted keys and four spaces; an artifact without its .wasm is refused
before anything is written; a table lists each program with its sizes and their ratio, in the file
and on the standard output; and a manifest that is not one is refused, naming it. Run with the
names of some cases to run only those."""

from __future__ import annotations

import json
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


def test_table_lists_each_program_with_its_ratio(root: Path) -> None:
    jspi, asyncify = scripts(root)
    manifest = root / 'page.variants.json'
    variants('manifest', '--out', manifest, '--jspi', jspi, '--asyncify', asyncify)
    out = root / 'sizes.md'
    result = variants('table', '--out', out, manifest)
    assert result.returncode == 0, result.stderr
    table = ('| program | jspi | asyncify | asyncify / jspi |\n'
             '| --- | ---: | ---: | ---: |\n'
             '| page | 102,988 | 297,636 | 2.89 |\n')
    assert out.read_text() == table and result.stdout == table, (out.read_text(), result.stdout)


def test_table_refuses_a_manifest_that_is_not_one(root: Path) -> None:
    bad = root / 'bad.variants.json'
    bad.write_text('{"jspi": {}}\n')
    result = variants('table', '--out', root / 'sizes.md', bad)
    assert result.returncode == 1 and f'{bad}: ' in result.stderr, result.stderr


CASES: list[Callable[[Path], None]] = [
    test_manifest_names_each_artifact_from_its_own_directory,
    test_manifest_refuses_an_artifact_without_its_wasm,
    test_table_lists_each_program_with_its_ratio,
    test_table_refuses_a_manifest_that_is_not_one,
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
