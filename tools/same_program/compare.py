#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Compares the two programs of webcpp.same-program byte for byte, and on emscripten the .wasm
beside each .js. Usage: compare.py --output FILE WITH WITHOUT"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('with_library')
    parser.add_argument('without_library')
    args = parser.parse_args(argv)
    pairs = [(Path(args.with_library), Path(args.without_library))]
    if pairs[0][0].suffix == '.js':
        pairs.append((pairs[0][0].with_suffix('.wasm'), pairs[0][1].with_suffix('.wasm')))
    lines, faults = [], []
    for a, b in pairs:
        same = a.read_bytes() == b.read_bytes()
        line = f'{a} ({a.stat().st_size} bytes) and {b} ({b.stat().st_size} bytes)'
        lines.append(('same: ' if same else 'differ: ') + line)
        if not same:
            faults.append(line)
    Path(args.output).write_text('\n'.join(lines) + '\n')
    for fault in faults:
        print(f'same_program: differ: {fault}', file=sys.stderr)
    return 1 if faults else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
