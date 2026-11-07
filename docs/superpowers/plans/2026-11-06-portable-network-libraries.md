# Portable Network Libraries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Asio, Cobalt and Beast with native Boost identity and explicit, build-system-independent WebAssembly adaptations.

**Architecture:** Native facades forward to Boost. Wasm implementations are shipped under explicit library-owned paths and selected through config, with one coherent Asio backend for all three libraries. B2 and external consumers compile those same files without applying patches.

**Tech Stack:** C++20, Boost 1.92, Emscripten 6.0.11, WASI SDK 34, Wasmtime 50.0.1, B2, CMake, Python, AsciiDoc and MrDocs.

**Spec:** `docs/superpowers/specs/2026-11-06-portable-network-libraries.md`.

## Global Constraints

- Work in the existing isolated checkout, preserving the unfinished Cobalt extraction.
- No remote CI, push, merge or publication during local implementation. On
  2026-11-07 the owner authorized remaining-work item 6: coordinated commits,
  publication, remote CI and integration after successful verification.
- Native upstream-equivalent types are actual Boost types; extensions are documented separately. The owner explicitly approved a corrected native Cobalt SSL wrapper after its upstream failures were reproduced.
- No consumer-time patches or replacement Boost include-tree precedence.
- Keep one Asio backend and one optional OpenSSL/CA provider per program.
- Preserve the browser scheduling default of 100 and all existing benchmark dimensions.
- Preserve immutable upstream examples; counterpart and runtime identities remain separate.
- All written artifacts use English, BSL/provenance notices and no em dash.

## Review Focus

- Header include order must not silently select a different backend (task 2).
- Compiled sources and consumers must agree on EH/thread/backend configuration (task 3).
- Native custom executors and traits must retain Boost identity (tasks 1 and 3).
- An unpacked distribution must not resolve hidden checkout/cache paths (task 5).
- An unavailable host facility must not become a fake successful example (tasks 4 and 6).

### Task 1: Native facade identity

**Files:** `tools/test/native_network_identity_test.py`,
`tools/test/fixtures/native_network_identity.cpp`,
`libs/asio/include/webcpp/asio/io_context.hpp`, `libs/asio/test/names_test.cpp`,
`libs/beast/include/webcpp/beast/websocket.hpp`,
`libs/cobalt/include/webcpp/cobalt.hpp` and corresponding configuration/docs.

**Interfaces:** Consume existing public headers plus installed Boost. Produce a
direct-compiler consumer whose context, timer, sockets, task/promise/generator and
WebSocket types are identical to Boost, with timer and HTTP behavior checked.

- [x] Write the real consumer and bounded driver; compile without B2/overlays.
- [x] Observe failures for the derived Asio context, missing Cobalt facade and Beast stream identity.
- [x] Add native forwarding, preserving existing Wasm implementations. Scope browser option tests to the browser API.
- [x] Run direct native consumer with both include orders and EH on/off, then relevant B2 regressions.
- [x] Commit explicit files and record that compiled Cobalt/source selection remains task 3.

### Task 2: Shipped Asio backend

**Files:** `libs/asio/include/webcpp/asio/config.hpp`, public facade headers,
new `libs/asio/include/webcpp/asio/detail/backend/`,
new `libs/asio/upstream/` synchronization manifest/tool, `libs/asio/src/`,
`libs/asio/build.jam`, `tools/boost/asio-{wasip2,wasip3,windows}/`,
new `libs/asio/test/distribution/` consumers.

**Interfaces:** Public `<webcpp/asio/...>` includes select native Boost or the
shipped Wasm implementation. Explicit source inventory identifies browser, P2
pollable and P3 waitable units and SDK contracts.

- [x] Add failing clean-distribution timer/TCP/UDP/DNS consumers for P2/P3 and browser timer/Promise consumers.
- [x] Import the pinned source and incorporate verified corrections with maintained provenance, namespace/guard isolation and explicit includes.
- [x] Move owned SDK adapters beside the library; keep deterministic SDK/version diagnostics and explicit configuration inputs.
- [x] Make B2 compile the shipped files; remove native Windows hidden patch selection and record the upstream limitation with its regression.
- [x] Run include-order/custom-token/multi-TU cases and existing network/cancel/thread tests; trace dependencies to reject overlay paths.
- [x] Commit the independently validated Asio distribution and its test evidence.

### Task 3: Native and Wasm Cobalt source selection

**Files:** `libs/cobalt/include/webcpp/cobalt/`, `libs/cobalt/src/`,
`libs/cobalt/build-support/`, `libs/cobalt/build.jam`,
`libs/cobalt/upstream/`, `libs/cobalt/test/`, old compatibility aliases.

**Interfaces:** Native public types and compiled core/runner use matching upstream
Boost. Wasm uses shipped Cobalt adaptations over task 2's backend; core, runner and
SSL stay separate targets.

- [x] Add source/link witnesses rejecting local native corrections and consumer-time patching; add executor/token/custom-main/entry-point runtime cases.
- [x] Import the adapted Wasm implementation and facade headers, retaining licenses and correction provenance.
- [x] Select unmodified native core sources and the native runner; keep known upstream regressions separate from Wasm corrections and issue-287 diagnostics.
- [x] Deliver the explicitly approved corrected native SSL wrapper as a separate type/source and rerun the native TLS state/cancel suite.
- [x] Run all current Cobalt operation/application/browser/TLS tests on their actual applicable profiles, including flags-mismatch and mixed-alias checks.
- [x] Commit coordinated Cobalt ownership/aliases and update the genesis plan/status without promoting historical results.

### Task 4: Beast backend audit

**Files:** `libs/beast/include/webcpp/beast/`, `libs/beast/build.jam`,
`libs/beast/test/`, application generators and matrices; shared WASI binding recipes.

**Interfaces:** Existing message/browser/host/socket/TLS entry points consume the
same selected Asio backend; native types remain upstream identities.

- [x] Add clean consumer HTTP/WebSocket/socket/browser/host-HTTP checks and native type/trait interoperability cases.
- [x] Adapt only the dependency boundaries that need it, preserving existing browser and host implementations; ship any required protocol-engine adaptation explicitly.
- [x] Run real peer, TLS state/cancel and supplied-stream regressions; reclassify unsupported original applications honestly.
- [x] Commit the reviewed Beast changes with exact profile evidence.

### Task 5: External build and source archive

**Files:** Per-library source/dependency inventories, new
`tools/test/portable_network_distribution_test.py` and an out-of-tree CMake consumer,
installation/archive metadata and per-library build-recipe documentation.

**Interfaces:** One declared source/configuration contract consumed by B2, a direct
compiler invocation and a CMake consumer. No second project release pipeline.

- [x] Build a source archive fixture without `.git`, `.local`, `bin` or B2 and prove current hidden dependencies fail.
- [x] Export explicit source/flags/dependency inputs and WIT generation requirements.
- [x] Run native and feasible Wasm consumers using explicit toolchain paths, inspect commands/dependencies and verify one runner/TLS provider.
- [x] Commit installation and consumer recipes only after the unpacked fixture passes.

Local consumer verification completed on 2026-11-06. Evidence is in the matching
SDD ledger under "Remaining-work item 1". Coordinated commits and publication
remain in the later closure phase; this does not close the full migration.

### Task 6: Examples, benchmarks and documentation

**Files:** Asio/Cobalt/Beast application inventories, benchmark generators/data,
`doc/*.adoc`, MrDocs configuration, `AGENTS.md`, organization guidance and proposals.

**Interfaces:** Retain the existing Cobalt genesis tasks as obligations. Fresh
source/runtime hashes bind all new support and measurement claims to this migration.

- [ ] Run every original application/profile or a named versioned negative probe; keep browser/host counterparts separate.
- [x] Repeat optimized size, compile/startup/performance/yield/memory measurements under the established methodology.
- [x] Apply webcpp-documentation: purpose, differences from Boost, config options/defaults, targets versus suspension modes, matrices and compiled examples.
- [x] Render/check docs and run relevant local build, lint and proposal checks; repair real failures.
- [x] Obtain a fresh whole-candidate review, address findings and record remaining environmental restrictions. Publication/CI remains a separate gate.

Remaining-work items 2/3 were completed locally on 2026-11-07. The dated library
reports retain the current application matrices, all 136 Release builds, 2,176
payload checks, 15,906 runtime observations and 442 yield cases. Asio application
coverage is its nine maintained guide programs, not the full Boost.Asio corpus.
The focused measurement review and three strict documentation builds passed;
they do not replace this plan's later whole-candidate closure gates. See the SDD
ledger for exact evidence, boundary diagnostics and retained SDK constraints.

Remaining-work items 4 and 5 are complete locally on 2026-11-07. Documentation,
tooling/proposal checks and the fresh whole-candidate review passed. The complete
lint covered 831 translation units and 1,528 commands; its two final style findings
were corrected and their exact checks passed again. The original failed run and
successful follow-ups remain separately recorded in `closure-lint-reconciled.json`.
The review has no unresolved findings. See `closure-items-4-5.md` in the SDD ledger.
The coordinated commits now record those reviewed changes. The broad original-application box
also remains open: Asio's dated matrix covers its nine guide programs, not every
original Boost.Asio example. This coverage boundary is explicit in the guides.


### Remaining-work item 6: coordinated publication

On 2026-11-07 the owner authorized coordinated publication and remote CI. Library
commits are Asio `e7cf267b4ab43437a09ce68f40a3994ca63b9054`, Cobalt
`36b9f2475aab1171e0898ab87d5b9630a8e04d71`, and Beast
`6c53f854070a4eebd844f21c29692e938181f8f6`. Cobalt has its public repository and
is registered as a submodule. These commits preserve the checked source and
measurement bytes; Git attributes retain imported/generated whitespace and CSV
line endings. The superproject records all three revisions together.

Remote CI is pending. The changed container recipe must first produce verified
immutable environment pins. The complete superproject CI validates the combined
candidate before integration; library workflows use the superproject's main and
must be rerun after its integration. No release or proposal archival is implied.
