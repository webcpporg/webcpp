#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks that libs/hash/bench/collect.py, which measures bench/pbkdf2_sha512 and renders
doc/performance.adoc, builds its table only from release builds: a program whose build directory,
b2's bench/<toolset>/<variant>/..., names another variant, or does not say, is refused before
anything runs or is written; one at variant=release is taken (it gets as far as running); and
`--render-only` refuses data whose build is not variant=release, before it writes the page. Run
with the names of some cases to run only those."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLLECT = ROOT / 'libs/hash/bench/collect.py'


def run(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(COLLECT), *map(str, args)], cwd=ROOT,
                          capture_output=True, text=True, check=False, timeout=120)


def program(scratch: Path, variant: str) -> Path:
    """A stand-in of bench/pbkdf2_sha512 where b2 builds it at variant, which fails when run."""
    path = (scratch / 'bin/libs/hash/bench/clang-darwin-21' / variant
            / 'cxxstd-20-iso/optimization-speed/pbkdf2_sha512')
    path.parent.mkdir(parents=True)
    path.write_text('#!/bin/sh\necho "the stand-in ran" >&2\nexit 3\n')
    path.chmod(0o755)
    return path


def expect(done: subprocess.CompletedProcess[str], status: int, *texts: str) -> None:
    if done.returncode != status:
        raise AssertionError(f'exit {done.returncode}, not {status}\n{done.stdout}{done.stderr}')
    for text in texts:
        if text not in done.stderr:
            raise AssertionError(f'{text!r} is not in the error:\n{done.stderr}')


def test_a_program_not_built_at_variant_release_is_refused(scratch: Path) -> None:
    data, page = scratch / 'data.json', scratch / 'page.adoc'
    for variant in ('debug', 'profile'):
        exe = program(scratch / variant, variant)
        done = run('--exe', f'native={exe}', '--data', data, '--page', page)
        expect(done, 1, f'native={exe} was built at variant={variant}',
               'only from release builds')
        if 'the stand-in ran' in done.stderr or data.exists() or page.exists():
            raise AssertionError(f'{variant}: the program ran or a file was written')
    stray = scratch / 'stray/pbkdf2_sha512'
    stray.parent.mkdir()
    stray.write_text('')
    done = run('--exe', f'wasip2={stray}', '--data', data, '--page', page)
    expect(done, 1, f'wasip2={stray}', 'bench/<toolset>/<variant>', 'only from release builds')


def test_a_program_built_at_variant_release_is_measured(scratch: Path) -> None:
    exe = program(scratch, 'release')
    done = run('--exe', f'native={exe}', '--data', scratch / 'data.json', '--page',
               scratch / 'page.adoc')
    # Past the check, collect.py runs it, and stops on its failure.
    expect(done, 1, 'native: --list exit 3', 'the stand-in ran')


def test_render_only_refuses_data_not_built_at_variant_release(scratch: Path) -> None:
    committed = json.loads((ROOT / 'libs/hash/doc/measurements.throughput.json').read_text())
    page = scratch / 'page.adoc'
    for build in ('variant=debug optimization=speed', None):
        data = dict(committed)
        if build is None:
            del data['build']
        else:
            data['build'] = build
        path = scratch / 'data.json'
        path.write_text(json.dumps(data))
        done = run('--render-only', '--data', path, '--page', page)
        expect(done, 1, 'only from release builds')
        if page.exists():
            raise AssertionError(f'{build}: the page was written')
    path = scratch / 'data.json'
    path.write_text(json.dumps(committed))
    expect(run('--render-only', '--data', path, '--page', page), 0)
    if page.read_text() != (ROOT / 'libs/hash/doc/performance.adoc').read_text():
        raise AssertionError('the committed data does not render the committed page')


CASES: list[Callable[[Path], None]] = [
    test_a_program_not_built_at_variant_release_is_refused,
    test_a_program_built_at_variant_release_is_measured,
    test_render_only_refuses_data_not_built_at_variant_release,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'hash_collect_test: no case named {", ".join(sorted(unknown))}', file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp hash collect ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('hash_collect_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
