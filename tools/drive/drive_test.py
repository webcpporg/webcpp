#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Checks tools/drive/drive.py with a stand-in for a driver: a small Python program that records
its process and, as it is told, prints and exits with 0, exits with 3, hangs, or starts a program
that hangs and waits for it. The cases: a driver that passes writes the output and shows what it
printed; one that fails exits with its status, writes nothing and names the test and the command;
a driver that hangs, and a program that hangs, are stopped once the bound has passed, with every
process of their group, and the run fails naming the test, the program and the bound; a run whose
driver leaves its program running leaves nothing either; a SIGKILL of drive.py, alone or with its
group, as b2 stops an action, and a SIGTERM, leave nothing behind; the bound is 30 s by default;
and usage errors exit 2. Each case runs in a scratch directory of its own. Run with the names of
some cases to run only those."""

from __future__ import annotations

import ctypes
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRIVE = HERE / 'drive.py'

# The stand-in driver: `<python> <stand-in> <mode> <record> <program>`. It records its pid and its
# process group into <record>, and its program's pid once it starts one, then: pass prints ready and
# exits 0; fail exits 3; hang sleeps; program-hangs starts the program, a Python that sleeps, in its
# group, as node's spawnSync does, and waits for it; orphan starts it and exits 0 at once.
STAND_IN = r'''
import json
import subprocess
import sys
import time
import os

mode, record, program = sys.argv[1:4]
recorded = {'pid': os.getpid()}
if os.name != 'nt':
    recorded['pgid'] = os.getpgid(0)


def save():
    with open(record + '.tmp', 'w') as file:
        json.dump(recorded, file)
    os.replace(record + '.tmp', record)


save()
if mode == 'pass':
    print(f'driving {program}: ready', flush=True)
    sys.exit(0)
if mode == 'fail':
    print('driving: not ready', flush=True)
    sys.exit(3)
if mode == 'hang':
    while True:
        time.sleep(1)
if mode.startswith('grandchild-'):
    child_record = record + '.child'
    child_code = ('import json, os, subprocess, sys\n'
                  'command = [sys.executable, "-c", "import time; time.sleep(600)"]\n'
                  'child = subprocess.Popen(command)\n'
                  'with open(sys.argv[1] + ".tmp", "w") as stream: json.dump(child.pid, stream)\n'
                  'os.replace(sys.argv[1] + ".tmp", sys.argv[1])\n'
                  'child.wait()\n')
    child = subprocess.Popen([sys.executable, '-c', child_code, child_record])
    while not os.path.exists(child_record):
        time.sleep(0.01)
    with open(child_record) as stream:
        recorded['grandchild'] = json.load(stream)
else:
    child = subprocess.Popen([sys.executable, '-c', 'import time\nwhile True: time.sleep(1)'])
recorded['child'] = child.pid
save()
if mode == 'grandchild-windows-status':
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.ExitProcess.argtypes = (wintypes.UINT,)
    kernel.ExitProcess.restype = None
    kernel.ExitProcess(0xC0000005)
if mode in ('orphan', 'grandchild-orphan'):
    sys.exit(0)
child.wait()
'''

SHOWN = 'webcpp.drive driven in libs/web/test/Jamfile'

# Reproduce Windows' missing signal/alarm API while still running real children
# under this host's process-tree implementation. Windows itself uses its Job Object.
WINDOWS_SIGNALS = r'''
import runpy
import signal
import sys

for name in ('SIGHUP', 'SIGALRM', 'alarm'):
    if hasattr(signal, name):
        delattr(signal, name)
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''


def outcome(result: subprocess.CompletedProcess[str]) -> str:
    return f'exit {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}'


class Run:
    """drive.py over the stand-in in mode, in scratch."""

    def __init__(self, scratch: Path, mode: str) -> None:
        self.stand_in = scratch / 'stand-in driver.py'
        self.stand_in.write_text(STAND_IN)
        self.record = scratch / f'{mode}.json'
        self.output = scratch / f'{mode}.driven'
        self.program = scratch / 'bin/driven program.js'
        self.mode = mode

    def command(self) -> list[str]:
        return [sys.executable, str(self.stand_in), self.mode, str(self.record), str(self.program)]

    def arguments(self, *extra: str) -> list[str]:
        return [sys.executable, str(DRIVE), '--program', SHOWN, '--output', str(self.output),
                *extra, '--', *self.command()]

    def run(self, *extra: str) -> subprocess.CompletedProcess[str]:
        # As b2 starts an action: in a process group of its own.
        return subprocess.run(self.arguments(*extra), capture_output=True, text=True,
                              check=False, timeout=120,
                              preexec_fn=os.setpgrp if os.name != 'nt' else None)

    def recorded(self, holds=lambda record: True, seconds: float = 30) -> dict:
        """What the stand-in recorded, once holds is true of it."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.record.is_file():
                record = json.loads(self.record.read_text())
                if holds(record):
                    return record
            time.sleep(0.05)
        raise AssertionError(f'the stand-in recorded nothing that holds in {seconds} s')


def windows_alive(pid: int, *, terminate: bool = False) -> bool:
    """Inspect a recorded process without sending os.kill's destructive Windows signal 0."""
    if sys.platform != 'win32':
        raise OSError('Windows process handles require Windows')
    from ctypes import wintypes

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel.TerminateProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100001, False, pid)  # SYNCHRONIZE | PROCESS_TERMINATE
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:  # ERROR_INVALID_PARAMETER: the process no longer exists.
            return False
        raise ctypes.WinError(error)
    try:
        state = kernel.WaitForSingleObject(handle, 0)
        if state == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        alive = state == 258  # WAIT_TIMEOUT
        if alive and terminate and not kernel.TerminateProcess(handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())
        return alive
    finally:
        kernel.CloseHandle(handle)


def gone(record: dict, seconds: float = 10) -> None:
    """Asserts that the stand-in's process group and each process it recorded are gone, within
    seconds, and that ps lists none of them: a killed process can stay a zombie for a moment."""
    pids = [record[key] for key in ('pid', 'child', 'grandchild') if key in record]
    deadline = time.monotonic() + seconds
    while True:
        if os.name == 'nt':
            alive = [str(pid) for pid in pids if windows_alive(pid)]
        else:
            listed = subprocess.run(['ps', '-A', '-o', 'pid=,pgid=,stat='], capture_output=True,
                                    text=True, check=True).stdout.split('\n')
            alive = [line for line in listed if line.split()[:1] and (
                int(line.split()[0]) in pids or int(line.split()[1]) == record['pgid'])
                and not line.split()[2].startswith('Z')]
        if not alive:
            return
        if time.monotonic() > deadline:
            for pid in pids:
                try:
                    if os.name == 'nt':
                        windows_alive(pid, terminate=True)
                    else:
                        os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            raise AssertionError(f'still there: {alive}')
        time.sleep(0.05)


def test_a_driver_that_passes_writes_the_output(scratch: Path) -> None:
    run = Run(scratch, 'pass')
    result = run.run()
    assert result.returncode == 0, outcome(result)
    assert f'driving {run.program}: ready' in result.stdout, outcome(result)
    assert run.output.read_text() == 'driven\n'
    gone(run.recorded())


def test_drivers_run_without_unix_signal_names(scratch: Path) -> None:
    for mode, status in (('pass', 0), ('fail', 3), ('program-hangs', 1), ('orphan', 0)):
        run = Run(scratch, mode)
        arguments = run.arguments('--timeout', '2')
        result = subprocess.run([sys.executable, '-c', WINDOWS_SIGNALS, *arguments[1:]],
                                capture_output=True, text=True, check=False, timeout=15)
        assert result.returncode == status, (mode, outcome(result))
        assert run.output.exists() == (status == 0), (mode, outcome(result))
        if mode == 'program-hangs':
            assert 'did not end within 2 s' in result.stderr, outcome(result)
        gone(run.recorded())


def test_a_driver_that_fails_exits_with_its_status(scratch: Path) -> None:
    run = Run(scratch, 'fail')
    run.output.write_text('left from an earlier run\n')
    result = run.run()
    assert result.returncode == 3, outcome(result)
    assert 'driving: not ready' in result.stdout, outcome(result)
    assert f'drive: {SHOWN}: the driver of {run.program} exited with 3' in result.stderr, (
        outcome(result))
    assert not run.output.exists()
    gone(run.recorded())


def test_a_hanging_driver_is_stopped_within_its_bound(scratch: Path) -> None:
    run = Run(scratch, 'hang')
    began = time.monotonic()
    result = run.run('--timeout', '2')
    assert time.monotonic() - began < 2 + 5 + 3, time.monotonic() - began
    assert result.returncode == 1, outcome(result)
    assert (f'drive: {SHOWN}: the driver of {run.program} did not end within 2 s; it was stopped '
            'with every process of its group, the program among them') in result.stderr, (
        outcome(result))
    assert not run.output.exists()
    gone(run.recorded())


def test_a_hanging_program_is_stopped_within_its_bound(scratch: Path) -> None:
    run = Run(scratch, 'program-hangs')
    began = time.monotonic()
    result = run.run('--timeout', '2')
    assert time.monotonic() - began < 2 + 5 + 3, time.monotonic() - began
    assert result.returncode == 1, outcome(result)
    assert f'drive: {SHOWN}: the driver of {run.program} did not end within 2 s' in (
        result.stderr), outcome(result)
    gone(run.recorded(lambda record: 'child' in record))


def test_a_program_the_driver_leaves_running_is_stopped(scratch: Path) -> None:
    # The driver passes, and leaves its program running: nothing of its group outlives the run.
    run = Run(scratch, 'orphan')
    result = run.run()
    assert result.returncode == 0, outcome(result)
    gone(run.recorded(lambda record: 'child' in record))


def test_descendants_cannot_outlive_the_driver(scratch: Path) -> None:
    for mode, status in (('grandchild-hangs', 1), ('grandchild-orphan', 0)):
        run = Run(scratch, mode)
        result = run.run('--timeout', '2')
        assert result.returncode == status, outcome(result)
        gone(run.recorded(lambda record: 'grandchild' in record))


def test_windows_status_keeps_all_32_bits(scratch: Path) -> None:
    run = Run(scratch, 'grandchild-windows-status')
    result = run.run()
    assert result.returncode == 0xC0000005, outcome(result)
    assert f'exited with {0xC0000005}' in result.stderr, outcome(result)
    assert not run.output.exists()
    gone(run.recorded(lambda record: 'grandchild' in record))


def test_nested_windows_jobs_keep_timeout_and_cleanup(scratch: Path) -> None:
    if sys.platform != 'win32':
        return
    # Give the runner an outer job, as a Windows CI service may do. Its keeper
    # must establish a nested job before any driver or descendant starts.
    bootstrap = ('import json, os, subprocess, sys\n'
                 f'sys.path.insert(0, {str(HERE.parent / "component")!r})\n'
                 'from process_tree import windows_job\n'
                 'windows_job()\n'
                 'result = subprocess.run(sys.argv[2:], capture_output=True,\n'
                 '                        text=True, timeout=15)\n'
                 'with open(sys.argv[1] + ".tmp", "w") as stream:\n'
                 '    json.dump([result.returncode, result.stdout, result.stderr], stream)\n'
                 'os.replace(sys.argv[1] + ".tmp", sys.argv[1])\n'
                 'sys.stdin.buffer.read(1)\n')
    for mode, status in (('pass', 0), ('grandchild-hangs', 1), ('grandchild-orphan', 0)):
        run = Run(scratch, mode)
        completed = scratch / f'{mode}.completed'
        outer = subprocess.Popen([sys.executable, '-c', bootstrap, str(completed),
                                  *run.arguments('--timeout', '2')], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 20
            while not completed.exists() and time.monotonic() < deadline:
                assert outer.poll() is None, (mode, outer.returncode)
                time.sleep(0.05)
            assert completed.exists(), f'{mode}: nested driver did not complete'
            result = json.loads(completed.read_text())
            assert result[0] == status, (mode, result)
            # The outer job must still be open while checking the inner tree.
            # Its kill-on-close cannot rescue a keeper that leaked descendants.
            assert outer.poll() is None, mode
            gone(run.recorded())
            assert outer.poll() is None, mode
        finally:
            outer.communicate('\n', timeout=20)
        assert outer.returncode == 0, outer.returncode


def test_a_killed_or_stopped_run_leaves_nothing(scratch: Path) -> None:
    # A SIGKILL, which drive.py cannot answer, to drive.py alone or to its process group, as b2
    # sends to an action it stops (b2 -l), and a SIGTERM leave nothing: the keeper sees drive.py
    # gone and kills its group.
    if os.name == 'nt':
        for name in ('killed', 'terminated'):
            run = Run(scratch, 'grandchild-hangs')
            run.record = scratch / f'{name}.json'
            process = subprocess.Popen(run.arguments(), stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
            recorded = run.recorded(lambda record: 'grandchild' in record)
            process.kill() if name == 'killed' else process.terminate()
            process.communicate(timeout=60)
            assert process.returncode != 0, process.returncode
            gone(recorded)
        return
    for name, kill, number in (('alone', os.kill, signal.SIGKILL),
                              ('group', os.killpg, signal.SIGKILL),
                              ('terminated', os.kill, signal.SIGTERM)):
        run = Run(scratch, 'grandchild-hangs')
        run.record = scratch / f'{name}.json'
        process = subprocess.Popen(run.arguments(), stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, preexec_fn=os.setpgrp)
        recorded = run.recorded(lambda record: 'grandchild' in record)
        kill(process.pid, number)
        process.communicate(timeout=60)
        assert process.returncode == -number, (name, process.returncode)
        gone(recorded)


def test_the_bound_is_30_seconds_by_default(scratch: Path) -> None:
    result = subprocess.run([sys.executable, str(DRIVE), '--help'], capture_output=True,
                            text=True, check=False)
    assert result.returncode == 0, outcome(result)
    assert '(30 by default)' in ' '.join(result.stdout.split()), outcome(result)
    run = Run(scratch, 'hang')
    process = subprocess.Popen(run.arguments(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, preexec_fn=os.setpgrp if os.name != 'nt' else None)
    recorded = run.recorded()
    try:
        process.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        pass
    else:
        raise AssertionError('drive.py stopped its driver before 30 s')
    process.kill()
    process.communicate()
    gone(recorded)


def test_usage_errors_exit_2(scratch: Path) -> None:
    run = Run(scratch, 'pass')
    for extra, words, message in (
        ((), [], 'drive.py: error: no driver to run'),
        (('--timeout', '0'), None, 'drive.py: error: --timeout 0 is not a number of seconds'),
        (('--timeout', 'soon'), None, 'drive.py: error: --timeout soon is not a number'),
    ):
        arguments = run.arguments(*extra)
        if words is not None:
            arguments = arguments[:arguments.index('--') + 1] + words
        result = subprocess.run(arguments, capture_output=True, text=True, check=False)
        assert result.returncode == 2, (extra, outcome(result))
        assert message in result.stderr, (extra, outcome(result))
    assert not run.record.exists()


CASES = [
    test_a_driver_that_passes_writes_the_output,
    test_drivers_run_without_unix_signal_names,
    test_a_driver_that_fails_exits_with_its_status,
    test_a_hanging_driver_is_stopped_within_its_bound,
    test_a_hanging_program_is_stopped_within_its_bound,
    test_a_program_the_driver_leaves_running_is_stopped,
    test_descendants_cannot_outlive_the_driver,
    test_windows_status_keeps_all_32_bits,
    test_nested_windows_jobs_keep_timeout_and_cleanup,
    test_a_killed_or_stopped_run_leaves_nothing,
    test_the_bound_is_30_seconds_by_default,
    test_usage_errors_exit_2,
]


def main(argv: list[str]) -> int:
    unknown = set(argv) - {case.__name__ for case in CASES}
    if unknown:
        print(f'drive_test: no case named {", ".join(sorted(unknown))}', file=sys.stderr)
        return 2
    for case in CASES:
        if argv and case.__name__ not in argv:
            continue
        windows_only = (test_windows_status_keeps_all_32_bits,
                        test_nested_windows_jobs_keep_timeout_and_cleanup)
        if case in windows_only and sys.platform != 'win32':
            print(f'{case.__name__}: skipped (requires Windows)')
            continue
        with tempfile.TemporaryDirectory(prefix='webcpp drive ') as scratch:
            case(Path(scratch))
        print(f'{case.__name__}: ok')
    print('drive_test: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
