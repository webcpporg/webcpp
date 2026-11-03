# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Check that preparing a private Boost overlay is exact and non-destructive."""
from pathlib import Path
import hashlib
import importlib.machinery
import importlib.util
import json
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare', HERE / 'prepare.py')
assert spec is not None and isinstance(spec.loader, importlib.machinery.SourceFileLoader)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class Preparation(unittest.TestCase):
    def test_exact_inputs_idempotence_and_mismatch(self):
        with tempfile.TemporaryDirectory(prefix='asio wasi patch ') as directory:
            root = Path(directory)
            source, output, bundle = root / 'boost', root / 'output', root / 'bundle'
            header = source / 'boost/asio/example.hpp'
            header.parent.mkdir(parents=True)
            header.write_text('before\n')
            (source / 'boost/version.hpp').write_text('#define BOOST_VERSION 109200\n')
            bundle.mkdir()
            digest = lambda data: hashlib.sha256(data.encode()).hexdigest()
            (bundle / 'manifest.json').write_text(json.dumps({
                'boost_version': 109200,
                'files': {'boost/asio/example.hpp': {
                    'before': digest('before\n'), 'after': digest('after\n')}}}))
            (bundle / 'boost-1.92.patch').write_text(
                '--- a/boost/asio/example.hpp\n+++ b/boost/asio/example.hpp\n'
                '@@ -1 +1 @@\n-before\n+after\n')
            prepare.prepare(source, output, bundle)
            self.assertEqual(header.read_text(), 'before\n')
            result = output / 'boost/asio/example.hpp'
            self.assertEqual(result.read_text(), 'after\n')
            modified = result.stat().st_mtime_ns
            prepare.prepare(source, output, bundle)
            self.assertEqual(result.stat().st_mtime_ns, modified)
            stale = output / 'boost/asio/removed.hpp'
            stale.write_text('old patch still shadows Boost\n')
            with self.assertRaisesRegex(ValueError, 'unexpected overlay file'):
                prepare.prepare(source, output, bundle)
            self.assertEqual(result.stat().st_mtime_ns, modified)
            stale.unlink()
            (output / 'linked').symlink_to(source, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                prepare.prepare(source, output, bundle)
            self.assertEqual(header.read_text(), 'before\n')
            (output / 'linked').unlink()
            header.write_text('different upstream version\n')
            with self.assertRaisesRegex(ValueError, 'incompatible Boost header'):
                prepare.prepare(source, output, bundle)
            self.assertEqual(result.read_text(), 'after\n')

    def test_refuses_the_installed_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            with self.assertRaisesRegex(ValueError, 'separate'):
                prepare.prepare(source, source, HERE)


if __name__ == '__main__':
    unittest.main()
