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

The changed container recipe produced verified immutable environment pins in
GitHub run 42370588658. All six publishers, six anonymous consumers and the
manifest assembly passed. The generated manifest is promoted unchanged. Full
remote test CI is pending. The complete superproject CI validates the combined
candidate before integration; library workflows use the superproject's main and
must be rerun after its integration. No release or proposal archival is implied.


The source-release check is a separate unresolved gate: the existing 0.1.0
notes and the older libraries are frozen, while the three changed libraries
retain Unreleased entries. No release tag or GitHub release exists. The attempted
in-preparation marker conflicted with those historical frozen sections and was
reverted without rewriting them. Reconcile this state in the separately authorized
release procedure; remote integration CI does not certify a release archive.

The first full remote run, 42370852663, exposed three tooling regressions. The
Linux CMake consumer built and ran, but dependency auditing rejected libm because
only header search roots were queried. The audit now also queries the selected
compiler's library paths, with a regression that still rejects an undeclared
library. Linker phony rules were also misread as dependency filenames; a real
compiler regression using `-MP` reproduces this and confirms that dependencies
in subsequent rules are still checked. The existing Cobalt lint fixture lacked the exact-file
inventory required
by the new classification gate; it now supplies that inventory and verifies that
an unlisted neighboring file remains linted. All three failures were reproduced before
correction. These findings supersede the corresponding local reconciliation claims;
the original reports and failed CI logs remain preserved.


The second remote candidate, 349f5b3 (run 42372677128), exposed additional
portability and lane-registration failures. Its green B2 job statuses do not
certify tests: the XML report is the verdict. Corrections under verification:

- Preserve the shipped Asio system executor's inherited fatal `noexcept`
  initialization boundary explicitly; native Boost types remain unchanged.
- Keep GCC 14 coroutine-allocation false positives confined to the affected
  test consumers. Use pinned GCC 15.3 for the GCC 15 lane to avoid compiler
  PR121643 without changing Cobalt's coroutine code. The exact relocated
  toolchain passed its compile/run probe and five ASan/UBSan Cobalt programs
  in Ubuntu 26.04.1.
- Register ICMP header checks only on native; give browser/P2 timer tests their
  actual Beast test dependency; exercise the unbounded backend control through
  its base type. JSPI/Asyncify with EH on/off and P2 EH on/off passed locally.
- Provision Chrome for Asio's concurrency-hint and all Cobalt browser lanes,
  with explicit suspension/EH expansion for direct programs and manifest-based
  expansion for network counterparts. The planner regression fails without it.
- Migrate the shared OpenSSL test clients to public WebCPP Asio headers.
  Move the Cobalt TLS profile matrix into Cobalt's own lane, preserving its
  native S/M and supported P3 combinations and the MSVC CRT/provider checks.
- Keep SDK/upstream limitations visible rather than patching native Boost:
  pinned Emscripten PIPEFS returns EAGAIN after writer closure instead of EOF;
  native IOCP retains its global thread-state allocation; MSVC rejects the
  upstream no-EH main promise without `unhandled_exception`. Negative witnesses
  are distinct from feature support. Windows runtime results remain a remote
  verification gate for the corrected candidate.

The completed run contains 131 lane artifacts. Its reconstructed report records
47 failed test cells and refuses the two cross-library TLS lanes; green B2 job
statuses did not override that verdict. The site could not download the report
artifact after that refusal. Every reported cause has a focused local correction
or an explicit upstream/SDK limitation witness. This is not a green remote verdict.

The browser investigation reproduced a separate starvation defect: successive
timer waits discarded the handler budget and could resume only through JavaScript
microtasks, preventing a worker proxy request from being serviced. The corrected
composition counts both polled and waited handlers until an explicit yield. A
nine-timer regression with limit four failed with zero yields and now requires
two. The unchanged Cobalt worker test, including its one-millisecond observer,
passed in real Chrome for JSPI/Asyncify with EH on/off. Fresh Asio Emscripten and
Asyncify suites passed, including stack witnesses, documentation and focused lint.

The finite echo counterpart now uses the existing primitive `accept(socket&)`
overload, preserving native Boost while allowing cancellation. Its reset driver
waits for an echoed byte before sending RST, so the test proves that a session
was accepted. Native S/M with EH on/off and WASIp2/P3 supported profiles passed.
The immutable SPSC queue's negative control stays native; the corrected queue's
forced-interleaving tests passed on native, Emscripten's four variants and WASIp3.

On 2026-11-07 the owner explicitly directed that newly identified original Boost
defects remain documented rather than patched. Native composed accept and MSVC's
no-EH main-promise limitation retain their negative witnesses. The previously
approved native SSL exception remains separate. Documentation now distinguishes
the shipped source layout from historical overlays and states the exact turn
budget and native allocation boundaries. Independent correction reviews found no
remaining code findings; real Windows results still require the next remote run.

Fresh local evidence, failed controls and independent reviews are retained under
`.superpowers/sdd/2026-11-06-portable-network-libraries/publication/`. A concurrent
local TLS build once exposed an incomplete Wasm file before execution; the same
entropy/thread driver and a subsequent fresh focused build passed. No test
expectation was changed for that build-output collision. No merge has been
performed for this candidate.

The third remote candidate, 861809f (run 42381776828), completed all eight
lint shards and tool-test shards successfully. Its report accepted all 133 XML
lanes and recorded three failed cells: the immutable ticker's MSVC C4457 warning
on 14.3 and 14.5, and a lost value in the native SPSC sequence counterpart.
The ticker adjustment is limited to that original compile probe; its bytes and
other warning policies remain unchanged. A deterministic witness reproduced the
queue's stale-notification data loss in both the original and the counterpart.
The existing wakeup correction does not fix that separate upstream defect.
Per the owner's 2026-11-07 direction, preserve that behavior, document the
limitation and withdraw the counterpart's reliable-transfer claim rather than
patching the original or accepting a probabilistic passing run.
The final site assembly also rejected Cobalt's 63-character rendered title,
which exceeds its 60-character limit. The shortened title has 51 characters;
the actual site build reproduced the rejection, then passed all 37 pages,
12 libraries, links and HTML checks with the regenerated final guide.

The owner also reaffirmed the native SSL exception and requested explicit
fixed-defect documentation. The guide now records the corrected handshake/state,
plaintext-fallback, shutdown, composed-transfer cancellation and move behavior,
with the concrete-type and target constraints. OpenSSL and native Cobalt's
core/plain I/O remain unchanged. The new candidate still requires full remote
verification before integration; these records do not mark it green.

Follow-up local verification passed nine deterministic queue limitation profiles
(native original/counterpart with EH on/off, Emscripten JSPI/Asyncify with EH
on/off, and cooperative WASIp3 with EH off), with three recurring matrix-policy
regressions. Real Chrome verified the unavailable SPSC UI and the remaining
portable programs in all four suspension/EH profiles. Focused clang-tidy,
Pyright, formatting, import integrity and text rules passed. The historical
source and measurement bytes remain unchanged. MSVC dry runs retained `/W4`
and `/WX`, applying `/wd4457` only to the original ticker probe. The full Cobalt
reference/guide build and independent review passed. Actual MSVC confirmation
of the new diagnostic scope and the complete remote CI remain the merge gate.

Candidate 8cbca68 (run 42388065736) passed all eight lint shards, all eight tool
test shards, documentation and the final site assembly. Its 133 XML lanes contain
131 passing lanes and two failures: both MSVC versions compile past C4457 but
reject the immutable ticker with C1128 because its Debug object exceeds the
default COFF section limit. Only that compile probe now selects `/bigobj`.
Real B2 dry runs for 14.3/14.5 confirm the option stays confined to that command,
with `/W4` and `/WX` retained and 63 other compiler commands unaffected in each
profile. The original source hash, fresh guide/reference build, text checks and
independent review passed. The SPSC limitation probes and unavailable browser UI
passed remotely. The next complete remote run must confirm actual MSVC compilation
with the expanded object format; this recorded failure does not authorize a merge.

Candidate f677c12 (run 42394021516) confirmed successful original ticker
compilation on both MSVC versions. All eight lint shards and tool-test shards
passed. The XML audit found a separate intermittent browser worker lifecycle
timeout in three suspension/EH profiles, despite the B2 job's zero exit status.
The same timeout reproduced locally in real Chrome before any change.

The lifecycle test's one-millisecond readiness observer generated hundreds of
thousands of zero-timeout polls and competed with worker setup. Under identical
controlled Chrome CPU throttling, the observer failed six of twelve executions;
a posted readiness notification passed twelve of twelve. The notification
changes a timer's expiry on the creator's executor, retaining an early signal.
Separate controls cover arrival before the wait. The five-second deadline and
all cancellation, completion and executor-affinity checks remain unchanged.
This is a test synchronization correction, not a change to Boost, SDK timer
polling or a general browser worker-latency guarantee.

Fresh native single/multi-thread profiles with EH on/off, cooperative WASIp3
with EH off, the strict Cobalt reference/guide build and independent review
passed. The exact combined candidate still requires a new full remote verdict
before integration. Evidence remains in the ignored publication directory;
neither historical measurement archives nor the original sources are rewritten.

Candidate f9d4729 passed the complete remote run 42400325361, including all
133 audited XML lanes, eight lint shards, eight tool-test shards, documentation
and site assembly. The exact tested merge 80c6688 was integrated into main.
Its subsequent main run 42407610002 exposed an intermittent false failure in
the WASIp3 localhost resolver test: the first `poll_one()` can already deliver
success, so the later cancellation cannot replace that completed callback with
`operation_aborted`. The test had also assumed that context destruction always
preceded a localhost callback after one poll.

A controlled immediate host-result fixture reproduces both incorrect
expectations against the unchanged test, with three failed assertions. The
corrected test distinguishes delivery before cancellation from pending work,
and delivery before context abandonment from forbidden delivery afterwards.
The existing deterministic pending-subtask test continues to require both
cancellation forms, shutdown cleanup and associated allocation release, with
an explicit assertion that no callback preceded cancellation. Production
Asio, Boost and SDK code remain unchanged. Evidence and exact local commands
are retained in the publication directory's `resolver-race` subdirectory.
The correction requires a new library and superproject CI verdict before
integration; the earlier green run does not validate it.

Fresh local validation passed twenty programs: fourteen capability tests on
WASIp3 with EH on/off, two real resolver tests on WASIp2 with EH on/off, and
four resolver tests on cooperative WASIp3 with EH off. Eleven affected
compilation profiles passed clang-tidy; formatting, text checks, the strict
Asio reference/guide build and independent review passed. The first broader
local run lacked socket permission for UDP bind; the authorized fresh run
passed without production changes.

Candidate 8c4f8da (run 42414092998) passed the corrected WASIp3 resolver
tests but failed two Trystero interoperability scenarios among 133 audited
XML lanes. Asio's own run 42414060357 passed all 29 XML lanes, eight lint
shards and documentation. Beast's run 42407655502 and Cobalt main's run
42407664390 also passed, with 53 and 65 XML lanes respectively. These
library results do not replace the failing superproject gate.

The recovered-browser relay scenario accepted a join reported by JavaScript
before C++ completed its handshake. It sent the fresh-message probe too
early and failed while the next connection was recovering normally. A
controlled one-way handshake delay reproduces the same false failure with
the unchanged driver. The corrected setup requires fresh, currently joined
peers on both sides within the existing 30-second bound, then the existing
10-second round-trip check. The registered control fails before the fix and
passes on browser and native backends afterwards. Relay-loss assertions,
backoff bounds and fatal console errors remain unchanged. No production
library code or upstream package is modified.

The separate native two-room scenario logged a JavaScript `OperationError`
while two connection attempts crossed. Its cause is still unconfirmed:
local macOS and Linux ARM runs have not reproduced that error. The JavaScript
fixture now records RTCError details while forwarding the original console
error, so the next failure retains the evidence needed for diagnosis. A
normal user-initiated SCTP abort observed in a diagnostic experiment is
already filtered by the original package and is not claimed as the CI
failure. The root CI and publication remain open until this is resolved.

Fresh complete local runs passed all 26 browser and 30 native interoperability
scenarios, including the newly registered delayed-handshake controls. Changed-file
text rules, JavaScript module syntax, whitespace checks and independent review
passed. Trystero commit e9326e9 contains only the test fixture, driver and testing
instructions. Its PR3 now records both the validated setup correction and the
separate unresolved native error; neither a passing repeat nor the additional
diagnostics is presented as a fix for that error.
