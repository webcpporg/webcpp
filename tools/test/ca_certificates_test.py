#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Test CA snapshot updates and consumption through public command lines."""
import hashlib
import json
from pathlib import Path
import re
import ssl
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
UPDATE = ROOT / 'tools/ca_certificates/update.py'
GENERATE = ROOT / 'tools/ca_certificates/generate.py'


class SnapshotTests(unittest.TestCase):
    def test_update_integrity_and_generation(self):
        # A bad digest, malformed replacement or corrupt checkout must never
        # turn into usable trust data or overwrite an already valid snapshot.
        with tempfile.TemporaryDirectory(prefix='webcpp CA test ') as scratch:
            directory = Path(scratch)
            pem = ROOT / 'third_party/ca_certificates/cacert.pem'
            data = pem.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            package = directory / 'package'
            command = [sys.executable, str(UPDATE), '--date', '2026-09-25',
                       '--source-file', str(pem), '--sha256', digest,
                       '--output', str(package)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((package / 'cacert.pem').read_bytes(), data)
            manifest = json.loads((package / 'manifest.json').read_text())
            self.assertEqual(manifest['sha256'], digest)
            self.assertGreater(manifest['certificate_count'], 0)
            before = (package / 'manifest.json').read_bytes()
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Added: 0; removed: 0', result.stdout)
            wrong = command.copy()
            wrong[wrong.index('--sha256') + 1] = '0' * 64
            result = subprocess.run(wrong, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((package / 'manifest.json').read_bytes(), before)
            self.assertEqual((package / 'cacert.pem').read_bytes(), data)
            output = directory / 'embedded.hpp'
            generate = [sys.executable, str(GENERATE), str(package / 'cacert.pem'),
                        str(package / 'manifest.json'), str(output)]
            result = subprocess.run(generate, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            output.unlink()
            (package / 'cacert.pem').write_bytes(data + b'corruption')
            result = subprocess.run(generate, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_replacement_reports_removals_and_rejects_invalid_imports(self):
        with tempfile.TemporaryDirectory(prefix='webcpp CA updates ') as scratch:
            directory = Path(scratch)
            data = (ROOT / 'third_party/ca_certificates/cacert.pem').read_bytes()
            blocks = re.findall(rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',
                                data, re.DOTALL)
            source = directory / 'input.pem'
            package = directory / 'package'

            def update(content, selected_date):
                source.write_bytes(content)
                return subprocess.run(
                    [sys.executable, str(UPDATE), '--date', selected_date,
                     '--source-file', str(source), '--sha256', hashlib.sha256(content).hexdigest(),
                     '--output', str(package)], capture_output=True, text=True)

            self.assertEqual(update(b'\n'.join(blocks[:2]), '2026-09-25').returncode, 0)
            reduced = update(blocks[0], '2026-10-16')
            self.assertEqual(reduced.returncode, 0, reduced.stderr)
            self.assertIn('Added: 0; removed: 1', reduced.stdout)
            self.assertIn('REMOVE SHA256:', reduced.stdout)
            before = (package / 'manifest.json').read_bytes()
            der = ssl.PEM_cert_to_DER_cert(blocks[0].decode())
            for malformed in (b'', b'garbage', blocks[0] + b'\n-----BEGIN CERTIFICATE-----',
                              blocks[0] + b'\n' + blocks[0],
                              ssl.DER_cert_to_PEM_cert(der + b'garbage').encode(),
                              ssl.DER_cert_to_PEM_cert(der + der).encode(),
                              b'-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----'):
                self.assertNotEqual(update(malformed, '2026-10-16').returncode, 0)
                self.assertEqual((package / 'manifest.json').read_bytes(), before)
            self.assertNotEqual(update(blocks[0], '2026-01-01').returncode, 0)
            self.assertEqual((package / 'manifest.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
