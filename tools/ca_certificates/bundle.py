# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Validate pinned public CA artifacts without importing system trust."""
import base64
import hashlib
import json
from pathlib import Path
import re
import ssl

CERTIFICATE = re.compile(
    rb'-----BEGIN CERTIFICATE-----\r?\n([A-Za-z0-9+/=\r\n]+)-----END CERTIFICATE-----')


def certificates(data: bytes) -> list[tuple[str, bytes]]:
    """Return distinct DER fingerprints and PEM blocks, rejecting partial data."""
    blocks = CERTIFICATE.findall(data)
    remainder = CERTIFICATE.sub(b'', data)
    if not blocks or b'-----BEGIN' in remainder or b'-----END' in remainder:
        raise ValueError('empty, malformed or unexpected PEM block in CA bundle')
    records = []
    for match in CERTIFICATE.finditer(data):
        der = base64.b64decode(re.sub(rb'\s', b'', match[1]), validate=True)
        records.append((hashlib.sha256(der).hexdigest(), match[0] + b'\n'))
    if len({record[0] for record in records}) != len(records):
        raise ValueError('duplicate certificate in CA bundle')
    # A fresh context has no system roots. OpenSSL parses the actual ASN.1 and
    # verifies that every supplied object is a CA, not merely valid base64.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cadata=b''.join(item[1] for item in records).decode('ascii'))
    if context.cert_store_stats()['x509_ca'] != len(records):
        raise ValueError('bundle contains a certificate that is not a CA')
    decoded = {hashlib.sha256(der).hexdigest()
               for der in context.get_ca_certs(binary_form=True)}
    if decoded != {record[0] for record in records}:
        raise ValueError('certificate DER contains trailing or noncanonical data')
    return records


def checked(pem: Path, manifest: Path) -> tuple[dict, list[tuple[str, bytes]]]:
    """Validate a snapshot's bytes and inventory against its recorded pin."""
    data = pem.read_bytes()
    pin = json.loads(manifest.read_text())
    if hashlib.sha256(data).hexdigest() != pin['sha256']:
        raise ValueError('CA bundle SHA-256 mismatch; restore or explicitly update the snapshot')
    records = certificates(data)
    if (pin['certificate_count'] != len(records) or
            pin['fingerprints'] != sorted(item[0] for item in records)):
        raise ValueError('CA bundle inventory differs from manifest')
    return pin, records
