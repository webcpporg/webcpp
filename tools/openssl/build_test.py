#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Check header publication and orchestration at unavailable tool boundaries."""
from __future__ import annotations

import argparse
import builtins
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import build
from source import inventory_digest


class HeaderPublicationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix='openssl publication ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.generated = self.root / 'generated'
        self.output = self.root / 'output'
        self.header = self.output / 'include/openssl/configuration.h'
        self.original = b'/* configured header */\n' * 8192
        for directory in (self.source, self.generated, self.output):
            (directory / 'include/openssl').mkdir(parents=True)
        (self.source / 'include/openssl/configuration.h').write_bytes(b'/* source fallback */\n')
        (self.generated / 'include/openssl/configuration.h').write_bytes(self.original)
        self.header.write_bytes(self.original)

    def publish(self, full: bool) -> None:
        scratch = Path(tempfile.mkdtemp(dir=self.root))
        shutil.copytree(self.source, scratch / 'source')

        def command(command: list[str], *, cwd: Path, env: dict, log: Path,
                    timeout: float = 600) -> None:
            log.write_text('completed\n')
            if command[-1] == 'build_generated':
                shutil.copytree(self.generated / 'include', cwd / 'include')
            if command[-1] == 'install_dev':
                shutil.copytree(self.generated / 'include', scratch / 'install/include')
                (scratch / 'install/lib').mkdir()
                for name in ('libssl.a', 'libcrypto.a'):
                    (scratch / 'install/lib' / name).write_bytes(b'archive fixture\n')

        args = argparse.Namespace(cc=sys.executable, ar='ar', platform='wasi',
                                  threading='single', variant='release', test=False,
                                  headers_only=not full, flags=['--target=wasm32-wasip3'])
        with patch.object(build, 'run', side_effect=command):
            build.build_source(args, self.output,
                               {'version': 'fixture', 'source_date_epoch': 1700000000}, scratch)

    def test_full_build_keeps_identical_headers_inode_timestamp_and_permissions(self) -> None:
        self.header.chmod(0o644)
        os.utime(self.header, ns=(1700000000000000000, 1700000000000000000))
        before = self.header.stat()
        self.publish(True)
        after = self.header.stat()
        self.assertEqual(self.header.read_bytes(), self.original)
        self.assertEqual((after.st_ino, after.st_mtime_ns, after.st_mode),
                         (before.st_ino, before.st_mtime_ns, before.st_mode))

    def test_header_action_refreshes_identical_headers_without_replacing_them(self) -> None:
        os.utime(self.header, ns=(1700000000000000000, 1700000000000000000))
        before = self.header.stat()
        self.publish(False)
        after = self.header.stat()
        self.assertEqual(self.header.read_bytes(), self.original)
        self.assertEqual((after.st_ino, after.st_mode), (before.st_ino, before.st_mode))
        self.assertGreater(after.st_mtime_ns, before.st_mtime_ns)

    @unittest.skipIf(sys.platform == 'win32', 'POSIX permits replacement of mapped files')
    def test_republication_keeps_existing_mapped_readers_valid(self) -> None:
        # Pause at the real write-open boundary, before shutil copies any bytes.
        # Truncating the published inode here used to kill this reader with SIGBUS.
        for full, changed in ((False, False), (False, True), (True, False), (True, True)):
            with self.subTest(full=full, changed=changed):
                self.header.write_bytes(self.original)
                replacement = b'/* updated configuration */\n' * 8192 if changed else self.original
                (self.generated / 'include/openssl/configuration.h').write_bytes(replacement)
                reader = subprocess.Popen(
                    [sys.executable, '-u', '-c',
                     'import hashlib, mmap, resource, signal, sys; signal.alarm(10); '
                     'resource.setrlimit(resource.RLIMIT_CORE, (0, 0)); '
                     'f = open(sys.argv[1], "rb"); '
                     'm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ); '
                     'print("mapped", flush=True); sys.stdin.readline(); '
                     'print(hashlib.sha256(m).hexdigest())', str(self.header)],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True)
                original_open = builtins.open
                result = []

                def inspect_open(path, mode='r', *args, **kwargs):
                    stream = original_open(path, mode, *args, **kwargs)
                    if (isinstance(path, (str, Path)) and Path(path) == self.header
                            and mode == 'wb' and not result):
                        result.append(reader.communicate(input='read\n', timeout=15))
                    return stream

                try:
                    assert reader.stdout is not None
                    self.assertEqual(reader.stdout.readline(), 'mapped\n')
                    with patch('builtins.open', side_effect=inspect_open):
                        self.publish(full)
                    if not result:
                        result.append(reader.communicate(input='read\n', timeout=15))
                    self.assertEqual(reader.returncode, 0, result[0][1])
                    self.assertEqual(result[0][0].strip(),
                                     hashlib.sha256(self.original).hexdigest())
                    self.assertEqual(self.header.read_bytes(), replacement)
                finally:
                    if reader.poll() is None:
                        reader.kill()
                    reader.communicate(timeout=15)

    def test_changed_headers_keep_source_permissions(self) -> None:
        source = self.generated / 'include/openssl/configuration.h'
        source.write_bytes(b'/* updated configuration */\n')
        source.chmod(0o644)
        self.header.chmod(0o600)
        self.publish(False)
        self.assertEqual(self.header.read_bytes(), source.read_bytes())
        self.assertEqual(stat.S_IMODE(self.header.stat().st_mode),
                         stat.S_IMODE(source.stat().st_mode))

    def test_changed_headers_receive_a_new_build_timestamp(self) -> None:
        # Source headers can predate the recipe. Retaining their old timestamp
        # would make B2 rerun header generation and rebuild archives forever.
        source = self.generated / 'include/openssl/configuration.h'
        source.write_bytes(b'/* updated configuration */\n')
        os.utime(source, ns=(1700000000000000000, 1700000000000000000))
        self.publish(True)
        self.assertGreater(self.header.stat().st_mtime_ns, source.stat().st_mtime_ns)

    def test_failed_copy_leaves_the_published_header_and_no_partial_files(self) -> None:
        (self.generated / 'include/openssl/configuration.h').write_bytes(b'/* changed */\n')
        original_copy = shutil.copyfile

        def fail_copy(source, destination, *, follow_symlinks=True):
            if Path(destination).parent == self.header.parent:
                Path(destination).write_bytes(b'partial')
                raise OSError('interrupted header copy')
            return original_copy(source, destination, follow_symlinks=follow_symlinks)

        for full in (False, True):
            with self.subTest(full=full), patch.object(build.shutil, 'copyfile',
                                                     side_effect=fail_copy):
                with self.assertRaisesRegex(OSError, 'interrupted header copy'):
                    self.publish(full)
                self.assertEqual(self.header.read_bytes(), self.original)
                self.assertEqual(list(self.header.parent.iterdir()), [self.header])
                for name in ('libssl.a', 'libcrypto.a', 'build.json'):
                    self.assertFalse((self.output / name).exists(), name)


class UpstreamResultsTest(unittest.TestCase):
    def test_skipped_preparation_does_not_hide_the_full_suite_summary(self) -> None:
        log = ('00-prep_fipsmodule_cnf.t .. skipped: FIPS is disabled\n'
               'Files=1, Tests=0, 0 wallclock secs\nResult: NOTESTS\n'
               '01-test_sanity.t .. ok\n02-test_errstr.t .. ok\n'
               'All tests successful.\nFiles=2, Tests=21, 1 wallclock secs\nResult: PASS\n')
        proof = build.suite_result(log, ['00-prep_fipsmodule_cnf.t', '01-test_sanity.t',
                                         '02-test_errstr.t'])
        self.assertEqual(proof['files'], 2)
        self.assertEqual(proof['tests'], 21)
        self.assertEqual(proof['recipes'], 3)

    def test_a_successful_subset_is_not_a_successful_suite(self) -> None:
        log = ('01-test_sanity.t .. ok\nAll tests successful.\n'
               'Files=1, Tests=6, 1 wallclock secs\nResult: PASS\n')
        with self.assertRaisesRegex(RuntimeError, 'missing recipes.*02-test_errstr.t'):
            build.suite_result(log, ['01-test_sanity.t', '02-test_errstr.t'])


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

    def test_windows_suite_failure_does_not_publish_libraries(self) -> None:
        output = self.root / 'failed-suite'

        def command(command: list[str], *, cwd: Path, env: dict, log: Path,
                    timeout: float = 600) -> None:
            log.write_text('completed\n')
            if command[-1] == 'build_libs':
                (cwd / 'include/openssl').mkdir(parents=True)
                (cwd / 'include/openssl/configuration.h').write_text('matching headers\n')
                (cwd / 'libssl.lib').write_bytes(b'ssl')
                (cwd / 'libcrypto.lib').write_bytes(b'crypto')
            if 'test' in command:
                self.assertEqual(command, ['nmake', '/nologo', 'test', 'TESTS=alltests'])
                self.assertEqual(env['HARNESS_JOBS'], '2')
                raise RuntimeError('upstream Windows test failed')

        args = ['build.py', '--source', str(self.source), '--output', str(output),
                '--platform', 'windows', '--threading', 'multi', '--cc', str(self.compiler),
                '--test']
        with patch.object(build, 'HERE', self.root), patch.object(sys, 'argv', args), \
                patch.object(build, 'run', side_effect=command), \
                patch.object(build, 'windows_target', return_value='VC-WIN64A'), \
                patch.object(build, 'windows_perl', return_value='native-perl.exe'):
            with self.assertRaisesRegex(RuntimeError, 'upstream Windows test failed'):
                build.main()
        for name in ('libssl.lib', 'libcrypto.lib', 'build.json', 'upstream-tests.json'):
            self.assertFalse((output / name).exists(), name)

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
