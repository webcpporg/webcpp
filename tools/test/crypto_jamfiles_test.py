#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Builds every fixture of tools/test/fixtures/crypto_jamfiles, a Jamfile as a user of
webcpp::crypto writes it (b2's raw exe), with b2 as a user runs it, and checks its outcome file:
the build's status, the lines a failure prints, and a program's output (CODING-GUIDELINES.md
chapter 8), through user_jamfiles.py. One scratch superproject per target, with libs/crypto and
the fixtures in it; every case of a target shares one build directory, so BearSSL's 295 files are
compiled once per target. Run with the names of some cases to run only those, and with
--target <name> to run one target."""

from __future__ import annotations

import sys

import harness
import user_jamfiles

CASES = harness.FIXTURES / 'crypto_jamfiles'

# Cases whose outcome needs code that is not merged yet: a run without names leaves them out
# (and says so), a run that names one builds it. Each entry names what it waits for. The
# integrator empties it when the code it waits for is merged, and then rewrites the lines of those
# cases' outcome files as b2's whole output lines (a line: directive, if need be).
NOT_YET: dict[str, str] = {}


def main(argv: list[str]) -> int:
    return user_jamfiles.main('crypto_jamfiles', CASES, ('config', 'secure', 'crypto', 'hash'), NOT_YET, argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
