#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Build an ordinary Cobalt consumer in a path with spaces; reject stale patches."""
from pathlib import Path
import shutil
import sys

import harness

SOURCE = '''#include <boost/cobalt.hpp>
#include <boost/cobalt/io.hpp>
#include <boost/asio/io_context.hpp>
int main() {
    boost::asio::io_context ctx;
    boost::cobalt::io::datagram_socket socket(
        {boost::cobalt::io::udp_v4, "127.0.0.1", 0}, ctx.get_executor());
    return socket.close().has_error() ? 1 : 0;
}
'''
JAM = '''import webcpp ;
webcpp.targets native wasip3 ;
webcpp.run cobalt : cobalt.cpp : <library>/webcpp//boost_cobalt ;
'''


def test_archive_and_consumer_share_private_headers(root: Path) -> None:
    harness.add_library(root, 'cobalt', JAM, {'cobalt.cpp': SOURCE})
    launcher = 'testing.launcher=tools/boost/asio-wasip3/run.sh'
    for handling in ('on', 'off'):
        result = harness.run_b2(root, '-a', '-j4', 'toolset=clang-wasip3', launcher,
                                f'exception-handling={handling}', 'libs/cobalt/test')
        harness.expect(result, True, '**passed**')
    # The prepared headers must not affect native consumers.
    harness.expect(harness.run_b2(root, '-a', '-j4', 'libs/cobalt/test'), True, '**passed**')


def test_modified_upstream_source_is_refused(root: Path) -> None:
    source = root / 'modified Boost source'
    shutil.copytree(harness.boost_source() / 'libs/cobalt/src', source / 'libs/cobalt/src')
    (source / 'boost').mkdir()
    shutil.copyfile(harness.boost_source() / 'boost/version.hpp', source / 'boost/version.hpp')
    endpoint = source / 'libs/cobalt/src/io/endpoint.cpp'
    endpoint.write_text(endpoint.read_text() + '\n// Different upstream input.\n')
    result = harness.run_b2(root, '-j4', 'toolset=clang-wasip3', f'-sBOOST_SOURCE={source}',
                            '/webcpp//boost_cobalt')
    harness.expect(result, False, 'incompatible Boost header: libs/cobalt/src/io/endpoint.cpp')


CASES = [test_archive_and_consumer_share_private_headers, test_modified_upstream_source_is_refused]

if __name__ == '__main__':
    sys.exit(harness.run_cases('cobalt_wasip3_test', CASES, sys.argv[1:]))
