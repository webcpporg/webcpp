# OpenSSL source integration

## Approved scope and design

Build pinned, unmodified OpenSSL 3.5.9 from an upstream Git submodule through
B2. Export one explicit static dependency to consumers. Use upstream Configure
and its file-by-file Make build rather than duplicating its platform manifests.
Keep generated headers and archives together, isolated by toolchain and variant.
Support native Clang/GCC on macOS/Linux and WASIp3 single/cooperative threading;
reject unsupported platforms explicitly. Native Windows requires a separate
MSVC/nmake integration and is not claimed by this increment.

The existing local probe established WASIp3 source compatibility and secure host
entropy plumbing. Integration must retain that configuration, fail closed when
entropy fails, and never select a host-installed OpenSSL as a fallback.

## Constraints

- Preserve existing uncommitted WASIp3 work and other sessions.
- Run local tests only. No CI, publication, push, or unrelated dependency updates.
- Keep upstream sources and generated files unmodified by hand.
- Use the selected B2 C compiler and flags. Keep archive/header configuration paired.
- Document cooperative threads and the SDK's missing cooperative C++ EH runtime.

## Implementation sequence

1. Add a real B2 consumer test that requires the source-built dependency, observes
   its threading configuration, and calls RAND and TLS APIs. Observe failure.
2. Pin the upstream submodule; implement B2-generated archives and headers with
   checked toolchain/platform configuration and an external WASIp3 Configure target.
3. Connect Asio's explicit OpenSSL alias; preserve browser diagnostics. Test real
   verified TLS 1.2/1.3, rejected identities, entropy failure, and thread isolation.
4. Update instructions and AsciiDoc capability/reference guidance using the project
   documentation skill. Record exact local evidence and limitations.
5. Review the full change independently, fix findings, and run focused verification.

## Verification

Fresh builds of native single/multi and WASIp3 single/multi, including supported
exception variants; paths containing spaces; missing checkout and unsupported
platform diagnostics; incremental rebuild after changed configuration/source;
no dependency action for unrelated programs. Inspect native linkage for absence
of a host OpenSSL dylib. Exercise TLS through webcpp::asio::ssl, not only raw
OpenSSL. No statistical random-byte test is presented as an entropy proof.

## Initial progress

- Existing probe inspected; native threaded and WASIp3 single/cooperative builds
  passed previously. Production integration is still pending.

## Completion evidence

- Source dependency implemented and pinned, with no upstream source patches.
- Public B2 target and Asio alias integrated. Effective compiler flags identify
  separate artifact directories; all 142 installed public headers are outputs.
- Shared WASIp3 cooperative configuration extracted without changing its existing
  precedence or missing-runtime diagnostics; both existing profile tests passed.
- Seven Release runtime profiles passed: native Clang single/multi with EH on/off;
  WASIp3 single with EH on/off and cooperative with EH off. This covers 42 TLS
  cases, 12 entropy process runs (including failures), and three four-thread runs.
- Native GCC 15 multi/EH-on passed six additional TLS cases. Native executable
  inspection found no dependency on a host libssl/libcrypto dynamic library.
- Five B2 behavior cases passed, covering source linkage, incremental reuse,
  changed C flags, deleted generated headers, lazy missing-source failure,
  unsupported targets, pin mismatch, and an actual source checkout with spaces.
- The path-with-spaces test exposed upstream Configure resolving source symlinks.
  Build staging now copies the unchanged source tree into a temporary directory.
  That native case then passed; fresh WASIp3 cooperative TLS, entropy success and
  failure, four-thread operation, and both Asio SSL tests passed after the fix.
- Eight native/browser SSL regressions, two WASIp3 SSL tests, Python type/style
  checks, C/C++ formatting, AsciiDoc source checks, MrDocs generation and rendered
  documentation checks passed. Logs are under .local/openssl-*.log; the standard
  runtime matrix is .local/openssl-integration/all-results.json.
- Independent read-only review found no remaining Critical/Important issue.
  Its archiver-index concern was resolved by using the selected AR for indexing.
- No CI, push, merge, or commit was performed. The submodule registration staged
  only .gitmodules and the new gitlink; other prior changes were preserved.

## Explicit limits

Native runtime coverage is macOS arm64. Linux Clang/GCC mappings are implemented
but unverified here. Windows/MSVC, full upstream OpenSSL test-suite execution,
FIPS validation, snapshot/restore reseeding, and independent concurrent B2 runs
writing the same output directory are outside this increment. Cross-process
build isolation requires separate --build-dir values. C flags retain B2's normal
scope; apply dependency-specific flags directly to the OpenSSL target.
