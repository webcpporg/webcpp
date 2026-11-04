#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)
"""Exercise real loopback TLS with trusted and rejected peer identities."""
import json
import os
from pathlib import Path
import shlex
import socket
import ssl
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parent
program = Path(sys.argv[1]).resolve()
wasm = program.suffix == '.wasm'
embedded = '--embedded' in sys.argv[2:]
require_sni = '--require-sni' in sys.argv[2:]
client_args = [arg.removeprefix('--client-arg=') for arg in sys.argv[2:]
               if arg.startswith('--client-arg=')]
WASMTIME = os.environ.get('WASMTIME', 'wasmtime')
wasip2 = '--wasip2' in sys.argv[2:]
launcher = ([str(WASMTIME), 'run', '-W', 'timeout=15s'] if wasip2 else
            [str(WASMTIME), 'run', '-S', 'p3', '-W', 'component-model-async=y',
             '-W', 'component-model-threading=y', '-W', 'timeout=15s'])
if not ssl.HAS_TLSv1_3:
    raise SystemExit('The Python TLS server requires TLS 1.3; select a newer Python interpreter.')
print('Native test server: ' + ssl.OPENSSL_VERSION, flush=True)
import tempfile
scratch = tempfile.TemporaryDirectory(prefix='webcpp-tls-')
certs = Path(scratch.name)
# The CLI creates fresh, short-lived test fixtures only. It is not linked into
# the client, which uses the source-built dependency under test.
openssl = os.environ.get('OPENSSL_TEST_CLI', 'openssl')
for name in ('ca', 'untrusted'):
    command = [openssl, 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
               '-noenc', '-sha256', '-days', '1', '-subj', '/CN=WebCPP test ' + name,
               '-addext', 'basicConstraints=critical,CA:TRUE',
               '-addext', 'keyUsage=critical,keyCertSign,cRLSign',
               '-keyout', str(certs / (name + '-key.pem')),
               '-out', str(certs / (name + '.pem'))]
    print(shlex.join(command), flush=True)
    subprocess.run(command, check=True, capture_output=True, timeout=15)
    (certs / (name + '-key.pem')).chmod(0o600)

# Issue a distinct server certificate from the test CA, as a real TLS
# deployment does. The client receives only the CA's public certificate.
extensions = certs / 'server.ext'
extensions.write_text('basicConstraints=critical,CA:FALSE\n'
                      'keyUsage=critical,digitalSignature\n'
                      'extendedKeyUsage=serverAuth\n'
                      'subjectAltName=DNS:localhost\n')
commands = [
    [openssl, 'req', '-new', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
     '-noenc', '-subj', '/CN=localhost', '-keyout', str(certs / 'server-key.pem'),
     '-out', str(certs / 'server.csr')],
    [openssl, 'x509', '-req', '-in', str(certs / 'server.csr'), '-CA', str(certs / 'ca.pem'),
     '-CAkey', str(certs / 'ca-key.pem'), '-set_serial', '1', '-days', '1', '-sha256',
     '-extfile', str(extensions), '-out', str(certs / 'server.pem')],
]
for command in commands:
    print(shlex.join(command), flush=True)
    subprocess.run(command, check=True, capture_output=True, timeout=15)
(certs / 'server-key.pem').chmod(0o600)

if '--state-test' in sys.argv[2:]:
    for version in ('1.2', '1.3'):
        command = [str(program), (certs / 'server.pem').read_text(),
                   (certs / 'server-key.pem').read_text(), (certs / 'ca.pem').read_text(),
                   version, *client_args]
        if wasm:
            command = (launcher + ['-S', 'inherit-network=y', '-S', 'tcp=y']) + command
        # Fixture keys are ephemeral and stay local; do not print them in the command.
        print('Run TLS state test: ' + str(program) + ' TLS ' + version, flush=True)
        try:
            result = subprocess.run(command, timeout=20)
        except subprocess.TimeoutExpired:
            raise SystemExit('FAIL TLS state test timed out: ' + version) from None
        if result.returncode:
            raise SystemExit(f'FAIL TLS state test: {version}, exit {result.returncode}')
    scratch.cleanup()
    print('PASS TLS 1.2/1.3 state tests', flush=True)
    raise SystemExit(0)

records = []
if embedded:
    der = ssl.PEM_cert_to_DER_cert((certs / 'ca.pem').read_text())
    for extra in (b'garbage', der):
        invalid = ssl.DER_cert_to_PEM_cert(der + extra)
        command = [str(program), '0', 'localhost', invalid, 'accept', '1.3']
        if wasm:
            command = launcher + command
        run = subprocess.run(command, capture_output=True, text=True, timeout=20)
        if run.returncode != 1 or not run.stderr.startswith('CA preparation:'):
            raise RuntimeError('Trailing DER data was not rejected before connecting: '
                               + run.stderr)
    print('PASS malformed DER rejected before network access', flush=True)
for version in ('1.2', '1.3'):
    cases = ['valid', 'wrong-hostname', 'untrusted-ca']
    if embedded:
        cases.append('default-rejects-private-ca')
    for case in cases:
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(15)
        port = listener.getsockname()[1]
        errors = []
        sni_names = []
        hostname = 'wrong.invalid' if case == 'wrong-hostname' else 'localhost'
        def serve():
            try:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                protocol = ssl.TLSVersion.TLSv1_2 if version == '1.2' else ssl.TLSVersion.TLSv1_3
                context.minimum_version = protocol
                context.maximum_version = protocol
                context.load_cert_chain(str(certs / 'server.pem'), str(certs / 'server-key.pem'))
                if require_sni:
                    def check_sni(tls, name, context):
                        sni_names.append(name)
                        if name != hostname:
                            return ssl.ALERT_DESCRIPTION_UNRECOGNIZED_NAME
                    context.sni_callback = check_sni
                peer, _ = listener.accept()
                peer.settimeout(10)
                with peer:
                    try:
                        with context.wrap_socket(peer, server_side=True) as tls:
                            if case != 'valid':
                                raise RuntimeError('Client accepted an invalid peer identity')
                            data = b''
                            while len(data) < 4:
                                part = tls.recv(4 - len(data))
                                if not part:
                                    raise RuntimeError('Premature TLS EOF')
                                data += part
                            if data != b'ping':
                                raise RuntimeError('Unexpected TLS application data')
                            tls.sendall(b'pong')
                            tls.unwrap().close()
                    except ssl.SSLError:
                        if case == 'valid':
                            raise
            except Exception as error:
                errors.append(str(error))
            finally:
                listener.close()
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        ca = ('untrusted' if case == 'untrusted-ca' else 'ca') + '.pem'
        if embedded:
            authorities = ('@default' if case == 'default-rejects-private-ca'
                           else (certs / ca).read_text())
            command = [str(program), str(port), hostname, authorities]
            if wasm:
                # No filesystem preopen: roots are compiled in or supplied as bytes.
                command = (launcher + ['-S', 'inherit-network=y', '-S', 'tcp=y']) + command
        elif not wasm:
            command = [str(program), str(port), hostname, str(certs / ca)]
        else:
            command = [*launcher, '-S', 'inherit-network=y', '-S', 'tcp=y',
                       '--dir', str(certs) + '::/certs',
                       str(program), str(port), hostname, '/certs/' + ca]
        command += ['accept' if case == 'valid' else 'reject', version]
        command += client_args
        print(shlex.join(command), flush=True)
        run = subprocess.run(command, capture_output=True, text=True, timeout=20)
        thread.join(timeout=16)
        print(run.stdout + run.stderr, end='', flush=True)
        ok = (run.returncode == 0 and not errors and not thread.is_alive()
              and (not require_sni or sni_names == [hostname]))
        records.append({'program': str(program), 'version': version,
                        'case': case, 'command': command,
                        'server_tls': ssl.OPENSSL_VERSION,
                        'exit': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr,
                        'server_errors': errors, 'passed': ok})
        program.with_suffix('.tls-results.json').write_text(json.dumps(records, indent=2) + '\n')
        if not ok:
            print('FAIL', case, errors)
            raise SystemExit(1)
scratch.cleanup()
print(f'PASS all {len(records)} TLS cases: ' + str(program))
