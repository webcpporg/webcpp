# Embedded CA certificates implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Supply a pinned Mozilla CA bundle through B2 and a native/WASIp3 TLS
client factory that defaults to embedded roots and supports complete replacement.

**Architecture:** The third-party data snapshot retains its MPL-2.0 notices.
A Python updater downloads a dated curl export and checks its published digest,
validates certificates, reports additions/removals, and writes a manifest. A B2
generator verifies the snapshot and emits immutable PEM data in a private header.
The Asio factory returns `boost::system::result<ssl::context>` and never adds
system roots or default roots when the caller supplies a replacement bundle.

**Tech Stack:** Python 3.9+, B2, C++20, Boost.Asio/System, source-built OpenSSL.

**Spec:** The contract below implements the user's approved design in this chat.

## Contract and constraints

- No CI, push, merge, or changes to upstream OpenSSL. Keep existing local changes.
- `/webcpp/third_party//ca_certificates` embeds data without runtime files/network.
- `/webcpp/asio//tls` links the helper's dependencies; existing raw SSL stays intact.
- `make_tls_client_context()` uses the pinned bundle; the `std::string_view`
  overload uses only its PEM input. Empty, malformed, or partially invalid input
  returns an error and no usable context. Verification is enabled, TLS >= 1.2.
- Hostname verification/SNI remain per-connection application responsibilities.
- No-exceptions builds receive errors as values. OpenSSL owns its allocations.
- No system trust import, runtime updater, Firefox policy parity, or revocation
  fetching. An embedded bundle is updated by rebuilding and redeploying.
- Updating roots is explicit, dated and reviewable, including removals. Hashes
  provide integrity against the recorded pin, not independent publisher identity.
- Data snapshots are an authorized exception to source-code submodules: curl's
  dated PEM export is a published artifact, preserved byte-for-byte with a digest.

## Review focus

- Replacing roots must remove public trust, not append corporate trust to it.
- Truncated input after a valid certificate must not silently succeed.
- Missing/corrupt snapshot must fail the build that uses it, never fall back.
- WASIp3 must work without preopened certificate directories.
- Updates must reject bad hashes before changing the current snapshot.

### Task 1: Snapshot, updater and B2 target

- [x] Write CLI tests for import, repeat import, bad hash, malformed input,
  fingerprint changes, and generated-header corruption detection; run RED.
- [x] Implement `tools/ca_certificates/{bundle,update,generate}.py` and acquire
  the dated bundle/license under `third_party/ca_certificates`.
- [x] Add the B2 target and a scratch consumer test, including path spaces and
  rebuilding after input changes. Run Python and B2 checks locally.

### Task 2: TLS client context and real connections

- [x] Write C++ tests for default trust, replacement, empty/malformed/truncated
  PEM, verify mode, and protocol floor. Observe missing API failure.
- [x] Implement `libs/asio/include/webcpp/asio/tls_client_context.hpp` and `/tls`.
- [x] Extend real TLS driver to run embedded default rejection and supplied CA
  success/wrong-host/untrusted-CA cases without filesystem grants in WASI.
- [x] Run Release native single/multi EH on/off and WASIp3 single EH on/off,
  cooperative multi EH off. Keep bounded localhost TLS fixtures.

### Task 3: Examples, docs and review

- [x] Add a compiled example and AsciiDoc guidance for updates and substitution;
  update the feature matrix and MrDocs coverage using webcpp-documentation.
- [x] Run formatting, Python static analysis, relevant local tests and rendered
  documentation. Review changes independently and resolve concrete findings.
- [x] Record commands/results here and report limitations. Leave changes local.


## Completion evidence (2026-10-16)

- The snapshot updater downloaded the dated curl artifact and matched published
  SHA-256 `a41b5d356aea97a529fe27e0f7316d2f9d946d75927476cf9cf1b90637d00505`:
  121 CAs, original PEM and MPL license retained.
- `python3 tools/test/ca_certificates_test.py`: two CLI integration cases passed,
  including corrupt digest, malformed/truncated/duplicate certificates, trailing
  DER, rollback prevention, removals and build-header validation.
- `python3 tools/test/ca_certificates_b2_test.py`: two scratch B2 cases passed,
  including paths with spaces, incremental rebuild, corruption and lazy lookup.
- `python3 tools/ca_certificates/run.py --fresh`: seven Release profiles passed,
  56 real TLS cases and 14 malformed-DER cases rejected before network access.
  Profiles: native single/multi with EH on/off; WASIp3 single with EH on/off;
  WASIp3 cooperative multi with EH off. Each also ran the C++ factory checks.
  Evidence: `.local/ca-matrix-final.log` and `.local/ca-integration/`.
- Native regression: `b2 -a variant=release toolset=clang libs/asio/test
  libs/asio/example` passed with 40 passed markers; examples compared output.
- Browser unsupported-target check passed. The native example passed B2's output
  comparison; WASIp3 example passed `tools/example/run_example.py` with the full
  Wasmtime command and no certificate preopen. Its B2 launch attempt with flags
  in `testing.launcher` was a command error: the example driver accepts only an
  executable as launcher. Direct command comparison is the recorded WASI check.
- Focused clang-tidy on the native test/header and example passed. Pyright,
  clang-format and source rules passed. MrDocs/reference, doc-check, HTML
  conversion and rendered-check passed. No full-tree lint or CI was run.
- Independent read-only review found acceptance of trailing DER and a future
  date-sensitive build test. The real Python CLI and TLS executable reproduced
  the DER issue before the fix. Complete DER consumption now rejects it; the
  manifest fingerprint matches the actual loaded certificate. The build test
  takes its date from the snapshot instead of a fixed calendar date.
- No push, merge, or commit. Existing OpenSSL/WASIp3 working-tree changes were
  retained. Native runtime evidence is macOS arm64; Linux/Windows are not newly
  validated. Root update scheduling, runtime refresh, native system trust,
  complete Firefox constraints and revocation fetching remain outside scope.
