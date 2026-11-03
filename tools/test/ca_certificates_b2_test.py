#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Exercise embedded roots, rebuilds, and corrupt inputs in a scratch B2 consumer."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import harness

JAM = '''import webcpp ;
webcpp.run roots : roots.cpp : <library>/webcpp/third_party//ca_certificates ;
'''
SOURCE = '''#include <webcpp/asio/detail/ca_certificates.hpp>
#include <cstdio>
#include <string_view>
int main() {
    std::string_view pem = webcpp::asio::detail::ca_certificates::pem;
    if (!pem.starts_with("-----BEGIN CERTIFICATE-----")) return 1;
    std::printf("%zu\\n", webcpp::asio::detail::ca_certificates::count);
}
'''


def test_b2_rebuilds_and_checks_integrity(root: Path) -> None:
    harness.add_library(root, 'ca_user', JAM, {'roots.cpp': SOURCE})
    build = ('toolset=clang', 'variant=release', 'libs/ca_user/test')
    harness.expect(harness.run_b2(root, '-a', *build), True, '**passed**')
    outputs = list((root / 'bin').rglob('roots.output'))
    assert len(outputs) == 1, outputs
    before = int(outputs[0].read_text().splitlines()[0])
    again = harness.run_b2(root, *build)
    harness.expect(again, True)
    assert 'webcpp-ca-certificates.generate ' not in again.stdout
    package = root / 'third_party/ca_certificates'
    pem = package / 'cacert.pem'
    data = pem.read_bytes()
    blocks = re.findall(rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',
                        data, re.DOTALL)
    reduced = b'\n'.join(blocks[:-1])
    incoming = root / 'replacement.pem'
    incoming.write_bytes(reduced)
    snapshot_date = json.loads((package / 'manifest.json').read_text())['date']
    subprocess.run([sys.executable, str(root / 'tools/ca_certificates/update.py'),
                    '--date', snapshot_date, '--source-file', str(incoming),
                    '--sha256', hashlib.sha256(reduced).hexdigest(), '--output', str(package)],
                   check=True, capture_output=True)
    # B2 compares timestamps at whole-second resolution. Make this deliberate
    # source update newer than the preceding build without relying on sleeps.
    changed = outputs[0].stat().st_mtime + 2
    os.utime(pem, (changed, changed))
    harness.expect(harness.run_b2(root, *build), True, '**passed**')
    assert int(outputs[0].read_text().splitlines()[0]) == before - 1
    pem.write_bytes(reduced + b'corrupted bytes')
    changed = max(changed, outputs[0].stat().st_mtime) + 2
    os.utime(pem, (changed, changed))
    harness.expect(harness.run_b2(root, *build), False, 'CA bundle SHA-256 mismatch')


def test_missing_bundle_does_not_break_unrelated_targets(root: Path) -> None:
    (root / 'third_party/ca_certificates/cacert.pem').unlink()
    harness.expect(harness.run_b2(root, 'declared-targets'), True)
    harness.expect(harness.run_b2(root, 'third_party//ca_certificates'), False, 'cacert.pem')


def test_installed_roots_work_without_checkout_include_paths(root: Path) -> None:
    prefix = root / 'installed with spaces'
    harness.expect(harness.run_b2(root, 'install', f'--prefix={prefix}'), True)
    consumer = prefix / 'consumer.cpp'
    consumer.write_text(SOURCE)
    binary = prefix / 'consumer'
    result = subprocess.run(['clang++', '-std=c++20', '-I' + str(prefix / 'include'),
                             str(consumer), '-o', str(binary)],
                            cwd=prefix, env=harness.b2_environment(),
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    source = root / 'third_party/ca_certificates'
    manifest = json.loads((source / 'manifest.json').read_text())
    assert int(result.stdout) == manifest['certificate_count'], result.stdout
    installed = prefix / 'include/webcpp/ca_certificates'
    for name in ('LICENSE-MPL-2.0.txt', 'README.md', 'cacert.pem', 'manifest.json'):
        assert (installed / name).read_bytes() == (source / name).read_bytes(), name


if __name__ == '__main__':
    sys.exit(harness.run_cases('ca_certificates_b2_test', [
        test_b2_rebuilds_and_checks_integrity,
        test_missing_bundle_does_not_break_unrelated_targets,
        test_installed_roots_work_without_checkout_include_paths], sys.argv[1:]))
