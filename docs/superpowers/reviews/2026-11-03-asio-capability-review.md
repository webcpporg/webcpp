# Final whole-candidate review: Asio capability completion

Date: 2026-11-03.

## Review boundary

Reviewed the frozen root range `15e2f44..0da952f`, Asio range
`dad1aef..a8d0f17`, and `final-proposals-review.diff` against the approved
capability-completion design and plan. This is the single final reviewer pass.
No subagents were dispatched. No source, index, HEAD, branch, SDK, installed
Boost tree or generated output was modified. This report is the only written
review artifact.

The review included the complete candidate's shared capability/header/build
integration, WASI UDP and asynchronous DNS paths, private descriptor ABI and
cancellation lifetime, browser affinity/main-thread queue lifetime, P2 shared
TLS/Cobalt integration, recurring B2 test registration and public documentation.
It also read the progress/verification records and the task review corrections.
The earlier task approvals were considered evidence, not a substitute for
checking their shared boundaries.

## Strengths

- `libs/asio/include/webcpp/asio/config.hpp:77` distinguishes derived 0/1
  facilities from optional OpenSSL selection. Requirement switches diagnose
  compiler-visible limitations while portable browser includes and runtime
  permission errors retain their intended behavior.
- The checked UDP overlay preserves the entire buffer sequence and one-datagram
  semantics. Synchronous scratch uses the context allocator, asynchronous scratch
  uses the associated allocator, and scatter/copy cleanup precedes callback
  delivery. The retry fix separates immutable validation failure from EAGAIN.
- `tools/boost/asio-wasip3/include/boost/asio/detail/wasi_p3_resolver.hpp:181`
  defers host lookup until queued execution and joins native waitables to the
  reactor instead of blocking initiation or polling DNS on a timer. The
  cancellation queue protects borrowed descriptors until the active poll returns.
  SDK/version/header checks make the private ABI dependency explicit.
- `libs/asio/include/webcpp/asio/browser/main_thread_context.hpp:85` separates
  queued-control lifetime from the context service. It safely discards pending
  callbacks during reentrant destruction, retains control during delivery and
  owns operation memory before potentially throwing handler moves. The public
  allocator-resource lifetime clarification is present.
- P2 TLS reuses the existing pinned source provider, CA contract and checked
  Cobalt overlays. Actual peer identity/trust failures, transfer, shutdown,
  cancellation and entropy failure evidence are distinguished from build success.
- The evidence record does not disguise the initial invalid WASI launcher run,
  UDP RED chronology, raw Asyncify pthread return-value failure, screenshot
  limitation or upstream Cobalt issue 287 as successful feature coverage.

## Issues

### Critical (Must Fix)

None found.

### Important (Should Fix)

1. **Provision Chrome for both new browser own lanes.**

   Locations: `libs/asio/test/browser/Jamfile:69` and `:84`;
   missing integration in `tools/ci/matrix.py:194`.

   The newly registered `browser-workers` and `browser-worker-exceptions` lanes
   are absent from `CHROME_LANES`. The actual matrix functions therefore produce
   `chrome=False` and `os=ubuntu-24.04` for both. The workflow only installs the
   pinned browser and sets `CHROME` when that flag is true
   (`.github/workflows/library.yml:336`). On Linux, `findChrome` immediately
   rejects an absent `CHROME` (`libs/asio/test/browser/run.mjs:29`). These jobs
   cannot execute their real-browser tests when scheduled, despite the successful
   local macOS runs.

   Add both lanes to the browser provisioning classification and extend the
   focused matrix regression to cover their actual entries. Do not rely on an
   incidental runner browser or change the driver to silently skip execution.

2. **Encode the promised profile coverage in recurring own-lane requests.**

   Locations: `libs/asio/test/browser/Jamfile:46`, `:79`,
   `libs/asio/test/wasip2_tls_cobalt/Jamfile:38`; shared request construction at
   `tools/ci/matrix.py:516` and `:771`.

   The new browser drivers compile direct sources, not the older browser lane's
   two-variant manifests. Their lane declarations and CI requests supply no
   suspension/EH expansion. Consequently `browser-workers` schedules only default
   JSPI/EH-on, `browser-worker-exceptions` schedules only JSPI/EH-on, and
   `wasip2-tls` schedules only EH-on. The manually supplied local matrix flags do
   not persist in recurring coverage. Asyncify and the supported no-EH paths,
   including the explicitly retained Cobalt limitation boundary, can regress
   without these own lanes exercising them.

   Encode JSPI/Asyncify plus EH-on/off for `browser-workers`, both suspension
   variants with EH-on for `browser-worker-exceptions`, and EH-on/off for
   `wasip2-tls`, either in the established own-lane options mechanism or explicit
   B2 target variants. Add focused checks of the generated requests and confirm
   that the B2 graph contains the intended configurations. Avoid expanding the
   exception-only fixture into an unsupported no-EH execution.

### Minor (Nice to Have)

3. **Point the P2 TLS how-to at the lane that runs its advertised tests.**

   Locations: `libs/asio/doc/wasip2.adoc:35` and
   `libs/asio/doc/building.adoc:439`.

   The new P2 command names only `libs/asio/test/wasip2_tls_cobalt`, but
   `webcpp.lane` marks the TLS/entropy/status drivers explicit
   (`tools/webcpp.jam:930`). That directory command runs the ordinary consumers
   and skips the advertised real TLS peer checks. The general TLS guide also
   says `libs/asio/test/tls//tls-integration` covers P2, although its Jamfile
   declares only native/P3 (`libs/asio/test/tls/Jamfile:9`, `:46`).

   Keep the directory for the ordinary Cobalt tests and additionally name
   `libs/asio/test/wasip2_tls_cobalt//wasip2-tls` in the P2 command. Describe the
   separate P2 lane in the general TLS guide instead of extending the old lane's
   claimed scope. The older `tools/openssl/test/run.py --fresh` driver also
   remains native/P3; do not imply it supplies the new P2 evidence.

4. **Remove the stale single-thread Cobalt DNS refusal statement.**

   Location: `libs/asio/doc/feature-matrix.adoc:410`.

   The paragraph still says async resolution without threads returns
   `operation_not_supported` and that this negative behavior is tested. The
   preceding updated numeric-resolver row and the completed P3 native-async
   backend now establish the opposite. This wrongly tells a user the completed
   capability is unavailable.

   State the actual numeric/forward asynchronous resolver behavior and its
   evidence, retaining the separate qualification that arbitrary external DNS
   access depends on host policy and is not established by localhost/numeric
   consumers.

## Checks and evidence

- Read the implementation changes and immediate shared dependencies, including
  allocator/cancellation completion paths, overlay preparation/ABI checks,
  optional provider selection, header diagnostics, driver registration,
  the lint integrity-gated exemption and changed proposal/public documentation.
- Read `progress.md`, the final local verification document, task reports and
  scoped approved task reviews. Their recorded native 105, P2 66, P3 117 and
  Emscripten 233 broad B2 checks, own-lane runtime results, real browser runs,
  targeted static analysis and rendered-content checks were not rerun.
- Named focused experiment: **recurring lane environment/profile synthesis**.
  Imported `tools/ci/matrix.py` with `python3 -B`, constructed the three actual
  `OwnLane` records, and called only `own_lane_entry` and `own_lane_command`.
  This was read-only, did not dispatch CI, and produced:

  ```text
  browser-workers chrome=False os=ubuntu-24.04
  b2 --user-config=candidate-user-config.jam -a --dump-tests --out-xml=candidate.xml toolset=emscripten libs/asio/test/browser//browser-workers
  browser-worker-exceptions chrome=False os=ubuntu-24.04
  b2 --user-config=candidate-user-config.jam -a --dump-tests --out-xml=candidate.xml toolset=emscripten libs/asio/test/browser//browser-worker-exceptions
  wasip2-tls chrome=False os=ubuntu-24.04
  b2 --user-config=candidate-user-config.jam -a --dump-tests --out-xml=candidate.xml toolset=clang-wasip2 testing.launcher=tools/boost/asio-wasip2/run.sh libs/asio/test/wasip2_tls_cobalt//wasip2-tls
  ```

  Inspected `tools/drive/drive.jam:94` to confirm that direct-source driven
  tests do not implicitly expand suspension or exception modes. Inspected
  `tools/webcpp.jam:930` to confirm explicit own-lane members are excluded from
  an ordinary directory build. No repeat feature suite was needed to establish
  these integration defects.
- Parent reported that final broad runs, documentation, metadata/check-release,
  proposal export verification and proposal checks finished successfully during
  this review. Before report freeze, the parent also confirmed completed database
  generation with 1,451 compilation commands and all headers materialized. This does not establish correctness of the missing recurring
  environment/profile settings found above.

## Recommendations

Resolve the four findings in one scoped fix wave. Use focused matrix regressions
and the affected generated B2 graph/driver checks to verify the automation
corrections; re-render/check the corrected guide text. No SDK change, production
backend rewrite, remote CI dispatch or broad suite replay is needed to resolve
these findings.

## Declined to judge

- General external DNS reachability, IPv6 traffic, multicast and all native
  OS-specific devices: outside the approved implementation increment and
  explicitly listed as unverified/future validation in the feature matrix.
- Broader Cobalt coroutine composition and fixing upstream issue 287: excluded
  by the binding scope; this review checks preservation of the documented limit.
- Runtime guarantees for other browser engines, Windows/Linux native execution
  or other SDK/runtime versions: the supplied local evidence does not establish
  those combinations and the candidate does not claim it does.
- Desktop/narrow rendered-page visual perfection: the recorded screenshot
  attempts did not yield usable images; rendered content/link checks do not
  establish pixel-level review. This remains unverified, not approved visually.
- Publication, fresh remote CI and merge readiness against remote branch state:
  explicitly excluded from this increment; no remote action was performed.

## Assessment

**Ready to merge? With fixes.**

The completed runtime implementations and their scoped corrections are coherent
with the approved design; this pass found no additional production backend or
lifetime defect. Two recurring-test integration defects must be corrected, and
the two documentation findings should be reconciled in the same local fix wave.
The verdict is for this frozen candidate and does not close publication gates.
