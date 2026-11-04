#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Keep a test's process tree alive only while its owner holds the keeper's pipe.

POSIX uses a process group in the owner's session. Windows uses a Job Object
with kill-on-close, assigned to the keeper before it can launch a child. The
job handle is not inherited, so normal exit, termination and owner-pipe EOF
all close the keeper's only handle and terminate its descendants. Nested jobs
on supported Windows hosts retain the surrounding CI job's restrictions.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path


def windows_job() -> None:
    """Contain this keeper before it creates children; fail closed on any API error."""
    if sys.platform != 'win32':
        raise OSError('Job Objects require Windows')
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                    ('flags', wintypes.DWORD), ('minimum_working_set', ctypes.c_size_t),
                    ('maximum_working_set', ctypes.c_size_t), ('active_processes', wintypes.DWORD),
                    ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD),
                    ('scheduling', wintypes.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in
                    ('reads', 'writes', 'other', 'read_bytes', 'write_bytes', 'other_bytes')]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [('basic', BasicLimits), ('io', IoCounters),
                    ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                    ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int,
                                               ctypes.c_void_p, wintypes.DWORD)
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.argtypes = ()
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL

    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
            raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        kernel.CloseHandle(job)
        raise
    # Keep the non-inheritable kernel handle open until this process exits.
    # Closing it here would terminate this keeper along with its descendants.


def start_tree(words: list[str], *, capture: bool = False) -> subprocess.Popen[bytes]:
    """Start a keeper in its own group, retaining its lifetime pipe in the returned process."""
    return subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), *words], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None,
        preexec_fn=os.setpgrp if os.name != 'nt' else None,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)


def terminate_tree(process: subprocess.Popen[bytes], *, force: bool = False) -> None:
    """Stop the keeper's whole group or job, including children left after their parent exits."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        if os.name == 'nt':
            # TerminateProcess closes the keeper's Job Object handle. Windows
            # has no SIGTERM equivalent that reliably stops arbitrary children.
            process.kill() if force else process.terminate()
        else:
            os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)


def exit_status(status: int) -> int:
    """Fit Python's signed C-int exit APIs without losing a Windows DWORD's bits."""
    if sys.platform == 'win32':
        # Popen returns unsigned DWORDs. Both os._exit and older sys.exit
        # implementations need the signed representation of those same 32 bits.
        return ctypes.c_int32(status).value
    return status if status >= 0 else 128 - status


def keep(words: list[str]) -> None:
    if os.name == 'nt':
        try:
            windows_job()
        except OSError as error:
            print(f'cannot contain test processes: {error}', file=sys.stderr, flush=True)
            os._exit(127)
    else:
        # The handler is not inherited by an executed child. Waiting for this
        # keeper therefore also waits for a child handling the group's SIGTERM.
        signal.signal(signal.SIGTERM, lambda *_: None)
    try:
        child = subprocess.Popen(words, stdin=subprocess.DEVNULL)
    except OSError as error:
        print(f'cannot start {words[0]}: {error.strerror or error}', file=sys.stderr, flush=True)
        os._exit(127)

    def watch() -> None:
        try:
            while os.read(0, 4096):
                pass
        finally:
            if os.name == 'nt':
                os._exit(1)
            os.killpg(0, signal.SIGKILL)

    threading.Thread(target=watch, daemon=True).start()
    status = child.wait()
    # Avoid interpreter shutdown waiting for the thread reading the lifetime pipe.
    os._exit(exit_status(status))


if __name__ == '__main__':
    keep(sys.argv[1:])
