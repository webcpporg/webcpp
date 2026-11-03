# Cobalt SSL Cancellation Verification Plan

> Execute inline using superpowers:executing-plans and test-driven-development,
> followed by one independent review of this follow-up's changes.

**Goal:** Verify encrypted transfer cancellation and failed/cancelled TLS shutdown
through the public Cobalt SSL target on native and WASIp3; fix reproduced defects.

**Architecture:** A new real loopback TLS executable reuses the existing temporary
certificate harness and public B2 dependency. Exercise primitive and composed
transfers. Observe received application data, TCP backpressure and close_notify
before cancellation; do not use timing guesses to arrange an operation's state.

**Tech stack:** Boost 1.92, source-built OpenSSL 3.5.9, B2, wasi-sdk 34,
Wasmtime 49.0.3, native macOS arm64.

**Spec:** The user's latest request authorizes these additional tests and any
necessary fixes, on native/WASIp3, with local progress and no CI.

## Constraints and review focus

- Reuse this isolated checkout and preserve all pre-existing uncommitted work.
- No CI, push, merge or commit. Never modify installed Boost or generated files.
- Existing supported matrix: native single/multi EH on/off; WASIp3 single EH
  on/off and cooperative multi EH off. This is build-profile coverage, not a
  claim of concurrent access to one SSL stream.
- A cancellation must originate from a Cobalt promise, preserving the handler's
  cancellation slot. Do not substitute socket.close/cancel for that action.
- Confirm operations are pending. Check operation_aborted and partial byte counts.
- Confirm an incomplete shutdown reports stream_truncated, not successful EOF.
- Failed/cancelled shutdown must clear secure state and block application I/O.
- Cancellation is terminal in these tests: close the socket afterward. Do not
  promise recovery, rollback of transmitted bytes, or safe connection reuse.
- Test-only changes may pass immediately because existing behavior is being
  characterized. Use deliberate isolated mutations to prove the tests detect
  dropped cancellation and missing shutdown state updates before completion.

## Task 1: Tests, fixes and matrix

- [x] Add tools/openssl/test/cobalt_ssl_cancel.cpp and its explicit Jamfile target.
  Read/write_some and composed read/write use real verified TLS; a partial read
  and bounded socket buffers make progress and backpressure observable.
- [x] Run the test with tls.py --state-test first on native, then WASIp3.
  Expected: six scenarios per TLS version pass, or a reproducible diagnostic
  identifies a defect to investigate before editing production code.
- [x] Prove the tests fail under isolated cancellation/state mutations. Restore
  the ordinary configuration and run all seven Release profiles, plus the
  existing TLS/state and relevant Asio regressions if production changes occur.
- [x] Update AsciiDoc evidence and maintainer guidance using webcpp-documentation.
  Run formatting, scoped lint, clang-tidy, documentation build and review.

## Evidence and rulings

- Initial production state is the completed shared SSL patch from the preceding
  task; no production code changes are presumed necessary.
- Pre-flight: the executable uses the existing four-argument state-test fixture
  interface; no new certificate generator or network service is needed.
- RED: `.local/cobalt-ssl-cancel-red-native.log` shows primitive cancellation
  succeeding, followed by composed read cancellation hanging until the watchdog.
  Boost 1.92's composition promise did not attach its state to the received
  handler's cancellation slot.
- Ruling: add a checked `tools/boost/cobalt-common` header overlay to the core
  archive and its usage requirements. Connect the source after moving the handler
  into the promise. This fixes compiled read/write and user-defined compositions
  on every Cobalt target, without introducing an OpenSSL dependency. It pins
  this patched integration to Boost 1.92 until the patch is rebased and verified.
- GREEN: initial native and WASIp3 single/EH-on runs pass all six cases with
  TLS 1.2/1.3 after the common fix. No additional SSL wrapper change was needed.
- An initial uninstrumented WASIp3 run hit the watchdog during the write case.
  Subsequent isolated runs passed; the full matrix later exposed a concrete
  cancellation/completion race in the fixture, described below. The earlier
  watchdog alone does not establish another backend defect.
- Independent review found one important fixture issue, also reproduced by
  `.local/cobalt-ssl-cancel-wasi-coop-off-cancel.log`: TCP backpressure does not
  exclude a queued successful SSL completion. The old primitive writer loop
  began another await after cancellation and triggered throw_if_cancelled.
- Ruling: each cancellable primitive promise now performs exactly one write.
  An uncancelled parent controls filling the transport. If cancellation loses
  to a successful completion, close that connection and retry with a new one,
  at most eight times. Require a real operation_aborted; never manufacture one
  from coroutine state. Observable data/readiness drives setup; the watchdog
  bounds failure, rather than an arbitrary number of scheduling turns.
- `.local/cobalt-ssl-cancel-mutations.log`: five isolated negative controls
  pass. Dropping transfer cancellation is detected for read_some and write_some;
  dropping shutdown state updates fails both shutdown cases; relinking the
  unmodified upstream read composition reproduces lost cancellation. These
  controls do not alter normal build inputs or the installed Boost tree.
- `.local/cobalt-ssl-cancel-core-regression.log`: four core B2 tests pass,
  including an application-defined composed timer cancelled through its promise,
  native and JSPI/Asyncify with EH on/off. The public header and compiled library
  receive the same common patch.
- `.local/cobalt-ssl-cancel-b2-regression.log`: all four SSL build tests pass,
  including optional OpenSSL, checked sources, native/WASI paths with spaces and
  unique transitive OpenSSL linkage.
- Scoped lint, clang-format, clang-tidy and Pyright pass. The source and rendered
  documentation checks pass in `.local/cobalt-ssl-cancel-doc.log`.
- Review exclusions remain explicit: connection reuse after terminal cancellation,
  concurrent access to one SSL stream, separate cancellation-type guarantees and
  the rest of Boost are outside these tests. Only macOS native runtime is measured;
  no Linux or Windows runtime validation is claimed. No CI, push, merge or commit.
- Final verification: `.local/cobalt-ssl-cancel-final.log` exits zero for the
  current source in all seven Release profiles. Six cases times two TLS versions
  times seven profiles establish 84 distinct combinations. Each WASIp3 profile
  passes three complete repetitions. Every completed write case records a real
  interruption, including when the fixture must retry a raced completion.
- `.local/cobalt-ssl-cancel-matrix.log` records successful existing Asio tests,
  examples and ordinary/buffered TLS/state regressions in all seven profiles.
  Its final cancellation step caught the earlier fixture race; the corrected
  cancellation executable is verified by the separate final log above. Preserve
  both logs rather than presenting the earlier failing matrix as wholly green.
- Final review resolution: the sole important finding is addressed by the
  one-operation promise and fresh-connection retry, with the lost-cancellation
  negative control proving that successful writes do not falsely satisfy it.
  The installed and patched hashes of all three Cobalt overlays remain verified.
