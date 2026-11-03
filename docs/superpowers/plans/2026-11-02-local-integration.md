# Local WASIp3 and TLS integration closeout

## Scope and repository pair

Consolidate the approved Asio/Cobalt WASIp3, source-built OpenSSL, embedded CA,
and Cobalt SSL work into local commits. Run local verification only. No CI,
push, remote repository creation or merge is part of this closeout.

The verified implementation pair is:

- Superproject build: `c07c2129fd6c0d45000938edecfd0f759c9288f0`.
- Asio library: `6a7f3fed2b4207c75c5180a336757258b7d074c3`.
- OpenSSL source: `45e844fa2a14ec92d146bd8f5778ac130b6625fb` (3.5.9).
- Boost baseline: 1.92.0, checked by the patch manifests.

The Asio repository is local at `libs/asio`, on `work/task14-guide`, without a
remote or a superproject gitlink. The superproject is on `work/asio-task9-review`.
Both repositories must be preserved together. The owner must establish the
library repository before publication and submodule registration; cloning the
superproject alone does not currently supply this local library.

## Findings resolved before committing

1. The WASIp3 acceptor object did not inherit the common Cobalt composition
   include path from its parent archive. A real pending `accept()` cancelled
   through its promise hit the watchdog with exit 134. Explicit common-overlay
   dependencies on the separate endpoint/acceptor objects fix this. The new
   `cobalt_accept_cancel` test requires `operation_aborted` and an unopened
   returned socket. No peer connects and no guessed delay establishes readiness.
2. Header installation omitted `webcpp_ca_certificates.hpp`. A standalone
   consumer of the installed include directory failed to compile. The B2
   installation now generates and installs that header plus the exact PEM,
   manifest, README and MPL license. It does not build dependency archives.
3. The CA incremental test could mutate its input within the same whole second
   observed by B2. Explicitly newer timestamps on its temporary inputs make the
   test deterministic without sleeping or removing integrity checks. Builds
   still follow B2 timestamp semantics; use `-a` for fresh verification.
4. Git whitespace checking now recognizes the mandatory blank context lines
   in the four unified Boost patches. No patch payload or pinned hash changed.

Independent review confirmed both important findings resolved and reported no
remaining critical or important finding in this scope.

## Fresh verification on 2026-11-02

All seven Release profiles passed fresh `b2 -a` builds of `libs/asio/test`,
`libs/asio/example`, and the three Cobalt SSL executables. Native runtime was
macOS arm64. WASIp3 used wasi-sdk 34 and Wasmtime 49.0.3.

| Target | Threads | Exceptions | Result |
| --- | --- | --- | --- |
| Native Clang | single | on | passed |
| Native Clang | single | off | passed |
| Native Clang | multi | on | passed |
| Native Clang | multi | off | passed |
| WASIp3 | single | on | passed |
| WASIp3 | single | off | passed |
| WASIp3 | cooperative multi | off | passed |

Each profile additionally passed `tools/openssl/test/tls.py` with normal and
buffered SSL clients, the state test, and the cancellation test. Six cancellation
and shutdown cases with TLS 1.2/1.3 across seven profiles give 84 combinations.
The new composed-accept cancellation test passed in all seven profiles.

The following tool suites passed:

- Asio and Cobalt patch preparation tests.
- `asio_wasip3_test.py`, `cobalt_wasip3_test.py`, `cobalt_ssl_test.py`.
- `ca_certificates_test.py`, all three `ca_certificates_b2_test.py` cases.
- All five `openssl_test.py` cases and all `jamroot_test.py` cases.
- The four Cobalt cases in `boost_libraries_test.py`, including native,
  Emscripten JSPI and Asyncify with exceptions on/off.

An additional native client compiled against the installed WebCPP headers and
matching source-built OpenSSL archives, constructed the default TLS context,
and verified that peer verification was enabled. No checkout WebCPP include
path or generated-header include path was supplied to that compiler command.

Scoped text lint, C++ formatting, Python analysis and clang-tidy on the two
cancellation test programs passed. `b2 -a libs/asio/doc` passed source checks,
MrDocs reference generation, AsciiDoc conversion and rendered checks.

Machine-local commands and logs are retained under `.local/closeout-2026-11-02/`:

- `verified-matrix.log` and `verified-*-suite.log`: final build/runtime matrix.
- `verified-tools.log`, `tools-[0-5].log`, `ca-b2-green.log`, `jamroot.log`:
  final relevant tool results.
- `accept-red.log`, `accept-green.log`, `install-red.log`: failure and correction
  evidence. Earlier `matrix.log` and `tools.log` deliberately retain failures.
- `installed-tls.cpp`, `installed-tls.log`: standalone installed-header client.
- `lint.log`, `tidy.log`, `doc.log`: code and documentation checks.

## Limits and remaining integration work

This closeout does not establish Linux/Windows runtime coverage, CPU-parallel
WASIp3 threads, a cooperative exception runtime, safe TLS connection reuse after
terminal cancellation, or concurrent access to one SSL stream. Those limits
remain in the library's capability matrix. The exception-free Cobalt issue-287
diagnostic remains present.

Publication, the Asio remote/submodule registration, main-branch integration,
and CI validation remain separate owner-directed steps. Worktrees and local
test evidence are preserved; no unrelated checkout was changed.
