# Local WASIp3 and TLS integration closeout

## Initial closeout: scope and repository pair

The initial closeout consolidated the approved Asio/Cobalt WASIp3, source-built
OpenSSL, embedded CA, and Cobalt SSL work into local commits. It ran local
verification only. CI, publication and main-branch integration were outside
that initial scope; the owner subsequently authorized the follow-up below.

The verified implementation pair is:

- Superproject build: `c07c2129fd6c0d45000938edecfd0f759c9288f0`.
- Asio library: `6a7f3fed2b4207c75c5180a336757258b7d074c3`.
- OpenSSL source: `45e844fa2a14ec92d146bd8f5778ac130b6625fb` (3.5.9).
- Boost baseline: 1.92.0, checked by the patch manifests.

At that point the Asio repository was local at `libs/asio`, on
`work/task14-guide`, without a remote or a superproject gitlink. The superproject
was on `work/asio-task9-review`. Both repositories had to be preserved together;
cloning the superproject alone did not supply that local library.

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

Publication, Asio remote/submodule registration and main-branch integration
were separate owner-directed steps at the end of the initial closeout. The
follow-up below supersedes that pending integration status. CI remains excluded
at the owner's request. Worktrees and local test evidence are preserved.


## Follow-up integration authorized on 2026-11-02

The owner requested the remaining integration. The selected destination is
`https://github.com/webcpporg/asio`, public like the other first-party libraries.
The Asio main merge is `3611a6ed78dcde4a3da3f314d3aba5453ff99428`, retaining
all existing history. Its subject includes `[skip ci]`; only that main branch
is published. The superproject records it as `libs/asio`, with relative URL
`../asio.git`, and its main integration remains local. No superproject push or
CI execution is included.

The superproject merge incorporates main at
`a4c770e07becaa32b840554512b37d96b4440d18`. Its new shared guidelines and skill
structure are retained. Asio-specific rules move into the appropriate shared
chapters, and obsolete external-OpenSSL CI planning is removed. Other libraries'
updated gitlinks are preserved. Existing dirty nativejson-benchmark files in
the primary checkout are outside this work.

### Integration findings and corrections

1. Lint's compilation database used dry-run paths for generated headers before
   those headers existed. A clean scratch consumer of the embedded CA target
   reproduced the failure. Compile-only headers-alone targets now materialize
   dependencies for both exception modes before header analysis; they execute
   no test programs. The focused regression passed after failing beforehand.
2. The OpenSSL builder required Git even for a source distribution. An actual
   distribution consumer reproduced that failure. Source staging now checks
   a canonical SHA-256 of paths, Git modes and file-content hashes before
   Configure. Git checkouts additionally keep revision and tracked-diff checks.
   The updater derives inventory, omitted nested pins and timestamp from Git
   objects at the selected commit. A parent repository cannot masquerade as
   the extracted source's own checkout.
3. Distribution refused OpenSSL's 11 unused nested repositories. It now omits
   only paths and commits recorded for the matching OpenSSL source pin. Unknown
   paths, different nested commits and stale source pins are still refused.
   The real distribution contains 5,789 OpenSSL files whose digest matches the
   build pin. A native B2 consumer built from that archive and ran TLS and RAND.
4. Full lint exposed chained diagnostic calls, a missing const, a Python loader
   type assumption and intentional upstream-source includes lacking an explicit
   suppression. These were corrected without changing TLS behavior. No upstream
   Boost or OpenSSL checkout was edited.

### Final local verification

The final seven-profile Release matrix passed after the source-build changes:
all suites and examples, normal/buffered TLS, state tests, and 84 combinations
of transfer/shutdown errors and cancellation with TLS 1.2/1.3. Native runtime is
macOS arm64; WASIp3 uses wasi-sdk 34 and Wasmtime 49.0.3. The profile table above
applies unchanged. Cooperative threads remain distinct from CPU parallelism.

Full lint reported 177 compilation commands, 64 translation units analyzed,
zero Pyright errors or warnings, and `lint: clean`. A fresh `b2 -a doc` passed
MrDocs, AsciiDoc and rendered checks. The OpenSSL suite passed all seven cases;
the source updater suite passed all five cases. The full release suite and the
real distribution's TLS/RAND test passed. The other build/patch/CA/report suites
were rerun against the merged tree. The harness suite initially lacked its
JSON Schema fixture submodule; initializing that exact pinned fixture made the
unchanged suite pass. All 58 cases of the final lint-tool regression suite
passed, including the new generated-header dependency regression.

Evidence is retained under `.local/merge-2026-11-02/`:

- `final/matrix.log`, `final/verified-*.log`: final seven-profile builds and TLS.
- `lint-final.log`, `lint-headers-{red,green}.log`, `lint-suite-final.log`:
  full lint, generated-header reproduction and the lint regression suite.
- `openssl-archive-{red,green}.log`, `openssl-full-green.log`,
  `openssl-source-test.log`, `openssl-real-dist-green.log`: source validation.
- `review-real-openssl-dist-{red,green}.log`, `review-release-full.log`:
  distribution reproduction and release tests.
- `tools.log`, `tools_*.log`, `harness-final.log`, `doc-final.log`: other checks.

Earlier failing logs are intentionally retained. Independent review found no
remaining blocker in the changes to source verification, release packaging or
lint preparation. This integration does not complete Asio proposal tasks 22/23
or the separate conformance items still named in CODING-GUIDELINES.md chapter 19.
