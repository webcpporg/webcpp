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
import shutil
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

HOST_SOURCE = '''#include <boost/asio/associated_executor.hpp>
#include <boost/asio/associated_allocator.hpp>
#include <boost/asio/associated_cancellation_slot.hpp>
#include <boost/asio/async_result.hpp>
#include <boost/asio/bind_allocator.hpp>
#include <boost/asio/execution.hpp>
void host_traits() {}
'''


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


def test_wasip2_host_traits_without_socket_reactor(root: Path) -> None:
    fixture(root)
    directory = root / 'libs/demo/test'
    jam = directory / 'Jamfile'
    jam.write_text(jam.read_text() + '''
webcpp.compile host_traits : host_traits.cpp
  : <toolset>clang-wasip2:<library>/webcpp/asio-wasip3//host-headers ;
''')
    (directory / 'host_traits.cpp').write_text(HOST_SOURCE)
    for toolset in ('clang', 'clang-wasip2'):
        for handling in ('on', 'off'):
            result = harness.run_b2(root, '-a', f'toolset={toolset}',
                                    f'exception-handling={handling}',
                                    'libs/demo/test//host_traits')
            harness.expect(result, True, '**passed**')


def test_wasip2_consumer_and_unsupported_profiles(root: Path) -> None:
    # Use the public B2 alias in a clean path with spaces, including its ABI guard.
    for name in ('config', 'asio'):
        source = harness.ROOT / 'libs' / name
        target = root / 'libs' / name
        shutil.copytree(source / 'include', target / 'include')
        shutil.copyfile(source / 'build.jam', target / 'build.jam')
    harness.link_wasi_tools(root)
    harness.add_library(root, 'p2_user', '''import webcpp ;
webcpp.targets wasip2 ;
webcpp.run consumer : consumer.cpp : <library>/webcpp/asio//asio ;
''', {'consumer.cpp': '''#include <webcpp/asio/io_context.hpp>
#include <webcpp/asio/steady_timer.hpp>
int main() {
    webcpp::asio::io_context context;
    webcpp::asio::steady_timer timer(context, std::chrono::milliseconds(0));
    bool completed = false;
    timer.async_wait([&](boost::system::error_code error) { completed = !error; });
    context.run(); // lint-run: validate the public WASIp2 timer target
    return completed ? 0 : 1;
}
'''})
    options = ('toolset=clang-wasip2',
               'testing.launcher=tools/boost/asio-wasip2/run.sh', 'libs/p2_user/test')
    for handling in ('on', 'off'):
        harness.expect(harness.run_b2(root, '-a', f'exception-handling={handling}', *options),
                       True, '**passed**')
    harness.expect(harness.run_b2(root, 'threading=multi', *options),
                   False, 'WASIp2 supports threading=single only')
    # TLS/Cobalt now have real P2 runtime consumers in
    # libs/asio/test/wasip2_tls_cobalt. Only unsupported profiles are refused.
    stale = root / 'unknown SDK'
    stale.mkdir()
    (stale / 'VERSION').write_text('34.0\nwasi-libc: unknown\n')
    harness.expect(harness.run_b2(root, f'-sWASI_SDK={stale}', *options),
                   False, 'revalidate the bridge')
    harness.expect(harness.run_b2(root, *options), True)


CASES = [test_overlay_is_wasi_only_and_precedes_stock_headers,
         test_cooperative_profile_and_missing_exception_runtime,
         test_wasip2_host_traits_without_socket_reactor,
         test_wasip2_consumer_and_unsupported_profiles]

if __name__ == '__main__':
    sys.exit(harness.run_cases('asio_wasip3_test', CASES, sys.argv[1:]))
