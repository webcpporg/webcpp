#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Check optional shipped Cobalt SSL dependencies and maintainer provenance."""
from pathlib import Path
import re
import shutil
import subprocess
import sys

import harness

SOURCE = '''#include <webcpp/cobalt/io/ssl.hpp>
#include <webcpp/asio/io_context.hpp>
#include <webcpp/asio/ssl/host_name_verification.hpp>
int main() {
    webcpp::asio::io_context context;
    webcpp::cobalt::io::ssl::context tls(webcpp::asio::ssl::context::tls_client);
    webcpp::cobalt::io::ssl::stream stream(tls, context.get_executor());
    auto verified = stream.set_verify_callback(
        webcpp::asio::ssl::host_name_verification("localhost"));
    return verified && stream.native_ssl_handle() && !stream.secure() ? 0 : 1;
}
'''
JAM = '''import webcpp ;
webcpp.targets native wasip3 ;
webcpp.run cobalt_ssl : cobalt_ssl.cpp
  : <library>/webcpp//boost_cobalt_io_ssl
    <library>/webcpp/third_party//openssl ;
'''


def test_transitive_openssl_is_unique(root: Path) -> None:
    harness.copy_integration_libraries(root, 'config', 'asio', 'cobalt')
    harness.link_wasi_tools(root)
    harness.add_library(root, 'cobalt_ssl', JAM, {'cobalt_ssl.cpp': SOURCE})
    result = harness.run_b2(root, '-n', '-a', '-d+2', 'variant=release',
                            'libs/cobalt_ssl/test')
    harness.expect(result, True)
    archives = set(re.findall(r'"([^"\n]+/config-[^"\n]+/libssl\.a)"', result.stdout))
    assert len(archives) == 1, archives


def test_public_archive_in_a_path_with_spaces(root: Path) -> None:
    harness.copy_integration_libraries(root, 'config', 'asio', 'cobalt')
    harness.link_wasi_tools(root)
    harness.add_library(root, 'cobalt_ssl', JAM, {'cobalt_ssl.cpp': SOURCE})
    for target in ('clang', 'clang-wasip3'):
        result = harness.run_b2(root, '-j6', 'variant=release', 'toolset=' + target,
                                'testing.launcher=tools/boost/asio-wasip3/run.sh'
                                if target == 'clang-wasip3' else 'testing.launcher=',
                                'libs/cobalt_ssl/test')
        harness.expect(result, True, '**passed**')


def test_changed_ssl_maintainer_input_is_refused(root: Path) -> None:
    source = root / 'modified Boost source'
    shutil.copytree(harness.boost_source() / 'libs/cobalt/src', source / 'libs/cobalt/src')
    (source / 'boost').mkdir()
    shutil.copyfile(harness.boost_source() / 'boost/version.hpp', source / 'boost/version.hpp')
    ssl_source = source / 'libs/cobalt/src/io/ssl.cpp'
    ssl_source.write_text(ssl_source.read_text() + '\n// Different upstream input.\n')
    result = subprocess.run(
        [sys.executable, str(harness.ROOT / 'libs/cobalt/upstream/sync.py'),
         '--boost-include', str(harness.boost_include()), '--boost-source', str(source), '--check'],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    harness.expect(result, False,
                   'upstream file differs from pinned Cobalt 1.92: libs/cobalt/src/io/ssl.cpp')


def test_ssl_is_optional_and_unsupported_targets_are_refused(root: Path) -> None:
    harness.copy_integration_libraries(root, 'config', 'asio', 'cobalt')
    harness.link_wasi_tools(root)
    harness.third_party_of_its_own(root, 'openssl', checked_out=False)
    harness.expect(harness.run_b2(root, '-n', '/webcpp//boost_cobalt'), True)
    for target in ('clang', 'clang-wasip2', 'clang-wasip3'):
        harness.expect(harness.run_b2(root, 'toolset=' + target,
                                      '/webcpp//boost_cobalt_io_ssl'), False,
                       'OpenSSL sources are missing')
    harness.expect(harness.run_b2(root, 'toolset=emscripten',
                                  '/webcpp//boost_cobalt_io_ssl'), False,
                   'Cobalt SSL requires native or WASI OpenSSL; '
                   'browser TLS is managed by HTTPS/WSS.')


CASES = [test_transitive_openssl_is_unique, test_public_archive_in_a_path_with_spaces,
         test_changed_ssl_maintainer_input_is_refused,
         test_ssl_is_optional_and_unsupported_targets_are_refused]

if __name__ == '__main__':
    sys.exit(harness.run_cases('cobalt_ssl_test', CASES, sys.argv[1:]))
