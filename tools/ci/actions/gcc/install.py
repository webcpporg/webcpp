#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Install the corrected GCC 15 toolchain without changing host packages.

The official image is fixed at its Linux-X64 manifest digest. Only /usr/local
is extracted; GCC is relocatable. Ubuntu 26.04 provides its glibc dependencies.
The runtime library path follows the compiler, including after a cache restore.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
IMAGE = 'gcc@sha256:3a49295e08ff62055af03114fd1162403c7613f91b18b10da72b352ed9ea375b'
VERSION = '15.3.0'


class Failure(Exception):
    """An unsupported host, untrusted directory or unusable compiler."""


def run(command: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(command, env=env, text=True, capture_output=True,
                            check=False, timeout=600)
    if result.returncode:
        raise Failure(f'{command[0]} failed:\n{result.stdout}{result.stderr}')
    return result.stdout


def runtime(prefix: Path) -> dict[str, str]:
    previous = os.environ.get('LD_LIBRARY_PATH', '')
    search = str(prefix / 'lib64') + (':' + previous if previous else '')
    return {**os.environ, 'LD_LIBRARY_PATH': search}


def verify(prefix: Path) -> None:
    """Reject a stale compiler or the PR121643 await_suspend regression."""
    env = runtime(prefix)
    compiler = str(prefix / 'bin/g++-15')
    version = run([compiler, '-dumpfullversion'], env=env).strip()
    if version != VERSION:
        raise Failure(f'expected GCC {VERSION}, found {version}')
    with tempfile.TemporaryDirectory(prefix='webcpp-gcc-probe-') as temporary:
        executable = str(Path(temporary) / 'probe')
        run([compiler, '-std=c++20', '-O0', '-Wall', '-Wextra', '-Werror',
             str(Path(__file__).with_name('coroutine_probe.cpp')), '-o', executable], env=env)
        run([executable], env=env)


def prepare(prefix: Path) -> None:
    """Install atomically, preserving an existing directory that is not ours."""
    marker = prefix / '.webcpp-image'
    if prefix.is_symlink():
        raise Failure(f'refusing a symlink compiler prefix: {prefix}')
    if prefix.exists():
        if not marker.is_file() or marker.read_text().strip() != IMAGE:
            raise Failure(f'refusing an unrecognized compiler directory: {prefix}')
        verify(prefix)
        return
    prefix.parent.mkdir(parents=True, exist_ok=True)
    run(['docker', 'pull', '--platform', 'linux/amd64', IMAGE])
    container = run(['docker', 'create', '--platform', 'linux/amd64', IMAGE, '/bin/true']).strip()
    if re.fullmatch(r'[0-9a-f]{12,64}', container) is None:
        raise Failure('docker create did not return a container ID')
    try:
        with tempfile.TemporaryDirectory(dir=prefix.parent, prefix='.gcc-stage-') as temporary:
            stage = Path(temporary) / 'compiler'
            stage.mkdir()
            run(['docker', 'cp', f'{container}:/usr/local/.', str(stage)])
            for name in ('gcc', 'g++'):
                (stage / 'bin' / (name + '-15')).symlink_to(name)
            verify(stage)
            (stage / '.webcpp-image').write_text(IMAGE + '\n')
            stage.rename(prefix)
    finally:
        run(['docker', 'rm', '-f', container])
    verify(prefix)


def install() -> None:
    if (os.environ.get('RUNNER_OS'), os.environ.get('RUNNER_ARCH')) != ('Linux', 'X64'):
        raise Failure('the pinned GCC toolchain requires Linux-X64')
    prefix = ROOT / '.local/gcc-15.3.0'
    prepare(prefix)
    with Path(os.environ['GITHUB_PATH']).open('a') as output:
        output.write(str(prefix / 'bin') + '\n')
    with Path(os.environ['GITHUB_ENV']).open('a') as output:
        output.write('LD_LIBRARY_PATH=' + runtime(prefix)['LD_LIBRARY_PATH'] + '\n')
    print(f'GCC {VERSION}: coroutine compile/run probe passed; {prefix}')


if __name__ == '__main__':
    try:
        install()
    except (Failure, OSError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error)) from error
