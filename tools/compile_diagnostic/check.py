#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Fails a webcpp.compile-diagnostic test whose -verify directives clang dropped. Usage:
check.py --database FILE --output FILE

The test's compile ran clang's -verify with -verify-ignore-unexpected=error, which tolerates the
cascade of errors that follows a header's #error, and also hides the errors -verify itself reports
on a directive it cannot read: a header it names that cannot be located, a text whose `}}` is not
on its line. -verify then drops that directive, and the test passes on nothing. FILE, the
compilation database entry clang wrote for that compile (-MJ), gives its exact command, which this
runs again with -fsyntax-only and clang's diagnostic log, which records every diagnostic, those
-verify ignores included. An error located inside a directive, in a comment after its
`expected-<kind>`, is one of -verify's own: each is printed, and the check fails. Otherwise it
writes --output."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from pathlib import Path

# The start of a -verify directive in a line: `expected-` and its kind, after a comment's opener.
DIRECTIVE = re.compile(r'(//|/\*).*?\bexpected-(?:error|warning|remark|note|no-diagnostics)')


def command_of(database: Path) -> tuple[list[str], Path]:
    """The words of the compile that wrote database, without what makes it write files (its -c,
    -o and -MJ, which a run with -fsyntax-only would leave unused, an error under -Werror), and
    its directory. clang writes an entry followed by a comma, and rewrites the file at each
    compile; the last entry is taken all the same."""
    entries = json.loads('[' + database.read_text().strip().rstrip(',') + ']')
    entry = entries[-1]
    words: list[str] = []
    arguments = iter(entry['arguments'])
    for word in arguments:
        if word in ('-o', '-MJ'):
            next(arguments, None)
        elif word != '-c':
            words.append(word)
    return words, Path(entry['directory'])


def diagnostics_of(log: Path) -> list[dict[str, str]]:
    """The diagnostics of clang's -diagnostic-log-file log, each a dict of its keys: one <dict>
    per compile, which holds an <array> of <dict>s of <key> and value pairs."""
    root = ElementTree.fromstring('<log>' + log.read_text() + '</log>')
    found = []
    for array in root.iter('array'):
        for entry in array.findall('dict'):
            children = list(entry)
            found.append({key.text or '': value.text or ''
                          for key, value in zip(children[::2], children[1::2])})
    return found


def in_directive(directory: Path, diagnostic: dict[str, str]) -> bool:
    """Whether diagnostic is located in a -verify directive: on a line that holds one, at or
    after its `expected-<kind>`."""
    path = directory / diagnostic.get('filename', '')
    try:
        line_number = int(diagnostic.get('line', '0'))
        column = int(diagnostic.get('column', '0'))
        lines = path.read_text(errors='replace').splitlines()
    except (OSError, ValueError):
        return False
    if not 1 <= line_number <= len(lines):
        return False
    line = lines[line_number - 1]
    return any(column - 1 >= match.end(1) for match in DIRECTIVE.finditer(line))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    database = Path(args.database)
    if not database.is_file():
        print(f'compile_diagnostic: missing: {database}, the compile\'s -MJ entry; build the test '
              'again with -a', file=sys.stderr)
        return 1
    words, directory = command_of(database)
    with tempfile.TemporaryDirectory() as scratch:
        log = Path(scratch) / 'diagnostics.log'
        # The compile's verdict was the test's; this run only records what clang reported.
        run = subprocess.run(words + ['-fsyntax-only', '-Xclang', '-diagnostic-log-file',
                                      '-Xclang', str(log)],
                             cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, check=False)
        if not log.is_file():
            print(f'compile_diagnostic: clang wrote no diagnostic log for {database}:\n'
                  f'{run.stdout}', file=sys.stderr)
            return 1
        diagnostics = diagnostics_of(log)
    dropped = [diagnostic for diagnostic in diagnostics
               if diagnostic.get('level') in ('error', 'fatal error')
               and in_directive(directory, diagnostic)]
    for diagnostic in dropped:
        print(f'{diagnostic.get("filename")}:{diagnostic.get("line")}:{diagnostic.get("column")}: '
              f'error: {diagnostic.get("message")} (clang\'s -verify drops this directive, so the '
              'test would pass without it)', file=sys.stderr)
    if dropped:
        return 1
    Path(args.output).write_text(f'{len(diagnostics)} diagnostics, every directive read\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
