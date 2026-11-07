#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""The GCC installer rejects unsupported hosts and verifies restored toolchains."""
from __future__ import annotations

from importlib.machinery import SourceFileLoader
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch

SCRIPT = Path(__file__).parent / 'actions/gcc/install.py'
SPEC = importlib.util.spec_from_file_location('gcc_install', SCRIPT)
assert SPEC and isinstance(SPEC.loader, SourceFileLoader)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class GccInstallTest(unittest.TestCase):
    def test_wrong_host_never_runs_docker(self):
        with patch.dict(os.environ, {'RUNNER_OS': 'macOS', 'RUNNER_ARCH': 'ARM64'}):
            with patch.object(installer, 'run') as run:
                with self.assertRaisesRegex(installer.Failure, 'Linux-X64'):
                    installer.install()
                run.assert_not_called()

    def test_version_mismatch_is_rejected_before_probe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(installer, 'run', return_value='15.2.0\n') as run:
                with self.assertRaisesRegex(installer.Failure, '15.3.0'):
                    installer.verify(root)
                self.assertEqual(run.call_count, 1)

    def test_verified_toolchain_compiles_and_runs_coroutine_probe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(installer, 'run', side_effect=['15.3.0\n', '', '']) as run:
                installer.verify(root)
                calls = run.call_args_list
                self.assertEqual(len(calls), 3)
                compile_args = calls[1].args[0]
                self.assertEqual(compile_args[0], str(root / 'bin/g++-15'))
                self.assertIn('-Werror', compile_args)
                self.assertIn(str(SCRIPT.with_name('coroutine_probe.cpp')), compile_args)
                self.assertEqual(calls[2].args[0], [compile_args[-1]])
                environment = calls[2].kwargs['env']
                self.assertTrue(environment['LD_LIBRARY_PATH'].startswith(str(root / 'lib64')))

    def test_probe_failure_is_not_treated_as_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(installer, 'run', side_effect=['15.3.0\n', installer.Failure('ICE')]):
                with self.assertRaisesRegex(installer.Failure, 'ICE'):
                    installer.verify(Path(temporary))

    def test_fresh_install_uses_only_pinned_image_and_removes_container(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'gcc'
            seen = []
            def run(command, **_kwargs):
                seen.append(command)
                if command[:2] == ['docker', 'create']:
                    return '0123456789abcdef\n'
                if command[:2] == ['docker', 'cp']:
                    destination = Path(command[-1])
                    (destination / 'bin').mkdir()
                    (destination / 'bin/gcc').write_text('compiler')
                    (destination / 'bin/g++').write_text('compiler')
                return ''
            with patch.object(installer, 'run', side_effect=run), patch.object(installer, 'verify'):
                installer.prepare(root)
            self.assertTrue((root / 'bin/g++-15').is_symlink())
            self.assertEqual((root / '.webcpp-image').read_text().strip(), installer.IMAGE)
            self.assertIn(['docker', 'pull', '--platform', 'linux/amd64', installer.IMAGE], seen)
            self.assertIn(['docker', 'rm', '-f', '0123456789abcdef'], seen)
            self.assertIn('@sha256:', installer.IMAGE)

    def test_failed_probe_leaves_no_install_and_cleans_container(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'gcc'
            def run(command, **_kwargs):
                if command[:2] == ['docker', 'create']:
                    return '0123456789abcdef\n'
                if command[:2] == ['docker', 'cp']:
                    (Path(command[-1]) / 'bin').mkdir()
                return ''
            with patch.object(installer, 'run', side_effect=run) as invoke:
                with patch.object(installer, 'verify', side_effect=installer.Failure('broken')):
                    with self.assertRaisesRegex(installer.Failure, 'broken'):
                        installer.prepare(root)
            self.assertFalse(root.exists())
            self.assertIn(call(['docker', 'rm', '-f', '0123456789abcdef']),
                          invoke.call_args_list)

    def test_unknown_existing_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / 'user-file'
            marker.write_text('keep')
            with patch.object(installer, 'run') as run:
                with self.assertRaises(installer.Failure):
                    installer.prepare(root)
                run.assert_not_called()
            self.assertEqual(marker.read_text(), 'keep')

    def test_matching_cache_is_verified_without_docker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.webcpp-image').write_text(installer.IMAGE + '\n')
            with patch.object(installer, 'run') as run, patch.object(installer, 'verify') as verify:
                installer.prepare(root)
                run.assert_not_called()
                verify.assert_called_once_with(root)


if __name__ == '__main__':
    unittest.main()
