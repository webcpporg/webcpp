# Portable Asio, Cobalt and Beast distribution

## Owner direction and scope

On 2026-11-06 the owner requested Asio first, coordinated Cobalt delivery, and a
Beast audit under the same consumption contract. Native applications must use the
corresponding Boost implementations. WebAssembly selects explicit adaptations
through each library's configuration and target-specific headers. Consumer builds
must not patch an installed Boost or manufacture replacement headers behind B2.
The public entry points are `webcpp::asio`, `webcpp::cobalt` and `webcpp::beast`.

This supersedes the Cobalt genesis decision that keeping all upstream include paths
and namespaces was more important than portable distribution. The existing genesis
application, browser, benchmark and documentation obligations remain in scope.
Earlier green results identify the previous implementation and must be rerun after
the migration. No remote CI, publication or merge is part of local implementation.

## Native contract

The supported upstream-equivalent public types are aliases to the actual Boost
types, not subclasses that merely behave similarly. Identity is checked with
`std::is_same_v`, including Asio contexts, timers, sockets and executors, Cobalt
coroutine types/tokens and Beast HTTP/WebSocket types. Explicit WebCPP additions,
such as trust-policy helpers, remain separately documented extensions.

Native Cobalt uses the upstream compiled core and upstream entry-point behavior.
It must not silently receive local coroutine or I/O corrections through an include
overlay. Known upstream failures remain independently reproduced and documented;
correcting them upstream is distinct from claiming a patched library is native
Boost. The current Windows IOCP correction requires the same treatment.

Owner-approved exception on 2026-11-06: retain WebCPP's corrected Cobalt SSL
wrapper on native targets too. The unmodified upstream wrapper reproduced state,
shutdown and post-cancellation write failures. `webcpp::cobalt::io::ssl::stream`
therefore has its own type and implementation, while the core coroutine types,
executor and plain I/O types remain Boost. Its headers and compiled source must
ship explicitly and coexist with the unmodified `boost::cobalt::io::ssl` type.
This exception does not authorize patching installed Boost or changing the native
core/runner. TLS state, transfer, errors and cancellation require fresh native and
WASI runtime evidence.

The current Asio `io_context_options` and turn-control methods are browser
extensions. Native code uses Boost's constructors and members. Code that needs a
browser-only option uses an explicit target conditional. WASI behavior is specified
independently; preserving its existing wrapper initially does not establish native
identity or final packaging completion.

## WebAssembly contract

Targets are Emscripten, WASIp2 and WASIp3. JSPI and Asyncify are Emscripten suspension
variants, not WASI versions. Thread mode, exception mode, compiler/SDK and actual
runtime remain separate matrix dimensions. Config derives target capabilities from
the compiler and backend; a caller cannot forge support by defining a capability.
Compiler and linker requirements still have to agree with header configuration.

Adapted implementation files are shipped as ordinary, versioned library sources.
Source synchronization may use an audited maintainer generator, but a consumer
must not need to run that generator, Git, or a patch program. Each derived file has
an upstream revision, license, original hash and resulting hash. The initial
upstream baseline remains Boost 1.92.0.

Wasm implementation includes use explicit library-owned paths. They must not rely
on placing a replacement `boost/asio` or `boost/cobalt` directory before installed
Boost. Internal namespaces and include guards must prevent accidental mixing of
upstream and adapted implementations. Public algorithms continue to use the
appropriate Asio executor, cancellation and completion-token traits. The precise
private source transformation is an implementation decision gated by include-order,
multi-translation-unit and custom-token conformance tests.

The three libraries must select one consistent Asio backend. A native Beast or
Cobalt template must not accidentally instantiate against an incompatible Wasm
executor family. Preserve the existing browser scheduler, default 100 callbacks,
worker ownership and cleanup. Plain Asio must not depend on Cobalt or optional TLS.
Optional guest TLS continues to use one shared OpenSSL/CA provider.

## Build-system boundary

B2 remains the project's primary development, testing, documentation and release
tool. It consumes the same shipped sources that an external build consumes.
Generated WIT bindings, platform source units, compiler/link flags, exports and
optional provider dependencies are explicit build requirements. Generation of WIT
bindings is a normal toolchain step, not permission to rewrite Boost headers.

Provide a documented consumer recipe and machine-readable source/configuration
inventory. Prove consumption with direct compiler commands and an out-of-tree
CMake consumer. Do not maintain a second release or CI pipeline. Both consumers
must work from an unpacked source distribution with no `.git`, `bin/`, `.local/`,
B2 installation or existing overlay. Dependencies/toolchains may be supplied at
explicit paths; the test must not silently read developer-specific caches.

Native and Wasm builds of the same source can have different type identities and
ABIs. Native interoperability with Boost must be proved, not extrapolated into
cross-backend binary interoperability. Specialization and customization points
must have a documented, tested migration path.

## Examples, evidence and documentation

Retain every original example and its exact identity. Run feasible originals on
native, real browsers and Wasmtime. An environment lacking a facility cannot be
advertised as running the unchanged example. A browser fetch/WebSocket counterpart,
WASI host-HTTP counterpart, or supplied-stream counterpart has a separate identity,
states its semantic differences and remains a real C++ program.

Preserve and extend the existing Release size, compile-time, startup, throughput,
yield/responsiveness and memory methodology. Record source/artifact hashes, actual
flags, runtimes, sample counts and unavailable measurements. Prior measurements
remain historical until reproduced for the new implementation.

Each library's Diataxis AsciiDoc guide leads with its purpose: making existing
Boost-style C++ applications easy to compile for WebAssembly. State what is new
relative to Boost, the native forwarding contract, every public configuration
option and its default/scope, build recipes, feature/application matrix and
versioned limitations. MrDocs describes WebCPP additions and public adaptations;
link the corresponding pinned Boost reference instead of duplicating prose
unnecessarily. Examples in documentation come from compiled sources.

## Acceptance and sequencing

1. Establish direct native-consumer identity and runtime witnesses first.
2. Package the Asio Wasm backend and its SDK support, without consumer patching.
3. Package Cobalt against that backend and restore upstream native source selection.
4. Audit and adapt Beast against the same dependency contract.
5. Run every feasible declared application/profile, refresh measurements and docs.
6. Verify source-distribution consumption, local checks and an independent review.

No stage alone completes the three-library migration. Do not remove the old Wasm
build path until its replacement has equivalent user-facing evidence. Native
identity checks do not certify the current Cobalt archive or Windows recipe: those
have their own source-selection gates.
