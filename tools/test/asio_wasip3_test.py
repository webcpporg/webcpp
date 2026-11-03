#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Verify private WASIp3 headers and profile selection in a checkout with spaces.

These build tests need wasi-sdk but do not execute a WASI runtime. The library's
wasi_core and wasi_contract programs provide runtime coverage separately.
"""

from pathlib import Path
import sys

import harness


JAM = '''
use-project /webcpp/asio-wasip3 : ../../../tools/boost/asio-wasip3 ;
webcpp.compile wasi_configuration : wasi_configuration.cpp
  : <toolset>clang-wasip3:<library>/webcpp/asio-wasip3//headers ;
'''
SOURCE = '''#include <boost/asio/io_context.hpp>
#include <boost/asio/steady_timer.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/ip/udp.hpp>
#if defined(__wasip3__) && !defined(_REENTRANT) && defined(BOOST_ASIO_HAS_THREADS)
#error "single profile must disable Asio threads"
#endif
#if defined(__wasip3__) && defined(_REENTRANT) && !defined(BOOST_ASIO_HAS_THREADS)
#error "cooperative profile must enable Asio threads"
#endif
void instantiate() {
    boost::asio::io_context context;
    boost::asio::steady_timer timer(context);
    boost::asio::ip::tcp::socket tcp(context);
    boost::asio::ip::udp::socket udp(context);
}
'''
TARGET = 'libs/demo/test//wasi_configuration'


def fixture(root: Path) -> None:
    directory = root / 'libs/demo/test'
    jam = directory / 'Jamfile'
    jam.write_text(jam.read_text() + JAM)
    (directory / 'wasi_configuration.cpp').write_text(SOURCE)


def test_overlay_is_wasi_only_and_precedes_stock_headers(root: Path) -> None:
    fixture(root)
    result = harness.run_b2(root, '-a', TARGET)
    harness.expect(result, True, '**passed**')
    overlay = root / 'bin/boost-asio-wasip3/include/boost/asio/detail/config.hpp'
    assert not overlay.exists(), result.stdout
    for handling in ('on', 'off'):
        result = harness.run_b2(root, '-a', 'toolset=clang-wasip3', 'threading=single',
                                f'exception-handling={handling}', TARGET)
        harness.expect(result, True, '**passed**')
        assert '__wasip3__' in overlay.read_text()


def test_cooperative_profile_and_missing_exception_runtime(root: Path) -> None:
    fixture(root)
    sdk = root / 'SDK with spaces'
    library = sdk / 'share/wasi-sysroot/experimental-coop-threads/lib/wasm32-wasip3'
    library.mkdir(parents=True)
    (library / 'libc.a').touch()
    config = harness.user_config(root).read_text()
    ignored = root / 'ignored-sdk'
    config += f'\nmodules.poke : WASI_SDK : "{ignored}" ;\n'
    harness.configure(root, config)
    options = ('-a', '-n', 'toolset=clang-wasip3', 'threading=multi', f'-sWASI_SDK={sdk}')
    result = harness.run_b2(root, *options, 'exception-handling=off', TARGET)
    harness.expect(result, True, 'experimental-coop-threads', '-pthread', 'include/c++/v1')
    result = harness.run_b2(root, *options, 'exception-handling=on', TARGET)
    harness.expect(result, False, 'no cooperative WASIp3 C++ exception runtime')
    (library / 'libc.a').unlink()
    result = harness.run_b2(root, *options, 'exception-handling=off', TARGET)
    harness.expect(result, False, 'requires wasi-sdk', 'experimental-coop-threads sysroot')


CASES = [test_overlay_is_wasi_only_and_precedes_stock_headers,
         test_cooperative_profile_and_missing_exception_runtime]

if __name__ == '__main__':
    sys.exit(harness.run_cases('asio_wasip3_test', CASES, sys.argv[1:]))
