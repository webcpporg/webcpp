#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks third_party/: the JSON Schema Test Suite, pinned, reaches a test that names
/webcpp/third_party//json-schema-test-suite at the directory its define gives, natively and on
emscripten, and on wasip2 and wasip3, where wasmtime is given that directory; a changed file of the
suite runs such a test again; and a suite that is not checked out stops a build that needs it,
naming the command that checks it out, and no other build. Each case builds a scratch superproject
with the fixture library demo, whose path holds a space. It also checks that BearSSL, pinned and built
from its real sources with the canary of libs/crypto, compiles file by file with the flags a C
library needs and holds the canary's symbol; that a BearSSL or a libs/crypto that is not checked
out stops the build that needs it, naming the command; and that loading third_party/Jamfile prints
nothing b2 warns of. Run with the names of some cases to run
only those."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import harness

WASIP2 = ('toolset=clang-wasip2', 'testing.launcher=wasmtime')
WASIP3 = ('toolset=clang-wasip3', 'testing.launcher=wasmtime')
EMSCRIPTEN = ('toolset=emscripten',)

BEARSSL = 'third_party/libs/bearssl'

# The commit BearSSL is pinned at, of the mirror webcpporg/bearssl.
BEARSSL_COMMIT = '7bea48e5e850ab4cafbe68d3765cdaba13a86d6f'

PASSED = re.compile(r'^\*\*passed\*\* (.*)$', re.MULTILINE)

SUITE = 'third_party/libs/JSON-Schema-Test-Suite'

# The commit the suite is pinned at, of 2026-09-21.
SUITE_COMMIT = '5b0ee1613e45fcc2bddac00e07c19cd49b00d8a8'

WYCHEPROOF = 'third_party/libs/wycheproof'

# The commit Wycheproof is pinned at, of 2026-10-06.
WYCHEPROOF_COMMIT = '12fd3aaf33eb5fa1f52e026912ee00c054f9d984'

READER_JAMFILE = ('import webcpp ;\n'
                  '\n'
                  'webcpp.targets native wasip2 wasip3 emscripten ;\n'
                  '\n'
                  'webcpp.run reads_suite : reads_suite.cpp\n'
                  '  : <library>/webcpp/third_party//json-schema-test-suite ;\n')

READER_SOURCE = r'''#include <fstream>
#include <iostream>
#include <iterator>
#include <string>

int main() {
    std::ifstream file(WEBCPP_TEST_JSON_SCHEMA_TEST_SUITE "/tests/draft2020-12/type.json");
    std::string const text((std::istreambuf_iterator<char>(file)),
                           std::istreambuf_iterator<char>());
    if (text.empty() || text.front() != '[') {
        std::cout << "cannot read " WEBCPP_TEST_JSON_SCHEMA_TEST_SUITE "\n";
        return 1;
    }
    std::cout << "read the suite\n" << WEBCPP_TEST_JSON_SCHEMA_TEST_SUITE << "\n";
    return 0;
}
'''


def passed(result: subprocess.CompletedProcess) -> set[str]:
    """The tests b2 reports as passed, by name: reads_suite for .../reads_suite.test."""
    return {path.rsplit('/', 1)[-1].removesuffix('.test') for path in PASSED.findall(result.stdout)}


def output_of(root: Path, name: str) -> str:
    """The text of the one file named name that b2 wrote under the scratch superproject's bin/."""
    found = sorted((root / 'bin').rglob(name))
    assert len(found) == 1, (name, found)
    return found[0].read_text()


def add_reader(root: Path) -> None:
    """Adds the library suite_reader, whose one test reads a file of the suite, then prints the
    directory the define names."""
    harness.add_library(root, 'suite_reader', READER_JAMFILE, {'reads_suite.cpp': READER_SOURCE})


def expect_read(root: Path) -> None:
    """Asserts that reads_suite read the suite at the directory its define names: the scratch
    superproject's, absolute, with forward slashes and no trailing slash, as b2 sees the root
    (macOS's $TMPDIR is reached through a link, /var being /private/var)."""
    lines = output_of(root, 'reads_suite.output').splitlines()
    assert lines[:2] == ['read the suite', (root.resolve() / SUITE).as_posix()], lines


def test_the_suite_is_pinned(_: Path) -> None:
    listed = subprocess.run(['git', '-C', str(harness.ROOT), 'ls-files', '-s', SUITE],
                            capture_output=True, text=True, check=True)
    assert listed.stdout.split()[:2] == ['160000', SUITE_COMMIT], listed.stdout


def test_wycheproof_is_pinned(_: Path) -> None:
    listed = subprocess.run(['git', '-C', str(harness.ROOT), 'ls-files', '-s', WYCHEPROOF],
                            capture_output=True, text=True, check=True)
    assert listed.stdout.split()[:2] == ['160000', WYCHEPROOF_COMMIT], listed.stdout


def test_the_suite_reaches_a_native_test(root: Path) -> None:
    add_reader(root)
    result = harness.run_b2(root, '-a', 'libs/suite_reader/test')
    harness.expect(result, True)
    assert passed(result) == {'reads_suite'}, (passed(result), result.stdout[-4000:])
    expect_read(root)


def test_the_suite_reaches_a_test_on_emscripten(root: Path) -> None:
    harness.link_emsdk(root)
    add_reader(root)
    result = harness.run_b2(root, '-a', *EMSCRIPTEN, 'libs/suite_reader/test')
    harness.expect(result, True)
    assert passed(result) == {'reads_suite'}, (passed(result), result.stdout[-4000:])
    expect_read(root)


def test_the_suite_reaches_a_test_on_wasi(root: Path) -> None:
    add_reader(root)
    for request in (WASIP2, WASIP3):
        result = harness.run_b2(root, '-a', *request, 'libs/suite_reader/test')
        harness.expect(result, True)
        assert passed(result) == {'reads_suite'}, (request, passed(result), result.stdout[-4000:])
        expect_read(root)
        shutil.rmtree(root / 'bin')


def test_a_changed_suite_file_runs_the_test_again(root: Path) -> None:
    # The suite of the case's own: a date set through the link would be the checkout's.
    harness.third_party_of_its_own(root, 'JSON-Schema-Test-Suite')
    add_reader(root)
    harness.expect(harness.run_b2(root, 'libs/suite_reader/test'), True)
    again = harness.run_b2(root, 'libs/suite_reader/test')
    harness.expect(again, True)
    assert passed(again) == set(), again.stdout[-4000:]
    # A file of tests/, then one of remotes/: each runs it again.
    # Each file gets its date back afterwards, and a run then finds the test up to date, so that
    # the next file is the one that runs it again, not a date still in the future.
    for changed in ('tests/draft2020-12/type.json', 'remotes/integer.json'):
        path = root / SUITE / changed
        dates = path.stat()
        later = time.time() + 60
        os.utime(path, (later, later))
        result = harness.run_b2(root, 'libs/suite_reader/test')
        harness.expect(result, True)
        assert passed(result) == {'reads_suite'}, (changed, passed(result), result.stdout[-4000:])
        os.utime(path, ns=(dates.st_atime_ns, dates.st_mtime_ns))
        again = harness.run_b2(root, 'libs/suite_reader/test')
        harness.expect(again, True)
        assert passed(again) == set(), (changed, again.stdout[-4000:])


def test_bearssl_is_pinned(_: Path) -> None:
    listed = subprocess.run(['git', '-C', str(harness.ROOT), 'ls-files', '-s', BEARSSL],
                            capture_output=True, text=True, check=True)
    assert listed.stdout.split()[:2] == ['160000', BEARSSL_COMMIT], listed.stdout


def test_bearssl_is_built_file_by_file(root: Path) -> None:
    harness.copy_integration_libraries(root, 'config', 'crypto')
    result = harness.run_b2(root, '-a', '-d+2', 'third_party//bearssl')
    harness.expect(result, True)
    compiles = [line for line in result.stdout.splitlines()
                if re.search(r'(clang|gcc)\S* .*-x c ', line) and ' -c ' in line]
    # The 294 files of BearSSL's src/ and webcpp::crypto's canary.
    assert len(compiles) == 295, (len(compiles), result.stdout[-4000:])
    required = ['-ffunction-sections', '-fdata-sections', '-DBR_RDRAND=0', '-DBR_USE_URANDOM=0',
                '-DBR_USE_GETENTROPY=1', '-D_DEFAULT_SOURCE']
    if sys.platform == 'darwin':
        required.append('-include sys/random.h')
    for line in compiles:
        for flag in required:
            assert flag in line, (flag, line)
        assert '-std=' not in line, line
    archive = sorted((root / 'bin').rglob('libbearssl.a'))
    assert len(archive) == 1, archive
    symbols = subprocess.run(['nm', str(archive[0])], capture_output=True, text=True, check=True)
    prefix = '_' if sys.platform == 'darwin' else ''
    canary = (f'{prefix}webcpp_crypto_bearssl_7bea48e_getentropy__add_third_party_bearssl'
              '_to_your_link')
    assert canary in symbols.stdout.split(), symbols.stdout[-2000:]


def test_third_party_jamfile_loads_without_noise(root: Path) -> None:
    # b2 prints "Unescaped special character in argument" on stdout for a flag such as /OPT:REF
    # that a Jamfile does not quote, on every load of that Jamfile.
    result = harness.run_b2(root, '-n', 'third_party//json-schema-test-suite')
    harness.expect(result, True)
    assert 'Unescaped special character' not in result.stdout, result.stdout[-4000:]


def test_bearssl_not_checked_out_is_refused(root: Path) -> None:
    harness.copy_integration_libraries(root, 'config', 'crypto')
    harness.third_party_of_its_own(root, 'bearssl', checked_out=False)
    result = harness.run_b2(root, 'third_party//bearssl')
    harness.expect(result, False, 'third_party/libs/bearssl is not checked out',
                   'git submodule update --init third_party/libs/bearssl')
    # A build that needs no BearSSL never looks for it.
    harness.expect(harness.run_b2(root, 'libs/demo/test//pass'), True)


def test_crypto_not_checked_out_is_refused(root: Path) -> None:
    # No libs/crypto in the scratch superproject: the canary is missing.
    result = harness.run_b2(root, 'third_party//bearssl')
    harness.expect(result, False, 'libs/crypto is not checked out',
                   'git submodule update --init libs/crypto')


def test_a_suite_not_checked_out_is_refused(root: Path) -> None:
    harness.third_party_of_its_own(root, 'JSON-Schema-Test-Suite', checked_out=False)
    add_reader(root)
    result = harness.run_b2(root, 'libs/suite_reader/test')
    harness.expect(result, False, 'third_party/libs/JSON-Schema-Test-Suite is not checked out',
                   'git submodule update --init third_party/libs/JSON-Schema-Test-Suite')
    # A build that needs no suite never looks for it.
    harness.expect(harness.run_b2(root, 'libs/demo/test//pass'), True)


CASES = [
    test_the_suite_is_pinned,
    test_wycheproof_is_pinned,
    test_the_suite_reaches_a_native_test,
    test_the_suite_reaches_a_test_on_emscripten,
    test_the_suite_reaches_a_test_on_wasi,
    test_a_changed_suite_file_runs_the_test_again,
    test_a_suite_not_checked_out_is_refused,
    test_bearssl_is_pinned,
    test_bearssl_is_built_file_by_file,
    test_third_party_jamfile_loads_without_noise,
    test_bearssl_not_checked_out_is_refused,
    test_crypto_not_checked_out_is_refused,
]


if __name__ == '__main__':
    sys.exit(harness.run_cases('third_party_test', CASES, sys.argv[1:]))
