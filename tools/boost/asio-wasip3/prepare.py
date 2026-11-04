# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Apply a checked Asio patch to private headers, never to installed Boost."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(source: Path, output: Path, bundle: Path) -> None:
    source, output, bundle = source.resolve(), output.resolve(), bundle.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('the overlay must be separate from the installed Boost tree')
    manifest = json.loads((bundle / 'manifest.json').read_text())
    version = (source / 'boost/version.hpp').read_text()
    if not re.search(r'^#define BOOST_VERSION ' + str(manifest['boost_version']) + r'\s*$',
                     version, re.MULTILINE):
        raise ValueError('this Asio patch requires Boost 1.92; rebase and verify the patch')
    inputs = {}
    for name, hashes in manifest['files'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or not name.startswith('boost/asio/'):
            raise ValueError('invalid patch manifest path: ' + name)
        data = (source / path).read_bytes()
        if digest(data) != hashes['before']:
            raise ValueError('incompatible Boost header: ' + name + '; rebase the Asio patch')
        inputs[name] = data
    # An obsolete patched header would still shadow its upstream replacement.
    # Refuse stale output rather than deleting files from a developer's checkout.
    for path in output.rglob('*'):
        if path.is_symlink():
            raise ValueError('overlay contains a symlink: ' + str(path))
        if path.is_file() and path.relative_to(output).as_posix() not in inputs:
            raise ValueError('unexpected overlay file: ' + str(path)
                             + '; clean the private overlay directory and rebuild')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='asio-patch-', dir=output.parent) as temporary:
        stage = Path(temporary)
        for name, data in inputs.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        subprocess.run(['git', 'apply', '--no-index', str(bundle / 'boost-1.92.patch')],
                       cwd=stage, check=True, capture_output=True, text=True)
        for name, hashes in manifest['files'].items():
            if digest((stage / name).read_bytes()) != hashes['after']:
                raise ValueError('patched header failed verification: ' + name)
        for name in inputs:
            destination = output / name
            data = (stage / name).read_bytes()
            if destination.is_file() and destination.read_bytes() == data:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage / name, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boost', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stamp', type=Path)
    parser.add_argument('--bundle', type=Path, default=Path(__file__).parent)
    arguments = parser.parse_args()
    try:
        prepare(arguments.boost, arguments.output, arguments.bundle)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Asio preparation failed: {error}\n')
    if arguments.stamp:
        arguments.stamp.parent.mkdir(parents=True, exist_ok=True)
        arguments.stamp.write_text('Boost.Asio patched headers verified\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
