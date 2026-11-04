#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Runs the driver of a test of webcpp.drive, bounded, and leaves no process of it behind.

Usage: drive.py --program NAME --output FILE [--timeout SECONDS] -- WORD...

The words are the driver's command, `<original words> <script> <arguments> <program>`, as
webcpp.drive gives them: its last word is the program it drives. --program names the test's
declaration in a message, as webcpp.drive does ("webcpp.drive <name> in <Jamfile>").

The driver runs with its standard input /dev/null, and what it prints is this script's output, the
action's, which b2 shows and --out-xml records. It is the child of the shared process_tree.py
keeper, which owns a POSIX process group or a Windows Job Object. Its standard input is a pipe
that only this script holds: when it ends, however this script ended, the keeper stops its whole
tree. Once the driver has ended, its tree is stopped too, so that a program it left running does
not outlive the test. On Windows the job is assigned before the driver starts; descendants inherit
membership, and the keeper's non-inheritable handle closes on exit to terminate them all.

The run is bounded by --timeout, 30 s by default as serve.py's: a driver that has not ended by then,
because it hangs or waits on a program that hangs, is stopped with its whole tree, and the run
fails, naming the test, the program and the bound. POSIX sends SIGTERM then SIGKILL after GRACE
seconds; Windows terminates the keeper, which closes the job and stops its descendants immediately.

Exit with the driver's status, 0 when it passed, which writes the output file (`driven`); 1 when
the bound passed; 2 on a usage error. On any failure the output file is not left behind.
"""

from __future__ import annotations

import argparse
import contextlib
import subprocess
import sys
from pathlib import Path

# Shared process containment, independent of the HTTP runner's POSIX alarms.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'component'))

from process_tree import exit_status, start_tree, terminate_tree

# Seconds between the SIGTERM of a group and its SIGKILL, as serve.py waits.
GRACE = 5


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Runs the driver of a driven test, bounded, and leaves nothing behind.')
    parser.add_argument('--program', required=True, help='the test, as a message names it')
    parser.add_argument('--output', required=True, type=Path,
                        help='written once the driver exits with 0')
    parser.add_argument('--timeout', default='30',
                        help='seconds the driver may take, its program included (30 by default)')
    parser.add_argument('words', nargs='*', help='the driver\'s command, after --')
    arguments = parser.parse_args(argv)
    if not arguments.words:
        parser.error('no driver to run: give its command after --')
    try:
        timeout = float(arguments.timeout)
    except ValueError:
        parser.error(f'--timeout {arguments.timeout} is not a number of seconds')
    if not timeout > 0:
        parser.error(f'--timeout {arguments.timeout} is not a number of seconds above 0')
    arguments.timeout = timeout
    return arguments


def main(argv: list[str]) -> int:
    arguments = parse(argv)
    with contextlib.suppress(FileNotFoundError):
        arguments.output.unlink()
    driver = f'the driver of {arguments.words[-1]}'
    keeper = start_tree(arguments.words)
    try:
        status = keeper.wait(arguments.timeout)
    except subprocess.TimeoutExpired:
        terminate_tree(keeper)
        with contextlib.suppress(subprocess.TimeoutExpired):
            keeper.wait(GRACE)
        terminate_tree(keeper, force=True)
        keeper.wait()
        print(f'drive: {arguments.program}: {driver} did not end within {arguments.timeout:g} s; '
              'it was stopped with every process of its group, the program among them',
              file=sys.stderr, flush=True)
        return 1
    finally:
        # What the driver left running ends with the test.
        terminate_tree(keeper, force=True)
        if keeper.stdin is not None:
            keeper.stdin.close()
    if status != 0:
        print(f'drive: {arguments.program}: {driver} exited with {status}', file=sys.stderr,
              flush=True)
        return status
    arguments.output.write_text('driven\n')
    return 0


if __name__ == '__main__':
    sys.exit(exit_status(main(sys.argv[1:])))
