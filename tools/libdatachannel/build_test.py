#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Check the native dependency build's persistent symbol boundary through CMake."""
from pathlib import Path
import subprocess
import tempfile
import unittest


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


if __name__ == '__main__':
    unittest.main()
