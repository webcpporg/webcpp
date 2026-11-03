# Cobalt SSL Wrapper Integration Plan

> Execute inline with superpowers:executing-plans, followed by one independent review.

**Goal:** Enable Boost.Cobalt's own SSL stream through an optional B2 dependency
on native and WASIp3, with reproduced defects fixed and verified local TLS.

**Architecture:** Reuse the existing Cobalt archive, runner, OpenSSL source build
and CA bundle. Compile `io/ssl.cpp` in a separate static library, with a checked
private header/source patch shared by its consumers. The WASIp3 capability
overlay remains platform-specific. Installed Boost files remain untouched.

**Tech stack:** Boost 1.92, OpenSSL 3.5.9, B2, wasi-sdk 34, Wasmtime 49.0.3.

**Spec:** The user approved reproducing and correcting the SSL wrapper issues,
adding native/WASIp3 B2 support, and showing local code/tests without CI.

## Constraints and decisions

- Use the existing isolated checkout; preserve unrelated uncommitted work.
- No CI, publishing, push, merge or commit during this task.
- Public dependency: `/webcpp/asio//cobalt_ssl`; low-level compiled dependency:
  `/webcpp//boost_cobalt_io_ssl`. OpenSSL remains optional for plain Cobalt.
- Native single/multi and EH on/off; WASIp3 single EH on/off and cooperative
  multi EH off. Preserve the explicit refusal of unavailable cooperative EH.
- Reuse CA preparation and retain the Cobalt issue-287 warning without EH.
- Correct the verification callback constraint and expose the underlying SSL
  handle with an unambiguous `native_ssl_handle()` accessor, preserving the
  existing socket `native_handle()` interface.

## Review focus

- A successful handshake must switch reads/writes to TLS before resuming users.
- Failed/cancelled handshakes must not permit plaintext application fallback.
- Repeated handshakes, buffered handshakes and shutdown must follow coherent state.
- Certificate verification, hostname and SNI must reach the actual SSL connection.
- Patches, archive and consumers must agree; plain Cobalt must remain independent.

## Tasks

- [x] Reproduce the upstream state bug with a real loopback TLS server and the
  callback compilation error; preserve the commands and output as local evidence.
- [x] Add wrapper regression tests for encrypted traffic, secure state, certificate
  rejection, hostname/SNI, buffered handshake, cancellation and shutdown. Observe
  failures before correcting the wrapper.
- [x] Add the checked shared SSL patch and optional compiled B2 targets. Reuse the
  existing patch preparation engine with an explicit bundle argument and tests.
- [x] Run the wrapper TLS suite in all seven supported profiles; check ordinary
  consumers, patch integrity and negative target configurations. Run the existing
  Asio suite and native/browser Cobalt controls for regression coverage.
- [x] Update the AsciiDoc guide/matrix and maintainer instructions. Run focused
  lint, format, documentation checks and independent review; resolve findings.

## Evidence

- `.local/cobalt-ssl-red.log`: unmodified upstream wrapper completes a real TLS
  handshake with `secure=0`, then writes five plaintext bytes; the Python/OpenSSL
  server rejects them with `RECORD_LAYER_FAILURE`.
- `.local/cobalt-ssl-callback-red.log`: hostname verification fails to compile
  because the constraint uses `ssl::context` rather than `ssl::verify_context`.
- `.local/cobalt-ssl-target-red.log`: public dependency does not exist initially.
- `.local/cobalt-ssl-bundle-red.log`: preparation initially refuses `--bundle`.
- Native normal and buffered TLS matrices pass after the patch. Native and
  WASIp3 state tests pass real buffered ClientHello, STARTTLS, state-at-await-time,
  shutdown, handshake cancellation and blocked plaintext after failure.
- Ruling: inherited completion-handler associations preserve the executor,
  allocator, cancellation slot and immediate executor together. Replacing them
  with an unbound lambda would lose cancellation; the pending-handshake test
  observes cancellation through the Cobalt promise, not direct socket cancellation.
- Ruling: nested OpenSSL dependencies exposed non-idempotent fingerprinting.
  `.local/cobalt-ssl-dedup-red.log` records two distinct archives for equivalent
  compiler settings. Cache the fingerprint by immutable property set;
  `test_transitive_openssl_is_unique` now passes. This is a required integration
  correction to avoid linking two OpenSSL copies, not a change to its build recipe.

## Final local verification

- `.local/cobalt-ssl-matrix.log`: Release tests and examples pass in all seven
  profiles: native single/multi with EH on/off, WASIp3 single with EH on/off,
  and WASIp3 cooperative multi with EH off. Each profile runs the public target.
- The wrapper matrix passes 112 TLS scenarios, 28 malformed-DER rejection
  checks, and 14 state-test executions. These cover TLS 1.2/1.3, certificate
  and hostname verification, SNI, encrypted ping/pong, STARTTLS, nonempty
  buffered ClientHello, successful shutdown, handshake cancellation, and
  blocked application I/O after handshake failure/cancellation or shutdown.
- `.local/cobalt-ssl-build-tests.log`: all four B2 integration cases pass,
  including paths with spaces, source checksum rejection, optional OpenSSL,
  unsupported targets and one transitive OpenSSL archive. The optional-source
  case passes again after applying the native-path lint correction.
- `.local/cobalt-ssl-openssl-regression.log`: all five existing OpenSSL build
  checks pass. `.local/cobalt-ssl-source-regression.log`: existing Cobalt source
  integration checks pass, including native/Emscripten exception variants.
- `.local/cobalt-ssl-browser-regression.log`: JSPI and Asyncify exact-exit
  checks pass with and without exceptions, using the Emscripten toolset.
- The patch preparation unit test, scoped source lint, clang-format, clang-tidy
  and Pyright pass. `.local/cobalt-ssl-doc.log` records successful AsciiDoc
  generation, source checks and rendered HTML checks. No visual browser
  inspection is claimed.
- Independent review found no actionable defect. Its suggested additional
  shutdown-error/cancellation tests remain outside the verified matrix;
  successful shutdown and pending-handshake cancellation are tested separately.
  Encrypted data-transfer cancellation also remains explicitly unverified.
- Native runtime evidence is macOS arm64. Linux, Windows, browser SSL, WASIp2
  and WASIp3 cooperative EH-on are not established by this run. Existing
  no-exceptions issue-287 warnings and cooperative-thread limits are preserved.
- No CI, push, merge or commit was performed.
