#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Check build orchestration at the unavailable native Windows tool boundary."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import build
from source import inventory_digest


class WindowsBuildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix='openssl windows ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        data = b'# source fixture\n'
        (self.source / 'Configure').write_bytes(data)
        (self.source / 'ms').mkdir()
        (self.source / 'ms/applink.c').write_bytes(data)
        (self.root / 'msvc.conf').write_text('# configuration fixture\n')
        self.pin = {'version': 'fixture', 'source_date_epoch': 1700000000,
                    'omitted_submodules': {}, 'executable_files': [],
                    'source_sha256': inventory_digest([
                        (name, '100644', hashlib.sha256(data).hexdigest())
                        for name in ('Configure', 'ms/applink.c')])}
        (self.root / 'pin.json').write_text(json.dumps(self.pin))
        self.compiler = self.root / 'Visual Studio/cl.exe'
        self.compiler.parent.mkdir()
        self.compiler.write_bytes(b'compiler boundary fixture\n')
        self.compiler.chmod(0o755)

    def test_windows_build_installs_static_libraries_and_matching_headers(self) -> None:
        for arch, target in (('x86', 'VC-WIN32'), ('x64', 'VC-WIN64A'),
                             ('arm64', 'VC-WIN64-ARM')):
            with self.subTest(arch=arch):
                commands = []
                environments = []
                timeouts = []
                output = self.root / arch

                def command(command: list[str], *, cwd: Path, env: dict, log: Path,
                            timeout: float = 600) -> None:
                    commands.append(command)
                    environments.append(env)
                    timeouts.append(timeout)
                    log.write_text('completed\n')
                    if command[-1] == 'build_libs':
                        (cwd / 'include/openssl').mkdir(parents=True)
                        (cwd / 'include/openssl/configuration.h').write_text(arch)
                        (cwd / 'libssl.lib').write_bytes(b'ssl-' + arch.encode())
                        (cwd / 'libcrypto.lib').write_bytes(b'crypto-' + arch.encode())

                args = ['build.py', '--source', str(self.source), '--output', str(output),
                        '--platform', 'windows', '--threading', 'multi', '--cc', str(self.compiler),
                        '--ar', 'link', '--variant', 'debug', '--', '/MDd', '/Od', '/Z7', '/GL']
                with patch.object(build, 'HERE', self.root), patch.object(sys, 'argv', args), \
                        patch.object(build, 'run', side_effect=command), \
                        patch.object(build, 'windows_target', return_value=target), \
                        patch.object(build, 'windows_perl', return_value='native-perl.exe'):
                    build.main()
                self.assertEqual(commands[0][0], 'native-perl.exe')
                self.assertIn(target + '-webcpp', commands[0])
                self.assertNotIn('--debug', commands[0])
                self.assertIn('no-shared', commands[0])
                self.assertIn('no-asm', commands[0])
                self.assertEqual(commands[1], ['nmake', '/nologo', 'build_libs'])
                self.assertEqual(len(commands), 2)
                self.assertEqual(timeouts, [600, 1800])
                self.assertEqual((output / 'libssl.lib').read_bytes(), b'ssl-' + arch.encode())
                self.assertEqual((output / 'include/openssl/configuration.h').read_text(), arch)
                self.assertEqual((output / 'include/openssl/applink.c').read_bytes(),
                                 b'# source fixture\n')
                self.assertFalse((output / 'ossl_static.pdb').exists())
                record = json.loads((output / 'build.json').read_text())
                self.assertEqual(set(record['sha256']), {'libssl.lib', 'libcrypto.lib'})
                self.assertEqual(record['flags'], ['/MDd', '/Od', '/Z7', '/GL', '/Gy', '/Gw'])
                self.assertEqual(environments[0]['CFLAGS'], '/MDd /Od /Z7 /GL /Gy /Gw')
                self.assertEqual(environments[0]['CC'], str(self.compiler.absolute()))
                self.assertEqual(environments[0]['AR'], 'link')
                self.assertEqual(environments[0]['ARFLAGS'], '/lib /nologo')
                self.assertNotIn('CL', environments[0])
                self.assertNotIn('_CL_', environments[0])

    def test_a_stalled_command_keeps_its_diagnostic_log(self) -> None:
        log = self.root / 'stalled.log'
        with self.assertRaisesRegex(RuntimeError, r'command timed out after 2s; full log:'):
            build.run([sys.executable, '-u', '-c',
                       'import time; print("last compiler output"); time.sleep(10)'],
                      cwd=self.root, env=os.environ.copy(), log=log, timeout=2)
        self.assertEqual(log.read_text(), 'last compiler output\n')

    def test_windows_target_uses_the_configured_compilers_architecture(self) -> None:
        for output, target in (('WEBCPP_OPENSSL_X86', 'VC-WIN32'),
                               ('WEBCPP_OPENSSL_X64', 'VC-WIN64A'),
                               ('WEBCPP_OPENSSL_ARM64', 'VC-WIN64-ARM')):
            with patch.object(build.subprocess, 'check_output', return_value=output) as compiler:
                self.assertEqual(build.windows_target(Path('cl.exe'), ['/MDd'], self.root,
                                                      os.environ.copy()), target)
            command = compiler.call_args.args[0]
            self.assertEqual(command[:4], ['cl.exe', '/MDd', '/nologo', '/EP'])
            self.assertTrue(Path(command[-1]).is_file())
        with patch.object(build.subprocess, 'check_output', return_value='not MSVC'):
            with self.assertRaisesRegex(RuntimeError, 'MSVC target'):
                build.windows_target(Path('cl.exe'), [], self.root, os.environ.copy())

    def test_native_perl_is_selected_after_git_bash_perl(self) -> None:
        env = {'PATH': os.pathsep.join(('git-bash', 'strawberry'))}
        with patch.object(build.shutil, 'which', side_effect=['git-perl', 'native-perl']), \
                patch.object(build.subprocess, 'check_output',
                             side_effect=['msys', 'MSWin32']):
            self.assertEqual(build.windows_perl(env), 'native-perl')
        with patch.object(build.shutil, 'which', return_value='git-perl'), \
                patch.object(build.subprocess, 'check_output', return_value='msys'):
            with self.assertRaisesRegex(RuntimeError, 'native Windows Perl'):
                build.windows_perl(env)

    def test_msvc_profile_keeps_upstream_windows_features_and_b2_flags(self) -> None:
        root = Path(__file__).resolve().parents[2]
        source = root / 'third_party/libs/openssl/Configure'
        profile = root / 'tools/openssl/msvc.conf'
        for name in ('VC-WIN32', 'VC-WIN64A', 'VC-WIN64-ARM'):
            directory = self.root / name
            directory.mkdir()
            probe = directory / 'probe.conf'
            # Resolve the actual Windows inheritance with upstream Configure.
            # Only rendering uses the host's Perl platform, since nmake and
            # native Windows Perl cannot run on the Unix tool-test runners.
            probe.write_text('my %targets = ("VC-probe" => {\n'
                             f'  inherit_from => ["{name}-webcpp"],\n'
                             + ('  build_scheme => ["unified", "unix"],\n'
                                '  build_file => "Makefile", perl_platform => "Unix"\n'
                                if sys.platform != 'win32' else '') + '});\n')
            flags = '/MDd /Z7 /Od /DWEBCPP_TEST_OPENSSL_CONFIGURATION=17'
            perl = build.windows_perl(os.environ.copy()) if sys.platform == 'win32' else 'perl'
            result = subprocess.run(
                [perl, str(source), '--config=' + str(profile), '--config=' + str(probe),
                 'VC-probe', 'no-asm', 'no-shared', 'no-tests', 'no-apps', 'no-docs',
                 'no-module', '--prefix=' + str(directory / 'install')], cwd=directory,
                env={**os.environ, 'CC': 'cl.exe', 'CFLAGS': flags},
                capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = subprocess.check_output(
                [perl, '-I.', '-Mconfigdata', '-MJSON::PP', '-e',
                 'print encode_json({flags => $configdata::config{CFLAGS}, '
                 'lib_flags => $configdata::target{lib_cflags}, '
                 'defines => $configdata::target{defines}, '
                 'threads => $configdata::target{thread_scheme}});'],
                cwd=directory, text=True, timeout=30)
            configuration = json.loads(data)
            self.assertEqual(configuration['flags'], [flags])
            self.assertNotIn('/MT', configuration['lib_flags'])
            self.assertNotIn('/Zi', configuration['lib_flags'])
            self.assertIn('OPENSSL_SYS_WIN32', configuration['defines'])
            self.assertNotIn('_DEBUG', configuration['defines'])
            self.assertEqual(configuration['threads'], 'winthreads')


if __name__ == '__main__':
    unittest.main()
