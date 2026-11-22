# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""The check of the Botan checkout that /third_party//botan configures and compiles.

tools/third_party_build.py key applies check_checkout before it keys Botan's configurations
(tools/webcpp-third-party.jam), so that b2 never configures a checkout other than its pin: its
HEAD must be tools/botan/pin.json's commit and its tracked files unchanged. A source distribution,
which holds no .git, carries the files of the commit its release recorded, and is taken as it is.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess


def check_checkout(checkout: Path, pin: dict) -> None:
    """Raises RuntimeError unless checkout, a Git checkout, is at pin's commit and clean."""
    if not os.path.lexists(checkout / '.git'):
        return
    revision = subprocess.run(['git', '-C', str(checkout), 'rev-parse', 'HEAD'],
                              capture_output=True, text=True)
    if revision.returncode != 0 or revision.stdout.strip() != pin['commit']:
        raise RuntimeError(f'Botan checkout {checkout} is not at {pin["commit"]} '
                           '(tools/botan/pin.json); run `git submodule update --init '
                           'third_party/libs/botan`')
    status = subprocess.run(['git', '-C', str(checkout), 'status', '--porcelain',
                             '--untracked-files=no'], capture_output=True, text=True)
    if status.returncode != 0 or status.stdout.strip():
        raise RuntimeError(f'Botan checkout {checkout} has changed files; restore them:\n'
                           f'{status.stdout.rstrip()}')
