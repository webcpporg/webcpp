#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Prepare and consume immutable Linux-X64 CI images and tool archives.

Normal jobs only pull checked digests. The explicit preparation workflow builds
candidates, verifies them with anonymous registry access, and emits a manifest
for review. Tool images hold archives only; restoration never executes them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[2]
PINS = ROOT / 'tools/ci/environments.json'
PACKAGE = 'ghcr.io/webcpporg/ci-environment'
HEX = re.compile(r'[0-9a-f]{64}')
IMAGE = re.compile(re.escape(PACKAGE) + r'@sha256:[0-9a-f]{64}')
TOOLS = ('wasi-sdk', 'wasmtime', 'wit-bindgen', 'wasi-wit', 'mrdocs', 'chrome')
PREPARE = 'run the trusted prepare-environments workflow and promote its verified manifest'


class Failure(Exception):
    """A missing, stale or unusable prepared environment."""


class Artifact(TypedDict):
    image: str
    recipe: str
    archives: list[str]
    source: str


def identity(tool: str = '', variant: str = '') -> str:
    """The manifest key, restricted to the supported Linux-X64 artifacts."""
    if tool not in ('', *TOOLS) or (tool != 'chrome' and variant) or (
            tool == 'chrome' and variant not in ('chrome', 'chrome-headless-shell')):
        raise Failure(f'unsupported tool/variant: {tool!r}/{variant!r}')
    return '-'.join(part for part in (tool or 'native', variant, 'linux-x64') if part)


def digest(path: Path) -> str:
    """SHA-256 of a file, streamed so SDK archives need no matching RAM allocation."""
    value = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def recipe(tool: str = '', variant: str = '') -> str:
    """Bind the artifact to its recipe and platform, excluding the output manifest."""
    key = identity(tool, variant)
    paths = ['tools/ci/container/Dockerfile'] if not tool else [
        f'tools/ci/actions/{tool}/install.sh', 'tools/ci/download.sh',
        'tools/ci/helpers.sh']
    inputs = [(name, digest(ROOT / name)) for name in paths]
    return hashlib.sha256(json.dumps([1, key, inputs], separators=(',', ':')).encode()).hexdigest()


def checked(value: object, tool: str = '', variant: str = '') -> Artifact:
    """Reject mutable names, stale recipes and malformed manifests before Docker runs."""
    if not isinstance(value, dict) or not isinstance(value.get('image'), str) or not (
            IMAGE.fullmatch(value['image'])):
        raise Failure(f'invalid immutable image for {identity(tool, variant)}; {PREPARE}')
    if value.get('recipe') != recipe(tool, variant):
        raise Failure(f'stale recipe for {identity(tool, variant)}; {PREPARE}')
    archives = value.get('archives')
    if (not isinstance(archives, list) or any(not isinstance(item, str) or not HEX.fullmatch(item)
                                            for item in archives)
            or len(set(archives)) != len(archives) or bool(archives) != bool(tool)):
        raise Failure('invalid archive hashes in prepared environment')
    source = value.get('source')
    if not isinstance(source, str) or re.fullmatch(r'[0-9a-f]{40}', source) is None:
        raise Failure('prepared environment lacks its source commit')
    return {'image': value['image'], 'recipe': value['recipe'], 'archives': archives,
            'source': source}


def pinned(tool: str = '', variant: str = '') -> Artifact:
    """Read and validate the selected artifact; a missing pin never triggers a build."""
    try:
        document = json.loads(PINS.read_text())
        if document['schema'] != 1:
            raise ValueError('unsupported manifest schema')
        return checked(document['artifacts'][identity(tool, variant)], tool, variant)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise Failure(f'no usable prepared environment in {PINS}: {error}; {PREPARE}') from error


def docker(*arguments: str, capture: bool = False) -> subprocess.CompletedProcess:
    """Run Docker with a finite bound and preserve its diagnostic on failure."""
    return subprocess.run(['docker', *arguments], cwd=ROOT, check=False, text=True,
                          capture_output=capture, timeout=1200)


def require(*arguments: str) -> None:
    if docker(*arguments).returncode:
        raise Failure(f'docker {arguments[0]} failed; {PREPARE}')


def acquire(artifact: Artifact) -> str:
    """Pull an absent immutable reference, never a mutable tag or a local build."""
    image = artifact['image']
    if docker('image', 'inspect', image, capture=True).returncode:
        require('pull', image)
    return image


def native() -> str:
    """The checked image for the two native container lanes."""
    return acquire(pinned())


def verify_archives(directory: Path, expected: list[str]) -> None:
    """Validate the complete set before exposing any bundle file to an installer."""
    if sorted(path.name for path in directory.iterdir()) != sorted(expected):
        raise Failure('prepared bundle has missing or unexpected archives')
    for name in expected:
        path = directory / name
        if path.is_symlink() or not path.is_file() or digest(path) != name:
            raise Failure(f'prepared bundle SHA-256 mismatch or non-regular file: {name}')


def restore(artifact: Artifact, cache: Path) -> None:
    """Copy a stopped image's archives, validate all of them, then install atomically."""
    image = acquire(artifact)
    created = docker('create', image, '/unused', capture=True)
    if created.returncode:
        raise Failure(f'cannot create archive container: {created.stderr}')
    container = created.stdout.strip()
    if re.fullmatch(r'[a-zA-Z0-9_-]+', container) is None:
        raise Failure('docker create returned no container identifier')
    try:
        with tempfile.TemporaryDirectory(prefix='webcpp-archives-') as temporary:
            stage = Path(temporary)
            require('cp', f'{container}:/archives/.', str(stage))
            verify_archives(stage, artifact['archives'])
            cache.mkdir(parents=True, exist_ok=True)
            for name in artifact['archives']:
                with tempfile.NamedTemporaryFile(dir=cache, prefix='.prepared-', delete=False) as f:
                    pending = Path(f.name)
                try:
                    shutil.copyfile(stage / name, pending)
                    os.replace(pending, cache / name)
                finally:
                    pending.unlink(missing_ok=True)
    finally:
        require('rm', '-f', container)


def restore_tool(tool: str, variant: str, cache: Path) -> None:
    identity(tool, variant)
    if tool == 'chrome':
        print('environment: Chrome uses its official download and verified archive cache')
        return
    host = (os.environ.get('RUNNER_OS'), os.environ.get('RUNNER_ARCH'))
    if host != ('Linux', 'X64'):
        print(f'environment: {host} has no published bundle; using checked upstream downloads')
        return
    restore(pinned(tool, variant), cache)


def write_manifest(path: Path, artifacts: dict[str, Artifact]) -> None:
    """Write a generated pin manifest with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {'_comment': 'Generated by tools/ci/environment.py; do not edit.',
                'schema': 1, 'artifacts': artifacts}
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + '\n')


def smoke_native(image: str) -> None:
    """Compile and run C++20 with both pinned compilers inside the isolated image."""
    require('run', '--rm', '--network', 'none', image, 'bash', '-euc',
            'printf "%s\\n" "#include <concepts>" '
            '"static_assert(std::same_as<int, int>); int main() {}" > /tmp/smoke.cpp; '
            'for cc in g++-14 clang++-18; do '
            '$cc --version; $cc -std=c++20 /tmp/smoke.cpp -o /tmp/smoke; /tmp/smoke; done; '
            'python3 --version; cmake --version; perl -v')


def publish(tool: str, variant: str, cache: Path | None, output: Path) -> None:
    """Publish only from an explicitly dispatched organization preparation workflow."""
    if (os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
            or os.environ.get('GITHUB_REPOSITORY') != 'webcpporg/webcpp'
            or os.environ.get('WEBCPP_PREPARE_ENVIRONMENT') != '1'):
        raise Failure('publication requires a trusted workflow_dispatch in webcpporg/webcpp')
    if tool == 'chrome':
        raise Failure('Chrome binaries are not published; use the official download cache')
    source = os.environ.get('GITHUB_SHA', '')
    if re.fullmatch(r'[0-9a-f]{40}', source) is None:
        raise Failure('publication requires GITHUB_SHA of the reviewed source')
    key = identity(tool, variant)
    fingerprint = recipe(tool, variant)
    tag = f'{PACKAGE}:{key}-{fingerprint}'
    archives: list[str] = []
    labels = ['--label', 'org.opencontainers.image.source=https://github.com/webcpporg/webcpp',
              '--label', f'org.opencontainers.image.revision={source}']
    if tool:
        if cache is None:
            raise Failure('tool publication requires --cache')
        archives = sorted(path.name for path in cache.iterdir())
        if not archives or any(HEX.fullmatch(name) is None for name in archives):
            raise Failure('tool cache must contain only SHA-256 named archives')
        verify_archives(cache, archives)
        with tempfile.TemporaryDirectory(prefix='webcpp-bundle-') as temporary:
            context = Path(temporary)
            shutil.copytree(cache, context / 'archives')
            (context / 'Dockerfile').write_text('FROM scratch\nCOPY archives/ /archives/\n')
            require('build', '--platform', 'linux/amd64', *labels, '--tag', tag, str(context))
    else:
        require('build', '--platform', 'linux/amd64', *labels, '--tag', tag,
                str(ROOT / 'tools/ci/container'))
        smoke_native(tag)
    require('push', tag)
    result = docker('image', 'inspect', '--format', '{{json .RepoDigests}}', tag, capture=True)
    if result.returncode:
        raise Failure(f'cannot inspect pushed digest: {result.stderr}')
    images = json.loads(result.stdout)
    references = [image for image in images if isinstance(image, str) and IMAGE.fullmatch(image)]
    if len(references) != 1:
        raise Failure('publication did not resolve to one immutable package digest')
    artifact: Artifact = {'image': references[0], 'recipe': fingerprint,
                          'archives': archives, 'source': source}
    write_manifest(output, {key: checked(artifact, tool, variant)})


def verify_candidate(candidate: Path, tool: str, variant: str, cache: Path | None) -> None:
    """Prove anonymous pull and offline installation before promoting a candidate."""
    document = json.loads(candidate.read_text())
    artifact = checked(document['artifacts'][identity(tool, variant)], tool, variant)
    previous = os.environ.get('DOCKER_CONFIG')
    try:
        with tempfile.TemporaryDirectory(prefix='webcpp-anonymous-') as temporary:
            os.environ['DOCKER_CONFIG'] = temporary
            # Always contact the registry, even if an image is already in the daemon cache.
            require('pull', artifact['image'])
            if tool:
                if cache is None:
                    raise Failure('tool verification requires --cache')
                restore(artifact, cache)
                installer_env = {**os.environ, 'WEBCPP_DOWNLOAD_CACHE': str(cache.resolve()),
                                 'WEBCPP_DOWNLOAD_OFFLINE': '1', 'WEBCPP_CHROME_PRODUCT': variant}
                result = subprocess.run(['bash', f'tools/ci/actions/{tool}/install.sh'],
                                        cwd=ROOT, env=installer_env, check=False, timeout=600)
                if result.returncode:
                    raise Failure(f'offline installation failed for {tool}/{variant}')
            else:
                smoke_native(artifact['image'])
    finally:
        if previous is None:
            os.environ.pop('DOCKER_CONFIG', None)
        else:
            os.environ['DOCKER_CONFIG'] = previous


def merge(directory: Path, output: Path) -> None:
    """Assemble the complete verified workflow artifacts; never invent missing pins."""
    selections = [('', ''), *((tool, '') for tool in TOOLS if tool != 'chrome')]
    expected = {identity(tool, variant): (tool, variant) for tool, variant in selections}
    artifacts: dict[str, Artifact] = {}
    for path in sorted(directory.glob('*.json')):
        document = json.loads(path.read_text())
        if document.get('schema') != 1:
            raise Failure(f'unsupported manifest schema: {path}')
        for key, value in document['artifacts'].items():
            if key not in expected or key in artifacts:
                raise Failure(f'unexpected or duplicate environment: {key}')
            artifacts[key] = checked(value, *expected[key])
    missing = sorted(expected.keys() - artifacts.keys())
    if missing:
        raise Failure('missing prepared environments: ' + ', '.join(missing))
    write_manifest(output, artifacts)


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',
                        choices=('recipe', 'native', 'restore-tool', 'publish', 'verify', 'merge'))
    parser.add_argument('--tool', default='')
    parser.add_argument('--variant', default='')
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args(arguments)
    try:
        if args.command == 'recipe':
            print(recipe(args.tool, args.variant))
        elif args.command == 'native':
            print(native())
        elif args.command == 'restore-tool':
            if not args.tool or args.cache is None:
                raise Failure('restore-tool requires --tool and --cache')
            restore_tool(args.tool, args.variant, args.cache)
        elif args.command == 'publish':
            if args.out is None:
                raise Failure('publish requires --out')
            publish(args.tool, args.variant, args.cache, args.out)
        elif args.command == 'verify':
            if args.candidate is None:
                raise Failure('verify requires --candidate')
            verify_candidate(args.candidate, args.tool, args.variant, args.cache)
        elif args.command == 'merge':
            if args.directory is None or args.out is None:
                raise Failure('merge requires --directory and --out')
            merge(args.directory, args.out)
        return 0
    except (Failure, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(f'environment.py: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
