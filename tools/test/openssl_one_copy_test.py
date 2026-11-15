#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Checks that the OpenSSL aliases of several libraries in one program link libssl.a and
libcrypto.a once each, from one directory (CODING-GUIDELINES.md chapter 5 rule 10): asio's and
crypto's in libs/crypto/test//openssl_one_copy, and, when libs/hash is checked out, hash's and
crypto's in libs/hash/test//openssl_one_copy.

It reads the link line b2 prints (-d+2 with -n, so nothing is rebuilt) for each program and its
_no_exceptions twin, and fails on any archive count other than one per program, or on archives
from two directories.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = re.compile(r'[^\s"]*/lib(ssl|crypto)\.a')
LINK = re.compile(r'-o "?[^\s"]*/openssl_one_copy(_no_exceptions)?"?(\s|$)')


def check_link_line(line: str) -> list[str]:
    """The faults of one link line: an archive not exactly once, or two directories."""
    found = [m.group(0) for m in ARCHIVE.finditer(line)]
    faults = []
    for name in ('libssl.a', 'libcrypto.a'):
        count = sum(1 for path in found if path.endswith('/' + name))
        if count != 1:
            faults.append(f'{name} is linked {count} times')
    if len({path.rsplit('/', 1)[0] for path in found}) > 1:
        faults.append(f'the archives come from different directories: {sorted(set(found))}')
    return faults


def self_test() -> None:
    """The checker itself: a line with a repeated archive or two directories must fail."""
    good = '-o "x/openssl_one_copy" /a/config-1/libssl.a /a/config-1/libcrypto.a'
    assert check_link_line(good) == []
    twice = good + ' /a/config-1/libssl.a'
    assert check_link_line(twice) == ['libssl.a is linked 2 times']
    split = '-o "x/openssl_one_copy" /a/config-1/libssl.a /b/config-2/libcrypto.a'
    assert 'different directories' in ' '.join(check_link_line(split))
    assert check_link_line('-o "x/openssl_one_copy"') != []


def programs() -> list[str]:
    """The b2 targets checked: crypto's pair always, hash's when its library is checked out."""
    libraries = ['crypto'] + (['hash'] if (ROOT / 'libs/hash/build.jam').is_file() else [])
    return [f'libs/{library}/test//openssl_one_copy{suffix}'
            for library in libraries for suffix in ('', '_no_exceptions')]


def main() -> int:
    self_test()
    targets = programs()
    unset = ('CPATH', 'CPLUS_INCLUDE_PATH', 'C_INCLUDE_PATH')
    env = {k: v for k, v in os.environ.items() if k not in unset}
    command = ['b2', f'--user-config={ROOT}/.local/user-config.jam', '-a', '-n', '-d+2', '-j3',
               '--build-dir=' + str(ROOT / 'bin/lane-onecopy'), *sys.argv[1:], *targets]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(result.stdout + result.stderr, file=sys.stderr)
        return 1
    lines = [line for line in result.stdout.splitlines()
             if LINK.search(line) and ARCHIVE.search(line)]
    # b2 prints a command on several lines; join each link command from its -o line to the next
    # blank.
    text = result.stdout
    commands = [chunk for chunk in re.split(r'\n\s*\n', text)
                if LINK.search(chunk) and ARCHIVE.search(chunk)]
    if len(commands) != len(targets):
        print(f'openssl_one_copy: expected {len(targets)} link commands, found {len(commands)} '
              f'({len(lines)} lines)', file=sys.stderr)
        return 1
    faults = [fault for chunk in commands for fault in check_link_line(chunk)]
    for fault in faults:
        print(f'openssl_one_copy: {fault}', file=sys.stderr)
    if not faults:
        print('openssl_one_copy_test: ok')
    return 1 if faults else 0


if __name__ == '__main__':
    sys.exit(main())
