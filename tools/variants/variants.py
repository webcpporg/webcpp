#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Writes the manifest of a page program's suspension variants, the table of their sizes, and the
sizes of linked programs on any target.

Usage: variants.py manifest --out FILE --jspi SCRIPT --asyncify SCRIPT
       variants.py table --variant VARIANT --out FILE MANIFEST...
       variants.py programs --variant VARIANT --target TARGET --toolset TOOLSET
           --baseline NAME --names NAME... --out FILE -- PROGRAM...
       variants.py programs-table --out FILE JSON

manifest writes FILE, <name>.variants.json, which a page's loader reads: for each variant, the
script, its JavaScript glue, relative to FILE's directory and written with /, and the size in bytes
of the .wasm beside it. Keys are sorted, indented by four spaces. A script or a .wasm that does not
exist is refused before anything is written.

table writes FILE, a Markdown table of every manifest's sizes, one row per program named by its
manifest's file name less .variants.json, sorted, with asyncify's size over jspi's, and prints it.
A manifest that lacks a variant, its script or a positive integer size is refused, naming it. A
table is built only from release builds: VARIANT, the b2 variant the manifests were built at
(webcpp.size-table, which requires <variant>release, gives it), other than release is refused
before anything is written.

programs writes FILE, <name>.sizes.json (webcpp.program-sizes), the sizes of the programs NAME, each
a <name>-program file of webcpp.link among PROGRAM (other files, a project's library objects that b2
appends to the make, are not programs): per file, its raw bytes, its gzip -9n bytes and their
excess over the baseline's same file. The file is natively the executable, stripped with strip (a
copy: the program is left as it is); on wasip2 and wasip3 the .wasm; on emscripten the .wasm and
its .js glue, two rows. A name without its program, a baseline not among the names, and a build at
another VARIANT than release are refused before anything is written. programs-table writes FILE,
the Markdown table of such a JSON, and prints it; it refuses a JSON not built at release.

A failure is a line on the standard error and status 1; a usage error is status 2.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePath
from typing import Any

VARIANTS = ('jspi', 'asyncify')
SUFFIX = '.variants.json'
# The only b2 variant a size table is built from.
RELEASE = 'release'
RELEASE_ONLY = 'a size table is built only from release builds, not variant={variant}: '
# The suffix webcpp.link gives a program's explicit executable.
PROGRAM = '-program'


class Refused(Exception):
    """What makes variants.py stop with status 1, as the line it prints."""


def manifest(out: Path, scripts: dict[str, Path]) -> None:
    """Writes out, naming each variant's script relative to out's directory and its .wasm's
    size; refuses a script or a .wasm that does not exist before it writes anything."""
    entries: dict[str, dict[str, Any]] = {}
    for variant, script in scripts.items():
        wasm = script.with_suffix('.wasm')
        for path in (script, wasm):
            if not path.is_file():
                raise Refused(f'{path} does not exist')
        relative = os.path.relpath(script, out.parent)
        entries[variant] = {'bytes': wasm.stat().st_size,
                            'script': PurePath(relative).as_posix()}
    out.write_text(json.dumps(entries, indent=4, sort_keys=True) + '\n')


def sizes(path: Path) -> tuple[int, int]:
    """The sizes, jspi's and asyncify's, that the manifest path records; refuses one that is not
    a manifest, naming path and what it lacks."""
    try:
        read = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise Refused(f'{path}: cannot be read as JSON: {error}') from error
    if not isinstance(read, dict):
        raise Refused(f'{path}: is not a JSON object')
    found: list[int] = []
    for variant in VARIANTS:
        entry = read.get(variant)
        if not isinstance(entry, dict):
            raise Refused(f'{path}: has no variant {variant}')
        if not isinstance(entry.get('script'), str):
            raise Refused(f'{path}: {variant} has no script string')
        size = entry.get('bytes')
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise Refused(f'{path}: {variant} has no positive integer bytes')
        found.append(size)
    return found[0], found[1]


def program(path: Path) -> str:
    """The program a manifest is of: its file name less .variants.json."""
    name = path.name
    return name[:-len(SUFFIX)] if name.endswith(SUFFIX) else name


def table(out: Path, manifests: list[Path], variant: str) -> str:
    """Writes out, the Markdown table of the manifests' sizes, and returns it; refuses a build at
    another variant than release, and a manifest that is not one, before it writes anything."""
    if variant != RELEASE:
        raise Refused(RELEASE_ONLY.format(variant=variant)
                      + 'webcpp.size-table requires <variant>release')
    rows = sorted((program(path), *sizes(path)) for path in manifests)
    lines = ['| program | jspi | asyncify | asyncify / jspi |', '| --- | ---: | ---: | ---: |']
    lines += [f'| {name} | {jspi:,} | {asyncify:,} | {asyncify / jspi:.2f} |'
              for name, jspi, asyncify in rows]
    text = '\n'.join(lines) + '\n'
    out.write_text(text)
    return text


def gzipped(data: bytes) -> int:
    """The bytes gzip -9n gives: no name and no time stamp in its header."""
    return len(gzip.compress(data, compresslevel=9, mtime=0))


def stripped(path: Path) -> bytes:
    """The bytes of path stripped by strip, from a copy: path is left as it is."""
    strip = shutil.which('strip')
    if strip is None:
        raise Refused('strip is not on PATH: a native program is sized stripped')
    with tempfile.TemporaryDirectory(prefix='webcpp sizes ') as scratch:
        copy = Path(scratch) / path.name
        shutil.copyfile(path, copy)
        done = subprocess.run([strip, str(copy)], capture_output=True, text=True, check=False)
        if done.returncode != 0:
            raise Refused(f'strip {path}: exit {done.returncode}: {done.stderr.strip()}')
        return copy.read_bytes()


def files_of(path: Path, target: str) -> list[tuple[str, bytes]]:
    """The files a program's size is read from, by kind, with their bytes: natively the executable
    stripped; on WebAssembly the .wasm, and on emscripten the .js glue beside it."""
    if target == 'native':
        return [('executable', stripped(path))]
    wasm = path.with_suffix('.wasm')
    files = []
    if path.suffix == '.js':
        files.append(('js', path.read_bytes()))
    if not wasm.is_file():
        raise Refused(f'{wasm} does not exist')
    files.append(('wasm', wasm.read_bytes()))
    return sorted(files)


def name_of(path: Path) -> str:
    """The webcpp.link program a file is of: its name less its suffix and -program."""
    stem = path.name if path.suffix not in ('.js', '.wasm', '.exe') else path.stem
    return stem[:-len(PROGRAM)] if stem.endswith(PROGRAM) else stem


def programs(variant: str, target: str, toolset: str, baseline: str, names: list[str],
             paths: list[Path]) -> dict[str, Any]:
    """The sizes of the programs names, found among paths, against baseline's; refuses a build at
    another variant than release, a baseline not among names, and a name without its program."""
    if variant != RELEASE:
        raise Refused(RELEASE_ONLY.format(variant=variant)
                      + 'webcpp.program-sizes requires <variant>release')
    if baseline not in names:
        raise Refused(f'the baseline {baseline} is not among the programs named, '
                      f'{" ".join(names)}')
    found = {name_of(path): path for path in paths}
    for name in names:
        if name not in found:
            raise Refused(f'{name} is not among the programs given')
    measured = {name: files_of(found[name], target) for name in dict.fromkeys(names)}
    base = {kind: (len(data), gzipped(data)) for kind, data in measured[baseline]}
    rows = []
    for name in sorted(measured):
        for kind, data in measured[name]:
            raw, packed = len(data), gzipped(data)
            rows.append({'program': name, 'file': kind, 'bytes': raw, 'gzip': packed,
                         'over_baseline': raw - base[kind][0],
                         'gzip_over_baseline': packed - base[kind][1]})
    return {'variant': variant, 'target': target, 'toolset': toolset, 'baseline': baseline,
            'programs': rows}


def programs_table(path: Path) -> str:
    """The Markdown table of the sizes path holds; refuses data not built at release."""
    try:
        read = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise Refused(f'{path}: cannot be read as JSON: {error}') from error
    variant = read.get('variant') if isinstance(read, dict) else None
    if variant != RELEASE:
        raise Refused(f'{path}: ' + RELEASE_ONLY.format(variant=variant)
                      + 'webcpp.program-sizes requires <variant>release')
    lines = [f'Linked programs on {read["target"]}, built with {read["toolset"]} at '
             f'variant={variant}, against the baseline {read["baseline"]}.', '',
             '| program | file | bytes | gzip -9n | over baseline | gzip -9n over baseline |',
             '| --- | --- | ---: | ---: | ---: | ---: |']
    lines += [f'| {r["program"]} | {r["file"]} | {r["bytes"]:,} | {r["gzip"]:,} '
              f'| {r["over_baseline"]:,} | {r["gzip_over_baseline"]:,} |'
              for r in read['programs']]
    return '\n'.join(lines) + '\n'


def parser() -> argparse.ArgumentParser:
    """The command line: the subcommands manifest and table."""
    parsed = argparse.ArgumentParser(
        prog='variants.py', description="A page program's variants' manifest, and their sizes.")
    commands = parsed.add_subparsers(dest='command', required=True)
    written = commands.add_parser('manifest', help='write the manifest of a program')
    written.add_argument('--out', type=Path, required=True)
    for variant in VARIANTS:
        written.add_argument(f'--{variant}', type=Path, required=True)
    sized = commands.add_parser('table', help='write the table of the manifests\' sizes')
    sized.add_argument('--variant', required=True,
                       help='the b2 variant the manifests were built at: only release is taken')
    sized.add_argument('--out', type=Path, required=True)
    sized.add_argument('manifests', type=Path, nargs='+')
    linked = commands.add_parser('programs', help='write the sizes of linked programs')
    linked.add_argument('--variant', required=True,
                        help='the b2 variant the programs were built at: only release is taken')
    linked.add_argument('--target', required=True)
    linked.add_argument('--toolset', required=True)
    linked.add_argument('--baseline', required=True)
    linked.add_argument('--names', nargs='+', required=True)
    linked.add_argument('--out', type=Path, required=True)
    linked.add_argument('programs', type=Path, nargs='+')
    tabled = commands.add_parser('programs-table', help='write the table of programs\' sizes')
    tabled.add_argument('--out', type=Path, required=True)
    tabled.add_argument('sizes', type=Path)
    return parsed


def main(argv: list[str]) -> int:
    """Runs the subcommand argv names; 0 when it is done, 1 when it refused."""
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == 'manifest':
            manifest(arguments.out, {variant: getattr(arguments, variant)
                                     for variant in VARIANTS})
        elif arguments.command == 'programs':
            sized = programs(arguments.variant, arguments.target, arguments.toolset,
                             arguments.baseline, arguments.names, arguments.programs)
            arguments.out.write_text(json.dumps(sized, indent=4) + '\n')
        elif arguments.command == 'programs-table':
            text = programs_table(arguments.sizes)
            arguments.out.write_text(text)
            sys.stdout.write(text)
        else:
            sys.stdout.write(table(arguments.out, arguments.manifests, arguments.variant))
    except Refused as refused:
        print(f'variants.py: {refused}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
