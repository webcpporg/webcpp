# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Verify the exact distributable libdatachannel source tree before running upstream code.

The source digest covers sorted (POSIX path, Git file mode, content SHA-256)
records encoded as compact ASCII JSON. The required pinned nested source trees
are included. Dot paths and explicitly omitted unused dependencies match
tools/release/release.py distributions.
Only this verified tree enters CMake, for checkouts and source archives alike.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys


def inventory_digest(records: list[tuple[str, str, str]]) -> str:
    """Hash paths, file types, executable bits and bytes without trusting timestamps."""
    data = json.dumps(sorted(records), ensure_ascii=True, separators=(',', ':')).encode('ascii')
    return hashlib.sha256(b'webcpp-libdatachannel-source-v1\0' + data).hexdigest()


def check_checkout(source: Path, pin: dict) -> None:
    """Keep Git pin and clean-tree checks only for a source checkout of its own."""
    if not os.path.lexists(source / '.git'):
        return
    top = subprocess.check_output(['git', '-C', str(source), 'rev-parse', '--show-toplevel'],
                                  text=True).strip()
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'],
                                       text=True).strip()
    if Path(top).resolve() != source or revision != pin['commit']:
        raise RuntimeError('libdatachannel checkout differs from tools/libdatachannel/pin.json; '
                           'update the submodule')
    subprocess.run(['git', '-C', str(source), 'diff', '--exit-code', 'HEAD', '--'],
                   check=True, stdout=subprocess.DEVNULL)
    for relative, revision in pin.get('required_submodules', {}).items():
        nested = source / relative
        if not (nested / '.git').exists():
            raise RuntimeError(f'libdatachannel source dependency is missing: {relative}; '
                               'run git submodule update --init --recursive '
                               'third_party/libs/libdatachannel')
        check_checkout(nested, {'commit': revision})


def stage_source(source: Path, destination: Path, pin: dict) -> None:
    """Copy distributable inputs, then verify the actual bytes CMake will consume."""
    omitted = pin['omitted_submodules']

    def excluded(directory: str, names: list[str]) -> set[str]:
        relative = Path(directory).relative_to(source)
        return {name for name in names if name.startswith('.') or
                (relative / name).as_posix() in omitted}

    shutil.copytree(source, destination, symlinks=True, ignore=excluded)
    windows = sys.platform == 'win32'
    executable = set(pin.get('executable_files', ()))
    normalize_eol = set()
    if windows and (source / '.git').exists():
        # Git for Windows may check text out as CRLF. Restore only paths Git
        # identifies as LF in its index and CRLF in the checkout, then verify
        # their canonical bytes against the same digest as every other host.
        for prefix in ('', *pin.get('required_submodules', {})):
            checkout = source / prefix
            entries = subprocess.check_output(
                ['git', '-C', str(checkout), 'ls-files', '--eol', '-z'])
            for entry in entries.split(b'\0'):
                if not entry:
                    continue
                metadata, name = entry.decode('utf-8').split('\t', 1)
                if metadata.split()[:2] == ['i/lf', 'w/crlf']:
                    normalize_eol.add((Path(prefix) / name).as_posix())
    records = []
    for directory, directories, files in os.walk(destination, followlinks=False):
        for name in directories + files:
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                continue
            if not stat.S_ISREG(mode):
                raise RuntimeError('libdatachannel source tree differs from '
                                   'tools/libdatachannel/pin.json: '
                                   f'unsupported file type: {path.relative_to(destination)}')
            relative = path.relative_to(destination).as_posix()
            data = path.read_bytes()
            if relative in normalize_eol:
                data = data.replace(b'\r\n', b'\n')
                path.write_bytes(data)
            # Windows has no POSIX executable bit. The pinned path inventory
            # supplies that metadata; paths, file types and bytes still match.
            is_executable = relative in executable if windows else bool(mode & 0o111)
            records.append((relative, '100755' if is_executable else '100644',
                            hashlib.sha256(data).hexdigest()))
    if inventory_digest(records) != pin['source_sha256']:
        raise RuntimeError('libdatachannel source tree differs from tools/libdatachannel/pin.json; '
                           'restore the pinned source checkout or distribution')
