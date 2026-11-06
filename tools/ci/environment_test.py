#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Exercises the prepared-environment CLI through a controlled Docker boundary.

The native lane must pull an immutable image and never build on a miss. Archive
restoration copies bytes without starting a container, checks all hashes before
publishing any file, and cleans the stopped container on every exit path.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
IMAGE = 'ghcr.io/webcpporg/ci-environment@sha256:' + 'a' * 64
DOCKER = '''#!/usr/bin/env python3
import json, os, pathlib, shutil, sys
args = sys.argv[1:]
with open(os.environ['DOCKER_LOG'], 'a') as output:
    output.write(json.dumps(args) + '\\n')
if args[:3] == ['image', 'inspect', '--format']:
    print(json.dumps(['ghcr.io/webcpporg/ci-environment@sha256:' + 'a' * 64]))
    sys.exit(0)
if args[:2] == ['image', 'inspect']:
    sys.exit(0 if os.environ.get('IMAGE_PRESENT') else 1)
if args[0] == 'pull':
    config = os.environ.get('DOCKER_CONFIG', '')
    if config:
        pathlib.Path(os.environ['DOCKER_LOG'] + '.config').write_text(
            json.dumps([config, sorted(p.name for p in pathlib.Path(config).iterdir())]))
    sys.exit(int(os.environ.get('PULL_STATUS', '0')))
if args[0] == 'create':
    print('container-fixture')
elif args[0] == 'cp':
    shutil.copytree(os.environ['ARCHIVES'], args[-1], dirs_exist_ok=True, symlinks=True)
elif args[0] == 'rm':
    pass
elif args[0] in ('build', 'push', 'run'):
    sys.exit(int(os.environ.get(args[0].upper() + '_STATUS', '0')))
elif args[0] != 'pull':
    sys.exit('unexpected Docker operation: ' + repr(args))
'''


class EnvironmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix='webcpp environment ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(HERE, self.root / 'tools/ci', ignore=shutil.ignore_patterns('__pycache__'))
        self.binary = self.root / 'bin'
        self.binary.mkdir()
        docker = self.binary / 'docker'
        docker.write_text(DOCKER)
        docker.chmod(0o755)
        self.archives = self.root / 'archives'
        self.archives.mkdir()
        self.log = self.root / 'docker.log'
        self.cache = self.root / 'cache'
        self.env = {**os.environ, 'PATH': str(self.binary) + os.pathsep + os.environ['PATH'],
                    'DOCKER_LOG': str(self.log), 'ARCHIVES': str(self.archives),
                    'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64'}
        self.env.pop('WEBCPP_PREPARE_ENVIRONMENT', None)
        self.pins: dict = {'schema': 1, 'artifacts': {}}

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, 'tools/ci/environment.py', *arguments],
                              cwd=self.root, env=self.env, text=True, capture_output=True,
                              check=False, timeout=20)

    def pin(self, key: str, *, tool: str = '', variant: str = '',
            archives: list[str] | None = None) -> None:
        command = ['recipe', '--tool', tool, '--variant', variant] if tool else ['recipe']
        recipe = self.run_cli(*command)
        self.assertEqual(recipe.returncode, 0, recipe.stderr)
        self.pins['artifacts'][key] = {'image': IMAGE, 'recipe': recipe.stdout.strip(),
                                      'archives': archives or [], 'source': 'b' * 40}
        self.write_pins()

    def write_pins(self) -> None:
        (self.root / 'tools/ci/environments.json').write_text(json.dumps(self.pins))

    def calls(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def blob(self, contents: bytes) -> str:
        digest = hashlib.sha256(contents).hexdigest()
        (self.archives / digest).write_bytes(contents)
        return digest

    def test_native_pulls_digest_and_never_builds(self) -> None:
        self.pin('native-linux-x64')
        result = self.run_cli('native')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [['image', 'inspect', IMAGE], ['pull', IMAGE]])
        self.assertIn(IMAGE, result.stdout)

    def test_unavailable_native_image_fails_without_building(self) -> None:
        self.pin('native-linux-x64')
        self.env['PULL_STATUS'] = '1'
        result = self.run_cli('native')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('prepare-environments', result.stderr)
        self.assertFalse(any(call[0] == 'build' for call in self.calls()))

    def test_stale_recipe_or_mutable_tag_is_rejected_before_docker(self) -> None:
        self.pin('native-linux-x64')
        for field, value in [('recipe', '0' * 64), ('image', 'ubuntu:latest')]:
            with self.subTest(field=field):
                self.pin('native-linux-x64')
                self.pins['artifacts']['native-linux-x64'][field] = value
                self.write_pins()
                result = self.run_cli('native')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.log.exists())

    def test_archives_are_verified_and_copied_without_execution(self) -> None:
        digest = self.blob(b'archive bytes')
        self.pin('wasi-sdk-linux-x64', tool='wasi-sdk', archives=[digest])
        result = self.run_cli('restore-tool', '--tool', 'wasi-sdk', '--cache', str(self.cache))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.cache / digest).read_bytes(), b'archive bytes')
        self.assertEqual([call[0] for call in self.calls()],
                         ['image', 'pull', 'create', 'cp', 'rm'])
        self.assertNotIn('run', [call[0] for call in self.calls()])

    def test_bad_bundle_does_not_publish_any_blob_and_removes_container(self) -> None:
        first = self.blob(b'first')
        second = self.blob(b'second')
        (self.archives / second).write_bytes(b'corrupt')
        self.pin('wasi-wit-linux-x64', tool='wasi-wit', archives=[first, second])
        result = self.run_cli('restore-tool', '--tool', 'wasi-wit', '--cache', str(self.cache))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SHA-256', result.stderr)
        self.assertFalse(self.cache.exists() and list(self.cache.iterdir()))
        self.assertEqual(self.calls()[-1][0], 'rm')

    def test_symlink_in_bundle_is_rejected(self) -> None:
        digest = hashlib.sha256(b'outside').hexdigest()
        outside = self.root / 'outside'
        outside.write_bytes(b'outside')
        (self.archives / digest).symlink_to(outside)
        self.pin('wasi-sdk-linux-x64', tool='wasi-sdk', archives=[digest])
        result = self.run_cli('restore-tool', '--tool', 'wasi-sdk', '--cache', str(self.cache))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.cache.exists() and list(self.cache.iterdir()))

    def test_other_hosts_explicitly_use_the_existing_upstream_path(self) -> None:
        self.env.update(RUNNER_OS='macOS', RUNNER_ARCH='ARM64')
        result = self.run_cli('restore-tool', '--tool', 'wasi-sdk', '--cache', str(self.cache))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('upstream', result.stdout)
        self.assertFalse(self.log.exists())

    def test_missing_pins_fail_closed_on_linux(self) -> None:
        (self.root / 'tools/ci/environments.json').unlink(missing_ok=True)
        result = self.run_cli('restore-tool', '--tool', 'wasi-sdk', '--cache', str(self.cache))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('prepare-environments', result.stderr)
        self.assertFalse(self.log.exists())

    def test_publication_is_refused_in_pull_requests_and_forks(self) -> None:
        for event, repository in [('pull_request', 'webcpporg/webcpp'),
                                  ('workflow_dispatch', 'someone/webcpp')]:
            with self.subTest(event=event, repository=repository):
                self.env.update(GITHUB_EVENT_NAME=event, GITHUB_REPOSITORY=repository,
                                WEBCPP_PREPARE_ENVIRONMENT='1', GITHUB_SHA='b' * 40)
                result = self.run_cli('publish', '--out', str(self.root / 'candidate.json'))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('trusted workflow_dispatch', result.stderr)
                self.assertFalse(self.log.exists())

    def test_manifest_promotion_requires_every_environment(self) -> None:
        directory = self.root / 'candidates'
        directory.mkdir()
        output = self.root / 'promoted.json'
        result = self.run_cli('merge', '--directory', str(directory), '--out', str(output))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing prepared environments', result.stderr)
        self.assertFalse(output.exists())

    def test_workflow_separates_publication_from_pull_request_jobs(self) -> None:
        workflow = HERE.parents[1] / '.github/workflows/prepare-environments.yml'
        self.assertTrue(workflow.is_file(), 'explicit preparation workflow is missing')
        text = workflow.read_text()
        self.assertIn("github.event_name == 'workflow_dispatch'", text)
        self.assertIn("github.repository == 'webcpporg/webcpp'", text)
        self.assertIn('packages: write', text.split('  verify:', 1)[0])
        self.assertNotIn('packages: write', text.split('  verify:', 1)[1])
        self.assertIn('environment.py verify', text)
        caller = (HERE.parents[1] / '.github/workflows/ci.yml').read_text()
        self.assertIn('inputs.prepare-environment != true', caller)
        self.assertIn('uses: ./.github/workflows/prepare-environments.yml', caller)

    def test_chrome_remains_on_the_official_download_path(self) -> None:
        result = self.run_cli('restore-tool', '--tool', 'chrome', '--variant', 'chrome',
                              '--cache', str(self.cache))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('official', result.stdout)
        self.assertFalse(self.log.exists())
        self.env.update(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='webcpporg/webcpp',
                        WEBCPP_PREPARE_ENVIRONMENT='1', GITHUB_SHA='b' * 40)
        result = self.run_cli('publish', '--tool', 'chrome', '--variant', 'chrome',
                              '--cache', str(self.cache),
                              '--out', str(self.root / 'candidate.json'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not published', result.stderr)
        self.assertFalse(self.log.exists())

    def test_native_publication_smokes_before_push_and_records_digest(self) -> None:
        self.env.update(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='webcpporg/webcpp',
                        WEBCPP_PREPARE_ENVIRONMENT='1', GITHUB_SHA='b' * 40)
        output = self.root / 'candidate.json'
        result = self.run_cli('publish', '--out', str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call[0] for call in self.calls()], ['build', 'run', 'push', 'image'])
        value = json.loads(output.read_text())['artifacts']['native-linux-x64']
        self.assertEqual(value['image'], IMAGE)
        self.assertEqual(value['source'], 'b' * 40)
        self.assertEqual(value['archives'], [])

    def test_failed_smoke_never_pushes(self) -> None:
        self.env.update(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='webcpporg/webcpp',
                        WEBCPP_PREPARE_ENVIRONMENT='1', GITHUB_SHA='b' * 40, RUN_STATUS='1')
        output = self.root / 'candidate.json'
        result = self.run_cli('publish', '--out', str(output))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([call[0] for call in self.calls()], ['build', 'run'])
        self.assertFalse(output.exists())

    def test_verification_pulls_with_empty_credentials_even_when_image_is_cached(self) -> None:
        self.pin('native-linux-x64')
        self.env['IMAGE_PRESENT'] = '1'
        result = self.run_cli('verify', '--candidate',
                              str(self.root / 'tools/ci/environments.json'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call[0] for call in self.calls()], ['pull', 'run'])
        configuration, files = json.loads(Path(str(self.log) + '.config').read_text())
        self.assertEqual(files, [])
        self.assertFalse(Path(configuration).exists())

    def test_archive_cache_is_an_optional_optimization(self) -> None:
        text = (HERE / 'actions/tool-archives/action.yml').read_text()
        for name in ('Restore tool archives', 'Save tool archives'):
            block = text.split('    - name: ' + name + '\n', 1)[1].split('    - name:', 1)[0]
            self.assertIn('continue-on-error: true', block)
        self.assertIn("steps.restore.outputs.cache-hit != 'true'", text)


if __name__ == '__main__':
    unittest.main()
