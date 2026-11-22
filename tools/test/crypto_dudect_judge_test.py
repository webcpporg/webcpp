#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks libs/crypto/test/constant_time/dudect_judge.py, the CI's judge of dudect's outputs, with
scratch outputs and fake programs: it prints each output in a group and warns for every case whose
|t| is 10 or more, the planted program and the harness's test excepted; with --rerun it measures
each judged case over 10 again in two fresh processes and fails exactly when two of the three
values are 10 or more, naming them; it never reruns a case that is not judged; it refuses an
output with no case line; and on wasip2 it runs the program through the launcher. Run with the
names of some cases to run only those."""

from __future__ import annotations

import shlex
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JUDGE = ROOT / 'libs/crypto/test/constant_time/dudect_judge.py'

FAKE = '''#!/usr/bin/env python3
import sys
from pathlib import Path
answers = {answers!r}
counter = Path(sys.argv[0] + '.count')
done = int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(done + 1))
assert sys.argv[1:] == ['--case', {case!r}], sys.argv
print('dudect case={case} t=' + answers[done] + ' threshold=10 judged=yes')
'''

LAUNCHER = '''#!/usr/bin/env python3
import sys
from pathlib import Path
Path({log!r}).write_text(' '.join(sys.argv[1:]))
print('dudect case={case} t=1.00 threshold=10 judged=yes')
'''


def run_judge(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(JUDGE), *args], capture_output=True, text=True,
                          check=False, timeout=120)


def write_output(directory: Path, name: str, text: str, suffix: str = '') -> Path:
    """bin/<build directory>/<name>.output holding text and the lane's exit line."""
    where = directory / f'{name}.test/clang/release{suffix}'
    where.mkdir(parents=True, exist_ok=True)
    (where / f'{name}.output').write_text(text + '\nEXIT STATUS: 0\n')
    return where


def write_script(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(0o755)


def write_fake_program(path: Path, answers: list[str], case: str) -> None:
    write_script(path, FAKE.format(answers=answers, case=case))


BEARSSL = ('dudect case=chacha_open t=69.80 threshold=10 judged=yes\n'
           'dudect evidence case=chacha_open crop=1 limit_ns=9.00 class0_n=5 class0_mean_ns=3.00 '
           'class1_n=6 class1_mean_ns=4.00\n'
           'dudect case=equal t=3.10 threshold=10 judged=yes\n')


def expect(done: subprocess.CompletedProcess[str], status: int) -> None:
    if done.returncode != status:
        raise AssertionError(f'exit {done.returncode}, not {status}\n{done.stdout}{done.stderr}')


def judge_prints_and_warns(scratch: Path) -> None:
    write_output(scratch, 'dudect_bearssl', BEARSSL)
    done = run_judge('--bin', str(scratch), '--target', 'native')
    expect(done, 0)
    for text in ('::group::dudect_bearssl (native)\n', BEARSSL, '::endgroup::\n'):
        assert text in done.stdout, done.stdout
    warnings = [line for line in done.stdout.splitlines() if line.startswith('::warning')]
    assert len(warnings) == 1, done.stdout
    assert warnings[0].startswith('::warning title=dudect dudect_bearssl chacha_open (native)::'
                                  'dudect case=chacha_open t=69.80 '), warnings
    assert 'dudect evidence case=chacha_open' in warnings[0], warnings


def judge_two_of_three_pass(scratch: Path) -> None:
    directory = write_output(scratch, 'dudect_bearssl', BEARSSL)
    write_fake_program(directory / 'dudect_bearssl', ['3.10', '2.70'], 'chacha_open')
    done = run_judge('--bin', str(scratch), '--target', 'native', '--rerun')
    expect(done, 0)
    assert '69.80, 3.10, 2.70' in done.stdout, done.stdout


def judge_two_of_three_fail(scratch: Path) -> None:
    directory = write_output(scratch, 'dudect_bearssl',
                             'dudect case=equal t=14.00 threshold=10 judged=yes\n')
    write_fake_program(directory / 'dudect_bearssl', answers=['12.50', '3.00'], case='equal')
    done = run_judge('--bin', str(scratch), '--target', 'native', '--rerun')
    assert done.returncode == 1, done
    assert ('dudect: equal (dudect_bearssl, native) exceeded 10 in 2 of 3 runs: '
            '14.00, 12.50, 3.00') in done.stderr, done.stderr


def judge_unjudged_case(scratch: Path) -> None:
    directory = write_output(scratch, 'dudect_sodium',
                             'dudect case=x25519_agree t=30.00 threshold=10 judged=no\n')
    # No program: a rerun would fail to start it.
    done = run_judge('--bin', str(scratch), '--target', 'native', '--rerun')
    expect(done, 0)
    assert done.stdout.count('::warning') == 1, done.stdout
    assert not list(directory.glob('*.count')), 'the case was run again'


def judge_skips_planted(scratch: Path) -> None:
    write_output(scratch, 'dudect_planted',
                 'dudect case=x25519_agree t=66.70 threshold=10 judged=yes\n')
    write_output(scratch, 'dudect_harness',
                 'dudect case=x t=10.00 threshold=10 judged=yes\nplanted leak found\n')
    done = run_judge('--bin', str(scratch), '--target', 'native', '--rerun')
    expect(done, 0)
    assert 't=66.70' in done.stdout and '::warning' not in done.stdout, done.stdout
    assert '::group::dudect_planted (native)' in done.stdout, done.stdout


def judge_output_without_case_lines(scratch: Path) -> None:
    write_output(scratch, 'dudect_ctaes', '')
    done = run_judge('--bin', str(scratch), '--target', 'native')
    expect(done, 1)
    assert 'dudect_ctaes.output' in done.stderr, done.stderr


def judge_wasip2_launcher(scratch: Path) -> None:
    directory = write_output(scratch, 'dudect_bearssl', BEARSSL, suffix='/wasi')
    log = scratch / 'launcher.log'
    launcher = scratch / 'launch.py'
    write_script(launcher, LAUNCHER.format(log=str(log), case='chacha_open'))
    done = run_judge('--bin', str(scratch), '--target', 'wasip2', '--rerun', '--launcher',
                     shlex.join([sys.executable, str(launcher)]))
    expect(done, 0)
    wanted = f'{directory / "dudect_bearssl.wasm"} --case chacha_open'
    assert log.read_text() == wanted, log.read_text()
    assert '69.80, 1.00, 1.00' in done.stdout, done.stdout


CASES: list[Callable[[Path], None]] = [
    judge_prints_and_warns,
    judge_two_of_three_pass,
    judge_two_of_three_fail,
    judge_unjudged_case,
    judge_skips_planted,
    judge_output_without_case_lines,
    judge_wasip2_launcher,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'crypto_dudect_judge_test: no case named {", ".join(sorted(unknown))}',
              file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp crypto dudect judge ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('crypto_dudect_judge_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
