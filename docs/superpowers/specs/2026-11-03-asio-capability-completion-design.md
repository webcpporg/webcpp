# Asio implementation gaps and capability diagnostics

The owner requested completing the gaps attributable to WebCPP's implementation,
while documenting and guarding unsupported SDK/environment combinations. This
request follows the explicit inventory in the conversation and authorizes execution
without another approval round. Existing compatibility and allocator contracts stay
in force. The existing isolated worktree is reused.

## Deliverables

1. Complete WASI connected UDP gather sends and scatter receives without changing
   datagram atomicity, partial/truncated result semantics or allocator ownership.
2. Add WASIp3 single-thread asynchronous forward resolution using the available
   native asynchronous interface, preserving deferred initiation, cancellation,
   associated executors/allocators and useful progress of unrelated operations.
3. Integrate source-built OpenSSL, embedded/replacement CAs, Cobalt and its SSL
   wrapper on WASIp2, using the existing shared provider and checked Boost patches.
4. Establish browser worker-profile feasibility using real compiler/runtime
   consumers. Implement the integration where the pinned SDK and engine support
   it. A demonstrated toolchain/runtime blocker is documented and guarded, not
   hidden with a different program or an SDK upgrade.
5. Centralize compile-time capabilities in Asio config.hpp and apply diagnostics
   at unsupported feature headers/build requests. Keep ordinary umbrella headers
   and browser transport abstractions usable. Do not confuse compile-time support
   with runtime network grants, certificates, reachable peers or a custom transport
   selected at runtime.
6. Update the AsciiDoc/Diataxis feature matrix and MrDocs comments. Distinguish
   implementation gaps, unavailable external facilities, and unverified behavior.

## Boundaries

Do not change the pinned SDK, add runtime/OS APIs, repair upstream Cobalt issue 287,
implement raw browser sockets or a proxy, invent reverse DNS from a forward-only
host API, or claim CPU parallelism from cooperative threads. Those dependencies
remain documented with deliberate diagnostics where compiler-visible. Runtime-only
failures remain error values. Keep native/P3/browser behavior and shared OpenSSL
provenance intact. No push, merge or CI dispatch is part of this implementation
increment; the previously authorized publication closure remains a separate gate.

## Compiler contract

Capability macros are derived by config.hpp from the compiler target and verified
build selections. They use the WEBCPP_ASIO_ prefix, have documented 0/1 values,
and cannot be forced to claim support. Availability of a backend and selection of
an optional compiled dependency are distinct. Feature-specific headers must reject
known-invalid use with a named target, missing requirement and supported alternative.
Generic headers must not reject supported alternatives such as a custom browser
transport. Unsupported runtime flags/options are still errors, not global build bans.

## Verification

Public B2 consumers must fail before each implementation and pass afterward.
Run native/P2/P3 regressions, browser tests as relevant, EH on/off, negative compile
controls, handler allocation/cancellation/lifetime tests, real TLS trust/hostname and
transfer/shutdown cases. Use bounded local drivers and preserve logs. Builds use
wasi-sdk 34.0, Wasmtime 50.0.1, Boost 1.92 and Emscripten 6.0.11. Never count an
unsupported error as successful feature execution. Each delegated task receives a
fresh review, followed by an integration review of the final candidate.
