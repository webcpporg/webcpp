#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Exercise the source-built OpenSSL dependency through real B2 consumers."""
from pathlib import Path
import sys
import io
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import harness

sys.path.insert(0, str(harness.ROOT / 'tools/release'))
import release

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


def test_native_upstream_suite_checks_the_consumed_archives(root: Path) -> None:
    # Disabling the harness, selecting only one recipe, or publishing different
    # archives must fail this consumer-level proof of the opt-in upstream suite.
    harness.add_library(root, 'openssl_user', JAM, {'uses_openssl.cpp': SOURCE})
    for threads in ('single', 'multi'):
        result = harness.run_b2(
            root, '-a', '-j2', 'toolset=clang', 'variant=release', f'threading={threads}',
            'webcpp-openssl-tests=on', 'libs/openssl_user/test', timeout=2400,
            env_extra={'TESTS': 'test_this_does_not_exist', 'HARNESS_JOBS': '999'})
        harness.expect(result, True, 'upstream suite passed', '**passed**')
    records = list((root / 'bin/third_party').rglob('upstream-tests.json'))
    assert len(records) == 2, records
    for path in records:
        proof = json.loads(path.read_text())
        config = json.loads((path.parent / 'build.json').read_text())
        log = (path.parent / 'upstream-tests.log').read_text()
        assert proof['result'] == 'passed', proof
        assert proof['selection'] == 'alltests', proof
        assert 'no-tests' not in config['configure'], config
        assert 'no-apps' not in config['configure'], config
        assert 'All tests successful.' in log, log[-3000:]
        for recipe in (root / 'third_party/libs/openssl/test/recipes').glob('*.t'):
            assert recipe.name in log, recipe.name
        assert proof['sha256'] == config['sha256'], proof
        for name, digest in proof['sha256'].items():
            assert hashlib.sha256((path.parent / name).read_bytes()).hexdigest() == digest
        print(f'OpenSSL upstream {config["threading"]}: {proof["files"]} files, '
              f'{proof["tests"]} tests, consumed archive hashes verified', flush=True)
    result = harness.run_b2(root, '-j2', 'toolset=clang', 'variant=release', 'threading=multi',
                            'webcpp-openssl-tests=on', 'libs/openssl_user/test')
    harness.expect(result, True)
    assert 'webcpp-openssl.build ' not in result.stdout, result.stdout


def test_upstream_suite_rejects_wasi_by_name(root: Path) -> None:
    for toolset in ('clang-wasip2', 'clang-wasip3'):
        result = harness.run_b2(root, 'third_party//openssl', 'toolset=' + toolset,
                                'webcpp-openssl-tests=on')
        harness.expect(result, False, 'upstream test harness requires native executables')


def test_upstream_failure_prevents_archive_publication(root: Path) -> None:
    # Plant a fault in an executable after the real upstream build. The pinned
    # source remains unchanged, and the real, unfiltered harness must reject it.
    make = shutil.which('make')
    assert make
    wrappers = root / 'tool wrappers'
    wrappers.mkdir()
    wrapper = wrappers / 'make'
    wrapper.write_text('#!/usr/bin/env python3\n'
                       'import os, pathlib, subprocess, sys\n'
                       f'make = {make!r}\n'
                       'if "test" in sys.argv[1:]:\n'
                       '    subprocess.run([make, "-j2", "build_tests"], check=True)\n'
                       '    executable = pathlib.Path("test/evp_test")\n'
                       '    assert executable.is_file()\n'
                       '    executable.write_text("#!/bin/sh\\n"'
                       '"echo planted EVP executable failure >&2\\nexit 1\\n")\n'
                       '    print("planted EVP executable failure", flush=True)\n'
                       'os.execv(make, [make, *sys.argv[1:]])\n')
    wrapper.chmod(0o755)
    result = harness.run_b2(
        root, '-a', '-j2', 'third_party//openssl', 'toolset=clang', 'variant=release',
        'threading=single', 'webcpp-openssl-tests=on', timeout=2400,
        env_extra={'PATH': str(wrappers) + os.pathsep + os.environ['PATH']})
    harness.expect(result, False, 'command failed')
    logs = list((root / 'bin/third_party').rglob('upstream-tests.log'))
    assert len(logs) == 1, result.stdout
    log = logs[0].read_text()
    assert 'planted EVP executable failure' in log, log[-4000:]
    assert 'Result: FAIL' in log, log[-4000:]
    for name in ('libssl.a', 'libcrypto.a', 'build.json', 'upstream-tests.json'):
        assert not (logs[0].parent / name).exists(), name


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


def test_wasip2_source_dependency(root: Path) -> None:
    jam = JAM.replace('import webcpp ;', 'import webcpp ;\nwebcpp.targets wasip2 ;')
    harness.add_library(root, 'openssl_user', jam, {'uses_openssl.cpp': SOURCE})
    for exceptions in ('on', 'off'):
        result = harness.run_b2(root, 'toolset=clang-wasip2', 'variant=release',
                                'threading=single', f'exception-handling={exceptions}',
                                'testing.launcher=wasmtime run -W timeout=15s',
                                'libs/openssl_user/test', timeout=600)
        harness.expect(result, True, '**passed**')
    for path in (root / 'bin/third_party').rglob('build.json'):
        configuration = json.loads(path.read_text())
        assert 'webcpp-wasip2' in configuration['configure'], configuration
        assert 'no-threads' in configuration['configure'], configuration
        assert '--target=wasm32-wasip2' in configuration['flags'], configuration
    result = harness.run_b2(root, 'third_party//openssl', 'toolset=clang-wasip2',
                            'threading=multi')
    harness.expect(result, False, 'WASIp2', 'threading=single')


def test_symlinked_compiler_without_c_sibling(root: Path) -> None:
    compiler = shutil.which('clang++')
    assert compiler
    alias = root / 'toolchain/bin/clang++'
    alias.parent.mkdir(parents=True)
    alias.symlink_to(compiler)
    config = harness.user_config(root).read_text()
    harness.configure(root, config + f'\nusing clang : alias : "{alias.as_posix()}" ;\n')
    harness.add_library(root, 'openssl_user', JAM, {'uses_openssl.cpp': SOURCE})
    result = harness.run_b2(root, '-a', 'toolset=clang-alias', 'variant=release',
                            'threading=single', 'libs/openssl_user/test')
    harness.expect(result, True, '**passed**')


def test_msvc_build_commands_preserve_the_consumers_configuration(root: Path) -> None:
    # Dry-run the real B2 toolset on any host. The Windows lanes run these
    # commands with MSVC; this checks the adapter's configuration boundary.
    compiler = root / 'Visual Studio/bin/cl.exe'
    compiler.parent.mkdir(parents=True)
    compiler.write_text('')
    setup = compiler.parent / 'vcvarsall.bat'
    setup.write_text('')
    harness.configure(root, f'using msvc : 14.3 : "{compiler.as_posix()}"\n'
                      f'  : <setup>"{setup.as_posix()}" <rewrite-setup-scripts>off ;\n')
    (root / 'Jamroot').write_text(
        'import webcpp-openssl ;\n'
        'project : build-dir bin ;\n'
        f'webcpp-openssl.declare "{root.as_posix()}" : ssl.h configuration.h\n'
        '  : tools/openssl/build.py ;\n'
        'exe consumer : uses_openssl.cpp openssl ;\n')
    (root / 'uses_openssl.cpp').write_text(SOURCE)
    for variant, runtime, flag in (('debug', 'shared', '/MDd'), ('debug', 'static', '/MTd'),
                                   ('release', 'shared', '/MD'), ('release', 'static', '/MT')):
        result = harness.run_b2(
            root, '-n', '-a', 'consumer', 'toolset=msvc-14.3', 'target-os=windows',
            'architecture=x86', 'address-model=64', 'threading=multi', f'variant={variant}',
            f'runtime-link={runtime}', 'cflags=/DWEBCPP_TEST_OPENSSL_CONFIGURATION=17',
            env_extra={'BOOST_BUILD_PATH': str(root / 'tools')})
        harness.expect(result, True, 'webcpp-openssl.build', 'libssl.lib', 'libcrypto.lib',
                       flag, '--platform "windows"', 'vcvarsall.bat',
                       '--cc "cl"', '/DWEBCPP_TEST_OPENSSL_CONFIGURATION=17',
                       'ws2_32.lib', 'crypt32.lib', '/OPT:REF')
        assert 'libssl.a' not in result.stdout, result.stdout
        command = next(line for line in result.stdout.splitlines() if ' python3 "' in line)
        assert command.count('vcvarsall.bat') == 1, command
    # Windows normally asks MSVC to generate a reusable setup script. Exercise
    # that path too, even though B2 uses direct setup calls on Unix hosts.
    harness.configure(root, 'import modules ;\nimport os ;\n'
                      'local host = [ os.name ] ;\nmodules.poke os : .name : NT ;\n'
                      f'using msvc : 14.3 : "{compiler.as_posix()}"\n'
                      f'  : <setup>"{setup.as_posix()}" ;\n'
                      'modules.poke os : .name : $(host) ;\n')
    result = harness.run_b2(
        root, '-n', '-a', '-d2', '-d+6', 'consumer', 'toolset=msvc-14.3', 'target-os=windows',
        'architecture=x86', 'address-model=64', 'debug-store=database',
        env_extra={'BOOST_BUILD_PATH': str(root / 'tools')})
    harness.expect(result, True, 'msvc-setup.bat', '--cc "cl"', '/Zi', 'ossl_static.pdb')


def test_msvc_tls_lanes_keep_distinct_openssl_thread_profiles(root: Path) -> None:
    # Use the actual lane declarations and provider with B2's MSVC toolset.
    # Its shared CRT forces threading=multi even for a target named single.
    harness.add_library(root, 'asio',
                        'import webcpp ;\nwebcpp.targets native wasip3 ;\n', {})
    original = harness.ROOT / 'libs/asio'
    shutil.copyfile(original / 'build.jam', root / 'libs/asio/build.jam')
    for name in ('include', 'src', 'test/tls'):
        shutil.copytree(original / name, root / 'libs/asio' / name)
    config_library = root / 'libs/config'
    config_library.mkdir()
    shutil.copyfile(harness.ROOT / 'libs/config/build.jam', config_library / 'build.jam')
    shutil.copytree(harness.ROOT / 'libs/config/include', config_library / 'include')
    harness.copy_integration_libraries(root, 'cobalt')
    shutil.copytree(harness.ROOT / 'libs/cobalt/test/tls', root / 'libs/cobalt/test/tls')
    for name in ('package.json', 'package-lock.json'):
        shutil.copyfile(harness.ROOT / 'libs/cobalt/test' / name, root / 'libs/cobalt/test' / name)
    config = harness.user_config(root).read_text()
    for version in ('14.3', '14.5'):
        config += f'\nusing msvc : {version} : "{sys.executable}"' \
                  ' : <setup> <rewrite-setup-scripts>off ;\n'
    harness.configure(root, config)
    jamroot = root / 'Jamroot'
    # A foreign dry run cannot execute cmd.exe for Boost configuration checks.
    jamroot.write_text(jamroot.read_text().replace('<conditional>@boost-check',
                                                 '<webcpp-boost-check>off'))
    for version in ('14.3', '14.5'):
        lanes = (
            ('asio', f'openssl-upstream-msvc-{version}', 'release', ['tls_client.cpp']),
            ('asio', 'tls-integration', 'debug',
             ['tls_client.cpp', 'tls_client_embedded.cpp']),
            ('cobalt', 'tls-integration', 'debug',
             ['cobalt_ssl_client.cpp', 'cobalt_ssl_state.cpp', 'cobalt_ssl_cancel.cpp']),
        )
        for library, lane, variant, sources in lanes:
            result = harness.run_b2(
                root, '-a', '-n', '-d+2', f'toolset=msvc-{version}',
                'target-os=windows', 'architecture=x86', 'address-model=64',
                f'libs/{library}/test/tls//{lane}')
            harness.expect(result, True, 'webcpp-openssl.build')
            commands = [line for line in result.stdout.splitlines()
                        if '--source "' in line and '--threading "' in line]
            assert commands, result.stdout[-4000:]
            profiles: dict[str, set[str]] = {}
            stages: dict[str, set[str]] = {}
            for command in commands:
                options = dict(re.findall(r'--(threading|output|variant) "([^"]+)"', command))
                threads = options['threading']
                assert options['variant'] == variant, command
                runtime = '/MT' if threads == 'single' else '/MD'
                if variant == 'debug':
                    runtime += 'd'
                assert re.search(r'(?<!\S)' + runtime + r'(?!\S)', command), command
                headers_only = '--headers-only' in command
                stages.setdefault(threads, set()).add('headers' if headers_only else 'archives')
                if headers_only:
                    # Header preparation must not execute the optional upstream suite.
                    assert '--test' not in command, command
                else:
                    assert ('--test' in command) == lane.startswith('openssl-upstream'), command
                    profiles.setdefault(threads, set()).add(options['output'])
            assert stages == {'single': {'headers', 'archives'},
                              'multi': {'headers', 'archives'}}, (version, lane, stages)
            assert set(profiles) == {'single', 'multi'}, (version, lane, profiles)
            assert profiles['single'].isdisjoint(profiles['multi']), profiles
            lines = [line.replace('\\', '/') for line in result.stdout.splitlines()]
            foreign = ('libs/cobalt/test/tls/cobalt_ssl_' if library == 'asio'
                       else 'tools/openssl/test/tls_client')
            assert not any(' -c ' in line and foreign in line for line in lines), \
                (library, lane, foreign)
            drivers = [line.strip() for line in lines if '/tools/drive/drive.py"' in line]
            for source in sources:
                folder = ('libs/cobalt/test/tls' if source.startswith('cobalt_')
                          else 'tools/openssl/test')
                compiles = [line for line in lines
                            if ' -c ' in line and f'{folder}/{source}"' in line]
                for runtime in ('/MT', '/MD'):
                    if variant == 'debug':
                        runtime += 'd'
                    selected = [line for line in compiles
                                if re.search(r'(?<!\S)' + runtime + r'(?!\S)', line)]
                    expected = 2 if lane == 'tls-integration' else 1
                    assert len(selected) == expected, (source, runtime, compiles)
                    for command in selected:
                        threads = 'single' if runtime.startswith('/MT') else 'multi'
                        assert any(path.replace('\\', '/') + '/include' in command
                                   for path in profiles[threads]), \
                            (source, threads, command)
                        object_file = re.search(r'-Fo"([^"]+)"', command)
                        assert object_file, command
                        object_path = object_file.group(1)
                        links = [line for line in lines
                                 if ' link ' in line and f'"{object_path}"' in line]
                        assert len(links) == 1, (object_path, links)
                        output = re.search(r'/out:"([^"]+)"', links[0], re.IGNORECASE)
                        assert output, links[0]
                        executable = output.group(1)
                        assert any(line.endswith(f'"{executable}"') for line in drivers), drivers
            print(f'MSVC {version} {library}/{lane}: '
                  'distinct S/M providers and fixture links verified')


def test_wasip3_prebuilt_component_keeps_its_main(root: Path) -> None:
    # A provider may return an executable with auxiliary archives. Re-linking
    # only those archives can produce a valid component with a trapping main.
    harness.link_wasi_tools(root)
    harness.add_library(root, 'prebuilt',
                        'import webcpp ;\nwebcpp.targets wasip3 ;\n'
                        'webcpp.original python3 ;\n'
                        'webcpp.drive consumer : ../producer//bundle : : driver.py ;\n'
                        'webcpp.lane components : consumer : wasip3 ;\n',
                        {'driver.py': 'import os, subprocess, sys\n'
                         'subprocess.run([os.environ.get("WASMTIME", "wasmtime"), "run",\n'
                         '    "-S", "p3", "-W", "component-model-async=y",\n'
                         '    "-W", "timeout=10s", sys.argv[-1]], check=True, timeout=20)\n'})
    for name in ('package.json', 'package-lock.json'):
        shutil.copyfile(harness.FIXTURES / 'browser_demo/test/driver' / name,
                        root / 'libs/prebuilt/test' / name)
    producer = root / 'libs/prebuilt/producer'
    producer.mkdir()
    (producer / 'Jamfile').write_text('lib helper : helper.cpp : <link>static ;\n'
                                     'exe program : program.cpp helper ;\n'
                                     'alias bundle : program helper ;\n')
    (producer / 'helper.cpp').write_text('int fixture_value() { return 42; }\n')
    (producer / 'program.cpp').write_text(
        '#include <cstdio>\nint fixture_value();\n'
        'int main() {\n'
        '    if (fixture_value() != 42) return 1;\n'
        '    std::puts("prebuilt WASIp3 main: 42");\n'
        '}\n')
    result = harness.run_b2(root, '-a', '-d+2', 'toolset=clang-wasip3',
                            'exception-handling=on,off',
                            'libs/prebuilt/test//components')
    harness.expect(result, True, '**passed**', 'prebuilt WASIp3 main: 42')
    assert result.stdout.count('prebuilt WASIp3 main: 42') == 2, result.stdout[-4000:]


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
    result = harness.run_b2(root, 'third_party//openssl', 'toolset=emscripten')
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


def archived_source(root: Path) -> Path:
    """Extract the same committed OpenSSL blobs and modes as the source distribution."""
    destination = harness.third_party_of_its_own(root, 'openssl', checked_out=False)
    source = harness.ROOT / 'third_party/libs/openssl'
    files = [entry for entry in release.blobs(source)[0] if not release.hidden(entry[0])]
    data = release.contents(source, [oid for _, _, oid in files])
    members = {path: (0o755 if mode == '100755' else 0o644, data[oid], False)
               for path, mode, oid in files}
    archive = release.tar_bytes('openssl', 0, members)
    with tarfile.open(fileobj=io.BytesIO(archive)) as packed:
        packed.extractall(destination.parent)
    assert not (destination / '.git').exists()
    return destination


def test_source_archive_without_git_and_inside_parent_checkout(root: Path) -> None:
    archived_source(root)
    harness.add_library(root, 'openssl_user', JAM, {'uses_openssl.cpp': SOURCE})
    for parent_checkout in (False, True):
        if parent_checkout:
            subprocess.run(['git', 'init', '--quiet', str(root)], check=True)
        result = harness.run_b2(root, '-a', 'toolset=clang', 'variant=release',
                                'threading=single', 'libs/openssl_user/test')
        if result.returncode:
            print(result.stdout, flush=True)
        harness.expect(result, True, 'webcpp-openssl.build', '**passed**')


def test_source_archive_tampering_fails_before_configuration(root: Path) -> None:
    source = archived_source(root)
    original = source / 'Configure'
    content, mode = original.read_bytes(), original.stat().st_mode
    platform = 'darwin' if sys.platform == 'darwin' else 'linux'
    changes = ('changed', 'missing', 'added', 'mode', 'symlink')
    for change in changes:
        if change == 'changed':
            original.write_bytes(content + b'\n# changed\n')
        elif change == 'missing':
            original.unlink()
        elif change == 'added':
            (source / 'unexpected.pm').write_text('unexpected input\n')
        elif change == 'mode':
            original.chmod(0o644)
        else:
            original.unlink()
            original.symlink_to(harness.ROOT / 'third_party/libs/openssl/Configure')
        result = subprocess.run(
            [sys.executable, str(root / 'tools/openssl/build.py'), '--source', str(source),
             '--output', str(root / 'rejected'), '--platform', platform,
             '--threading', 'single', '--cc', str(root / 'missing-clang++')],
            capture_output=True, text=True, timeout=60)
        assert result.returncode != 0, change
        assert 'source tree differs' in result.stderr, result.stderr
        assert not (root / 'rejected/configure.log').exists(), change
        if original.is_symlink():
            original.unlink()
        original.write_bytes(content)
        original.chmod(mode)
        (source / 'unexpected.pm').unlink(missing_ok=True)


CASES = [test_native_upstream_suite_checks_the_consumed_archives,
         test_upstream_suite_rejects_wasi_by_name,
         test_upstream_failure_prevents_archive_publication,
         test_native_source_dependency, test_wasip2_source_dependency,
         test_symlinked_compiler_without_c_sibling,
         test_msvc_build_commands_preserve_the_consumers_configuration,
         test_msvc_tls_lanes_keep_distinct_openssl_thread_profiles,
         test_wasip3_prebuilt_component_keeps_its_main,
         test_missing_checkout_is_lazy_and_actionable,
         test_unsupported_target_is_rejected, test_pin_mismatch_fails_before_compilation,
         test_source_checkout_with_spaces,
         test_source_archive_without_git_and_inside_parent_checkout,
         test_source_archive_tampering_fails_before_configuration]
if __name__ == '__main__':
    sys.exit(harness.run_cases('openssl_test', CASES, sys.argv[1:]))
