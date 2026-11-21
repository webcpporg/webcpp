#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Checks tools/botan/configure.py over the real checkout, third_party/libs/botan: each target of
/third_party//botan configures, with the same sources everywhere and the modules of modules.txt
loaded, none that seeds a generator from the system; a complete configuration is never made again,
an interrupted one is; runs that make one configuration at once all succeed; an unknown module is
refused, naming it; the compiler settings of the environment change nothing, and neither does
a git repository around the configuration's directory. Run as
`python3 tools/botan/configure_test.py`."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHECKOUT = ROOT / 'third_party/libs/botan'
MODULES = HERE / 'modules.txt'
SCRIPT = HERE / 'configure.py'

# The targets of tools/webcpp-botan.jam's table: --os, --cc and --cpu.
TARGETS = {'macos-clang-arm64': ('macos', 'clang', 'arm64'),
           'linux-gcc-x86_64': ('linux', 'gcc', 'x86_64'),
           'linux-clang-arm64': ('linux', 'clang', 'arm64'),
           'windows-msvc-x86_64': ('windows', 'msvc', 'x86_64'),
           'emscripten': ('emscripten', 'emcc', 'wasm')}

# What --minimized-build with modules.txt gives at 3.14.1, on every target.
LIB_SOURCES = 208
TEST_SOURCES = 152

REFUSED = ('system_rng', 'auto_rng', 'entropy', 'jitter_rng', 'processor_rng', 'esdm_rng')


def configure(output: Path, target: tuple[str, str, str], modules: Path = MODULES,
              environment: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    system, compiler, cpu = target
    return subprocess.run([sys.executable, str(SCRIPT), '--source', str(CHECKOUT),
                           '--modules', str(modules), '--output', str(output), '--os', system,
                           '--cc', compiler, '--cpu', cpu],
                          capture_output=True, text=True, env=environment)


def listed(result: subprocess.CompletedProcess) -> tuple[list[str], list[str]]:
    """The library's and the test program's sources the helper printed, in its order."""
    lib: list[str] = []
    test: list[str] = []
    for line in result.stdout.splitlines():
        kind, _, path = line.partition(' ')
        {'lib': lib, 'test': test}[kind].append(path)
    return lib, test


def module_names() -> list[str]:
    modules: list[str] = []
    for line in MODULES.read_text().splitlines():
        modules += line.split('#', 1)[0].split()
    return modules


def without_directory(directory: Path, header: str) -> str:
    """The text of directory's build/<header>, with directory's name (and its partial's) as DIR."""
    text = (directory / 'build' / header).read_text()
    return re.sub(re.escape(str(directory)) + r'(\.partial-\w+)?', 'DIR', text)


def times(directory: Path) -> dict[str, int]:
    return {str(path.relative_to(directory)): path.stat().st_mtime_ns
            for path in directory.rglob('*')}


class ConfigureTest(unittest.TestCase):
    """One scratch directory for the whole class, so that each target configures once."""

    scratch: Path
    results: dict[str, subprocess.CompletedProcess]

    @classmethod
    def setUpClass(cls) -> None:
        cls.scratch = Path(tempfile.mkdtemp(prefix='botan configure ')).resolve()
        cls.results = {name: configure(cls.scratch / name, target)
                       for name, target in TARGETS.items()}

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.scratch)

    def test_every_target_configures(self) -> None:
        for name, result in self.results.items():
            self.assertEqual(result.returncode, 0, (name, result.stdout, result.stderr))
            lib, test = listed(result)
            self.assertEqual((len(lib), len(test)), (LIB_SOURCES, TEST_SOURCES), name)
            self.assertEqual(lib, sorted(lib), name)
            self.assertEqual(test, sorted(test), name)
            self.assertTrue(all((CHECKOUT / path).is_file() for path in lib + test), name)
            self.assertTrue((self.scratch / name / 'build/build.h').is_file(), name)

    def test_the_sources_are_the_same_on_every_target(self) -> None:
        lists = {name: listed(result) for name, result in self.results.items()}
        first = lists['macos-clang-arm64']
        for name, sources in lists.items():
            self.assertEqual(sources, first, name)

    def test_the_modules_are_loaded_and_no_system_generator(self) -> None:
        wanted = module_names()
        for name in TARGETS:
            loaded = json.loads((self.scratch / name / 'build/build_config.json')
                                .read_text())['mod_list']
            self.assertEqual([module for module in wanted if module not in loaded], [], name)
            self.assertEqual([module for module in REFUSED if module in loaded], [], name)

    def test_nothing_is_written_into_the_checkout(self) -> None:
        status = subprocess.run(['git', '-C', str(CHECKOUT), 'status', '--porcelain'],
                                capture_output=True, text=True, check=True)
        self.assertEqual(status.stdout, '')

    def test_a_complete_configuration_is_not_made_again(self) -> None:
        output = self.scratch / 'macos-clang-arm64'
        before = times(output)
        again = configure(output, TARGETS['macos-clang-arm64'])
        self.assertEqual(again.returncode, 0, again.stdout)
        self.assertEqual(again.stdout, self.results['macos-clang-arm64'].stdout)
        self.assertEqual(times(output), before)

    def test_an_interrupted_configuration_is_made_again(self) -> None:
        output = self.scratch / 'interrupted'
        # An interrupted run's partial, untouched for two hours, and a running one's, just made.
        stale = self.scratch / 'interrupted.partial-stale'
        running = self.scratch / 'interrupted.partial-running'
        for partial in (stale, running):
            partial.mkdir()
            (partial / 'build.h').write_text('half\n')
        hours_ago = time.time() - 7200
        os.utime(stale, (hours_ago, hours_ago))
        result = configure(output, TARGETS['linux-gcc-x86_64'])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(listed(result), listed(self.results['linux-gcc-x86_64']))
        self.assertFalse(stale.exists())
        self.assertTrue(running.exists())
        self.assertTrue((output / 'webcpp-configure.json').is_file())

    def test_concurrent_runs_of_one_configuration_all_succeed(self) -> None:
        output = self.scratch / 'concurrent'
        system, compiler, cpu = TARGETS['windows-msvc-x86_64']
        command = [sys.executable, str(SCRIPT), '--source', str(CHECKOUT), '--modules',
                   str(MODULES), '--output', str(output), '--os', system, '--cc', compiler,
                   '--cpu', cpu]
        # Three rounds of four runs at once, each round from no configuration.
        for _ in range(3):
            if output.exists():
                shutil.rmtree(output)
            runs = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True) for _ in range(4)]
            outputs = [run.communicate()[0] for run in runs]
            for run, text in zip(runs, outputs):
                self.assertEqual(run.returncode, 0, text)
                self.assertEqual(text, self.results['windows-msvc-x86_64'].stdout)
            self.assertTrue((output / 'webcpp-configure.json').is_file())
            self.assertTrue((output / 'build/build.h').is_file())
            self.assertEqual(sorted(self.scratch.glob('concurrent.partial-*')), [])

    def test_an_unknown_module_is_refused(self) -> None:
        modules = self.scratch / 'unknown.txt'
        modules.write_text('sha2_32 no_such_module  # one Botan does not know\n')
        output = self.scratch / 'unknown'
        result = configure(output, TARGETS['linux-gcc-x86_64'], modules)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('no_such_module', result.stdout)
        self.assertFalse(output.exists())

    def test_the_compiler_settings_of_the_environment_change_nothing(self) -> None:
        output = self.scratch / 'environment'
        environment = dict(os.environ, CXX='false', CXXFLAGS='-DWRONG', AR='false',
                           AR_OPTIONS='x', LDFLAGS='-lwrong')
        result = configure(output, TARGETS['linux-gcc-x86_64'], environment=environment)
        self.assertEqual(result.returncode, 0, result.stdout)
        reference = self.scratch / 'linux-gcc-x86_64'
        self.assertEqual(result.stdout, self.results['linux-gcc-x86_64'].stdout)
        for header in ('build.h', 'target_info.h'):
            # target_info.h names the directory it was configured into, which differs.
            self.assertEqual(without_directory(output, header),
                             without_directory(reference, header), header)

    def test_no_enclosing_repository_reaches_the_configuration(self) -> None:
        # In a build the configuration directory is inside the superproject's checkout, whose
        # commit upstream's configure.py would take as Botan's revision: a configuration made
        # inside a repository, of a commit of its own, is the one made outside any.
        repository = self.scratch / 'repository'
        repository.mkdir()
        git = ['git', '-C', str(repository), '-c', 'user.name=webcpp',
               '-c', 'user.email=webcpp@example.invalid', '-c', 'commit.gpgsign=false']
        subprocess.run(git[:3] + ['init', '-q'], check=True)
        subprocess.run(git + ['commit', '-q', '--allow-empty', '-m', 'enclosing'], check=True)
        output = repository / 'bin' / 'emscripten'
        result = configure(output, TARGETS['emscripten'])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout, self.results['emscripten'].stdout)
        reference = self.scratch / 'emscripten'
        for header in ('version_info.h', 'build.h', 'target_info.h'):
            text = without_directory(output, header)
            self.assertNotIn('git:', text, header)
            self.assertEqual(text, without_directory(reference, header), header)


if __name__ == '__main__':
    unittest.main()
