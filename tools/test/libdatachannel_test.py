#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Exercise one static OpenSSL provider through the real native WebRTC build graph."""
from pathlib import Path
import json
import re
import subprocess
import sys

import harness

JAM = '''import webcpp ;
webcpp.run provider : provider.cpp
    : <library>/webcpp/third_party//openssl
      <library>/webcpp/third_party//libdatachannel <threading>multi ;
'''
SOURCE = '''#include <rtc/rtc.hpp>
#include <openssl/ssl.h>
#include <cstdio>
#ifndef OPENSSL_THREADS
#error "WebRTC requires the threaded OpenSSL provider"
#endif
int main() {
    if (OPENSSL_VERSION_NUMBER != OpenSSL_version_num()) return 1;
    auto* tls = SSL_CTX_new(TLS_method());
    if (!tls) return 2;
    rtc::PeerConnection peer(rtc::Configuration{});
    auto channel = peer.createDataChannel("one-provider");
    peer.close();
    SSL_CTX_free(tls);
    std::puts("one pinned OpenSSL provider");
    return channel ? 0 : 3;
}
'''


def test_one_native_provider_in_a_path_with_spaces(root: Path) -> None:
    harness.add_library(root, 'datachannel_user', JAM, {'provider.cpp': SOURCE})
    result = harness.run_b2(root, '-a', '-j4', '-d+2', 'toolset=clang', 'variant=release',
                            'libs/datachannel_user/test')
    harness.expect(result, True, '**passed**')
    # The combined direct/transitive dependency must use one exact archive pair,
    # with users before providers even when OpenSSL was named first by the user.
    link = next(line for line in result.stdout.splitlines()
                if ' -o ' in line and '/libssl.a"' in line)
    for library in ('ssl', 'crypto', 'datachannel', 'juice', 'usrsctp', 'srtp2'):
        assert len(re.findall('/lib' + library + r'\.a"', link)) == 1, link
    assert link.index('/libdatachannel.a') < link.index('/libssl.a'), link
    assert link.index('/libssl.a') < link.index('/libcrypto.a'), link
    binary = next(path for path in (root / 'bin').rglob('provider') if path.is_file())
    command = ['otool', '-L', str(binary)] if sys.platform == 'darwin' else ['ldd', str(binary)]
    dependencies = subprocess.check_output(command, text=True)
    assert not re.search(r'lib(?:ssl|crypto|datachannel)[.-]', dependencies), dependencies
    records = [json.loads(path.read_text())
               for path in (root / 'bin/third_party').rglob('build.json')]
    datachannel = next(record for record in records if record['pin']['version'] == '0.24.6')
    openssl = next(record for record in records if 'openssl_sha256' not in record)
    assert datachannel['openssl_sha256'] == openssl['sha256'], records
    result = harness.run_b2(root, '-j4', 'toolset=clang', 'variant=release',
                            'libs/datachannel_user/test')
    harness.expect(result, True)
    assert 'webcpp-libdatachannel.build ' not in result.stdout, result.stdout
    # A free C++ ABI/compiler option changes the dependency's output directory.
    changed = harness.run_b2(root, '-n', '-a', '-d+2', 'toolset=clang', 'variant=release',
                             'cxxflags=-DWEBCPP_TEST_DATACHANNEL_VARIANT=1',
                             'libs/datachannel_user/test')
    harness.expect(changed, True)
    initial = re.findall(r'config-[a-f0-9]+/libdatachannel\.a', link)
    revised = re.findall(r'config-[a-f0-9]+/libdatachannel\.a', changed.stdout)
    assert revised and set(initial).isdisjoint(revised), (initial, revised)


def test_single_threaded_and_unsupported_consumers_are_refused(root: Path) -> None:
    result = harness.run_b2(root, '-n', 'toolset=clang', 'threading=single',
                            'third_party//libdatachannel')
    harness.expect(result, False, 'native backend uses worker threads', 'threading=multi')
    result = harness.run_b2(root, '-n', 'toolset=clang-wasip3', 'threading=multi',
                            'third_party//libdatachannel')
    harness.expect(result, False, 'requires native Clang/GCC')


def test_missing_source_is_lazy_and_never_uses_an_external_install(root: Path) -> None:
    harness.third_party_of_its_own(root, 'libdatachannel', checked_out=False)
    harness.expect(harness.run_b2(root, '-n', 'declared-targets'), True)
    result = harness.run_b2(root, '-n', 'threading=multi', 'third_party//libdatachannel')
    harness.expect(result, False, 'libdatachannel sources are missing',
                   'git submodule update --init --recursive third_party/libs/libdatachannel')


def provider_header_plan(root: Path, properties: list[str]) -> None:
    """Ask B2 for only RTC headers, retaining the real consumer's provider properties."""
    (root / 'Jamroot').write_text(
        'import webcpp-openssl ;\nimport webcpp-libdatachannel ;\n'
        'import webcpp-lint-headers ;\n'
        'project : build-dir bin ;\n'
        f'webcpp-openssl.declare "{root.as_posix()}" : ssl.h configuration.h\n'
        '  : tools/openssl/build.py ;\n'
        f'webcpp-libdatachannel.declare "{root.as_posix()}" : datachannel.hpp\n'
        '  : tools/libdatachannel/build.py ;\n'
        'exe consumer : provider.cpp libdatachannel openssl ;\n'
        'webcpp-lint-headers.declare-lint-headers ;\n')
    (root / 'provider.cpp').write_text(SOURCE)
    env = {'BOOST_BUILD_PATH': str(root / 'tools')}
    full = harness.run_b2(root, '-n', '-a', '-d+2', '-d+6', 'consumer', *properties,
                          env_extra=env)
    harness.expect(full, True, 'webcpp-openssl.build', 'webcpp-libdatachannel.build')
    if 'webcpp-openssl-tests=on' in properties:
        assert 'upstream-tests.json' in full.stdout, full.stdout[-6000:]
    if 'debug-store=database' in properties:
        assert 'ossl_static.pdb' in full.stdout, full.stdout[-6000:]
    selected = re.findall(r'^webcpp-libdatachannel\.prepare-headers (.+)$', full.stdout,
                          re.MULTILINE)
    assert len(selected) == 1, full.stdout[-6000:]
    request = [*properties, '--webcpp-lint-source=consumer',
               *(f'--webcpp-lint-property={prop}' for prop in properties),
               f'--webcpp-lint-header={selected[0]}', 'lint-provider-headers']
    headers = harness.run_b2(root, '-n', '-a', '-d+2', *request, env_extra=env)
    harness.expect(headers, True, 'webcpp-libdatachannel.prepare-headers',
                   'webcpp-openssl.generate-headers')
    assert not re.search(r'^webcpp-(?:openssl|libdatachannel)\.build ', headers.stdout,
                         re.MULTILINE), headers.stdout[-10000:]
    assert '--test ' not in headers.stdout, headers.stdout[-6000:]
    if 'target-os=windows' not in properties:
        built = harness.run_b2(root, '-d0', *request, env_extra=env)
        harness.expect(built, True)
        assert Path(selected[0]).is_file(), selected
        assert list((root / 'bin').rglob('configuration.h'))
        for artifact in ('*.a', '*.lib', 'build.json', 'upstream-tests.json', '*.run'):
            assert not list((root / 'bin').rglob(artifact)), artifact


def test_headers_only_do_not_build_upstream_proof(root: Path) -> None:
    provider_header_plan(root, ['toolset=clang', 'threading=multi', 'webcpp-openssl-tests=on'])


def test_headers_only_do_not_build_msvc_symbols(root: Path) -> None:
    compiler = root / 'Visual Studio/bin/cl.exe'
    compiler.parent.mkdir(parents=True)
    compiler.write_text('')
    setup = compiler.parent / 'vcvarsall.bat'
    setup.write_text('')
    harness.configure(root, f'using msvc : 14.3 : "{compiler.as_posix()}"\n'
                      f'  : <setup>"{setup.as_posix()}" <rewrite-setup-scripts>off ;\n')
    provider_header_plan(root, ['toolset=msvc-14.3', 'target-os=windows', 'architecture=x86',
                               'address-model=64', 'threading=multi', 'variant=debug',
                               'debug-store=database'])


def test_msvc_runtime_and_custom_cpp_flags_reach_both_dependencies(root: Path) -> None:
    compiler = root / 'Visual Studio/bin/cl.exe'
    compiler.parent.mkdir(parents=True)
    compiler.write_text('')
    setup = compiler.parent / 'vcvarsall.bat'
    setup.write_text('')
    harness.configure(root, f'using msvc : 14.3 : "{compiler.as_posix()}"\n'
                      f'  : <setup>"{setup.as_posix()}" <rewrite-setup-scripts>off ;\n')
    (root / 'Jamroot').write_text(
        'import webcpp-openssl ;\nimport webcpp-libdatachannel ;\n'
        'project : build-dir bin ;\n'
        f'webcpp-openssl.declare "{root.as_posix()}" : ssl.h configuration.h\n'
        '  : tools/openssl/build.py ;\n'
        f'webcpp-libdatachannel.declare "{root.as_posix()}" : rtc.hpp\n'
        '  : tools/libdatachannel/build.py ;\n'
        'exe consumer : provider.cpp libdatachannel openssl ;\n')
    (root / 'provider.cpp').write_text(SOURCE)
    for runtime, flag in (('shared', '/MDd'), ('static', '/MTd')):
        result = harness.run_b2(
            root, '-n', '-a', '-d+2', '-d+6', 'consumer', 'toolset=msvc-14.3', 'target-os=windows',
            'architecture=x86', 'address-model=64', 'threading=multi', 'variant=debug',
            'runtime-link=' + runtime, 'debug-store=database', 'cxxflags=/DWEBCPP_TEST_ABI=17',
            env_extra={'BOOST_BUILD_PATH': str(root / 'tools')})
        harness.expect(result, True, 'datachannel.lib', 'libssl.lib', '--cxx "cl"',
                       '/DWEBCPP_TEST_ABI=17', flag, 'RTC_STATIC', 'iphlpapi.lib',
                       'webcpp-datachannel.pdb', 'webcpp-juice.pdb',
                       'webcpp-usrsctp.pdb', 'webcpp-srtp2.pdb')
        command = next(line for line in result.stdout.splitlines() if '--cxx "cl"' in line)
        assert '/DWEBCPP_TEST_ABI=17' in command, command
        assert flag in command, command
        c_flags, cpp_flags = command.split('--cxx-flags', 1)
        assert '/DWEBCPP_TEST_ABI=17' not in c_flags, command
        assert '/DWEBCPP_TEST_ABI=17' in cpp_flags, command


CASES = [test_one_native_provider_in_a_path_with_spaces,
         test_headers_only_do_not_build_upstream_proof,
         test_headers_only_do_not_build_msvc_symbols,
         test_msvc_runtime_and_custom_cpp_flags_reach_both_dependencies,
         test_single_threaded_and_unsupported_consumers_are_refused,
         test_missing_source_is_lazy_and_never_uses_an_external_install]

if __name__ == '__main__':
    sys.exit(harness.run_cases('libdatachannel_test', CASES, sys.argv[1:]))
