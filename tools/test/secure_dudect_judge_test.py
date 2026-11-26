#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks libs/secure/test/constant_time/dudect_judge.py, secure's copy of crypto's judge of
dudect's outputs, with crypto_dudect_judge_test.py's cases: the same scratch outputs and fake
programs, run against secure's judge. Run with the names of some cases to run only those."""

from __future__ import annotations

import sys

import crypto_dudect_judge_test

crypto_dudect_judge_test.JUDGE = (crypto_dudect_judge_test.ROOT /
                                  'libs/secure/test/constant_time/dudect_judge.py')

if __name__ == '__main__':
    sys.exit(crypto_dudect_judge_test.main(sys.argv[1:]))
