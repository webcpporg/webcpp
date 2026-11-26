#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Builds every fixture of tools/test/fixtures/secure_jamfiles, a Jamfile as a user of
webcpp::secure writes it (b2's raw exe), with b2 as a user runs it, and checks its outcome file:
the build's status, the lines a failure prints, and a program's output (CODING-GUIDELINES.md
chapter 8), through user_jamfiles.py. The cases are the spec's scenario "A program that erases a
buffer builds nothing" (program, and program_no_exceptions with `<exception-handling>off`), and
the Emscripten case of each message of libs/secure/test/messages.

Each message of libs/secure/test/messages/<name>/ (a compile-diagnostic, natively and on WASI) has
the fixture <name>_on_emscripten, its Emscripten case: before building anything, the test checks
that the fixture's app.cpp is the message's source without its expected-error directive, and that
its outcome's one contains: line is the directive's text.

The scratch superproject holds libs/config and libs/secure. Run with the names of some cases to
run only those, and with --target <name> to run one target."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import harness
import user_jamfiles

CASES = harness.FIXTURES / 'secure_jamfiles'
MESSAGES = harness.ROOT / 'libs/secure/test/messages'

# Cases whose outcome needs code that is not merged yet, as crypto_jamfiles_test.py's NOT_YET.
NOT_YET: dict[str, str] = {}

DIRECTIVE = re.compile(r'^// expected-error@\S+ \{\{(.*)\}\}$', re.MULTILINE)


def program_of(source: str) -> str:
    """A message's source as a user's program: without its expected-error directive, the
    clang-format guards around it and the note on clang's -verify, which only the
    compile-diagnostic rule reads, and with no run of blank lines left behind."""
    text = re.sub(r'^// expected-error@.*\n', '', source, flags=re.MULTILINE)
    text = text.replace('// clang-format off\n// clang-format on\n', '')
    text = re.sub(r"^// clang's -verify reads.*\n(?://.*\n)*", '', text, flags=re.MULTILINE)
    return re.sub(r'\n\n\n+', '\n\n', text)


def message_faults(cases: list[Path]) -> list[str]:
    """The faults between libs/secure/test/messages and the fixtures, found without b2: a message
    with no fixture <name>_on_emscripten, a fixture whose source or text is not its message's,
    and a fixture named for a message there is no directory of."""
    faults: list[str] = []
    by_name = {case.name: case for case in cases}
    messages = sorted(p for p in MESSAGES.iterdir() if p.is_dir())
    for message in messages:
        name = message.name
        case = by_name.get(f'{name}_on_emscripten')
        if case is None:
            faults.append(f'test/messages/{name} has no fixture {name}_on_emscripten')
            continue
        source = (message / f'{name}.cpp').read_text()
        texts = DIRECTIVE.findall(source)
        if (case / 'app.cpp').read_text() != program_of(source):
            faults.append(f'{case.name}: app.cpp is not test/messages/{name}/{name}.cpp without '
                          'its directive')
        expected = user_jamfiles.outcome(case / f'{case.name}.outcome', 'emscripten')
        if expected.targets != ['emscripten'] or expected.contains != texts:
            faults.append(f'{case.name}: the outcome is not the text {texts!r} on emscripten '
                          'alone')
    names = {m.name for m in messages}
    for case in cases:
        if case.name.endswith('_on_emscripten') and \
                case.name[:-len('_on_emscripten')] not in names:
            faults.append(f'{case.name}: there is no test/messages/'
                          f'{case.name[:-len("_on_emscripten")]}')
    return faults


def main(argv: list[str]) -> int:
    return user_jamfiles.main('secure_jamfiles', CASES, ('config', 'secure'), NOT_YET, argv,
                              message_faults)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
