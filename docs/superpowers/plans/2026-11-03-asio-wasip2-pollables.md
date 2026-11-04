# Asio WASIp2 pollables and supplied WebSocket implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Run Asio timers, TCP, UDP and asynchronous name resolution on WASIp2, report unsupported facilities explicitly, and run both supplied-channel WebSocket examples with exceptions on and off.

**Architecture:** Preserve Boost.Asio's scheduler and protocol implementations. Reuse wasi-libc's P2 socket/readiness translation where it preserves the contract; connect any additional native P2 pollables through a checked private Boost overlay. Supplied WebSocket channels use the same executor, preserve partial I/O and report cancellation through ordinary completion handlers.

**Tech Stack:** C++20, Boost 1.92, wasi-sdk 34.0, Wasmtime 50.0.1, B2.

**Spec:** The owner approved both designs in this conversation on 2026-11-03. This document records that approved scope and the implementation choices below. This supersedes the earlier exclusion of Asio P2 sockets, but does not declare untested Cobalt, TLS or thread variants supported.

## Global constraints

- Work in the existing isolated checkout; preserve the preceding closure commits.
- Preserve native, Emscripten and WASIp3 behavior and private overlay hash checks.
- Start with single-threaded P2, exceptions on/off; reject unsupported thread configurations at build time.
- Keep unavailable static APIs distinguishable from runtime capability denial and unsupported socket options.
- Preserve deferred initiation, associated allocator/executor/cancellation, and completion outside initiation.
- Do not rewrite WebSocket framing or silently replace the supplied channel with TCP.
- Generated application files and matrices change only through their generators.
- Local tests first; final remote CI and merge still follow the existing authorized closure process.
- No tags or release publication.

## Review focus

- Idle waits, timer deadlines and an operation becoming ready during registration must not spin or lose wakeups.
- Cancelling or destroying a pending DNS/read/write operation must not leave borrowed buffers or invoke handlers twice.
- Unsupported calls must produce deliberate diagnostics or errors, not traps from absent POSIX facilities.
- A slow consumer and full output pipe must not be advertised as bounded cancellation when the host import blocks.
- Exceptions-off, associated allocation and native/P3 regressions need actual compiled consumers.

### Task 1: P2 Asio core, sockets and deliberate diagnostics

**Files:** `tools/boost/asio-wasip3/{boost-1.92.patch,manifest.json,Jamfile}`, `libs/asio/{build.jam,test/Jamfile}`, new `libs/asio/test/wasip2` consumers, Asio capability documentation.

**Interfaces:** Existing `webcpp::asio::io_context`, timers and IP socket types; `/webcpp/asio//asio` gains P2 single-thread support. Existing unsupported optional targets retain clear build errors until validated separately.

- [x] Add a P2 public-target consumer for timer, TCP/UDP echo, partial transfer, refusal and cancellation; run it against the current target and record the missing-port failure.
- [x] Inspect pinned wasi-libc readiness and reuse its `select`/`poll` to `wasi:io/poll` path. Extend only the necessary private overlay guards and build configuration.
- [x] Add consumer-level negative checks for unsupported thread/API/operation paths, paired with valid controls.
- [x] Run `b2 -a toolset=clang-wasip2` consumers in Wasmtime with real network grants, exceptions on/off, plus native/P3 regression consumers. Expected: correct payloads, callbacks and intentional diagnostics.
- [x] Commit the library and superproject changes with their evidence.

### Task 2: Pollable-based asynchronous DNS

**Files:** Asio resolver implementation and checked overlay, P2 resolver consumers and real peer driver.

**Interfaces:** `async_resolve` retains Asio completion-token semantics, owns host/service inputs and maps WASI DNS errors to values. No resolver worker thread or synchronous DNS call inside initiation.

- [x] Add a real lookup test with deferred initiation, cancellation and independent ready work. Record the existing unsupported behavior.
- [x] Integrate P2 address-stream pollables with the scheduler, preserving resource lifetime and associated allocation.
- [x] Run successful, invalid-name, cancellation and context-destruction cases in both exception profiles, plus unaffected native/P3 cases. Expected: no inline completion, no duplicate callback, no leaked resources.
- [x] Commit implementation and contract evidence.

### Task 3: Supplied-channel WebSocket on P2

**Files:** `libs/beast/include/webcpp/beast/websocket.hpp`, `libs/beast/build.jam`, supplied-channel adapters and application generator, `libs/beast/test/applications/streams`.

**Interfaces:** The existing WebSocket engine consumes a supplied byte-stream adapter and the P2 executor. The application retains ownership of its channel; WebSocket close is not invented Unix descriptor ownership.

- [x] Enable the two P2 application test consumers first and record their actual compile/runtime failure.
- [x] Implement readiness-driven asynchronous partial read/write and cancellation for supplied channels, preserve synchronous operations, and remove unnecessary socket-target coupling.
- [x] Verify actual upgrade, text/binary and fragmented frames, ping/pong, close, truncated input and pending-operation cancellation. Exercise slow consumers with documented host-blocking boundaries.
- [x] Run P2 EH on/off, native and P3 stream lanes from scratch. Expected: four formerly blocked P2 cells have real passing evidence.
- [x] Commit the adapter, applications and evidence.

### Task 4: Matrices, regression verification and review

**Files:** Asio/Beast guides and agents, matrix generator, root build/CI registration and proposal records.

- [x] Update approved P2 scope and per-feature/profile declarations; keep TLS, Cobalt and thread support separate from core support.
- [x] Regenerate the matrix using runtime evidence, not optimistic status replacements.
- [ ] Run all declared Asio/Beast local suites, focused build/tool tests, changed-code lint and documentation generation from scratch.
- [x] Obtain one fresh review, fix important findings with reproductions, and preserve remaining limitations explicitly.
- [ ] Continue exact-candidate CI/merge closure without claiming an older green run validates these changes.


## Verification record, 2026-11-03

The two approved implementation paths are committed locally. Broader release/CI gates
remain separate and are not inferred from the earlier green superproject commit.

- Asio commit: `dad1aef`, WASIp2 core/DNS and supplied CLI streams.
- Beast commit: `ab95e84`, supplied-channel WebSocket client/server and matrix.
- Fresh Release default suites plus supplied-stream lanes: native 138, WASIp3 131,
  WASIp2 68 passing B2 test targets, including compile/header and runtime targets.
  Each run covered exception handling on/off. No failed actions remained.
- Focused clang-tidy: 20 translation-unit configurations passed, covering both EH modes.
  Changed-file formatting, text rules and Pyright passed. Asio/Beast documentation rendered.
- Build-profile tests cover public target selection, P2 multi/Cobalt/TLS rejection,
  the SDK ABI refusal and the unchanged P3 profile contracts. CI matrix tooling passed.
- One fresh review found idle empty-poll trapping and quota narrowing. Consumer regressions
  failed before each fix and passed afterward. Added ready-at-registration and pending-write
  cancellation witnesses. The quota fixture models the host ABI; it does not claim every
  real host is nonblocking.
- WASIp2 supplied WebSocket cells now pass: client/server, EH on/off. The generated corpus
  matrix is 571 passed, 216 blocked, 432 platform-unavailable. P2 raw-socket Beast corpus
  integration remains blocked; core TCP support alone is not application evidence.

Decisions: reuse libc select/poll, pin the private descriptor ABI, retain deferred DNS
initiation and upstream public-result allocation, and keep host-blocking writes explicit.
The ABI bridge must be revalidated on SDK updates. No CPU-thread, guest TLS, Cobalt,
Unix addressing or host WebSocket-upgrade capability is implied for P2.

### Additional local regression, 2026-11-03

A fresh Emscripten Release build passed 271 B2 test targets with no unexpected
failures or skipped dependencies, updating 2,941 build targets. It covered the
Asio/Beast default tests/examples and Asio Asyncify/Cobalt lanes with EH on/off.
This is Node-based Emscripten regression evidence, not a fresh complete real-browser
or remote-CI run. The implementation commits above are unchanged.

Proposal commit `5a1fcb6` records the scope amendment and exact committed reference
trees (182 Asio files, 774 Beast files), with Git blobs and executable modes verified.
All 23 proposals pass their structural check, all 17 proposal-tool tests pass and
strict OpenSpec validation passes in all 15 roots. Root `b2 check-release` passed
for `e80ffab` after the implementation commits. The later local documentation-only
verification record does not replace the pending exact-candidate remote CI.

The full compilation-database preparation completed successfully with 1,419 commands.
It includes Asio P2 aggregate commands with and without exceptions and prepares the
checked overlays and generated dependencies used by the lint. This is preparation
and aggregate compilation evidence, not a claim that all 1,419 commands received
clang-tidy in this increment; the focused 20-configuration result above remains its
actual static-analysis scope.
