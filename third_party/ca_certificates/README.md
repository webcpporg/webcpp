# Mozilla CA snapshot

This directory preserves curl's dated PEM export of Mozilla's public root CA
certificates. `manifest.json` records its source URL, date, SHA-256 and the sorted
SHA-256 fingerprints of the DER certificates. `cacert.pem` is unchanged from the
published artifact, including its notices. The data is MPL-2.0; see
`LICENSE-MPL-2.0.txt` and https://curl.se/docs/caextract.html.

This published data artifact is intentionally a checked-in snapshot rather than
a source submodule. WebCPP's generator and updater are separately BSL-1.0.
When redistributing the embedded data, retain its MPL notice and make the
corresponding PEM source available under MPL-2.0, for example with this directory.

## Updating

From the superproject root, choose a published date from the curl CA Extract page:

```bash
python3 tools/ca_certificates/update.py --date 2026-09-25
python3 tools/test/ca_certificates_test.py
python3 tools/test/ca_certificates_b2_test.py
python3 tools/ca_certificates/run.py --fresh
```

The updater downloads the artifact and digest over verified HTTPS, validates its
certificates, and lists every added/removed DER fingerprint before replacing the
snapshot and manifest. Inspect that diff as a trust-policy change. Removal is as
important as addition. An older date is rejected. The digest records integrity;
it is not a publisher signature independent of curl's HTTPS delivery.

For an already downloaded artifact, supply `--source-file PATH --sha256 DIGEST`
with the same `--date`. The caller is responsible for authenticating that offline
artifact and digest. `--output DIRECTORY` supports staging an update for review.
An interrupted replacement is detected by the build's manifest check; restore the
pair from Git before retrying. Do not run simultaneous updates of one directory.

Normal B2 builds perform no download. `/webcpp/third_party//ca_certificates`
verifies the recorded bytes and inventory and generates immutable PEM data in a
build header. Its consumer needs no certificate files at runtime. Rebuild and
redeploy to update an already installed binary. This tool does not schedule
updates or change running applications.

`b2 install --prefix=DIR` installs the generated header at
`DIR/include/webcpp_ca_certificates.hpp`, and this directory's PEM source,
manifest, README and license at `DIR/include/webcpp/ca_certificates/`. It does
not compile or install OpenSSL. Keep those notices and source data when
redistributing an application that embeds the snapshot.

## Trust scope

The PEM export does not carry every additional trust constraint enforced by
Firefox. WebCPP does not promise Firefox's complete certificate policy, consult
the operating system's trust store, fetch CRLs/OCSP, or install private CAs.
Applications can explicitly replace the entire set through Asio's TLS client
factory. Replacement is not a union with public roots. The browser still owns
TLS for browser transports; this package does not override browser trust.
