# Cobalt WASIp3 Integration Plan

> Execution: implement in this session, then obtain an independent review.

**Goal:** Make `/webcpp/asio//cobalt` usable through B2 on WASIp3, reusing
the tested runner and Asio port, with explicit platform capability limits.

**Architecture:** Preserve installed Boost and its source tree. Apply a
version-checked patch to a private copy of the affected Cobalt headers and
sources. Propagate the same Asio overlay and thread configuration to the
compiled Cobalt archive and its consumers. Keep OpenSSL optional.

**Constraints:** Boost 1.92, wasi-sdk 34, Wasmtime 49.0.3; native and browser
behavior preserved. Single-thread builds support exceptions on/off. Cooperative
builds use the SDK's available no-exceptions runtime. No CI, push or merge.
All source, comments and documentation are English.

## Review focus

- A public-target consumer must link the archive, not a hand-picked source subset.
- Unsupported local sockets, signals and serial ports must not break IP APIs.
- Archive and application must agree about headers, threading and exceptions.
- Patch preparation must reject mismatched inputs and preserve installed files.
- Failed connections, cancellation and TLS peer verification retain error channels.

## Tasks

- [x] Reproduce the public B2 target rejection and register the existing Cobalt
  network and timer programs for WASIp3. Add tests of Cobalt's own I/O wrappers.
- [x] Generate the checked compatibility overlay and integrate it into the
  compiled Boost target. Enable the public target for WASIp3, preserving WASIp2
  rejection and the non-fatal no-exceptions diagnostic.
- [x] Validate ordinary consumers, I/O wrappers and optional TLS through B2 in
  the available profiles. Test build preparation, native/browser controls and
  explicit rejection of unavailable SDK configurations.
- [x] Update AsciiDoc capability matrices and build instructions, run focused
  lint/documentation checks and obtain a fresh independent review.

## Evidence

- Initial `b2 -n toolset=clang-wasip3 variant=release libs/asio//cobalt`
  rejects WASI in `cobalt-platform`, before application compilation.
  The first invocation also exposed an old Python on PATH; subsequent commands
  use Homebrew Python through PATH.
- Final local Release matrix passed: native single/multi with exceptions
  on/off, plus WASIp3 single with exceptions on/off and cooperative multi
  without exceptions. Native single and all WASIp3 profiles ran the complete
  Asio tests and examples; native multi ran the focused Cobalt tests. All seven
  profiles ran the Cobalt I/O wrapper test.
- The public-target Cobalt TLS client passed eight TLS scenarios and two
  malformed-CA cases per profile: 56 TLS and 14 malformed-CA checks in total.
  This uses Asio SSL streams with Cobalt tokens, not Cobalt's omitted SSL source.
- Existing native/Emscripten Cobalt source-selection tests and JSPI/Asyncify
  exception-on/off runtime and exact-exit controls passed.
- Preparation tests and two build tests passed, including a path containing
  spaces, source-integrity rejection and native isolation. All 11 original
  Boost inputs retain their recorded hashes; generated copies match the patch.
- WASIp2 and WASIp3 cooperative/exception-on configurations were explicitly
  rejected with their intended diagnostics.
- Independent review found one validation gap: refused TCP connections. Added
  that case and UDP receive cancellation, then reran the I/O tests in all seven
  profiles and the thread test in all three multi profiles successfully.
  An initial bound-but-not-listening setup timed out on macOS, reproduced with
  Python sockets independently of Boost. The test now closes the selected local
  port before connecting and checks the exact connection-refused error.
- Focused source/style checks, Pyright and Clang-Tidy passed. The local
  documentation build and its rendered-HTML validation passed. Browser visual
  inspection of the local file was unavailable because the browser rejects
  file URLs; no visual-layout claim is made.
- No CI, push, merge or commit was performed.
