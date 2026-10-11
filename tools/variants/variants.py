#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Writes the manifest of a page program's suspension variants, and the table of their sizes.

Usage: variants.py manifest --out FILE --jspi SCRIPT --asyncify SCRIPT
       variants.py table --out FILE MANIFEST...

manifest writes FILE, <name>.variants.json, which a page's loader reads: for each variant, the
script, its JavaScript glue, relative to FILE's directory and written with /, and the size in bytes
of the .wasm beside it. Keys are sorted, indented by four spaces. A script or a .wasm that does not
exist is refused before anything is written.

table writes FILE, a Markdown table of every manifest's sizes, one row per program named by its
manifest's file name less .variants.json, sorted, with asyncify's size over jspi's, and prints it.
A manifest that lacks a variant, its script or a positive integer size is refused, naming it.

A failure is a line on the standard error and status 1; a usage error is status 2.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path, PurePath
from typing import Any

VARIANTS = ('jspi', 'asyncify')
SUFFIX = '.variants.json'


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


def table(out: Path, manifests: list[Path]) -> str:
    """Writes out, the Markdown table of the manifests' sizes, and returns it; refuses a manifest
    that is not one before it writes anything."""
    rows = sorted((program(path), *sizes(path)) for path in manifests)
    lines = ['| program | jspi | asyncify | asyncify / jspi |', '| --- | ---: | ---: | ---: |']
    lines += [f'| {name} | {jspi:,} | {asyncify:,} | {asyncify / jspi:.2f} |'
              for name, jspi, asyncify in rows]
    text = '\n'.join(lines) + '\n'
    out.write_text(text)
    return text


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
    sized.add_argument('--out', type=Path, required=True)
    sized.add_argument('manifests', type=Path, nargs='+')
    return parsed


def main(argv: list[str]) -> int:
    """Runs the subcommand argv names; 0 when it is done, 1 when it refused."""
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == 'manifest':
            manifest(arguments.out, {variant: getattr(arguments, variant)
                                     for variant in VARIANTS})
        else:
            sys.stdout.write(table(arguments.out, arguments.manifests))
    except Refused as refused:
        print(f'variants.py: {refused}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
