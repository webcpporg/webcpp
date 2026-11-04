#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Exercises pinned downloads and per-tool archive preparation through the production shell.
Every transfer uses a file URL or loopback HTTP fixture. Paths deliberately contain spaces.
Run with case names to select cases.
"""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

CI = Path(__file__).resolve().parent
DOWNLOAD = CI / 'download.sh'
ARCHIVES = CI / 'actions/tool-archives'
BODY = b'the pinned tool archive\n'
DIGEST = hashlib.sha256(BODY).hexdigest()


def run_download(scratch: Path, url: str, *, cached: bool = True,
                 extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, 'NO_PROXY': '127.0.0.1', 'no_proxy': '127.0.0.1'}
    environment.pop('WEBCPP_DOWNLOAD_CACHE', None)
    environment.pop('WEBCPP_DOWNLOAD_OFFLINE', None)
    if cached:
        environment['WEBCPP_DOWNLOAD_CACHE'] = str(scratch / 'archive cache')
    environment.update(extra_env or {})
    return subprocess.run(['bash', str(DOWNLOAD), url, DIGEST, str(scratch / 'output archive')],
                          capture_output=True, text=True, check=False, env=environment,
                          timeout=30)


def fixture(scratch: Path) -> Path:
    source = scratch / 'source archive'
    source.write_bytes(BODY)
    return source


def cached_file(scratch: Path, body: bytes) -> Path:
    path = scratch / 'archive cache' / DIGEST
    path.parent.mkdir()
    path.write_bytes(body)
    return path


def test_a_cache_miss_publishes_the_archive_by_its_digest(scratch: Path) -> None:
    result = run_download(scratch, fixture(scratch).as_uri())
    assert result.returncode == 0, result.stderr
    assert (scratch / 'output archive').read_bytes() == BODY
    assert (scratch / 'archive cache' / DIGEST).is_file()
    assert (scratch / 'archive cache' / DIGEST).read_bytes() == BODY
    assert sorted(path.name for path in (scratch / 'archive cache').iterdir()) == [DIGEST]


def test_a_cache_hit_works_offline_and_returns_an_independent_copy(scratch: Path) -> None:
    archive = cached_file(scratch, BODY)
    result = run_download(scratch, (scratch / 'offline').as_uri())
    assert result.returncode == 0, result.stderr
    output = scratch / 'output archive'
    assert output.read_bytes() == BODY
    output.write_bytes(b'the installer may modify or remove its input')
    assert archive.read_bytes() == BODY


def test_a_corrupt_cache_entry_is_replaced_from_the_verified_download(scratch: Path) -> None:
    archive = cached_file(scratch, b'corrupt')
    result = run_download(scratch, fixture(scratch).as_uri())
    assert result.returncode == 0, result.stderr
    assert archive.read_bytes() == BODY
    assert (scratch / 'output archive').read_bytes() == BODY


def test_a_corrupt_offline_entry_leaves_neither_cache_nor_output(scratch: Path) -> None:
    archive = cached_file(scratch, b'corrupt')
    output = scratch / 'output archive'
    output.write_bytes(b'an earlier attempt')
    result = run_download(scratch, (scratch / 'offline').as_uri())
    assert result.returncode == 1, result.stderr
    assert not archive.exists()
    assert not output.exists()
    assert not list(scratch.glob('output archive.*'))
    assert not list(archive.parent.iterdir())


class PartialServer:
    """Pauses after a partial HTTP body, then drops every transfer before Content-Length."""

    def __init__(self) -> None:
        self.partial = threading.Event()
        self.release = threading.Event()
        self.stopped = threading.Event()
        self.listener = socket.create_server(('127.0.0.1', 0))
        self.listener.settimeout(0.1)
        self.address = self.listener.getsockname()
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f'http://127.0.0.1:{self.address[1]}/archive'

    def serve(self) -> None:
        while not self.stopped.is_set():
            try:
                connection, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with connection:
                connection.settimeout(5)
                connection.recv(65536)
                connection.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 1000000\r\n'
                                   b'Connection: close\r\n\r\n' + b'x' * 65536)
                self.partial.set()
                self.release.wait(5)

    def close(self) -> None:
        self.stopped.set()
        self.release.set()
        self.listener.close()
        self.thread.join(timeout=5)
        assert not self.thread.is_alive()


def test_a_failed_transfer_never_exposes_partial_output_or_cache(scratch: Path) -> None:
    server = PartialServer()
    output = scratch / 'output archive'
    cache = scratch / 'archive cache'
    environment = {**os.environ, 'WEBCPP_DOWNLOAD_CACHE': str(cache),
                   'WEBCPP_DOWNLOAD_OFFLINE': '', 'NO_PROXY': '127.0.0.1', 'no_proxy': '127.0.0.1'}
    process = subprocess.Popen(['bash', str(DOWNLOAD), server.url, DIGEST, str(output)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               env=environment, start_new_session=os.name != 'nt')
    try:
        assert server.partial.wait(10), 'curl did not reach the local HTTP fixture'
        deadline = time.monotonic() + 5
        while not any(path.stat().st_size for path in scratch.glob('output archive*')):
            assert time.monotonic() < deadline, 'curl did not start writing the fixture'
            time.sleep(0.01)
        assert not output.exists(), 'an unfinished download was visible at its final path'
        assert not (cache / DIGEST).exists(), 'an unfinished archive entered the cache'
        server.release.set()
        _, error = process.communicate(timeout=30)
        assert process.returncode == 1, error
        assert not output.exists()
        assert not list(scratch.glob('output archive.*'))
        assert cache.is_dir()
        assert not list(cache.iterdir())
    finally:
        server.close()
        if process.poll() is None:
            if os.name == 'nt':
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
        process.communicate(timeout=5)


def test_a_download_bounds_connections_transfers_and_retries(scratch: Path) -> None:
    # Wrap real curl only to observe its arguments; it still transfers the fixture's bytes.
    curl = shutil.which('curl')
    assert curl is not None
    programs = scratch / 'programs'
    programs.mkdir()
    arguments = scratch / 'curl arguments'
    wrapper = programs / 'curl'
    wrapper.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CURL_ARGUMENTS"\n'
                       f'exec {shlex.quote(curl)} "$@"\n')
    wrapper.chmod(0o755)
    result = run_download(scratch, fixture(scratch).as_uri(), extra_env={
        'PATH': f'{programs}{os.pathsep}{os.environ["PATH"]}',
        'CURL_ARGUMENTS': str(arguments),
    })
    assert result.returncode == 0, result.stderr
    words = arguments.read_text().splitlines()
    for option, upper_bound in (('--connect-timeout', 60), ('--max-time', 900),
                                ('--retry-max-time', 1800), ('--retry', 5)):
        assert option in words, f'curl has no {option} bound: {words}'
        assert 0 < int(words[words.index(option) + 1]) <= upper_bound
    assert '--retry-all-errors' in words
    assert (scratch / 'output archive').read_bytes() == BODY


def test_a_wrong_download_digest_never_enters_the_cache(scratch: Path) -> None:
    source = fixture(scratch)
    source.write_bytes(b'not the pinned bytes')
    result = run_download(scratch, source.as_uri())
    assert result.returncode == 1, result.stderr
    assert not (scratch / 'output archive').exists()
    assert (scratch / 'archive cache').is_dir()
    assert not list((scratch / 'archive cache').iterdir())
    assert not list(scratch.glob('output archive.*'))


def test_uncached_downloads_keep_their_original_contract(scratch: Path) -> None:
    source = fixture(scratch)
    result = run_download(scratch, source.as_uri(), cached=False)
    assert result.returncode == 0, result.stderr
    assert (scratch / 'output archive').read_bytes() == BODY
    source.unlink()
    result = run_download(scratch, source.as_uri(), cached=False)
    assert result.returncode == 1, result.stderr
    assert not (scratch / 'output archive').exists()
    assert not (scratch / 'archive cache').exists()
    assert not list(scratch.glob('output archive.*'))


def test_offline_mode_rejects_missing_and_corrupt_entries_without_curl(scratch: Path) -> None:
    source = fixture(scratch)
    programs = scratch / 'programs'
    programs.mkdir()
    called = scratch / 'curl was called'
    wrapper = programs / 'curl'
    wrapper.write_text('#!/bin/sh\nprintf called > "$CURL_CALLED"\nexit 99\n')
    wrapper.chmod(0o755)
    environment = {'WEBCPP_DOWNLOAD_OFFLINE': '1', 'CURL_CALLED': str(called),
                   'PATH': f'{programs}{os.pathsep}{os.environ["PATH"]}'}
    for contents in (None, b'corrupt'):
        cache = scratch / 'archive cache'
        cache.mkdir(exist_ok=True)
        if contents is not None:
            (cache / DIGEST).write_bytes(contents)
        result = run_download(scratch, source.as_uri(), extra_env=environment)
        assert result.returncode == 1, result.stderr
        assert not called.exists(), 'offline mode invoked curl'
        assert 'offline' in result.stderr.lower(), result.stderr
        assert not (scratch / 'output archive').exists()
        assert not list(cache.iterdir())
    (cache / DIGEST).write_bytes(BODY)
    result = run_download(scratch, source.as_uri(), extra_env=environment)
    assert result.returncode == 0, result.stderr
    assert (scratch / 'output archive').read_bytes() == BODY
    assert not called.exists()


def action_tree(scratch: Path) -> None:
    assert (ARCHIVES / 'cache.sh').is_file(), 'shared archive preparation helper is missing'
    directory = scratch / 'tools/ci'
    shutil.copytree(ARCHIVES, directory / 'actions/tool-archives')
    for name in ('download.sh', 'helpers.sh'):
        shutil.copy2(CI / name, directory / name)
    (directory / 'environments.json').write_text('{"fixture": 1}\n')
    for tool in ('wasi-sdk', 'wasmtime', 'wit-bindgen', 'wasi-wit', 'mrdocs', 'chrome'):
        action = directory / 'actions' / tool
        action.mkdir()
        (action / 'action.yml').write_text(f'name: {tool}\n')
        (action / 'install.sh').write_text(
            '#!/bin/bash\nset -euo pipefail\n'
            'bash tools/ci/download.sh "$ARCHIVE_URL" "$ARCHIVE_DIGEST" "$RUNNER_TEMP/input"\n'
            'printf "%s\\n" "$WEBCPP_DOWNLOAD_CACHE" >> "$GITHUB_PATH"\n'
            'printf "PRODUCT=%s\\n" "${WEBCPP_CHROME_PRODUCT-}" >> "$GITHUB_ENV"\n'
            'rm "$RUNNER_TEMP/input"\n')


def run_action(scratch: Path, operation: str, tool: str, variant: str = '',
               **variables: str) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, 'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64',
                   'RUNNER_TEMP': str(scratch), 'GITHUB_PATH': str(scratch / 'github-path'),
                   'GITHUB_ENV': str(scratch / 'github-env'),
                   'GITHUB_OUTPUT': str(scratch / 'github-output'),
                   'WEBCPP_PREPARE_ENVIRONMENT': ''}
    environment.pop('WEBCPP_DOWNLOAD_OFFLINE', None)
    environment.update(variables)
    return subprocess.run(['bash', 'tools/ci/actions/tool-archives/cache.sh', operation,
                           tool, variant], cwd=scratch, capture_output=True, text=True,
                          check=False, env=environment, timeout=30)


def cache_outputs(scratch: Path, tool: str, variant: str = '', **variables: str) -> dict[str, str]:
    (scratch / 'github-output').write_text('')
    result = run_action(scratch, 'key', tool, variant, **variables)
    assert result.returncode == 0, result.stderr
    return dict(line.split('=', 1) for line in (scratch / 'github-output').read_text().splitlines())


def test_tool_keys_track_pins_platform_variant_and_bundle_manifest(scratch: Path) -> None:
    action_tree(scratch)
    original = cache_outputs(scratch, 'wasmtime')
    assert original == cache_outputs(scratch, 'wasmtime')
    assert original['directory'] != cache_outputs(scratch, 'wasi-sdk')['directory']
    assert original['key'] != cache_outputs(scratch, 'wasmtime', RUNNER_OS='macOS')['key']
    assert original['key'] != cache_outputs(scratch, 'wasmtime', RUNNER_ARCH='ARM64')['key']
    shell = cache_outputs(scratch, 'chrome', 'chrome-headless-shell')
    chrome = cache_outputs(scratch, 'chrome', 'chrome')
    assert shell['key'] != chrome['key'] and shell['directory'] != chrome['directory']
    other = scratch / 'tools/ci/actions/wasi-sdk/install.sh'
    other.write_text(other.read_text() + '# an unrelated tool changed\n')
    assert original == cache_outputs(scratch, 'wasmtime')
    installer = scratch / 'tools/ci/actions/wasmtime/install.sh'
    installer.write_text(installer.read_text() + '# the pinned tool changed\n')
    revised = cache_outputs(scratch, 'wasmtime')
    assert original['key'] != revised['key']
    (scratch / 'tools/ci/environments.json').write_text('{"fixture": 2}\n')
    assert revised['key'] != cache_outputs(scratch, 'wasmtime')['key']


def test_the_installer_runs_and_exports_its_environment_on_cache_hits(scratch: Path) -> None:
    action_tree(scratch)
    source = fixture(scratch)
    variables = {'ARCHIVE_URL': source.as_uri(), 'ARCHIVE_DIGEST': DIGEST}
    for tool, variant in (('wasmtime', ''), ('chrome', 'chrome')):
        source.write_bytes(BODY)
        outputs = cache_outputs(scratch, tool, variant)
        for offline in (False, True):
            if offline:
                source.unlink()
            for output in ('github-path', 'github-env'):
                (scratch / output).write_text('')
            result = run_action(scratch, 'install', tool, variant, **variables,
                                WEBCPP_PREPARE_ENVIRONMENT='0' if offline else '1')
            assert result.returncode == 0, result.stderr
            assert (Path(outputs['directory']) / DIGEST).read_bytes() == BODY
            assert (scratch / 'github-path').read_text() == outputs['directory'] + '\n'
            assert (scratch / 'github-env').read_text() == f'PRODUCT={variant}\n'
            assert not (scratch / 'input').exists()


def test_linux_consumers_require_prepared_archives(scratch: Path) -> None:
    for state in ('missing', 'corrupt'):
        root = scratch / state
        action_tree(root)
        source = fixture(root)
        outputs = cache_outputs(root, 'wasmtime')
        cache = Path(outputs['directory'])
        if state == 'corrupt':
            cache.mkdir(parents=True)
            (cache / DIGEST).write_bytes(b'corrupt')
        result = run_action(root, 'install', 'wasmtime', ARCHIVE_URL=source.as_uri(),
                            ARCHIVE_DIGEST=DIGEST)
        assert result.returncode == 1, result.stderr
        assert 'offline' in result.stderr.lower(), result.stderr
        assert not (root / 'github-path').exists()
        assert not list(cache.iterdir())


def test_other_hosts_can_download_their_own_pinned_archives(scratch: Path) -> None:
    action_tree(scratch)
    source = fixture(scratch)
    result = run_action(scratch, 'install', 'wasmtime', RUNNER_OS='macOS', RUNNER_ARCH='ARM64',
                        ARCHIVE_URL=source.as_uri(), ARCHIVE_DIGEST=DIGEST)
    assert result.returncode == 0, result.stderr
    outputs = cache_outputs(scratch, 'wasmtime', RUNNER_OS='macOS', RUNNER_ARCH='ARM64')
    assert (Path(outputs['directory']) / DIGEST).read_bytes() == BODY


def test_unknown_tools_and_unsafe_variants_are_rejected(scratch: Path) -> None:
    action_tree(scratch)
    for tool, variant in (('../wasmtime', ''), ('unknown', ''), ('wasmtime', 'chrome'),
                          ('chrome', '../chrome'), ('chrome', '')):
        result = run_action(scratch, 'key', tool, variant)
        assert result.returncode == 2, (tool, variant, result.stderr)
        assert not (scratch / 'github-output').exists()
        assert not (scratch / '.local').exists()


CASES: list[Callable[[Path], None]] = [
    test_a_cache_miss_publishes_the_archive_by_its_digest,
    test_a_cache_hit_works_offline_and_returns_an_independent_copy,
    test_a_corrupt_cache_entry_is_replaced_from_the_verified_download,
    test_a_corrupt_offline_entry_leaves_neither_cache_nor_output,
    test_a_failed_transfer_never_exposes_partial_output_or_cache,
    test_a_download_bounds_connections_transfers_and_retries,
    test_a_wrong_download_digest_never_enters_the_cache,
    test_uncached_downloads_keep_their_original_contract,
    test_offline_mode_rejects_missing_and_corrupt_entries_without_curl,
    test_tool_keys_track_pins_platform_variant_and_bundle_manifest,
    test_the_installer_runs_and_exports_its_environment_on_cache_hits,
    test_linux_consumers_require_prepared_archives,
    test_other_hosts_can_download_their_own_pinned_archives,
    test_unknown_tools_and_unsafe_variants_are_rejected,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'download_cache_test: unknown cases: {", ".join(sorted(unknown))}', file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp archive cache ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('download_cache_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
