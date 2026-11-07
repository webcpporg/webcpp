#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Exercise the B2-free consumer through the standard tools-test entry point."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile

import harness
import portable_network_distribution as distribution


def native_inputs() -> list[str]:
    """Read explicit Boost setup; the consumer itself does not discover dependencies."""
    compiler = shutil.which('clang++')
    if not compiler:
        raise RuntimeError('the native distribution test requires clang++ on PATH')
    return ['--compiler', compiler, '--boost-include', str(harness.boost_include())]


def run_consumer(driver: str, *options: str) -> None:
    command = [sys.executable, str(harness.ROOT / 'tools/test' / driver),
               *native_inputs(), *options]
    result = subprocess.run(command, cwd=harness.ROOT, env=harness.b2_environment(),
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=300)
    assert result.returncode == 0, result.stdout[-12000:]
    if driver == 'portable_network_distribution.py':
        assert 'Dependency audit:' in result.stdout, 'missing actual compiler dependency evidence'
    print(result.stdout[-3000:], end='')


def test_native_identity_and_interoperability(root: Path) -> None:
    run_consumer('native_network_identity.py')


def test_unpacked_native_cmake_consumer(root: Path) -> None:
    run_consumer('portable_network_distribution.py', '--target', 'native',
                 '--build-system', 'cmake')


def test_unpacked_custom_configuration(root: Path) -> None:
    run_consumer('portable_network_distribution.py', '--target', 'native',
                 '--build-system', 'cmake', '--cobalt-executor', 'custom',
                 '--cobalt-pmr', 'custom')


def test_source_archive_roundtrip(root: Path) -> None:
    stage = root / 'unpacked source with spaces'
    stage.mkdir()
    distribution.snapshot(stage)
    archive = stage.parent / 'webcpp-network.tar.gz'
    assert archive.is_file(), 'the consumer must extract an actual source archive'
    with tarfile.open(archive) as packed:
        names = packed.getnames()
        assert 'libs/cobalt/sources.json' in names
        assert 'libs/asio/sources.json' in names
        for library in ('asio', 'cobalt', 'beast'):
            prefix = f'libs/{library}/upstream/'
            for record in ('pin.json', 'generated.json', 'sync.py', 'README.md'):
                assert prefix + record in names, f'missing source provenance: {prefix}{record}'
            original = distribution.ROOT / 'libs' / library / 'upstream'
            for path in original.rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts:
                    archived = stage / prefix / path.relative_to(original)
                    assert archived.read_bytes() == path.read_bytes(), str(archived)
        assert 'libs/asio/src/wasip2/pollable.cpp' in names
        assert 'libs/asio/src/wasip3/waitable.cpp' in names
        assert all(not member.issym() and not member.islnk() for member in packed)
    manifest = json.loads((stage / 'archive-manifest.json').read_text())
    for name, digest in manifest['sha256'].items():
        assert hashlib.sha256((stage / name).read_bytes()).hexdigest() == digest, name
    assert set(manifest['sha256']) == set(names) - {'archive-manifest.json'}
    assert not (stage.parent / 'source staging').exists(), 'remove inputs before extracting'


def test_audit_rejects_hidden_headers_and_mismatched_configuration(root: Path) -> None:
    stage = root / 'unpacked'
    distribution.snapshot(stage)
    compiler = shutil.which('clang++')
    assert compiler
    command = [compiler, '-std=c++20', '-isystem', str(harness.boost_include())]
    for library in ('config', 'asio', 'cobalt', 'beast'):
        command += ['-I', str(stage / 'libs' / library / 'include')]
    compiler_roots = distribution.compiler_search_paths(command, harness.b2_environment())
    source = stage / 'libs/cobalt/src/native/this_thread.cpp'
    depfile = stage / 'control.d'
    invocation = command + ['-MD', '-MF', str(depfile), '-c', str(source),
                            '-o', str(stage / 'control.o')]
    subprocess.run(invocation, env=harness.b2_environment(), check=True, capture_output=True)
    entries = [{'file': str(source), 'arguments': invocation}]
    try:
        distribution.dependency_audit(stage, stage, entries, harness.boost_include(),
                                      {'src/native/this_thread.cpp'},
                                      ['-DBOOST_COBALT_CUSTOM_EXECUTOR=1'], compiler_roots)
    except RuntimeError as error:
        assert 'different configuration' in str(error), str(error)
    else:
        raise AssertionError('the audit accepted a core compiled with the wrong configuration')

    source = stage / 'hidden.cpp'
    source.write_text('#include "' + str(harness.ROOT / 'libs/config/include/webcpp/config.hpp')
                      + '"\n')
    invocation = command + ['-MD', '-MF', str(depfile), '-c', str(source),
                            '-o', str(stage / 'control.o')]
    subprocess.run(invocation, env=harness.b2_environment(), check=True, capture_output=True)
    try:
        distribution.dependency_audit(stage, stage, [{'file': str(source),
                                      'arguments': invocation}], harness.boost_include(), set(), [],
                                      compiler_roots)
    except RuntimeError as error:
        assert 'checkout dependency' in str(error), str(error)
    else:
        raise AssertionError('the audit accepted a header outside the source archive')


def test_conflicting_cobalt_policies_are_rejected_without_b2(root: Path) -> None:
    stage = root / 'unpacked'
    distribution.snapshot(stage)
    compiler = shutil.which('clang++')
    assert compiler
    source = stage / 'conflict.cpp'
    source.write_text('#include <webcpp/cobalt/config.hpp>\n')
    command = [compiler, '-std=c++20', '-fsyntax-only', '-isystem', str(harness.boost_include())]
    for library in ('config', 'asio', 'cobalt'):
        command += ['-I', str(stage / 'libs' / library / 'include')]
    for flags, diagnostic in (
        (['-DBOOST_COBALT_USE_IO_CONTEXT=1', '-DBOOST_COBALT_CUSTOM_EXECUTOR=1'],
         'select either the io_context executor or a custom executor'),
        (['-DBOOST_COBALT_NO_PMR=1', '-DBOOST_COBALT_USE_STD_PMR=1'],
         'select exactly one PMR policy'),
    ):
        result = subprocess.run(command + flags + [str(source)], env=harness.b2_environment(),
                                text=True, capture_output=True)
        assert result.returncode != 0 and diagnostic in result.stderr, result.stderr


def test_mismatched_boost_headers_are_rejected_without_b2(root: Path) -> None:
    stage = root / 'unpacked'
    distribution.snapshot(stage)
    compiler = shutil.which('clang++')
    assert compiler
    shadow = root / 'different Boost/include/boost'
    shadow.mkdir(parents=True)
    source = stage / 'version.cpp'
    source.write_text('#include <webcpp/cobalt/task.hpp>\n')
    command = [compiler, '-std=c++20', '-fsyntax-only', '-I', str(shadow.parent),
               '-isystem', str(harness.boost_include())]
    for library in ('config', 'asio', 'cobalt'):
        command += ['-I', str(stage / 'libs' / library / 'include')]
    version = (harness.boost_include() / 'boost/version.hpp').read_text()
    contract = json.loads((stage / 'libs/cobalt/sources.json').read_text())
    assert 'src/native_version.cpp' in contract['profiles']['native']['core']
    for number in (109100, 109200, 109300):
        (shadow / 'version.hpp').write_text(version.replace('109200', str(number)))
        for unit in (source, stage / 'libs/cobalt/src/native_version.cpp'):
            result = subprocess.run(command + [str(unit)], env=harness.b2_environment(),
                                    text=True, capture_output=True, timeout=30)
            if number == 109200:
                assert result.returncode == 0, result.stderr
            else:
                assert result.returncode != 0, 'mismatched Boost headers were accepted'
                diagnostic = 'webcpp::cobalt requires Boost 1.92.0 headers'
                assert diagnostic in result.stderr, result.stderr


CASES = [test_source_archive_roundtrip, test_native_identity_and_interoperability,
         test_unpacked_native_cmake_consumer, test_unpacked_custom_configuration,
         test_audit_rejects_hidden_headers_and_mismatched_configuration,
         test_conflicting_cobalt_policies_are_rejected_without_b2,
         test_mismatched_boost_headers_are_rejected_without_b2]

if __name__ == '__main__':
    sys.exit(harness.run_cases('portable_network_distribution_test', CASES, sys.argv[1:]))
