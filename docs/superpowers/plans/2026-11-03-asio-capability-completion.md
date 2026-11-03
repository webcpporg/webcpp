# Asio Capability Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the WebCPP-owned Asio gaps and diagnose external unsupported combinations at their correct boundary.

**Architecture:** Reuse Boost and the checked private overlays, source-built OpenSSL and WASI native asynchronous resources. Keep target capability detection in config.hpp; preserve runtime errors for runtime facts.

**Tech Stack:** C++20, Boost 1.92, wasi-sdk 34.0, Wasmtime 50.0.1, Emscripten 6.0.11, B2, MrDocs/AsciiDoc.

**Spec:** docs/superpowers/specs/2026-11-03-asio-capability-completion-design.md

## Global Constraints

- English files/comments/commits, no em dash or coauthor trailer.
- Preserve allocator/executor/cancellation/deferred initiation and existing APIs.
- No installed Boost edits, no changed SDK or environment policy, no duplicate TLS provider.
- SDK/runtime blockers need reproducible evidence and explicit guards, not optimistic enablement.
- Do not hand-edit generated files; regenerate overlays and hash manifests from pristine inputs.
- Distinct build directories per concurrent task. Parent owns shared config.hpp, docs and final B2 integration.
- No push, merge, tag or remote CI in this increment. Local commands and examples are shown in chat.

## Review Focus

- UDP truncation, empty buffers and cancellation preserve one-datagram semantics.
- DNS does not block initiation or starve unrelated timers while the host is pending.
- TLS verifies trust/hostname and cancellation cannot leave borrowed state alive.
- Browser operations run on a valid thread/stack without recursive executor execution.
- A compiler guard rejects unsupported use without rejecting portable includes or supported runtime alternatives.

### Task 1: Complete WASI datagrams and P3 asynchronous DNS

**Files:** tools/boost/asio-wasip3 checked overlay/manifest and new private backend files as required; libs/asio/test/wasi_udp_gather_test.cpp, new focused DNS/datagram consumers, their own test subdirectory/Jamfile. Parent integrates root test/Jamfile and config.

**Interfaces:** Existing Asio UDP and async_resolve APIs. Both P2/P3 scalar and sequence consumers retain ordinary completion tokens. P3 S uses native async lookup without a worker pool. P2 resolver remains unchanged unless shared behavior requires correction.

- [ ] Write and run public-target RED consumers for connected gather send, scatter receive (sync/async), empty/oversize datagrams, cancellation, and P3 S deferred DNS with timer progress.
- [ ] Implement checked overlay changes with context/associated allocation and release before callbacks. Use native P3 waitable integration where required; never implement async DNS by blocking inside initiation.
- [ ] Verify P2/P3 EH twins, P3 cooperative where applicable, native controls, source hash preparation and meaningful failure cases.
- [ ] Write report with exact commands, RED/GREEN, changes and remaining external dependencies; parent reviews/integrates and commits.

### Task 2: WASIp2 TLS and Cobalt

**Files:** tools/openssl source build configuration, tools/boost Cobalt overlays/source integration, third_party/Jamfile, libs/asio/src/cobalt_main.cpp, libs/asio/test P2 TLS/Cobalt consumers. Coordinate modifications to libs/asio/build.jam with parent. Do not edit config.hpp or global docs.

**Interfaces:** Existing /webcpp/third_party//openssl and /webcpp/asio//cobalt, //tls, //cobalt_ssl gain validated P2 S/EH on/off. CA replacement/embedding contract remains identical. No new OpenSSL copy or system fallback.

- [ ] Run existing/public P2 consumers to capture deliberate baseline refusal, then register real minimal Cobalt and TLS consumers.
- [ ] Extend verified source recipe and Cobalt source/runner selection to P2. Preserve capability omission of signals, local sockets and thread APIs.
- [ ] Verify Cobalt main status, timer/TCP/UDP/resolver cancellation, real TLS trust and hostname failures, embedded/custom CAs, handshake/transfer/shutdown including cancellation under both EH modes. Retain the known no-EH pending-task move warning.
- [ ] Run native/P3 focused regressions and source build tests. Report exact evidence and changes for parent integration/review/commit.

### Task 3: Browser worker profile and environment boundary

**Files:** temporary feasibility consumers followed by tools/emscripten toolset sources and libs/asio browser implementation/tests where feasible. Parent coordinates shared build selection and config.hpp.

**Interfaces:** An explicit supported threaded browser build must coexist with existing single-thread JSPI/Asyncify. No blanket claim of DOM access from workers; do not silently switch suspension mechanisms.

- [ ] Reproduce the current public-target rejection and independently compile/run pinned Emscripten pthread consumers with each suspension mechanism in a real browser, with required isolation headers.
- [ ] If supported by the pinned environment, implement the worker executor/wakeup and main-thread handoff, preserving thread affinity, allocator/cancellation and same-context semantics. Add real-browser success/error/shutdown tests.
- [ ] For any external blocker, retain a smallest reproducible compile/runtime witness and precise diagnosis. Do not upgrade the SDK or classify missing WebCPP code as external.
- [ ] Report actual supported matrix, code changes, test commands and guard requirements for parent integration/review/commit.

### Task 4: Central config guards, documentation and final verification

**Files:** libs/asio/include/webcpp/asio/config.hpp and feature headers, libs/asio/build.jam/test/Jamfile, targeted tools/build tests, Asio AsciiDoc/MrDocs, root guidelines/agents and proposal scope/status.

**Interfaces:** Derived WEBCPP_ASIO capability macros with 0/1 values, optional dependency selection separate from platform availability, explicit compile-time requirement diagnostics. Existing generic/browser settings headers remain usable.

- [ ] Write positive/negative compiler consumers proving capabilities cannot be forged, optional dependencies are required only by their features, unsupported known profiles fail clearly and runtime alternatives remain usable.
- [ ] Implement central detection and header/build guards using final verified Task 1-3 outcomes. Runtime network permissions and blocking host calls remain documented error/behavior boundaries.
- [ ] Update feature tables with evidence and dependency ownership, include compiled examples, reconcile approved proposal and guideline scope without declaring publication complete.
- [ ] Run affected Release suites from scratch, focused tools/lint, MrDocs/rendered checks and proposal validation. Review delegated tasks and the complete candidate, fix important findings with RED/GREEN evidence.
- [ ] Commit scoped library/root/proposal changes and report completed work plus externally blocked cases, with no implicit CI/merge claim.
