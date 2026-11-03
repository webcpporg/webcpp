# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Verify the exact distributable OpenSSL source tree before running upstream code.

The source digest covers sorted (POSIX path, Git file mode, content SHA-256)
records encoded as compact ASCII JSON. Dot paths and pinned nested submodules
are omitted, exactly as tools/release/release.py omits them from a distribution.
Only this verified tree enters Configure, for checkouts and source archives alike.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess


def inventory_digest(records: list[tuple[str, str, str]]) -> str:
    """Hash paths, file types, executable bits and bytes without trusting timestamps."""
    data = json.dumps(sorted(records), ensure_ascii=True, separators=(',', ':')).encode('ascii')
    return hashlib.sha256(b'webcpp-openssl-source-v1\0' + data).hexdigest()


def check_checkout(source: Path, pin: dict) -> None:
    """Keep Git pin and clean-tree checks only for a source checkout of its own."""
    if not os.path.lexists(source / '.git'):
        return
    top = subprocess.check_output(['git', '-C', str(source), 'rev-parse', '--show-toplevel'],
                                  text=True).strip()
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'],
                                       text=True).strip()
    if Path(top).resolve() != source or revision != pin['commit']:
        raise RuntimeError('OpenSSL checkout differs from tools/openssl/pin.json; '
                           'update the submodule')
    subprocess.run(['git', '-C', str(source), 'diff', '--exit-code', 'HEAD', '--'],
                   check=True, stdout=subprocess.DEVNULL)


def stage_source(source: Path, destination: Path, pin: dict) -> None:
    """Copy distributable inputs, then verify the actual bytes Configure will consume."""
    omitted = pin['omitted_submodules']

    def excluded(directory: str, names: list[str]) -> set[str]:
        relative = Path(directory).relative_to(source)
        return {name for name in names if name.startswith('.') or
                (relative / name).as_posix() in omitted}

    shutil.copytree(source, destination, symlinks=True, ignore=excluded)
    records = []
    for directory, directories, files in os.walk(destination, followlinks=False):
        for name in directories + files:
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                continue
            if not stat.S_ISREG(mode):
                raise RuntimeError('OpenSSL source tree differs from tools/openssl/pin.json: '
                                   f'unsupported file type: {path.relative_to(destination)}')
            records.append((path.relative_to(destination).as_posix(),
                            '100755' if mode & 0o111 else '100644',
                            hashlib.sha256(path.read_bytes()).hexdigest()))
    if inventory_digest(records) != pin['source_sha256']:
        raise RuntimeError('OpenSSL source tree differs from tools/openssl/pin.json; '
                           'restore the pinned source checkout or distribution')
