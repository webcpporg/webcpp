#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks, without building anything, that every message of libs/hash/test/messages has its
Emscripten fixture in tools/test/fixtures/hash_jamfiles with the same source and text, and that
hash_jamfiles_test.py's check finds each kind of drift: a message without a fixture, a changed
source, a changed text, and a fixture that names a message with no directory."""

from __future__ import annotations

import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import hash_jamfiles_test as jamfiles
import user_jamfiles


def faults_of_copies(change: Callable[[Path, Path], None]) -> list[str]:
    """message_faults over copies of the messages and the fixtures, after change(messages,
    fixtures) has altered the copies."""
    with tempfile.TemporaryDirectory() as directory:
        messages = Path(directory) / 'messages'
        fixtures = Path(directory) / 'fixtures'
        shutil.copytree(jamfiles.MESSAGES, messages)
        shutil.copytree(jamfiles.CASES, fixtures)
        change(messages, fixtures)
        original = jamfiles.MESSAGES
        jamfiles.MESSAGES = messages
        try:
            return jamfiles.message_faults(user_jamfiles.case_directories(fixtures))
        finally:
            jamfiles.MESSAGES = original


def test_the_tree_has_no_fault():
    faults = jamfiles.message_faults(user_jamfiles.case_directories(jamfiles.CASES))
    assert faults == [], faults


def test_a_message_without_fixture_is_a_fault():
    def change(messages: Path, _: Path) -> None:
        shutil.copytree(messages / 'two_profiles', messages / 'three_profiles')
        (messages / 'three_profiles' / 'two_profiles.cpp').rename(
            messages / 'three_profiles' / 'three_profiles.cpp')

    faults = faults_of_copies(change)
    assert any('three_profiles has no fixture' in f for f in faults), faults


def test_a_changed_source_is_a_fault():
    def change(messages: Path, _: Path) -> None:
        source = messages / 'two_profiles' / 'two_profiles.cpp'
        source.write_text(source.read_text().replace('return 0;', 'return 1;'))

    faults = faults_of_copies(change)
    assert any(f.startswith('two_profiles: app.cpp') for f in faults), faults


def test_a_changed_text_is_a_fault():
    def change(messages: Path, _: Path) -> None:
        source = messages / 'xkcp_not_linked' / 'xkcp_not_linked.cpp'
        source.write_text(source.read_text().replace('needs XKCP', 'needs Keccak'))

    faults = faults_of_copies(change)
    assert any(f.startswith('xkcp_not_linked: the outcome') for f in faults), faults


def test_a_fixture_of_no_message_is_a_fault():
    def change(messages: Path, _: Path) -> None:
        shutil.rmtree(messages / 'two_overrides')

    faults = faults_of_copies(change)
    assert any(f.startswith('two_overrides: its Jamfile names') for f in faults), faults


def main() -> int:
    if not jamfiles.MESSAGES.is_dir():
        print('hash_jamfiles_format: libs/hash is not checked out. Check it out with '
              '`git submodule update --init libs/hash`.', file=sys.stderr)
        return 2
    for name, case in sorted(globals().items()):
        if name.startswith('test_'):
            case()
            print(f'{name}: ok')
    print('hash_jamfiles_format_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
