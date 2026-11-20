#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks tools/webcpp-mkdir.jam: on Windows, the action that makes a directory of the build
succeeds when another action made the directory between its test and its mkdir, which happens
when b2 -j makes one directory under two spellings, relative and absolute, at once (CI run
44690351573: `...failed common.mkdir bin\\third_party...`). A dry run of a project that imports
webcpp, whose b2 believes it is on Windows, prints for each directory b2's test and mkdir, then a
last line that decides by the directory alone: a mkdir that found it made fails, and the action
still succeeds. Run with the names of some cases to run only those."""

from __future__ import annotations

import sys
from pathlib import Path

import harness

# A project of one file in out/made, from a superproject that imports webcpp as a library's Jamfile
# does.
JAMFILE = '''import webcpp ;
make made.txt : : @touch : <location>out/made ;
actions touch
{
    echo made > "$(<)"
}
'''

# The action's last line, for a directory.
DECIDES = 'if exist "{}\\" (exit /b 0) else (exit /b 1)'


def test_the_action_on_windows_decides_by_the_directory(root: Path) -> None:
    # The user-config makes b2 believe it runs on Windows and leaves it so, for webcpp to choose
    # Windows's action; a dry run executes nothing.
    harness.configure(root, harness.user_config(root).read_text()
                      + '\nimport modules ;\nmodules.poke os : .name : NT ;\n')
    # Boost's version is read with Windows's findstr, which a dry run on another host has not.
    harness.replace(root / 'Jamroot', '<conditional>@boost-check', '<webcpp-boost-check>off')
    (root / 'libs/demo/test/mkdir').mkdir(parents=True)
    (root / 'libs/demo/test/mkdir/Jamfile').write_text(JAMFILE)
    result = harness.run_b2(root, '-n', '-a', '-d+2', 'libs/demo/test/mkdir//made.txt')
    harness.expect(result, True, 'common.mkdir')
    made = [line for line in result.stdout.splitlines() if line.startswith('common.mkdir ')]
    assert made, result.stdout
    for line in made:
        directory = line[len('common.mkdir '):].strip()
        assert DECIDES.format(directory) in result.stdout, (directory, result.stdout)
        assert f'if not exist "{directory}\\" mkdir "{directory}"' in result.stdout, result.stdout


CASES = [test_the_action_on_windows_decides_by_the_directory]

if __name__ == '__main__':
    sys.exit(harness.run_cases('mkdir_test', CASES, sys.argv[1:]))
