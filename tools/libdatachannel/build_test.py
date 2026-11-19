#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Check the native dependency build's persistent symbol boundary through CMake, and the order
in which a build publishes its outputs."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

ARCHIVES = ('libdatachannel.a', 'libjuice.a', 'libusrsctp.a', 'libsrtp2.a')


class BuildTest(unittest.TestCase):
    def test_each_static_library_keeps_its_own_compiler_database(self) -> None:
        with tempfile.TemporaryDirectory(prefix='libdatachannel symbols ') as directory:
            root = Path(directory)
            script = Path(__file__).with_name('msvc.cmake').resolve()
            (root / 'source.c').write_text('int symbol_fixture(void) { return 42; }\n')
            (root / 'CMakeLists.txt').write_text(
                'cmake_minimum_required(VERSION 3.21)\nproject(libdatachannel LANGUAGES C)\n'
                'foreach(library IN ITEMS datachannel juice usrsctp srtp2)\n'
                '  add_library(${library} STATIC source.c)\n'
                '  file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/${library}.txt"\n'
                '    CONTENT "$<TARGET_PROPERTY:${library},COMPILE_PDB_NAME>\\n'
                '$<TARGET_PROPERTY:${library},COMPILE_PDB_OUTPUT_DIRECTORY>\\n")\n'
                'endforeach()\n')
            subprocess.run(['cmake', '-S', str(root), '-B', str(root / 'build'),
                            '-DCMAKE_PROJECT_libdatachannel_INCLUDE=' + str(script),
                            '-DWEBCPP_SYMBOL_DIRECTORY=' + str(root / 'persistent symbols')],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for library in ('datachannel', 'juice', 'usrsctp', 'srtp2'):
                self.assertEqual((root / 'build' / (library + '.txt')).read_text().splitlines(),
                                 ['webcpp-' + library, str(root / 'persistent symbols')])


class PublicationTest(unittest.TestCase):
    """build() over stand-in commands: what a full build publishes, in which order."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix='libdatachannel publication ')
        self.root = Path(self.directory.name)
        self.compiler = self.root / 'compiler/clang++'
        self.compiler.parent.mkdir()
        for name in ('clang++', 'clang'):
            (self.compiler.parent / name).write_text('')
            (self.compiler.parent / name).chmod(0o755)
        self.openssl = self.root / 'openssl'
        (self.openssl / 'include/openssl').mkdir(parents=True)
        for name in ('libssl.a', 'libcrypto.a'):
            (self.openssl / name).write_bytes(name.encode())

    def tearDown(self) -> None:
        self.directory.cleanup()

    def build(self, output: Path, fail: bool = False) -> list[str]:
        """Runs build() for linux, the CMake build raising when fail, and returns the names it
        published by replacing, in order."""
        def stage(source: Path, staged: Path, pin: dict) -> None:
            (staged / 'include/rtc').mkdir(parents=True)
            (staged / 'include/rtc/rtc.hpp').write_text('// rtc\n')

        def command(command: list[str], directory: Path, env: dict, log: Path) -> None:
            log.write_text('completed\n')
            if command[:2] == ['cmake', '--build']:
                if fail:
                    raise RuntimeError('interrupted build')
                (directory / 'build').mkdir(exist_ok=True)
                for name in ARCHIVES:
                    (directory / 'build' / name).write_bytes(name.encode())

        published = []
        replace = Path.replace

        def publish(path: Path, target: Path) -> Path:
            published.append(Path(target).name)
            return replace(path, target)

        args = argparse.Namespace(source=self.root / 'source', output=output,
                                  openssl=self.openssl, platform='linux',
                                  cxx=str(self.compiler), variant='release',
                                  headers_only=False, flags=['--cxx-flags'])
        with patch.object(build, 'check_checkout'), \
                patch.object(build, 'stage_source', side_effect=stage), \
                patch.object(build, 'provider', return_value={'sha256': {}}), \
                patch.object(build, 'run', side_effect=command), \
                patch.object(Path, 'replace', publish):
            build.build(args)
        return published

    def test_an_interrupted_build_leaves_no_outputs_of_an_earlier_one(self) -> None:
        # B2 keeps a configuration's outputs once they exist (tools/webcpp-third-party.jam): an
        # interrupted build must not leave the archives or the record of an earlier one for a
        # later build to take as complete.
        output = self.root / 'interrupted'
        output.mkdir()
        for name in (*ARCHIVES, 'build.json'):
            (output / name).write_text('published by an earlier build\n')
        with self.assertRaisesRegex(RuntimeError, 'interrupted build'):
            self.build(output, fail=True)
        for name in (*ARCHIVES, 'build.json'):
            self.assertFalse((output / name).exists(), name)

    def test_the_build_record_is_published_whole_and_last(self) -> None:
        # The build record is what makes a configuration complete: B2 builds one without it
        # again (tools/webcpp-libdatachannel.jam), so it is the last output published, replaced
        # whole, never written in place.
        output = self.root / 'complete'
        published = self.build(output)
        self.assertEqual(published, [*ARCHIVES, 'build.json'])
        record = json.loads((output / 'build.json').read_text())
        self.assertEqual(sorted(record['sha256']), sorted(ARCHIVES))
        self.assertEqual([path.name for path in output.glob('*.new')], [])


if __name__ == '__main__':
    unittest.main()
