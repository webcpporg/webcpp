# Asio capability completion: local verification

Date: 2026-11-03. Scope and requirements are in
`2026-11-03-asio-capability-completion.md` and its linked design.

## Candidate scope

- Complete WASI connected UDP gather and scatter receive, including transient send
  readiness, truncation, empty datagrams, handler allocation and cancellation.
- Use the P3 native asynchronous name-lookup interface in single-thread and
  cooperative profiles. A checked private libc descriptor joins the existing
  reactor. Preserve deferred initiation, timer progress and resource lifetime.
- Enable the existing source-built OpenSSL, embedded/replacement CAs and Cobalt SSL
  targets on P2. Keep a single provider and the no-exceptions issue 287 notice.
- Enable explicit Emscripten pthread builds, creator-thread context execution and
  an allocator-aware main-thread handoff. Keep the default single-thread profile.
- Centralize derived capabilities and opt-in compile-time requirements. Document
  runtime permissions separately from compiler-visible constraints.

No SDK upgrade, upstream Cobalt fix, push, merge, remote CI or release is part of
this increment. The handler budget remains 100. The old remote run 41597577370
does not validate this candidate.

## Toolchain and commands

Local validation used Apple Clang 21, Boost 1.92, wasi-sdk 34.0 with its pinned
wasi-libc revision, Wasmtime 50.0.1, Emscripten 6.0.11 and Chrome 156. The wrapper
`.local/review-b2` unsets CPATH, CPLUS_INCLUDE_PATH and C_INCLUDE_PATH, selects
`.local/user-config.jam`, and uses the local writable Emscripten cache.

```sh
.local/review-b2 -a -j4 libs/asio/test libs/asio/example \
  toolset=clang variant=release exception-handling=on,off
.local/review-b2 -a -j4 libs/asio/test libs/asio/example \
  libs/asio/test//asyncify toolset=emscripten variant=release \
  exception-handling=on,off
.local/review-b2 -j4 libs/asio/test libs/asio/example \
  toolset=clang-wasip2 variant=release exception-handling=on,off \
  testing.launcher=tools/boost/asio-wasip3/run.sh
.local/review-b2 -j4 libs/asio/test libs/asio/example \
  toolset=clang-wasip3 variant=release exception-handling=on,off \
  testing.launcher=tools/boost/asio-wasip3/run.sh
.local/review-b2 -a libs/asio/doc
.local/review-b2 declared-targets declared-lanes -d0
```

The WASI launcher resolves the pinned Wasmtime from PATH. Initial broad WASI
commands built from scratch but omitted that launcher, so their runtime failures
are invalid test evidence. The corrected commands above executed the freshly built
artifacts successfully. An additional attempted `toolset=wasi` command was rejected
because the configured toolsets are `clang-wasip2` and `clang-wasip3`.

| Final broad local check | Passed B2 test targets | Result |
| --- | ---: | --- |
| Native Release, exceptions on/off | 105 | Exit 0; examples matched output |
| Emscripten Release, JSPI/Asyncify, exceptions on/off | 233 | Exit 0; Node execution and example output |
| WASIp2 Release, exceptions on/off | 66 | Exit 0; examples matched output |
| WASIp3 Release, exceptions on/off | 117 | Exit 0; examples matched output |

Counts include compile/diagnostic and runtime targets, not individual assertions.
They do not include every separate own lane and do not claim all-platform CI.

## Focused evidence

- P2 TLS/Cobalt: 26 checks across both exception profiles. Real peers cover trust,
  hostname, replacement and embedded CAs, transfer, handshake, shutdown errors and
  cancellation. The final registered `wasip2-tls` lane passed all 16 driver runs.
  Native/P3 TLS controls passed in both exception profiles.
- Entropy: independent processes generated distinct public keys; failed host
  entropy prevented random output and key generation. This checks wiring and
  fail-closed behavior, not the cryptographic strength of a host's entropy source.
- P3 DNS: real localhost lookups plus a deterministic pending native host-clock
  subtask proved deferred start, unrelated timer progress, cancellation and release
  before callbacks. Cooperative two-runner cancellation passed 20 repetitions,
  totaling 40 cancellations. P3 cooperative C++ exceptions remain unsupported by
  the pinned SDK runtime and are diagnosed by the build.
- Browser pthreads: real Chrome passed JSPI and Asyncify, each with exceptions on
  and off. Eight final lifecycle/affinity runs cover reentrant destruction, posted
  work, cancellation and allocator cleanup. Two EH-on runs cover throwing handler
  moves. Single-thread browser, idle and rendering controls passed separately.
- A versioned raw pthread-return probe records the SDK's Asyncify join-result
  limitation: the worker computes 42 but join yields zero. It deliberately fails
  its value check; it is not counted as a passing library test.
- Capability consumers passed native/P2/P3/browser and browser pthread compilation.
  They reject forged derived macros, unavailable feature headers and missing or
  explicitly disabled optional TLS selection, while retaining portable includes.
- Overlay preparation, SDK/private-ABI checks, source-build harness and OpenSSL
  recipe tests passed. The lint verifier regression passed for P2/P3 valid and
  rejected snapshots without hiding WebCPP bridge sources.
- Focused clang-tidy passed task-owned code and 16 parent-owned configurations.
  Owned Python checks, text/format rules and Node syntax checks passed. This is not
  a claim that the complete repository lint printed `lint: clean`.
- Complete lint database generation passed with 1,451 commands, including the
  explicit browser pthread header units. Database generation is not a full tidy
  run. The local `check-release` target also passed.
- MrDocs and rendered guide link/code checks passed after the final public comment
  changes. Desktop/narrow screenshot inspection remains unverified: local Chrome
  screenshots were blank and the in-app browser refused file URLs. No bypass was
  attempted.
- Proposal checking and 17 tool tests passed. OpenSpec 1.10.0 strict validation
  passed in all 15 proposal roots after exporting the 206-file candidate snapshot.

## Review and regression record

Task reviews approved TLS/Cobalt without findings, and approved WASI and browser
code after the following reproduced defects were fixed:

1. Connected UDP confused a transient EAGAIN with permanent initialization failure.
   Immutable validation state now permits readiness retries.
2. Native DNS result cleanup freed canonical empty-list/string sentinels. Cleanup
   now observes lengths, matching the pinned canonical ABI.
3. Cooperative cancellation could free a descriptor still borrowed by another
   reactor poll. Cancellation completion waits for that borrow to end.
4. A main-thread callback destroying its context could recursively drain the SDK
   queue and use a destroyed service. Allocator-owned shared control now survives
   active delivery and discards queued callbacks safely.
5. A throwing handler move leaked operation storage. RAII owns the operation before
   the move, and the failure path discards queued work without invoking it.

Each review fix has a public failing regression before its correction and a scoped
approved re-review. The original UDP feature test had a weaker chronology: its
first run failed on sandbox networking, and the valid pristine-overlay failure
was replayed after implementation. It is not described as strict test-first TDD.

The final whole-candidate review covered root `15e2f44..0da952f` and Asio
`dad1aef..a8d0f17`. It found no additional backend/lifetime defect, but requested
two important recurring-lane fixes: Chrome provisioning for the new browser lanes
and persisted EH/suspension coverage. It also identified stale P2 TLS guide
commands and a stale single-thread Cobalt DNS refusal statement. These findings
were resolved in one scoped fix wave, root `008a47b` and Asio `9455076`.
The complete matrix suite passed 41/41 cases. Local B2 XML confirmed 34 driver
configurations: four profiles for each of four worker drivers, two EH-on
suspension profiles for the exception fixture and two EH profiles for each of
eight P2 TLS drivers. Documentation generation and focused static checks passed.
An initial matrix test could not bind loopback in the sandbox; the same case and
the complete suite passed with local socket permission, without changing tests.

The scoped re-review approved every finding with no new breakage and no
out-of-scope observations. Reports are preserved in
`../reviews/2026-11-03-asio-capability-review.md` and
`../reviews/2026-11-03-asio-capability-fix-review.md`. Local raw reports, logs and
review packages are retained in `.local/asio-capability-evidence-2026-11-03.tar.gz`.
The completed branch and worktree are kept for the separately authorized
publication closure; nothing here asserts fresh remote CI or a merge.

The reviewer explicitly left broader external DNS/IPv6/multicast/native-device
validation, general Cobalt compositions and upstream issue 287, other host OSes
and engines, pixel-level documentation inspection and publication outside the
verdict. These remain the documented validation/external boundaries; none is
silently promoted to tested support by this review.

## Controller decisions

- The user's request supplies scope approval; no additional permission round was
  needed. A mistaken scope interpretation would require local rework.
- Reuse the existing isolated worktree and leave the primary checkout untouched.
  A wrong base would require rebasing the local candidate.
- Use disjoint task ownership and parent-owned shared files and commits. An
  integration mistake would require local rework, not discarded unrelated edits.
- Do not change SDKs or repair upstream Cobalt issue 287. Use guards only for
  compile-visible facts and runtime errors for host permissions. A changed SDK or
  runtime requires new validation before broadening the matrix.
- Review frozen task-specific diffs before committing the combined candidate;
  perform the final review against committed ranges. A missed integration defect
  requires a candidate fix, not a waived test.
