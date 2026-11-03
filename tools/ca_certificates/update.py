#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Import a dated curl/Mozilla CA snapshot; print every added/removed fingerprint."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import tempfile
import urllib.request

from bundle import certificates, checked

ROOT = Path(__file__).resolve().parents[2]


def download(url: str) -> bytes:
    """Fetch a bounded artifact over verified HTTPS from curl's own host."""
    with urllib.request.urlopen(url, timeout=30) as response:
        if not response.url.startswith('https://curl.se/'):
            raise ValueError('unexpected CA artifact redirect')
        data = response.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise ValueError('CA artifact exceeds 2 MiB')
        return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', required=True, type=date.fromisoformat)
    parser.add_argument('--source-file', type=Path, help='offline copy of the dated artifact')
    parser.add_argument('--sha256', help='required expected digest with --source-file')
    parser.add_argument('--output', type=Path, default=ROOT / 'third_party/ca_certificates')
    args = parser.parse_args()
    url = f'https://curl.se/ca/cacert-{args.date}.pem'
    if args.source_file:
        if not args.sha256:
            parser.error('--source-file requires --sha256')
        data = args.source_file.read_bytes()
        digest = args.sha256
    else:
        if args.sha256:
            parser.error('--sha256 is only used with --source-file')
        data = download(url)
        digest = download(url + '.sha256').decode('ascii').split()[0]
    if not re.fullmatch('[0-9a-f]{64}', digest) or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('CA bundle SHA-256 mismatch; no files changed')
    records = certificates(data)
    fingerprints = sorted(item[0] for item in records)
    old = set()
    if (args.output / 'manifest.json').exists():
        previous, _ = checked(args.output / 'cacert.pem', args.output / 'manifest.json')
        if args.date < date.fromisoformat(previous['date']):
            raise ValueError('refusing to replace the CA snapshot with an older date')
        old = set(previous['fingerprints'])
    added, removed = sorted(set(fingerprints) - old), sorted(old - set(fingerprints))
    print(f'Added: {len(added)}; removed: {len(removed)}', flush=True)
    for kind, values in (('ADD', added), ('REMOVE', removed)):
        for value in values:
            print(f'{kind} SHA256:{value}', flush=True)
    manifest = {'source': url, 'date': str(args.date), 'license': 'MPL-2.0',
                'sha256': digest, 'certificate_count': len(records),
                'fingerprints': fingerprints}
    args.output.mkdir(parents=True, exist_ok=True)
    # Both files are staged before replacement. An interruption between the two
    # replacements is detected by checked(), so no build uses a mismatched pair.
    with tempfile.TemporaryDirectory(dir=args.output, prefix='.update-') as scratch:
        staging = Path(scratch)
        (staging / 'cacert.pem').write_bytes(data)
        (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        for name in ('cacert.pem', 'manifest.json'):
            (staging / name).replace(args.output / name)
    print(f'Pinned {len(records)} CAs from {args.date}: {digest}')


if __name__ == '__main__':
    main()
