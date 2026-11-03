# Asio and Beast closure

**Goal:** Close the approved Asio and Beast integration together, including the owner's
2026-11-03 scope decisions and the independently verified findings in the Claude audit.

**Architecture:** Keep native and WASIp3 socket/TLS transport in Asio. Beast's socket
profiles follow Asio's supported targets; portable messages, host HTTP and supplied
streams remain independent. Preserve the browser's native WebSocket and fetch adapters.

**Tech Stack:** C++20, Boost 1.92, B2, Emscripten, WASI SDK 34, Wasmtime 50.0.1,
OpenSSL, Python, AsciiDoc, MrDocs and OpenSpec.

**Spec:** `proposals/libraries/{asio,beast}/openspec/changes/genesis`, reconciled with
the owner's later approvals. The sibling proposals checkout is an independent repository.

## Global constraints

- Keep the primary checkout and unrelated work intact. Never force-push.
- Treat the Claude audit as evidence to verify, not as authority for new rules.
- Preserve the 53 upstream Beast applications and explicit variant classifications.
- Asio and Beast are intended foundations for a later Trystero migration. The owner
  clarified this on 2026-11-03; never introduce a ban on combining those libraries.
- Reproduce behavioral defects through a real consumer before fixing them.
- Run final B2 checks with `-a` and unset inherited compiler include paths.
- Change generated artifacts only through their generators.
- Record prior approvals without asking for them again or inventing new approvals.
- CI, push and merge are authorized; publishing a release or tag is not.
- Merge only a tree identical to the successful final CI candidate. Library CI uses
  the superproject's `library.yml@main`, so integrate the root before library mains.

## Work and interfaces

### 1. Verify and reconcile Beast scope

- [x] Compare the actual Claude artifact, code, requirements and test evidence.
- [ ] Remove the P2 socket prerequisite tasks and amend the normative requirement.
- [x] Generate the application matrix: 567 passed, 122 blocked, 530 unavailable.
- [x] Preserve P2 host HTTP/messages/streams and explain every remaining blocked cell.
- [ ] Validate generators and OpenSpec; submit the proposal as proposed, not accepted.

Produces: Beast source and proposal changes. Its source reference snapshot is refreshed
only after the library changes are committed, preserving exact blobs and modes.

### 2. Fix Asio configuration and allocator conformance

- [x] Reproduce global configuration propagation and repair the config dependency.
- [x] Put config first in the affected public headers.
- [x] Reproduce resolver input allocations and route owned inputs through the associated
  allocator without changing deferred initiation or input lifetime.
- [x] Measure allocations on the supported WASIp3 profiles with explicit categories.
- [x] Connect thread tests and applicable exception/header tests to recurring lanes.

Produces: Asio headers, tests and lane declarations. Root CI consumes those declarations;
coordinate any cooperative SDK provisioning changes before changing CI.

### 3. Reconcile TLS and dependency contracts

- [ ] Generate embedded CA data under the owning library's private namespace and path;
  prove build-tree and installed consumers work.
- [x] Preserve public error identities and document any bounded compatibility departure.
- [x] Inspect the claimed Cobalt SSL state defect against the existing overlay and tests.
- [x] Reproduce mixed OpenSSL provenance with Trystero and choose a single provider for
  combined programs, including libdatachannel's transitive dependency.
- [x] Add upstream native OpenSSL test coverage and recurring TLS integration coverage;
  name harness limitations explicitly for WASI.

Produces: root dependency tooling, TLS contracts and test lanes. Do not hide a dependency
conflict by banning useful library combinations or silently selecting system libraries.

### 4. Reconcile rules, release preparation and Asio records

- [x] Disposition every current chapter 19 item and each additional audit claim using
  code changes, existing approved decisions or an explicit documented departure.
- [ ] Amend Asio targets, default turn limit 100, source-built OpenSSL and Diataxis order.
- [x] Add Asio's maintained AsciiDoc changelog and New Libraries entry.
- [ ] Reconcile preparation metadata without claiming a published release.
- [ ] Update gates, dates and status with actual repository, integration and CI evidence.
- [ ] Run release checks and every strict OpenSpec root plus proposal tooling tests.

### 5. Review and verify the final candidate

- [x] Finish collecting baseline CI 41597577370; it is not evidence for later edits.
- [x] Perform one fresh whole-branch review covering Asio, Beast and root integration.
- [x] Fix important findings with RED/GREEN tests and run the relevant complete suites.
- [ ] Commit explicit paths, refresh reference snapshots and publish the final candidate.
- [ ] Run and inspect full CI, including report XML, docs, lint and site, on that exact tree.

### 6. Integrate and close

- [ ] Recheck remote heads and merge root with the tested tree preserved.
- [ ] Create Beast main at its tested commit and make it the default branch.
- [ ] Merge library updates and verify their main CI, especially Asio's first run.
- [ ] Finish proposal records/archive only when their stated gates are actually met.
- [ ] Report merged commits, CI links and any explicit remaining limitations.

## Review focus

Check deferred token timing and allocator lifetime, cross-library error-code identity,
installed generated headers, one OpenSSL provider across shared/static boundaries,
TLS state transitions and shutdown cancellation, cooperative-thread SDK limitations,
WASI host versus guest transport dependencies, browser direct adapters, exact matrix
coverage and whether metadata claims more than the executed tests prove.
