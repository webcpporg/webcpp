# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Exercise both WASI launcher boundaries, including real runtime interruption."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class Launcher(unittest.TestCase):
    launcher = Path(__file__).resolve().with_name('run.sh')
    timeout_variable = 'WEBCPP_WASIP3_TEST_TIMEOUT'
    capabilities = [
        '-S', 'p3', '-S', 'inherit-network=y', '-S', 'allow-ip-name-lookup=y',
        '-W', 'component-model-async=y', '-W', 'component-model-threading=y',
    ]

    def invoke(self, timeout: str | None = None, *arguments: str,
               status: int = 0) -> tuple[subprocess.CompletedProcess[str], list[str] | None]:
        with tempfile.TemporaryDirectory(prefix='wasi launcher ') as directory:
            root = Path(directory)
            capture = root / 'arguments'
            runtime = root / 'wasmtime'
            runtime.write_text(
                '#!/usr/bin/env sh\n'
                'printf "%s\\0" "$@" > "$WEBCPP_RUN_TEST_CAPTURE"\n'
                'exit "$WEBCPP_RUN_TEST_STATUS"\n')
            runtime.chmod(0o755)
            environment = dict(os.environ)
            environment.pop(self.timeout_variable, None)
            environment.update({
                'PATH': str(root) + os.pathsep + environment.get('PATH', ''),
                'WEBCPP_RUN_TEST_CAPTURE': str(capture),
                'WEBCPP_RUN_TEST_STATUS': str(status),
            })
            if timeout is not None:
                environment[self.timeout_variable] = timeout
            result = subprocess.run(
                ['sh', str(self.launcher), *arguments], env=environment,
                capture_output=True, text=True, check=False, timeout=10)
            received = (capture.read_bytes().decode().split('\0')[:-1]
                        if capture.exists() else None)
            return result, received

    def test_default_allows_the_complete_suite_and_preserves_capabilities(self):
        result, arguments = self.invoke(None, 'finite workload.wasm')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(arguments, [
            'run', *self.capabilities, '-W', 'timeout=600s',
            'finite workload.wasm',
        ])

    def test_a_focused_test_can_choose_a_shorter_finite_timeout(self):
        result, arguments = self.invoke('15', 'loopback.wasm')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNotNone(arguments)
        self.assertIn('timeout=15s', arguments or [])

    def test_a_large_workload_can_choose_a_longer_finite_timeout(self):
        result, arguments = self.invoke('900', 'large.wasm')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNotNone(arguments)
        self.assertIn('timeout=900s', arguments or [])

    def test_invalid_bounds_fail_before_starting_the_guest(self):
        for timeout in ('', '0', '000', '-1', '1.5', '15s', 'none', ' 15', '15\n'):
            with self.subTest(timeout=timeout):
                result, arguments = self.invoke(timeout, 'guest.wasm')
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(self.timeout_variable, result.stderr)
                self.assertIn('positive integer', result.stderr)
                self.assertIsNone(arguments)

    def test_forwards_runtime_options_guest_arguments_and_exit_status(self):
        forwarded = ['--dir', 'host path::guest path', 'program.wasm', '--',
                     'argument with spaces', '', '*']
        result, arguments = self.invoke('30', *forwarded, status=7)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIsNotNone(arguments)
        self.assertEqual((arguments or [])[-len(forwarded):], forwarded)

    @unittest.skipUnless(shutil.which('wasmtime'), 'wasmtime is not on PATH')
    def test_real_runtime_completes_a_guest_and_interrupts_an_infinite_loop(self):
        with tempfile.TemporaryDirectory(prefix='wasi execution ') as directory:
            guest = Path(directory) / 'guest.wat'
            environment = {**os.environ, self.timeout_variable: '1'}
            for body, succeeds in (('', True), ('(loop $forever (br $forever))', False)):
                with self.subTest(succeeds=succeeds):
                    guest.write_text(f'(module (func (export "_start") {body}))\n')
                    result = subprocess.run(
                        ['sh', str(self.launcher), str(guest)], env=environment,
                        capture_output=True, text=True, check=False, timeout=30)
                    if succeeds:
                        self.assertEqual(result.returncode, 0, result.stderr)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn('wasm trap: interrupt', result.stderr)


class P2Launcher(Launcher):
    launcher = Path(__file__).resolve().parents[1] / 'asio-wasip2/run.sh'
    timeout_variable = 'WEBCPP_WASIP2_TEST_TIMEOUT'
    capabilities = ['-S', 'inherit-network=y', '-S', 'allow-ip-name-lookup=y']


if __name__ == '__main__':
    unittest.main()
