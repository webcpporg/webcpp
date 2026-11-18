#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""A third-party build's key names its inputs, and one configuration is selected at a time."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('third_party_build.py')

# A library's own source checks, as tools/<name>/source.py defines them: the stand-in refuses
# a pin whose commit says so, the way the real ones refuse a checkout that differs from it.
SOURCE = '''from pathlib import Path
import subprocess

def check_checkout(source: Path, pin: dict) -> None:
    (source / 'checked').write_text(str(source.is_absolute()) + ' ' + pin['commit'])
    if pin['commit'] == 'moved':
        raise RuntimeError('Demo checkout differs from tools/demo/pin.json; '
                           'update the submodule')
    if pin['commit'] == 'edited':
        raise subprocess.CalledProcessError(1, ['git', 'diff', '--exit-code', 'HEAD', '--'])
'''


class ThirdPartyBuildTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='third party ')
        self.root = Path(self.temporary.name)
        tools = self.root / 'tools/demo'
        tools.mkdir(parents=True)
        (tools / 'source.py').write_text(SOURCE)
        self.pin('pinned')
        (tools / 'build.py').write_text('# builds the demo\n')
        (self.root / 'third_party/libs/demo').mkdir(parents=True)

    def tearDown(self):
        self.temporary.cleanup()

    def pin(self, commit: str) -> None:
        (self.root / 'tools/demo/pin.json').write_text('{"commit": "%s"}\n' % commit)

    def run_script(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *arguments], text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)

    def key(self, *inputs: str) -> subprocess.CompletedProcess:
        return self.run_script('key', str(self.root), 'demo', 'third_party/libs/demo', *inputs)

    def test_the_key_names_each_inputs_path_and_bytes(self):
        inputs = ('tools/demo/build.py', 'tools/demo/pin.json')
        first = self.key(*inputs)
        self.assertEqual(first.returncode, 0, first.stdout)
        key = first.stdout.strip()
        self.assertRegex(key, r'^[0-9a-f]{64}$')
        self.assertEqual(self.key(*reversed(inputs)).stdout.strip(), key)
        build = self.root / 'tools/demo/build.py'
        build.write_text('# builds the demo differently\n')
        changed = self.key(*inputs).stdout.strip()
        self.assertNotEqual(changed, key)
        build.rename(self.root / 'tools/demo/make.py')
        moved = self.key('tools/demo/make.py', 'tools/demo/pin.json').stdout.strip()
        self.assertNotIn(moved, (key, changed))

    def test_the_key_checks_the_checkout_with_the_librarys_own_rules(self):
        result = self.key('tools/demo/pin.json')
        self.assertEqual(result.returncode, 0, result.stdout)
        checked = (self.root / 'third_party/libs/demo/checked').read_text()
        self.assertEqual(checked, 'True pinned')

    def test_a_checkout_that_differs_from_its_pin_has_no_key(self):
        self.pin('moved')
        result = self.key('tools/demo/pin.json')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'Demo checkout differs from '
                         'tools/demo/pin.json; update the submodule')

    def test_a_checkout_with_local_changes_has_no_key(self):
        self.pin('edited')
        result = self.key('tools/demo/pin.json')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'third_party/libs/demo differs from its '
                         'pinned commit; restore its files or update tools/demo/pin.json')

    def test_a_missing_input_has_no_key(self):
        result = self.key('tools/demo/pin.json', 'tools/demo/absent.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('tools/demo/absent.py', result.stdout)

    def test_a_selection_replaces_the_previous_one_of_its_library(self):
        directory = self.root / 'bin/release'
        directory.mkdir(parents=True)
        for name in ('demo-1111.selected', 'demo-2222.selected', 'other-3333.selected',
                     'demo.txt'):
            (directory / name).write_text('earlier\n')
        result = self.run_script('select', str(directory / 'demo-4444.selected'))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(sorted(path.name for path in directory.iterdir()),
                         ['demo-4444.selected', 'demo.txt', 'other-3333.selected'])
        self.assertEqual((directory / 'demo-4444.selected').read_text(), '4444\n')


if __name__ == '__main__':
    unittest.main()
