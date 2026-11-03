#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Exercise the source-built OpenSSL dependency through real B2 consumers."""
from pathlib import Path
import sys
import json
import subprocess
import harness

JAM = '''import webcpp ;
webcpp.run uses_openssl : uses_openssl.cpp
  : <library>/webcpp/third_party//openssl
    <threading>multi:<define>EXPECT_THREADS ;
'''
SOURCE = '''#include <openssl/ssl.h>
#include <openssl/rand.h>
#include <cstdio>
#if defined(EXPECT_THREADS) != defined(OPENSSL_THREADS)
#error "OpenSSL threading does not match the consumer"
#endif
int main() {
    unsigned char bytes[32];
    if (RAND_priv_bytes(bytes, sizeof(bytes)) != 1) return 1;
    SSL_CTX* context = SSL_CTX_new(TLS_method());
    if (!context) return 2;
    SSL_CTX_free(context);
    std::puts("source-built OpenSSL: random and TLS ready");
}
'''


def test_native_source_dependency(root: Path) -> None:
    harness.add_library(root, 'openssl_user', JAM, {'uses_openssl.cpp': SOURCE})
    for threads in ('single', 'multi'):
        result = harness.run_b2(root, '-a', 'toolset=clang', 'variant=release',
                                f'threading={threads}', 'libs/openssl_user/test')
        harness.expect(result, True, '**passed**')
    # A second identical invocation must reuse the archives and their headers.
    result = harness.run_b2(root, 'toolset=clang', 'variant=release',
                            'threading=multi', 'libs/openssl_user/test')
    harness.expect(result, True)
    assert 'webcpp-openssl.build ' not in result.stdout, result.stdout
    # Free C flags must produce a separate artifact configuration.
    result = harness.run_b2(root, 'toolset=clang', 'variant=release', 'threading=single',
                            'cflags=-DWEBCPP_TEST_OPENSSL_CONFIGURATION=17',
                            'third_party//openssl')
    harness.expect(result, True, 'webcpp-openssl.build')
    records = [json.loads(path.read_text())
               for path in (root / 'bin/third_party').rglob('build.json')]
    assert len(records) == 3, records
    custom = [record for record in records
              if '-DWEBCPP_TEST_OPENSSL_CONFIGURATION=17' in record['flags']]
    assert len(custom) == 1, records
    # All installed headers, not just configuration.h, are generated outputs.
    for header in (root / 'bin/third_party').rglob('include/openssl/ssl.h'):
        header.unlink()
    result = harness.run_b2(root, 'toolset=clang', 'variant=release',
                            'threading=single', 'libs/openssl_user/test')
    harness.expect(result, True, 'webcpp-openssl.build', '**passed**')


def test_pin_mismatch_fails_before_compilation(root: Path) -> None:
    pin = root / 'tools/openssl/pin.json'
    data = json.loads(pin.read_text())
    data['commit'] = '0' * 40
    pin.write_text(json.dumps(data))
    result = harness.run_b2(root, 'third_party//openssl', 'toolset=clang')
    harness.expect(result, False, 'checkout differs from tools/openssl/pin.json')


def test_missing_checkout_is_lazy_and_actionable(root: Path) -> None:
    harness.third_party_of_its_own(root, 'openssl', checked_out=False)
    result = harness.run_b2(root, 'declared-targets')
    harness.expect(result, True)
    result = harness.run_b2(root, 'third_party//openssl')
    harness.expect(result, False, 'git submodule update --init third_party/libs/openssl')


def test_unsupported_target_is_rejected(root: Path) -> None:
    for toolset in ('clang-wasip2', 'emscripten'):
        result = harness.run_b2(root, 'third_party//openssl', 'toolset=' + toolset)
        harness.expect(result, False, 'not supported by this recipe')


def test_source_checkout_with_spaces(root: Path) -> None:
    # A symlink to the real source does not test a source path containing spaces:
    # OpenSSL Configure resolves that link before emitting its Makefiles.
    destination = harness.third_party_of_its_own(root, 'openssl', checked_out=False)
    destination.rmdir()
    subprocess.run(['git', '-c', 'advice.detachedHead=false', 'clone', '--shared', '--quiet',
                    str(harness.ROOT / 'third_party/libs/openssl'), str(destination)],
                   check=True, timeout=60)
    harness.add_library(root, 'openssl_user', JAM, {'uses_openssl.cpp': SOURCE})
    result = harness.run_b2(root, 'toolset=clang', 'variant=release',
                            'threading=single', 'libs/openssl_user/test')
    if result.returncode:
        print(result.stdout, flush=True)
    harness.expect(result, True, '**passed**')


CASES = [test_native_source_dependency, test_missing_checkout_is_lazy_and_actionable,
         test_unsupported_target_is_rejected, test_pin_mismatch_fails_before_compilation,
         test_source_checkout_with_spaces]
if __name__ == '__main__':
    sys.exit(harness.run_cases('openssl_test', CASES, sys.argv[1:]))
