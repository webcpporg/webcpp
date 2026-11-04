#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Builds a driven native consumer and checks Windows command arguments from B2 itself."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

import harness


def consumer(root: Path, *, windows: bool = False) -> None:
    """Use the real drive rule with a native program, in the harness's spaced checkout path."""
    harness.configure(root, '')
    (root / 'program.cpp').write_text('int main() { return 0; }\n')
    (root / 'driver with space.py').write_text(
        'import json, pathlib, subprocess, sys\n'
        'assert sys.argv[1] == "argument with space", sys.argv\n'
        'subprocess.run([str(pathlib.Path(sys.argv[2]).resolve())], check=True)\n'
        'pathlib.Path("received.json").write_text(json.dumps(sys.argv[1:]))\n')
    (root / 'Jamroot').write_text(
        'import modules ;\nimport os ;\nimport project ;\n'
        'project : build-dir bin ;\n'
        'local host = [ os.name ] ;\n' +
        ('modules.poke os : .name : NT ;\n' if windows else '') +
        f'modules.load webcpp-drive : drive.jam : "{root.as_posix()}/tools/drive" ;\n'
        'import webcpp-drive ;\n'
        'modules.poke os : .name : $(host) ;\n'
        'alias node-modules ;\n'
        'local current = [ project.current ] ;\n'
        f'webcpp-drive.drive $(current) "{root.as_posix()}" . "Jamfile with space" '
        f'"{root.as_posix()}"\n'
        '  : upstream-single : program.cpp : : "driver with space.py" '
        f': "argument with space" : "{Path(sys.executable).as_posix()}" ;\n')


def test_native_driven_consumer_preserves_spaced_paths(root: Path) -> None:
    consumer(root)
    result = harness.run_b2(root, '-a', '-d2')
    harness.expect(result, True, '**passed**')
    received = json.loads((root / 'received.json').read_text())
    assert received[0] == 'argument with space', received
    assert (root / received[1]).is_file(), received
    assert len(list((root / 'bin').rglob('upstream-single.driven'))) == 1


def test_windows_action_keeps_program_name_one_argument(root: Path) -> None:
    consumer(root)
    harness.expect(harness.run_b2(root, '-a'), True, '**passed**')
    (root / 'received.json').unlink()
    consumer(root, windows=True)
    result = harness.run_b2(root, '-a', '-n', '-d2')
    harness.expect(result, True)
    command = next(line.strip() for line in result.stdout.splitlines()
                   if '--program ' in line and 'drive.py' in line)
    # This command uses no embedded double quotes or trailing backslashes. Windows
    # groups its quoted paths with double quotes, preserving ordinary single quotes.
    # Feed those actual B2 arguments to the real parser and process runner on every OS.
    lexer = shlex.shlex(command, posix=True)
    lexer.whitespace_split = True
    lexer.quotes = '"'
    lexer.escape = ''
    lexer.commenters = ''
    words = list(lexer)
    result = subprocess.run([sys.executable, *words[1:]], cwd=root,
                            capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, (command, result.stdout, result.stderr)
    assert words[words.index('--program') + 1] == (
        'webcpp.drive upstream-single in Jamfile with space'), words
    assert json.loads((root / 'received.json').read_text())[0] == 'argument with space'


CASES = [
    test_native_driven_consumer_preserves_spaced_paths,
    test_windows_action_keeps_program_name_one_argument,
]


if __name__ == '__main__':
    sys.exit(harness.run_cases('drive_test', CASES, sys.argv[1:], fixtures=()))
