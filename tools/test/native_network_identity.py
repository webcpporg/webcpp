#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Compile real native consumers without B2, generated overlays or a Cobalt archive."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def run(command: list[str], environment: dict[str, str]) -> None:
    """Show and execute a bounded consumer command with its actual output."""
    print(shlex.join(command), flush=True)
    subprocess.run(command, env=environment, check=True, timeout=60)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--boost-include', type=Path, required=True)
    arguments = parser.parse_args()
    environment = dict(os.environ)
    for name in ('CPATH', 'CPLUS_INCLUDE_PATH', 'C_INCLUDE_PATH'):
        environment.pop(name, None)
    command = [str(arguments.compiler), '-std=c++20', '-O2', '-pthread',
               '-Wall', '-Wextra', '-Werror', '-DBOOST_COBALT_NO_LIB=1',
               '-isystem', str(arguments.boost_include)]
    for library in ('config', 'asio', 'beast', 'cobalt'):
        command += ['-I', str(ROOT / 'libs' / library / 'include')]
    with tempfile.TemporaryDirectory(prefix='webcpp native consumer ') as temporary:
        output = Path(temporary)
        for exceptions in ('on', 'off'):
            flags = [] if exceptions == 'on' else ['-fno-exceptions']
            for upstream_first in (False, True):
                order = ['-DWEBCPP_TEST_BOOST_FIRST=1'] if upstream_first else []
                run(command + flags + order + ['-c',
                    str(FIXTURES / 'native_network_identity.cpp'), '-o',
                    str(output / f'identity-{exceptions}-{upstream_first}.o')], environment)
            executable = output / f'runtime-{exceptions}'
            run(command + flags + [str(FIXTURES / 'native_network_runtime.cpp'),
                str(ROOT / 'tools/throw_exception.cpp'), '-o', str(executable)], environment)
            run([str(executable)], environment)
    print('native identity: 4 compilations and 2 runtime consumers passed', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
