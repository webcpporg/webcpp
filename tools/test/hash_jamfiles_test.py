#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Builds every fixture of tools/test/fixtures/hash_jamfiles, a Jamfile as a user of webcpp::hash
writes it (b2's raw exe), with b2 as a user runs it, and checks its outcome file: the build's
status, the lines a failure prints, and a program's output (CODING-GUIDELINES.md chapter 8),
through user_jamfiles.py. The cases are each line of the library's spec 5.1, one program with
every C library, and each stop of the build: the canaries at link time on every target, and the
messages raised on Emscripten.

Each message of libs/hash/test/messages/<name>/ (a compile-diagnostic, natively and on WASI) has
the fixture <name>, its Emscripten case: before building anything, the test checks that the
fixture's app.cpp is the message's source without its expected-error directive, and that its
outcome's one contains: line is the directive's text, unless the message is in NO_FIXTURE.

The scratch superproject holds libs/config, libs/hash, libs/crypto (whose canary
/third_party//bearssl compiles) and libs/asio (whose /webcpp/asio//asio the asynchronous family's
messages name). Run with the names of some cases to run only those, and with
--target <name> to run one target."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import harness
import user_jamfiles

CASES = harness.FIXTURES / 'hash_jamfiles'
MESSAGES = harness.ROOT / 'libs/hash/test/messages'

# Cases whose outcome needs code that is not merged yet, as crypto_jamfiles_test.py's NOT_YET.
NOT_YET: dict[str, str] = {}

# The messages of libs/hash/test/messages without an Emscripten fixture, each with its reason.
NO_FIXTURE = {
    'ripemd128_on_openssl': 'it names /webcpp/hash//openssl, which Emscripten refuses before '
                            'the message (the fixture openssl_on_emscripten)',
    'webcrypto_off_emscripten': 'its message is off Emscripten alone: there the asynchronous '
                                'family takes backends::webcrypto',
    'kbkdf_hmac_on_openssl': 'it names /webcpp/hash//openssl, which Emscripten refuses before '
                             'the message (the fixture openssl_on_emscripten)',
}

DIRECTIVE = re.compile(r'^// expected-error@\S+ \{\{(.*)\}\}$', re.MULTILINE)
# The Jamfile's first line after the licence names the message a fixture builds.
CLAIM = re.compile(r'^# test/messages/(\S+) of webcpp::hash', re.MULTILINE)


def program_of(source: str) -> str:
    """A message's source as a user's program: without its expected-error directive, the
    clang-format guards around it and the note on clang's -verify, which only the
    compile-diagnostic rule reads, and with no run of blank lines left behind."""
    text = re.sub(r'^// expected-error@.*\n', '', source, flags=re.MULTILINE)
    text = text.replace('// clang-format off\n// clang-format on\n', '')
    text = re.sub(r"^// clang's -verify reads.*\n(?://.*\n)*", '', text, flags=re.MULTILINE)
    return re.sub(r'\n\n\n+', '\n\n', text)


def message_faults(cases: list[Path]) -> list[str]:
    """The faults between libs/hash/test/messages and the fixtures, found without b2: a message
    with no fixture and no entry in NO_FIXTURE, a fixture whose source or text is not its
    message's, and a fixture that claims a message there is no directory of."""
    faults: list[str] = []
    by_name = {case.name: case for case in cases}
    messages = sorted(p for p in MESSAGES.iterdir() if p.is_dir())
    for message in messages:
        name = message.name
        case = by_name.get(name)
        if name in NO_FIXTURE:
            if case is not None:
                faults.append(f'{name}: a fixture of a message in NO_FIXTURE')
            continue
        if case is None:
            faults.append(f'test/messages/{name} has no fixture {name} (an Emscripten case), '
                          'nor an entry in NO_FIXTURE')
            continue
        source = (message / f'{name}.cpp').read_text()
        texts = DIRECTIVE.findall(source)
        if (case / 'app.cpp').read_text() != program_of(source):
            faults.append(f'{name}: app.cpp is not test/messages/{name}/{name}.cpp without its '
                          'directive')
        expected = user_jamfiles.outcome(case / f'{name}.outcome', 'emscripten')
        if expected.targets != ['emscripten'] or expected.contains != texts:
            faults.append(f'{name}: the outcome is not the text {texts!r} on emscripten alone')
    names = {m.name for m in messages}
    for case in cases:
        claimed = CLAIM.search((case / 'Jamfile').read_text())
        if claimed and (claimed.group(1) != case.name or case.name not in names):
            faults.append(f'{case.name}: its Jamfile names test/messages/{claimed.group(1)}, '
                          'which is not its own message directory')
    return faults


def main(argv: list[str]) -> int:
    return user_jamfiles.main('hash_jamfiles', CASES, ('config', 'hash', 'crypto', 'asio'), NOT_YET,
                              argv, message_faults)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
