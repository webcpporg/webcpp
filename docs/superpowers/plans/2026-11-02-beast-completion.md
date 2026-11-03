# Complete the Beast portability implementation

The owner requests completion, publication and integration after the complete CI
passes. This continues the approved design in the Beast genesis proposal, not a
new reduction to the first working backend. Baseline: superproject `684c4fe`,
Beast `c7dfe2b`, proposals `853ce39`.

The binding specification is
`../../../../proposals/libraries/beast/openspec/changes/genesis/specs/beast/spec.md`;
its design and existing reference plan remain applicable.

## Execution and completion contract

- Work in the existing isolated checkout. The parent owns integration, TLS
  protocol tests, shared build/lint/CI changes and publication.
- Independent workers own browser adapters, WASI host APIs, and the application
  corpus. They use separate source/test paths and report required shared edits.
- Every promised supported profile requires real runtime evidence. Preserve the
  complete inventory, source adaptations and unavailable facilities explicitly.
- Native upstream applications provide the behavioural oracle. Browser results
  require a browser, not Node alone. Host HTTP must not import guest TCP/OpenSSL.
- Fresh local checks precede publication. Remote checks must run on the exact
  candidate commits before the main branches are merged. No bypass of checks or
  claim of self-approval as independent review.
- A partial backend, successful compilation alone, or an expected unsupported
  diagnostic cannot count as a completed application.

## Tasks

1. Complete browser layers, WebSocket and fetch, including cancellation, lifetime,
   allocators, limits, unsupported settings and JSPI/Asyncify real-browser tests.
2. Complete independent WASI host HTTP client/server APIs, full messages and
   supplied-stream counterparts for P2/P3, including resource and failure tests.
3. Verify Beast HTTP/WebSocket over guest TLS, peer identity, timeout, cancellation
   during transfer, normal/error/cancelled shutdown, with both exception modes.
4. Reconcile and implement all 53 applications or explicitly documented
   environment counterparts; resolve prerequisites in their owning libraries.
5. Complete the Diataxis/AsciiDoc/MrDocs guide and feature/application matrices;
   run every local lane, affected tool suite, lint and independent review.
6. Publish library candidate commits, register the Beast submodule, run library
   and superproject CI on the candidate, fix failures, then integrate only when
   the complete acceptance criteria and required checks pass.

## Decisions and evidence

- WASI host HTTP uses new independent worlds and a `host-http` target; existing
  export-only HTTP worlds remain unchanged for current consumers.
- The original upstream application corpus is immutable and hash-verified;
  adaptations remain inspectable and separately validated.
- Logs and per-domain progress are retained in `.local/beast-completion/`.
- Remote publication and CI are now authorized by the owner's current request;
  earlier no-CI restrictions do not apply to this completion phase.
