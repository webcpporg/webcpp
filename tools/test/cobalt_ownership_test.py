#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Exercise the public dependency graph from isolated consumer checkouts."""
from pathlib import Path
import sys

import harness


def test_asio_builds_without_cobalt_or_openssl(root: Path) -> None:
    harness.copy_integration_libraries(root, 'config', 'asio')
    harness.third_party_of_its_own(root, 'openssl', checked_out=False)
    assert not (root / 'libs/cobalt').exists()
    harness.add_library(root, 'consumer', '''import webcpp ;
webcpp.targets native ;
webcpp.run timer : timer.cpp : <library>/webcpp/asio//asio ;
''', {'timer.cpp': '''#include <webcpp/asio.hpp>
#include <chrono>
int main() {
    webcpp::asio::io_context context;
    webcpp::asio::steady_timer timer(context, std::chrono::milliseconds(1));
    bool completed = false;
    timer.async_wait([&](boost::system::error_code error) { completed = !error; });
    context.run();
    return completed ? 0 : 1;
}
'''})
    result = harness.run_b2(root, '-j4', '-d+2', 'libs/consumer/test')
    harness.expect(result, True, '**passed**')
    compiled = [line for line in result.stdout.splitlines() if ' -c ' in line]
    assert compiled, result.stdout
    assert all('cobalt' not in line and 'openssl' not in line for line in compiled), compiled
    assert not list((root / 'bin').rglob('libnative-core.a'))
    assert not list((root / 'bin').rglob('libwasm-core.a'))
    assert not list((root / 'bin').rglob('libssl.a'))


def test_only_the_cobalt_library_names_cobalt(root: Path) -> None:
    harness.copy_integration_libraries(root, 'config', 'asio', 'cobalt')
    # One name per target: the old Asio and root names are gone, not forwarded.
    # A program that still names one stops at its Jamfile, naming the target.
    old = ('/webcpp/asio//cobalt', '/webcpp/asio//cobalt_ssl',
           '/webcpp//boost_cobalt', '/webcpp//boost_cobalt_io_ssl')
    for index, target in enumerate((*old, '/webcpp/cobalt//cobalt')):
        harness.add_library(root, f'consumer{index}', f'''import webcpp ;
webcpp.targets native ;
webcpp.run main : main.cpp : <library>{target} ;
''', {'main.cpp': '''#include <webcpp/cobalt.hpp>
webcpp::cobalt::main co_main(int, char**) { co_return 0; }
'''})
        result = harness.run_b2(root, '-n', f'libs/consumer{index}/test')
        if target in old:
            harness.expect(result, False, 'Unable to find file or target named', target)
        else:
            harness.expect(result, True)


def test_core_and_runner_have_one_definition(root: Path) -> None:
    harness.copy_integration_libraries(root, 'config', 'asio', 'cobalt')
    harness.add_library(root, 'consumer', '''import webcpp ;
webcpp.targets native ;
webcpp.run main : main.cpp : <library>/webcpp/cobalt//cobalt
  <library>/webcpp/cobalt//core ;
''', {'main.cpp': '''#include <webcpp/cobalt.hpp>
webcpp::cobalt::main co_main(int, char**) { co_return 0; }
'''})
    result = harness.run_b2(root, '-j4', '-d+2', 'libs/consumer/test')
    harness.expect(result, True, '**passed**')
    assert len(list((root / 'bin').rglob('libnative-core.a'))) == 1
    assert len(list((root / 'bin').rglob('libnative-runner.a'))) == 1
    assert not list((root / 'bin').rglob('libwasm-core.a'))
    compiled = [line for line in result.stdout.splitlines() if ' -c ' in line]
    assert sum('src/native/main.cpp' in line for line in compiled) == 1, compiled
    assert all('boost-cobalt-' not in line for line in compiled), compiled
    assert not list((root / 'bin').rglob('libssl.a'))


def test_native_archive_rejects_mismatched_headers(root: Path) -> None:
    harness.copy_integration_libraries(root, 'config', 'asio', 'cobalt')
    original = harness.boost_include()
    shadow = root / 'different-boost/boost'
    shadow.mkdir(parents=True)
    for entry in (original / 'boost').iterdir():
        if entry.name != 'version.hpp':
            (shadow / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    version = (original / 'boost/version.hpp').read_text()
    (shadow / 'version.hpp').write_text(version.replace('109200', '109300'))
    config = harness.user_config(root)
    harness.configure(root, harness.USING_BOOST.sub(
        f'using boost : 1.93 : <include>"{shadow.parent}" '
        f'<library>"{original.parent / "lib"}" ;', config.read_text()))
    result = harness.run_b2(root, '-j4', 'libs/cobalt/src//native-core')
    harness.expect(result, False, 'webcpp::cobalt requires Boost 1.92.0 headers')


CASES = [test_asio_builds_without_cobalt_or_openssl,
         test_only_the_cobalt_library_names_cobalt,
         test_core_and_runner_have_one_definition,
         test_native_archive_rejects_mismatched_headers]

if __name__ == '__main__':
    sys.exit(harness.run_cases('cobalt_ownership_test', CASES, sys.argv[1:]))
