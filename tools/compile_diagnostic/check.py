#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Fails a webcpp.compile-diagnostic test whose -verify directives clang dropped. Usage:
check.py --database FILE --output FILE

The test's compile ran clang's -verify with -verify-ignore-unexpected=error (unless the test is
`alone`), which tolerates the cascade of errors that follows a header's #error, and also hides the
errors -verify itself reports on a directive it cannot read: a header it names that cannot be
located, a text whose `}}` is not on its line. -verify then drops that directive, and the test
passes on nothing. FILE, the compilation database entry clang wrote for that compile (-MJ), gives
its exact command, which this runs again with -fsyntax-only and clang's diagnostic log, which
records every diagnostic, those -verify ignores included. An error located in a comment, a // or a
/* */ one over several lines, after an `expected-<kind>` of that comment, is one of -verify's own:
each is printed, and the check fails. So does a run that reports no error at all, which no test of
the rule can mean.
Otherwise it writes --output."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from pathlib import Path

# A -verify directive in the text of a comment: `expected-` and its kind.
DIRECTIVE = re.compile(r'\bexpected-(?:error|warning|remark|note|no-diagnostics)')

# The start of a raw string literal's delimiter, at an R" that a prefix may precede.
RAW = re.compile(r'(?:u8|[uUL])?R"([^()\\\s]{0,16})\(')


class Malformed(Exception):
    """A compilation database entry this check cannot read."""


def comments_of(text: str) -> list[tuple[int, int]]:
    """The comments of the C++ source text, each as the offsets of its first and past its last
    character, opener included: a // comment runs to the end of its line, a backslash before the
    end continuing it; a /* */ comment to its */. A // or /* in a string, a character or a raw
    string literal opens none."""
    found: list[tuple[int, int]] = []
    at, size = 0, len(text)
    while at < size:
        two = text[at:at + 2]
        if two == '//':
            end = at
            while True:
                end = text.find('\n', end)
                if end < 0:
                    end = size
                    break
                if text[end - 1:end] == '\\' or text[end - 2:end] == '\\\r':
                    end += 1
                    continue
                break
            found.append((at, end))
            at = end
        elif two == '/*':
            end = text.find('*/', at + 2)
            end = size if end < 0 else end + 2
            found.append((at, end))
            at = end
        elif (raw := RAW.match(text, at)) and (at == 0 or not is_word(text[at - 1])):
            close = text.find(')' + raw.group(1) + '"', raw.end())
            at = size if close < 0 else close + len(raw.group(1)) + 2
        elif text[at] == '"' or (text[at] == "'" and (at == 0 or not is_word(text[at - 1]))):
            # A ' after a digit or a letter is a digit separator (1'000), not a character.
            quote, at = text[at], at + 1
            while at < size and text[at] not in (quote, '\n'):
                at += 2 if text[at] == '\\' else 1
            at += 1
        else:
            at += 1
    return found


def is_word(character: str) -> bool:
    """Whether character can end an identifier or a number."""
    return character.isalnum() or character == '_'


def command_of(database: Path) -> tuple[list[str], Path]:
    """The words of the compile that wrote database, without what makes it write files (its -c,
    -o and -MJ, which a run with -fsyntax-only would leave unused, an error under -Werror), and
    its directory. clang writes an entry followed by a comma, and rewrites the file at each
    compile; the last entry is taken all the same."""
    try:
        entry = json.loads('[' + database.read_text().strip().rstrip(',') + ']')[-1]
        arguments = iter(list(entry['arguments']))
        directory = Path(entry['directory'])
    except (OSError, ValueError, IndexError, KeyError, TypeError) as error:
        raise Malformed(f'{database} is not a compilation database entry of clang\'s -MJ: '
                        f'{error!r}') from error
    words: list[str] = []
    for word in arguments:
        if word in ('-o', '-MJ'):
            next(arguments, None)
        elif word != '-c':
            words.append(str(word))
    return words, directory


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
    """Whether diagnostic is located in a -verify directive: in a comment, at or after an
    `expected-<kind>` of that comment. Its column counts bytes from 1."""
    path = directory / diagnostic.get('filename', '')
    try:
        line_number = int(diagnostic.get('line', '0'))
        column = int(diagnostic.get('column', '0'))
        data = path.read_bytes()
    except (OSError, ValueError):
        return False
    starts = [0] + [index + 1 for index, byte in enumerate(data) if byte == ord('\n')]
    if not 1 <= line_number <= len(starts) or column < 1:
        return False
    # Latin-1 maps each byte to one character, so offsets of bytes and of characters agree.
    text = data.decode('latin-1')
    at = starts[line_number - 1] + column - 1
    for start, end in comments_of(text):
        if start <= at < end:
            return any(match.start() <= at for match in DIRECTIVE.finditer(text, start, end))
    return False


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
    try:
        words, directory = command_of(database)
    except Malformed as error:
        print(f'compile_diagnostic: {error}', file=sys.stderr)
        return 1
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
        try:
            diagnostics = diagnostics_of(log)
        except ElementTree.ParseError as error:
            print(f'compile_diagnostic: clang\'s diagnostic log of {database} does not parse: '
                  f'{error}', file=sys.stderr)
            return 1
    errors = [diagnostic for diagnostic in diagnostics
              if diagnostic.get('level') in ('error', 'fatal error')]
    if not errors:
        print(f'compile_diagnostic: the compile of {database} reported no error: a '
              'compile-diagnostic test states at least one, so its check would see nothing',
              file=sys.stderr)
        return 1
    dropped = [diagnostic for diagnostic in errors if in_directive(directory, diagnostic)]
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
