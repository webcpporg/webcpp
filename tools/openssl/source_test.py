#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Exercise committed source pin generation and the verified build staging boundary."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from source import check_checkout, stage_source
from update import regenerate


class SourceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix='openssl source ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'source'
        self.source.mkdir()
        self.git('init', '--quiet')
        (self.source / 'Configure').write_text('#!/usr/bin/env perl\n')
        (self.source / 'Configure').chmod(0o755)
        (self.source / 'crypto').mkdir()
        (self.source / 'crypto/input.c').write_text('int source_value = 7;\n')
        (self.source / '.metadata').write_text('not distributed\n')
        self.git('add', '.')
        self.git('commit', '--quiet', '-m', 'Create source fixture')
        self.nested = self.git('rev-parse', 'HEAD')
        self.git('update-index', '--add', '--cacheinfo', '160000', self.nested, 'external')
        (self.source / 'external').mkdir()
        self.git('commit', '--quiet', '-m', 'Record unused upstream fixture')
        self.pin = {'version': 'fixture', 'commit': self.git('rev-parse', 'HEAD'),
                    'repository': 'https://example.invalid/source.git'}

    def git(self, *arguments: str) -> str:
        env = {**os.environ, 'GIT_AUTHOR_DATE': '1700000000 +0000',
               'GIT_COMMITTER_DATE': '1700000000 +0000'}
        result = subprocess.run(
            ['git', '-C', str(self.source), '-c', 'user.name=Source test',
             '-c', 'user.email=source@example.invalid', '-c', 'commit.gpgsign=false',
             *arguments], env=env, check=True, capture_output=True, text=True)
        return result.stdout.strip()

    def test_generator_is_repeatable_and_uses_committed_metadata(self) -> None:
        manifest = self.root / 'pin.json'
        manifest.write_text(json.dumps(self.pin))
        command = [sys.executable, str(Path(__file__).with_name('update.py')),
                   '--source', str(self.source), '--pin', str(manifest)]
        subprocess.run(command, check=True, capture_output=True)
        original = manifest.read_bytes()
        pin = json.loads(original)
        self.assertEqual(pin['source_date_epoch'], 1700000000)
        self.assertEqual(pin['omitted_submodules'], {'external': self.nested})
        # Untracked bytes cannot enter a generated pin, even if Git ignores them.
        (self.source / 'extra.c').write_text('int untracked;\n')
        subprocess.run(command, check=True, capture_output=True)
        self.assertEqual(manifest.read_bytes(), original)
        with self.assertRaisesRegex(RuntimeError, 'source tree differs'):
            stage_source(self.source, self.root / 'rejected', pin)

    def test_staging_omits_hidden_and_unused_nested_inputs(self) -> None:
        pin = regenerate(self.source, self.pin)
        (self.source / 'external/untrusted.c').write_text('not a build input\n')
        (self.source / '.untracked').write_text('not a build input\n')
        destination = self.root / 'staged'
        stage_source(self.source, destination, pin)
        self.assertEqual(sorted(path.relative_to(destination).as_posix()
                                for path in destination.rglob('*') if path.is_file()),
                         ['Configure', 'crypto/input.c'])
        self.assertEqual((destination / 'Configure').read_bytes(), b'#!/usr/bin/env perl\n')
        self.assertEqual((destination / 'Configure').stat().st_mode & 0o777, 0o755)

    def test_checkout_and_generator_reject_mismatched_revision(self) -> None:
        self.pin['commit'] = '0' * 40
        for validate in (check_checkout, regenerate):
            with self.assertRaisesRegex(RuntimeError, 'checkout differs'):
                validate(self.source, self.pin)

    def test_windows_staging_verifies_bytes_without_executable_file_modes(self) -> None:
        pin = regenerate(self.source, self.pin)
        (self.source / 'Configure').chmod(0o644)
        with patch('source.sys.platform', 'win32'):
            stage_source(self.source, self.root / 'windows', pin)
            (self.source / 'crypto/input.c').write_text('int tampered;\n')
            with self.assertRaisesRegex(RuntimeError, 'source tree differs'):
                stage_source(self.source, self.root / 'tampered', pin)

    def test_windows_staging_normalizes_git_checkout_line_endings(self) -> None:
        pin = regenerate(self.source, self.pin)
        self.git('config', 'core.autocrlf', 'true')
        (self.source / 'Configure').write_bytes(b'#!/usr/bin/env perl\r\n')
        with patch('source.sys.platform', 'win32'):
            stage_source(self.source, self.root / 'windows', pin)
        self.assertEqual((self.root / 'windows/Configure').read_bytes(), b'#!/usr/bin/env perl\n')

    def test_checkout_and_generator_reject_dirty_tracked_sources(self) -> None:
        (self.source / 'crypto/input.c').write_text('int changed;\n')
        for validate in (check_checkout, regenerate):
            with self.assertRaises(subprocess.CalledProcessError):
                validate(self.source, self.pin)

    def test_generator_requires_a_source_checkout_of_its_own(self) -> None:
        pin = regenerate(self.source, self.pin)
        stage_source(self.source, self.root / 'archive', pin)
        with self.assertRaisesRegex(RuntimeError, 'requires its Git checkout'):
            regenerate(self.root / 'archive', pin)


if __name__ == '__main__':
    unittest.main()
