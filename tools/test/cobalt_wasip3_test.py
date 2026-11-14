#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Build shipped Cobalt in a path with spaces; verify maintainer input provenance."""
from pathlib import Path
import shutil
import subprocess
import sys

import harness

SOURCE = '''#include <webcpp/cobalt.hpp>
#include <webcpp/cobalt/io.hpp>
#include <webcpp/asio/io_context.hpp>
int main() {
    webcpp::asio::io_context ctx;
    webcpp::cobalt::io::datagram_socket socket(
        {webcpp::cobalt::io::udp_v4, "127.0.0.1", 0}, ctx.get_executor());
    return socket.close().has_error() ? 1 : 0;
}
'''
JAM = '''import webcpp ;
webcpp.targets native wasip3 ;
webcpp.run cobalt : cobalt.cpp : <library>/webcpp/cobalt//core ;
'''


def test_archive_and_consumer_share_shipped_headers(root: Path) -> None:
    harness.copy_integration_libraries(root, 'config', 'asio', 'cobalt')
    harness.link_wasi_tools(root)
    harness.add_library(root, 'cobalt_consumer', JAM, {'cobalt.cpp': SOURCE})
    launcher = 'testing.launcher=tools/boost/asio-wasip3/run.sh'
    for handling in ('on', 'off'):
        result = harness.run_b2(root, '-a', '-j4', '-d+2', 'toolset=clang-wasip3', launcher,
                                f'exception-handling={handling}', 'libs/cobalt_consumer/test')
        harness.expect(result, True, '**passed**')
        assert 'boost-cobalt-' not in result.stdout, result.stdout[-4000:]
        assert 'boost-asio-wasip3/include' not in result.stdout, result.stdout[-4000:]
    # Native selects its upstream identity implementation from the same facade.
    harness.expect(harness.run_b2(root, '-a', '-j4', 'libs/cobalt_consumer/test'),
                   True, '**passed**')


def test_modified_maintainer_input_is_refused(root: Path) -> None:
    source = root / 'modified Boost source'
    shutil.copytree(harness.boost_source() / 'libs/cobalt/src', source / 'libs/cobalt/src')
    (source / 'boost').mkdir()
    shutil.copyfile(harness.boost_source() / 'boost/version.hpp', source / 'boost/version.hpp')
    endpoint = source / 'libs/cobalt/src/io/endpoint.cpp'
    endpoint.write_text(endpoint.read_text() + '\n// Different upstream input.\n')
    result = subprocess.run(
        [sys.executable, str(harness.ROOT / 'libs/cobalt/upstream/sync.py'),
         '--boost-include', str(harness.boost_include()), '--boost-source', str(source), '--check'],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    harness.expect(result, False,
                   'upstream file differs from pinned Cobalt 1.92: libs/cobalt/src/io/endpoint.cpp')


CASES = [test_archive_and_consumer_share_shipped_headers, test_modified_maintainer_input_is_refused]

if __name__ == '__main__':
    sys.exit(harness.run_cases('cobalt_wasip3_test', CASES, sys.argv[1:]))
