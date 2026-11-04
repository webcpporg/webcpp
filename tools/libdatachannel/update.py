#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Regenerate source integrity metadata from the commit already named in pin.json.

Run python3 tools/libdatachannel/update.py after explicitly updating the libdatachannel pin.
Read committed Git objects, never working-tree bytes or downloaded artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess

from source import check_checkout, inventory_digest

HERE = Path(__file__).resolve().parent


def regenerate(source: Path, pin: dict) -> dict:
    """Derive the distribution inventory and timestamp from the exact pinned commit."""
    if not (source / '.git').exists():
        raise RuntimeError('regenerating the libdatachannel pin requires its Git checkout')
    check_checkout(source, pin)
    records, executable, omitted = [], [], {}
    for prefix, revision in [('', pin['commit']), *pin['required_submodules'].items()]:
        checkout = source / prefix
        tree = subprocess.check_output(['git', '-C', str(checkout), 'ls-tree', '-r', '-z',
                                        revision])
        files = []
        for entry in tree.split(b'\0'):
            if not entry:
                continue
            metadata, name = entry.decode('utf-8').split('\t', 1)
            mode, kind, oid = metadata.split()
            relative = (Path(prefix) / name).as_posix()
            if any(part.startswith('.') for part in Path(relative).parts):
                continue
            if mode == '160000':
                required = pin['required_submodules'].get(relative)
                if required is None:
                    omitted[relative] = oid
                elif required != oid:
                    raise RuntimeError(f'libdatachannel nested pin differs: {relative}')
            elif kind == 'blob' and mode in ('100644', '100755'):
                files.append((relative, mode, oid))
            else:
                raise RuntimeError(f'unsupported libdatachannel source entry: {relative} ({mode})')
        objects = subprocess.run(['git', '-C', str(checkout), 'cat-file', '--batch'],
                                 input=''.join(oid + '\n' for _, _, oid in files).encode('ascii'),
                                 stdout=subprocess.PIPE, check=True)
        stream = io.BytesIO(objects.stdout)
        for name, mode, oid in files:
            actual, kind, size = stream.readline().decode('ascii').split()
            data = stream.read(int(size))
            if actual != oid or kind != 'blob' or stream.read(1) != b'\n':
                raise RuntimeError(f'invalid Git object for {name}')
            records.append((name, mode, hashlib.sha256(data).hexdigest()))
            if mode == '100755':
                executable.append(name)
    timestamp = subprocess.check_output(
        ['git', '-C', str(source), 'show', '-s', '--format=%ct', pin['commit']], text=True)
    return {**pin, 'source_sha256': inventory_digest(records),
            'source_date_epoch': int(timestamp.strip()), 'omitted_submodules': omitted,
            'executable_files': sorted(executable)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path,
                        default=HERE.parents[1] / 'third_party/libs/libdatachannel')
    parser.add_argument('--pin', type=Path, default=HERE / 'pin.json')
    args = parser.parse_args()
    pin = regenerate(args.source.resolve(), json.loads(args.pin.read_text()))
    args.pin.write_text(json.dumps(pin, indent=2) + '\n')
    print(f'libdatachannel {pin["version"]}: {pin["source_sha256"]}')


if __name__ == '__main__':
    main()
