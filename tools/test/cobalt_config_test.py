#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Require specific diagnostics from Cobalt's public configuration contract."""
from pathlib import Path
import sys

import harness

CAPABILITIES = ('SOCKET_BACKEND', 'OPENSSL_BACKEND', 'BROWSER_BRIDGE', 'THREADS',
                'BROWSER_WORKERS', 'LOCAL_SOCKETS', 'SIGNALS', 'SERIAL_PORT',
                'HOST_DNS', 'REVERSE_DNS', 'PIPE_CREATION', 'POSIX_STDIO', 'POLLABLE_STDIO')


def fixture(root: Path, requirements: str = '') -> None:
    harness.copy_integration_libraries(root, 'config', 'asio', 'cobalt')
    harness.add_library(root, 'consumer', f'''import webcpp ;
webcpp.targets native wasip2 wasip3 emscripten ;
webcpp.compile config : config.cpp : <library>/webcpp/cobalt//core {requirements} ;
''', {'config.cpp': '#include <webcpp/cobalt/config.hpp>\n'})


def test_capabilities_cannot_be_overridden(root: Path) -> None:
    fixture(root)
    for capability in CAPABILITIES:
        result = harness.run_b2(root, '-a',
            f'define=WEBCPP_COBALT_HAS_{capability}=1', 'libs/consumer/test')
        harness.expect(result, False, 'webcpp::cobalt: capability macros are derived')


def test_browser_requirements_name_the_missing_feature(root: Path) -> None:
    fixture(root)
    harness.link_emsdk(root)
    for requirement, diagnostic in (
            ('SOCKET_BACKEND', 'webcpp::cobalt: raw TCP/UDP'),
            ('OPENSSL', 'webcpp::cobalt: guest OpenSSL'),
            ('THREADS', 'webcpp::cobalt: threads are disabled'),
            ('LOCAL_SOCKETS', 'webcpp::cobalt: local sockets'),
            ('SIGNALS', 'webcpp::cobalt: process signals'),
            ('SERIAL_PORT', 'webcpp::cobalt: serial ports'),
            ('REVERSE_DNS', 'webcpp::cobalt: reverse DNS')):
        result = harness.run_b2(root, '-a', 'toolset=emscripten',
            f'define=WEBCPP_COBALT_REQUIRE_{requirement}=1', 'libs/consumer/test')
        harness.expect(result, False, diagnostic)


def test_descriptor_requirements_name_sdk_limits(root: Path) -> None:
    fixture(root)
    harness.link_wasi_tools(root)
    for toolset, requirement, diagnostic in (
            ('clang-wasip2', 'PIPE_CREATION', 'wasi-libc does not create pipes on WASIp2'),
            ('clang-wasip2', 'POSIX_STDIO', 'stdio descriptors have no nonblocking mode'),
            ('clang-wasip3', 'POSIX_STDIO', 'stdio descriptors have no nonblocking mode'),
            ('clang-wasip3', 'POLLABLE_STDIO', 'pollable stdio adapter requires WASIp2')):
        result = harness.run_b2(root, '-a', f'toolset={toolset}',
            f'define=WEBCPP_COBALT_REQUIRE_{requirement}=1', 'libs/consumer/test')
        harness.expect(result, False, diagnostic)


def test_optional_ssl_is_explicit(root: Path) -> None:
    fixture(root)
    result = harness.run_b2(root, 'define=WEBCPP_COBALT_REQUIRE_OPENSSL=1',
                            'libs/consumer/test')
    harness.expect(result, False, 'requires /webcpp/cobalt//io_ssl or //cobalt_ssl')


def test_browser_ssl_header_names_its_transport_limit(root: Path) -> None:
    fixture(root)
    harness.link_emsdk(root)
    (root / 'libs/consumer/test/config.cpp').write_text(
        '#include <webcpp/cobalt/io/ssl.hpp>\n')
    result = harness.run_b2(root, 'toolset=emscripten', 'libs/consumer/test')
    harness.expect(result, False, 'webcpp::cobalt: guest SSL requires native/WASI OpenSSL')


def test_browser_socket_headers_name_the_transport_limit(root: Path) -> None:
    fixture(root)
    harness.link_emsdk(root)
    for header in ('io.hpp', 'io/acceptor.hpp', 'io/socket.hpp',
                   'io/stream_socket.hpp', 'io/datagram_socket.hpp'):
        (root / 'libs/consumer/test/config.cpp').write_text(
            '#include <webcpp/cobalt/' + header + '>\n')
        result = harness.run_b2(root, '-a', 'toolset=emscripten', 'libs/consumer/test')
        harness.expect(result, False, 'webcpp::cobalt: raw TCP/UDP requires native/WASI')


def test_unsupported_wasi_profiles_are_named(root: Path) -> None:
    fixture(root)
    harness.link_wasi_tools(root)
    for toolset, diagnostic in (
            ('clang-wasip2', 'WASIp2 supports threading=single only'),
            ('clang-wasip3', 'no cooperative WASIp3 C++ exception runtime')):
        result = harness.run_b2(root, '-n', f'toolset={toolset}', 'threading=multi',
                               'exception-handling=on', 'libs/consumer/test')
        harness.expect(result, False, diagnostic)


CASES = [test_capabilities_cannot_be_overridden,
         test_browser_requirements_name_the_missing_feature,
         test_descriptor_requirements_name_sdk_limits, test_optional_ssl_is_explicit,
         test_unsupported_wasi_profiles_are_named,
         test_browser_ssl_header_names_its_transport_limit,
         test_browser_socket_headers_name_the_transport_limit]

if __name__ == '__main__':
    sys.exit(harness.run_cases('cobalt_config_test', CASES, sys.argv[1:]))
