#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Check optional Cobalt SSL dependencies and private patches through B2."""
from pathlib import Path
import re
import shutil
import sys

import harness

SOURCE = '''#include <boost/cobalt/io/ssl.hpp>
#include <boost/asio/io_context.hpp>
#include <boost/asio/ssl/host_name_verification.hpp>
int main() {
    boost::asio::io_context context;
    boost::cobalt::io::ssl::context tls(boost::asio::ssl::context::tls_client);
    boost::cobalt::io::ssl::stream stream(tls, context.get_executor());
    auto verified = stream.set_verify_callback(
        boost::asio::ssl::host_name_verification("localhost"));
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
    harness.add_library(root, 'cobalt_ssl', JAM, {'cobalt_ssl.cpp': SOURCE})
    result = harness.run_b2(root, '-n', '-a', '-d+2', 'variant=release',
                            'libs/cobalt_ssl/test')
    harness.expect(result, True)
    archives = set(re.findall(r'"([^"\n]+/config-[^"\n]+/libssl\.a)"', result.stdout))
    assert len(archives) == 1, archives


def test_public_archive_in_a_path_with_spaces(root: Path) -> None:
    harness.add_library(root, 'cobalt_ssl', JAM, {'cobalt_ssl.cpp': SOURCE})
    for target in ('clang', 'clang-wasip3'):
        result = harness.run_b2(root, '-j6', 'variant=release', 'toolset=' + target,
                                'testing.launcher=tools/boost/asio-wasip3/run.sh'
                                if target == 'clang-wasip3' else 'testing.launcher=',
                                'libs/cobalt_ssl/test')
        harness.expect(result, True, '**passed**')


def test_changed_ssl_source_is_refused(root: Path) -> None:
    source = root / 'modified Boost source'
    shutil.copytree(harness.boost_source() / 'libs/cobalt/src', source / 'libs/cobalt/src')
    (source / 'boost').mkdir()
    shutil.copyfile(harness.boost_source() / 'boost/version.hpp', source / 'boost/version.hpp')
    ssl_source = source / 'libs/cobalt/src/io/ssl.cpp'
    ssl_source.write_text(ssl_source.read_text() + '\n// Different upstream input.\n')
    result = harness.run_b2(root, '-j6', f'-sBOOST_SOURCE={source}',
                            '/webcpp//boost_cobalt_io_ssl')
    harness.expect(result, False, 'incompatible Boost header: libs/cobalt/src/io/ssl.cpp')


def test_ssl_is_optional_and_unsupported_targets_are_refused(root: Path) -> None:
    # P2 Cobalt uses Asio's pollable backend and its Config dependency.
    for name in ('config', 'asio'):
        source = harness.ROOT / 'libs' / name
        target = root / 'libs' / name
        shutil.copytree(source / 'include', target / 'include')
        shutil.copyfile(source / 'build.jam', target / 'build.jam')
    harness.third_party_of_its_own(root, 'openssl', checked_out=False)
    harness.expect(harness.run_b2(root, '-n', '/webcpp//boost_cobalt'), True)
    for target in ('clang', 'clang-wasip2', 'clang-wasip3'):
        harness.expect(harness.run_b2(root, 'toolset=' + target,
                                      '/webcpp//boost_cobalt_io_ssl'), False,
                       'OpenSSL sources are missing')
    harness.expect(harness.run_b2(root, 'toolset=emscripten',
                                  '/webcpp//boost_cobalt_io_ssl'), False,
                   'Cobalt SSL requires native, WASIp2 or WASIp3 with source-built OpenSSL.')


CASES = [test_transitive_openssl_is_unique, test_public_archive_in_a_path_with_spaces,
         test_changed_ssl_source_is_refused,
         test_ssl_is_optional_and_unsupported_targets_are_refused]

if __name__ == '__main__':
    sys.exit(harness.run_cases('cobalt_ssl_test', CASES, sys.argv[1:]))
