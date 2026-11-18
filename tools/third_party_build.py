#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""The key of a source-built third-party library's inputs, and the selection of its builds.

key ROOT NAME SOURCE INPUT... prints the SHA-256 of each INPUT's path, relative to ROOT, and
bytes: the files that make NAME's build what it is, its scripts and its pin. B2 names the
directory of each configuration of NAME by this key and its build command, so a directory that
exists holds the build of exactly those inputs, and is never built again, b2 -a included
(tools/webcpp-third-party.jam). The checkout SOURCE, relative to ROOT, is checked first with
NAME's own rules, check_checkout of tools/NAME/source.py, against tools/NAME/pin.json: a checkout
that differs from its pin has no key, as it has no build.

select STAMP writes STAMP, <directory>/<library>-<configuration>.selected, and removes the other
selections of the library in its directory. A consumer depends on the selection of the
configuration it uses, so it is built again when that configuration changes, even to one built
earlier: its directory exists, and only the selection is new.

Exit 0 on success; 1, with the reason on standard output, when there is no key.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

USAGE = '''Usage: third_party_build.py key ROOT NAME SOURCE INPUT...
       third_party_build.py select STAMP'''


def check(root: Path, name: str, source: str) -> None:
    """Applies tools/<name>/source.py's check_checkout to source, against its pin."""
    tools = root / 'tools' / name
    rules = runpy.run_path(str(tools / 'source.py'))
    pin = json.loads((tools / 'pin.json').read_text())
    try:
        rules['check_checkout']((root / source).resolve(), pin)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f'{source} differs from its pinned commit; restore its files or '
                           f'update tools/{name}/pin.json') from error


def key(root: Path, inputs: list[str]) -> str:
    """The SHA-256 of each input's path and bytes, independent of the order inputs are given."""
    digest = hashlib.sha256(b'webcpp-third-party-inputs-v1\0')
    for relative in sorted(set(inputs)):
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f'{relative} is an input of a third-party build and is missing')
        content = path.read_bytes()
        digest.update(f'{Path(relative).as_posix()}\0{len(content)}\0'.encode())
        digest.update(content)
    return digest.hexdigest()


def select(stamp: Path) -> None:
    """Writes stamp and removes the other selections of its library in its directory."""
    library, _, selected = stamp.name.removesuffix('.selected').rpartition('-')
    for other in stamp.parent.glob(f'{library}-*.selected'):
        if other.name != stamp.name and other.name.rpartition('-')[0] == library:
            other.unlink()
    stamp.write_text(selected + '\n')


def main(arguments: list[str]) -> int:
    if len(arguments) >= 5 and arguments[0] == 'key':
        root = Path(arguments[1]).resolve()
        try:
            check(root, arguments[2], arguments[3])
            print(key(root, arguments[4:]))
        except RuntimeError as error:
            print(error)
            return 1
        return 0
    if len(arguments) == 2 and arguments[0] == 'select':
        select(Path(arguments[1]))
        return 0
    print(USAGE)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
