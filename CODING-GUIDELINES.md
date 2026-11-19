# webcpp's coding guidelines

This file is the single source of webcpp's rules on how code is written and
of every decision of its software design, each with its reason. It is
written for coding agents and human contributors alike. With
[AGENTS.md](AGENTS.md), which says how to work in the tree (the tools, the
commands, the API reference and the pages, the lanes, the CI and the
releases), it holds everything needed to port a library to webcpp or to
change one: an agent with no other context does it by following the two.
Read this file first, then `AGENTS.md`, then the library's own `AGENTS.md`
(`libs/<name>/AGENTS.md`), which holds only what is specific to that
library: the original and its version, how its oracle drives the original,
its particular cautions.

**One home for each rule and each decision.** A rule or a decision is
written here once. Every other file that needs it, `AGENTS.md`,
`CONTRIBUTING.md`, an agent skill, a library's `AGENTS.md` or page, a tool's
message, a proposal, points to its chapter instead of restating it; where
one of them seems to differ from this file, this file rules.

**Where a decision is made, and where it lives.** A decision is made in a
proposal, in [webcpporg/proposals](https://github.com/webcpporg/proposals),
and decided by the owner. Chapters 1 to 15 describe the tree as it is.
Chapters 16 to 18 hold what is decided and not yet built, and what is
proposed and not yet decided, each with the proposal that holds it in full
and rules over this summary while it is open. Chapter 19 holds the
conflicts still open between a decision and a rule, or between a design
document and its tree. The change that builds a decision moves it into
chapters 1 to 15, in the same change; the proposal's `design.md` stays as
the record of how it was decided.

Chapters 1 to 13 apply to every change: read them whole. Chapters 14 to 19
are read by section: the organization's, and those of the libraries a
change touches.

A chapter of this file is cited as "chapter N", one of the superproject's
`AGENTS.md` as "`AGENTS.md` chapter N". Every command below runs from the
superproject's root, in a shell where `CPATH`, `CPLUS_INCLUDE_PATH` and
`C_INCLUDE_PATH` are unset (`AGENTS.md` chapter 6).

## Contents

Working:

1. Process
2. Commits and text

Writing code:

3. Names
4. The language
5. Bringing a C library into webcpp
6. Exceptions and RTTI
7. Doc Comments
8. Tests
9. What the lint enforces

Libraries and ports:

10. Choosing and registering a port
11. Fidelity
12. Evidence: oracle and twins
13. Porting a library, step by step

Design:

14. The organization's design
15. The libraries' design

Not built yet:

16. Roadmap
17. Decided, not built
18. Proposed, not decided
19. Conflicts and open questions

## 1. Process

- **The specification before the code, a failing test before the
  implementation.** A behaviour is written down (in the page, or in the
  library's `AGENTS.md` for what is internal) before it is built, and a test
  is seen failing before the code that makes it pass.
- **A defect is first reproduced the way a user meets it:** the command a
  user runs, the page a reader opens, the lane CI runs. Then it is fixed, and
  the reproduction becomes a test.
- **Only a build from scratch counts as evidence:** `b2 -a`. b2 compares
  timestamps, and an incremental build can leave a stale result in place. An
  incremental build is for iterating.
- **Green, before any merge,** means all of these, run and read, not assumed:
  - every declared lane from scratch: `b2 -a libs/<name>/test
    libs/<name>/example` natively, and with `toolset=clang-wasip2
    testing.launcher=wasmtime` and `toolset=clang-wasip3
    testing.launcher=tools/boost/asio-wasip3/run.sh` where declared, and every own lane the
    library declares, `b2 -a libs/<name>/test/oracle//oracle` for an oracle
    and, on each target it names, `b2 -a toolset=clang-wasip2
    testing.launcher=wasmtime libs/wasi/test//http` for one on wasip2;
  - `b2 -a doc`;
  - the lint: `lint: clean`;
  - the tests of the build and of the tools, when they or what they test
    changed: `tools/test/jamroot_test.py`, `tools/test/webcpp_jam_test.py`,
    `tools/test/oracle_jam_test.py`, `tools/test/generated_jam_test.py`,
    `tools/test/component_jam_test.py`, `tools/generated/generated_test.py`,
    `tools/test/emscripten_test.py`, `tools/test/crypto_jamfiles_test.py`,
    `tools/test/crypto_jamfiles_format_test.py`,
    `tools/test/hash_jamfiles_test.py`, `tools/test/hash_jamfiles_format_test.py`,
    `tools/test/external_test.py`,
    `tools/test/doc_test.py`,
    `tools/test/harness_test.py`, `tools/test/third_party_test.py`,
    `tools/test/boost_libraries_test.py`,
    `tools/lint/lint_test.py`, `tools/report/report_test.py`,
    `tools/doc/doc_check_test.py`, `tools/doc/doc_comments_test.py`,
    `tools/doc/extensions_test.py`, `tools/doc/counts_test.py`,
    `tools/oracle/twins_test.py`, `tools/oracle/compare_test.py`,
    `tools/variants/variants_test.py`,
    `tools/example/run_example_test.py`, `tools/component/serve_test.py`,
    `tools/drive/drive_test.py`, `tools/node/install_test.py`,
    `tools/ci/matrix_test.py`, `tools/ci/assemble_test.py`,
    `tools/ci/actions_test.py`, `tools/release/changelog_test.py` and
    `tools/release/release_test.py`: every `tools/**/*_test.py`, as the CI
    runs them, each as `python3 <path>`. They
    build in scratch copies under `$TMPDIR`, whose path holds a space, so they
    run beside a build of the tree;
  - CI green, the library's and the superproject's.
- **Fix the lint, the failures and the flakiness you meet,** even when they
  are not yours; report what you cannot fix.
- **A change of the build or of a tool** has a test that fails without it:
  the tests of `tools/` pin every behaviour this file and `AGENTS.md` state.
  A change to b2's `--out-xml` format shows as a red `report_test.py`, whose
  samples are recorded, never edited by hand
  (`python3 tools/report/record_samples.py`).
- **A change that alters a decision updates it here,** in the same change:
  the rule of chapters 1 to 13, or the decision of chapter 14 or 15, with
  its reason. A change that builds a proposal moves its decisions from
  chapter 17 or 18 into chapter 14 or 15, and one that resolves an entry of
  chapter 19 removes it.

## 2. Commits and text

- **Identity.** Every contributor, human or agent, maintainer or external,
  commits under their own git identity: a name and an e-mail address they
  control, of which a GitHub noreply address
  (`<id>+<login>@users.noreply.github.com`) is one. An agent commits under
  the identity of the account it acts for or of its own account, never under
  another person's; these rules fix no address. Either way, with no trailer
  of any kind (no `Co-authored-by`, no `Signed-off-by`, no agent name):

  ```
  git -c user.name=<name> -c user.email=<address> commit -- <paths>
  ```

  Stage and commit with explicit paths, never `git add -A`. A subject is
  plain: what the change does, prefixed by the part it touches
  (`tools/doc: ...`, `xactor: ...`).
- **No accidental trailer.** git reads a last body paragraph that starts with
  `word:` as a trailer (`std::` does). Start such a paragraph otherwise.
- **English** in everything written to a file: code, comments, documents,
  commit messages.
- **No em dash** (U+2014) anywhere; use a plain dash.
- **The banned word.** No file, file name or commit mentions the word that
  `veru[s]` matches, in any case: `git grep -I -i -e 'veru[s]'` prints
  nothing in any repository, and the lint checks every commit's author,
  committer and message too.
- **The licence notice.** Every source file (`.hpp`, `.cpp`, `.py`, `.mjs`,
  `.js`, `.sh`, `.jam`, `Jamroot`, `Jamfile`, `build.jam`, `.yml`, `.adoc`,
  `.html`) opens with it: with `//` for C++, JavaScript and AsciiDoc, with
  `#` for Jam, Python, shell and YAML; a `#!` line stays first:

  ```
  // Copyright (c) 2026 WebCpp.org
  //
  // Distributed under the Boost Software License, Version 1.0. (See
  // accompanying file LICENSE_1_0.txt or copy at
  // https://www.boost.org/LICENSE_1_0.txt)
  ```

  An HTML file opens with a comment whose first line is `<!--` alone and
  whose next lines are the notice as it is, the comment going on with what
  the file is, as `tools/doc/docinfo.html` does:

  ```
  <!--
  Copyright (c) 2026 WebCpp.org

  Distributed under the Boost Software License, Version 1.0. (See
  accompanying file LICENSE_1_0.txt or copy at
  https://www.boost.org/LICENSE_1_0.txt)

  The style every page adds to Asciidoctor's, in its head (docinfo=shared).
  -->
  ```

  The lint checks each of these. Markdown files, including `SKILL.md`, do
  not need this source-file notice; upstream licence and attribution
  notices are preserved.
- **History.** A repository whose code was moved from elsewhere starts from one
  import commit; the history of the code it was moved from is not carried
  over.
- **Outward actions** belong to the owner: no push to a webcpporg
  repository, no merge, no remote repository created, no GitHub setting
  changed, no SSH key or credential touched by an agent. An external
  contributor proposes a change by a pull request from a fork
  (CONTRIBUTING.md).

## 3. Names

| What | Rule | xactor's |
| --- | --- | --- |
| namespace | `webcpp::<name>` | `webcpp::xactor` |
| what is not public | a namespace `detail`, at any depth | `webcpp::xactor::detail` |
| convenience header | `<webcpp/<name>.hpp>`, which includes every public header, but may leave out one that brings an optional heavy dependency (below) | `<webcpp/xactor.hpp>` |
| headers | `<webcpp/<name>/...>`, one per responsibility, `snake_case` | `<webcpp/xactor/scheduler.hpp>` |
| macros | `WEBCPP_<NAME>_*` | `WEBCPP_XACTOR_*` |
| configuration | `<webcpp/<name>/config.hpp>`, which every public header includes first, which includes `<webcpp/config.hpp>` first, with `WEBCPP_<NAME>_NO_EXCEPTIONS` (chapter 6) | `<webcpp/xactor/config.hpp>` |
| test-only macros | `WEBCPP_TEST_*` | |
| include guards | `WEBCPP_<NAME>_<HEADER>_HPP` | `WEBCPP_XACTOR_ACTOR_LOGIC_HPP` |
| b2 target | `/webcpp/<name>//<name>` | `/webcpp/xactor//xactor` |
| error category | `webcpp.<name>` | `webcpp.xactor` |
| identifiers | `snake_case`, Boost's convention; `.clang-tidy` enforces it | |

config is the one exception: it holds the collection's macros, `WEBCPP_*`, as
Boost.Config holds `BOOST_*`, in `<webcpp/config.hpp>` and
`<webcpp/version.hpp>`, whose include guards are `WEBCPP_CONFIG_HPP` and
`WEBCPP_VERSION_HPP`, and declares no namespace.

A convenience header may leave out a public header that brings an optional
heavy dependency, which a user of the rest should not pay for, and names in
its comment the header it leaves out and the dependency:
`<webcpp/pratt.hpp>` includes pratt's engine, and leaves out
`<webcpp/pratt/calculator.hpp>`, which brings Boost.Decimal.

A test's helpers that are shared between tests go in `webcpp::test`
(`libs/xactor/test/require.hpp`). Example programs alias the namespace
(`namespace xactor = webcpp::xactor;`), as Boost's do.

## 4. The language

- C++20, header-only except the explicitly documented units that must be linked
  once per program, such as Asio's JavaScript imports and Cobalt entry point
  (chapter 15). B2 supplies those units; users do not copy them into applications.
  The Jamroot sets `<cxxstd>20`, `<warnings>extra` and `<warnings-as-errors>on`.
- **What a library builds on, in this order:** what webcpp already has;
  then Boost (boost.org); then the C++ Alliance's libraries
  ([cppalliance](https://github.com/cppalliance)), whose authors are Boost's;
  then the standard library; then a library from outside that follows Boost,
  the standard library and the standards of its field; then a C++ port of a
  very widely used C library; and only then an implementation of the
  library's own. A library from outside comes in after the owner's review,
  with the reason written in the library's documentation (OpenSSL, for one,
  because it is the standard of its field). The same order governs each
  function an implementation of its own writes: it builds on those bases
  first, and follows their standards. So a hash is Boost.Hash2's before
  anything else, and a JSON parser is Boost.JSON's.
- **Written for the web.** Every library is written to be taken to the web:
  its memory, its I/O and its scheduling are its user's to customize (the
  allocators below; the executors and schedulers it runs on), and on the
  emscripten target it uses what the browser offers, so that a C++ program
  in a web page has a development environment as good as the web's own.
- **Within Boost, the newest library of a kind:** Boost.Coroutine2 rather
  than Boost.Coroutine, Boost.Variant2 rather than Boost.Variant, Boost.Hash2
  rather than Boost.ContainerHash for new hashing, Boost.Unordered's flat
  maps rather than an older map, Boost.Charconv rather than a hand-written
  conversion.
- **A library from outside is wrapped,** behind an interface that follows its
  counterpart in the standard library or in Boost as closely as it can, so
  that the outside library is an implementation detail the user never names
  and another implementation can replace it: as webcpp::webrtc hides
  libdatachannel behind the W3C's WebRTC API, with the page's own WebRTC as
  its other implementation.
- **Types of a fixed meaning.** An integer whose width matters is one of the
  fixed-width types of `<cstdint>` (`std::uint8_t`, `std::int64_t`,
  `std::uint32_t`), as Boost.Config's `<boost/cstdint.hpp>` guidelines give
  them; a size or an index is `std::size_t`, a difference
  `std::ptrdiff_t`; plain `int`, `long`, `short` and `unsigned` appear only
  where an interface of the standard library or of Boost asks for them.
- **Errors as values.** An operation that can fail returns its error:
  `boost::system::result<T>`, with an error category of the library's own
  (`webcpp.<name>`) and fixed enumerator values that are never reused.
- **No global or static mutable state.** `.clang-tidy` enforces part of it
  (`cppcoreguidelines-avoid-non-const-global-variables`).
- **Determinism.** No clock, file, network, process, thread, environment or
  entropy, unless that is the library's purpose. The lint's world rule finds
  them by name in every library header; a line that names one without
  reaching the world (a simulated clock), or that reaches it because it is the
  library's purpose, says why after `lint-world:` on the same line:

  ```cpp
  #include <boost/asio/io_context.hpp>  // lint-world: posts handlers only
  ```

- **Allocation.** A library is to avoid dynamic allocation as far as its job
  allows, and to let its user customize the allocator of what it does
  allocate, so that it can be used with Boost.Interprocess:
  - **A data structure that makes sense to share** (a parsed JSON document,
    a state machine's definition) takes an `Allocator` template parameter,
    allocates through `std::allocator_traits` of it, and holds every pointer
    as the allocator's `pointer` type (Boost.Interprocess's `offset_ptr`) or
    as an offset, never an absolute address, a vtable or a `std::function`: it
    can be built in a shared segment and used in place by another process
    that maps it elsewhere.
  - **Everything else** (run-time objects: actors, rooms, sockets, handlers)
    routes every allocation through an allocator its user gives, a template
    parameter or a `std::pmr::memory_resource`, with no requirement to live
    in a shared segment.
  - Each library's page says which of its types are shareable, and a test
    counts allocations. An approved exception for runtime or wrapped-library
    storage is named in chapter 15 and the guide, measured separately where a
    hook exists, and never hidden by a tolerance for unexplained allocations.

  A library ported or written from now on is born with this rule, as pratt
  is: its calculator's environment takes the user's `Allocator`; and as
  trystero is, through `std::pmr`: a `std::pmr::memory_resource` given in
  its `app_config`, and in a room's `room_options`, reaches every allocation
  of the app and its rooms, including the immutable password in the app's
  resource, which a counting test
  proves natively and on emscripten. The libraries written before it are
  brought to it by a review (chapter 16).
- **Asynchronous code runs on the executor its user supplies.** Libraries use
  Asio-compatible executors and completion mechanisms without driving the run
  family internally. A library whose model is actors uses xactor; its application
  drives that scheduler from its event loop. This records the owner's accepted
  Asio decision of 2026-10-11, rather than requiring the event loop itself to be
  implemented as actors.
- **Text** is passed and held as `std::string_view` where nothing must own
  it; `std::string` only where something does.
- **A function starts with its guards:** every condition it needs is checked
  first, and what fails returns there, before any work begins.
- **A comment says what the code does not make clear:** why, a constraint, an
  example of a value. A descriptive comment is one sentence of what the code
  that follows does, then an optional reason, in a few lines.
- **JSON literals in code are laid out for their reader:** a raw string
  literal that opens a line with `R"({` or `R"([` has its members four spaces
  deeper than that line, one per line, and closes at that line's indentation.

## 5. Bringing a C library into webcpp

A webcpp library that builds on a C library (webcpp::crypto on BearSSL and
libsecp256k1, for example) brings it in this way, so that the C code stays
exactly its authors' and the program carries only what it calls.

1. The C library is a submodule under `third_party/libs/<name>`, pinned at a
   commit and never edited. When upstream is not on GitHub, an unmodified
   `webcpporg/<name>` mirror stands in (BearSSL's is `webcpporg/bearssl`),
   refreshed only when the pin moves.
2. `third_party/Jamfile` builds it from its own sources, file by file, as a
   static library, in the library's own C dialect, on every target and with
   every file: a file that does not apply to a target still compiles, to the
   stubs other files call. A single unity source is not used. Three exceptions,
   each recorded in its row of chapter 10: BLAKE3's intrinsics files compile on
   their instruction sets alone, each flagged for its own set; XKCP is built
   from the one file of Keccak-p[1600] and the five high-level files
   webcpp::hash's adapter calls, not from every file of its package;
   libsodium is built without its `.S` files.
3. Every file is compiled with `-ffunction-sections -fdata-sections` (`/Gy
   /Gw` on MSVC); upstream's warnings are not webcpp's (`<warnings>off`); each
   define the library cannot work out for itself on a target sits beside the
   sources with its reason (BearSSL's `BR_USE_GETENTROPY=1` on WebAssembly).
4. Its usage requirements give the public include directory, the define
   `WEBCPP_<LIB>_HAS_<NAME>=1`, and the link-time removal of unused sections
   (`-Wl,--gc-sections`, `-Wl,-dead_strip`, `/OPT:REF`).
5. A program names the C library in its own Jamfile, beside the webcpp library
   that uses it, so that its choice is explicit:
   `exe app : app.cpp /webcpp/crypto//crypto /third_party//bearssl ;`. A
   library named and never called adds no byte to the program. webcpp::crypto
   follows this rule (chapter 15): the third-party project answers to both
   ids, `/webcpp/third_party//<name>` and `/third_party//<name>`, and a
   user's Jamfile writes the latter.
6. Three layers stop a wrong build, each saying exactly what to add:
   - at compile time, the backend's header checks `WEBCPP_<LIB>_HAS_<NAME>`
     and `#error`s with the Jamfile line to add;
   - at link time, every function that calls the C library references a
     canary, `webcpp_<lib>_<name>_<commit7>_<configuration>__add_third_party_<name>_to_your_link`,
     defined by a small file of webcpp's that the Jamfile adds to the library,
     so that a missing library, or one of another commit or configuration,
     fails to link with that name;
   - on MSVC, the header and the canary carry `#pragma
     detect_mismatch("webcpp_<lib>_backend_<name>", "<name>-<commit7>-<configuration>")`.
7. OpenSSL is source-built by `/webcpp/third_party//openssl`, using its
   upstream Configure/Make manifests through `tools/webcpp-openssl.jam`.
   This is a deliberate exception to spelling out its source list in B2:
   upstream still compiles individual C/assembly files. Keep the generated
   headers and static archives in the same B2 variant directory. Never patch
   the upstream checkout, silently use a system OpenSSL, or mix the archives
   with another OpenSSL copy. The Asio alias links this dependency explicitly.
   Its headers are upstream's, so this adapter uses B2 dependency ordering and
   exact archive paths instead of injecting canary calls into upstream APIs.
   Native Clang/GCC recipes cover macOS/Linux. MSVC uses upstream Configure
   with nmake, explicit B2 runtime/debug flags and static `.lib` outputs;
   its initial profile uses portable C (`no-asm`) without a NASM dependency.
   Recipe/staging tests run locally; real Windows compilation remains a
   separate CI validation, not inferred from a dry run.
   WASIp3 single and cooperative profiles must agree with the consumer's
   threading choice. Keep explicit host entropy seeding and fail-closed tests.
   Other libraries with external dependencies still use `webcpp.external`.
8. The webcpp library's `config.hpp` chooses the default backend from the
   target and the `HAS` defines, and refuses impossible combinations with
   `#error`. The backend is named after the C library (`backends::bearssl`),
   never after a quality.
9. The documentation gives, per backend, its Jamfile line, what it exports
   (headers and functions), and every message above with its fix, written so
   that an AI agent writes a correct Jamfile at once.
10. One copy per program: webcpp's build of a C library is never linked
    together with another copy of it.
11. The CI proves, on every target: the C library's own tests pass on
    webcpp's build; a program that uses it runs; one that names it without
    calling it is byte-identical to one without it; each message above comes
    from a test of its own, in a directory of its own; the canary's commit is
    the submodule's.
12. Moving a pin is a change of its own: the submodule, the canary's commit,
    the tests on every target and the size table.

## 6. Exceptions and RTTI

- **Every supported target profile with a C++ exception runtime builds with
  exceptions on.** A threading profile whose SDK supplies no such runtime
  refuses `exception-handling=on` by name; the feature matrix identifies that
  limitation. WASI SDK 34's experimental cooperative sysroot is one such
  profile, to be rechecked on SDK upgrades. Whether a program uses exceptions is
  the choice of whoever builds it, never an imposition of a library or of
  webcpp. Natively the compiler's default holds. On wasip2 and wasip3 the
  Jamroot compiles with `-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false`
  and links with `-fwasm-exceptions -lunwind` (its region
  `wasi-exceptions`): wasi-sdk 34 emits the legacy encoding by default, which
  wasmtime 47 refuses to run ("legacy_exceptions feature required"). A
  program that uses exceptions on wasip2 needs a host that runs them:
  wasmtime 47 or later (wasmtime 37 to 46 with `-W exceptions=y`), jco
  with `jco transpile --bindgen-enable-wasm-exnref`, or another Wasm 3.0
  engine.
- **A user's build without exceptions.** `exception-handling=off` compiles
  with `-fno-exceptions` on any target, Boost.Config then defines
  `BOOST_NO_EXCEPTIONS`, and `webcpp.jam` links `tools/throw_exception.cpp`,
  a `boost::throw_exception` handler that prints and aborts; MSVC also gets
  `_HAS_EXCEPTIONS=0`. Whether a build has exceptions is the user's choice
  alone: every library supports both (below), the lint analyses every
  program both ways, and a library proves what behaves otherwise without
  exceptions by tests of its own that declare `<exception-handling>off`
  (trystero's `platform_*_no_exceptions`).
- **Each library has its own configuration macro,**
  `WEBCPP_<NAME>_NO_EXCEPTIONS`, as Boost.Asio has `BOOST_ASIO_NO_EXCEPTIONS`,
  in `<webcpp/<name>/config.hpp>`, which the convenience header and every
  public header include first, and which includes `<webcpp/config.hpp>` first.
  It is defined when `WEBCPP_HAS_EXCEPTIONS` is not: when the code is compiled
  without exceptions (`BOOST_NO_EXCEPTIONS`, which Boost.Config defines under
  `-fno-exceptions` and so under `exception-handling=off`), or when the
  developer defines `WEBCPP_NO_EXCEPTIONS`, which disables every library's at
  once; and a developer may define it alone, to turn one library's exceptions
  off in a build that has them. A program sets `WEBCPP_NO_EXCEPTIONS` for
  every library alike, without knowing which one throws, so a library that
  raises no exception of its own has the macro too, and says so in its Doc
  Comment. Its test, `test/config_test.cpp`, is built three times: as the
  build asks (`config`), where the macro is defined exactly when
  `WEBCPP_HAS_EXCEPTIONS` is not; with `WEBCPP_NO_EXCEPTIONS` defined
  (`config_all_off`); and with the macro itself defined on the command line
  (`config_developer_defined`). wasi, which includes nothing of Boost, reads
  `WEBCPP_NO_EXCEPTIONS` itself, beside the compiler's own macros, until its
  redesign includes `<webcpp/config.hpp>`. MrDocs parses a library as a build
  with exceptions does, so `config.hpp` defines the macro for the reference
  under `#ifdef __MRDOCS__` and undefines it at once: the reference lists it,
  and every API that throws stays in the parse.
- **An exception is raised through `boost::throw_exception`, never a bare
  `throw`,** and every API that throws sits behind
  `#ifndef WEBCPP_<NAME>_NO_EXCEPTIONS`, so that code that uses it does not
  compile without exceptions. The lint's bare throw rule refuses a `throw`
  expression in a library's public header, outside comments and literals,
  wherever it is: inside that `#ifndef` region too, in a template that
  nothing instantiates, and as a rethrow, `throw;`, which
  `std::rethrow_exception` replaces.
- **A library works without exceptions.** Its headers compile with
  `-fno-exceptions`: what throws, tries or catches sits behind
  `#ifndef WEBCPP_<NAME>_NO_EXCEPTIONS`, and a failure that cannot be
  returned goes through `boost::throw_exception`. The lint checks it, by
  analysing every aggregate translation unit, and every test and example, a
  second time as b2 compiles them with `exception-handling=off` (below).
  Clang refuses a `throw`, a `try` or a `catch` there, in a template only
  where a test or an example instantiates it: in a template that none of them
  instantiates, only the bare throw rule sees a `throw`, and a `try` or a
  `catch` is not checked. The one exception is a header that wraps a
  dependency which reports errors by throwing: its library declares it with
  `<exception-handling>on`, with the reason in a comment, on each
  headers-alone call, test and program of the backend that brings the
  dependency, since b2 lets no usage requirement override a build's
  `exception-handling=off` (measured: a usage requirement of the backend's
  target leaves its dependents compiled with `-fno-exceptions`); the lint
  leaves that header out of the analysis without exceptions, and names it;
  and the header declares nothing without exceptions: what follows its
  `config.hpp` sits inside `#ifndef WEBCPP_<NAME>_NO_EXCEPTIONS`, with a
  comment that names the dependency, so that a program built without
  exceptions that uses it fails on the first name it uses, and one that only
  includes it compiles. No library has such a header today; the fixture
  browser_demo's `native.hpp` is one, against the fake dependency of its
  `deps/include` (a fixture without `config.hpp`, it tests
  `BOOST_NO_EXCEPTIONS`): a program built without exceptions that includes
  `<webcpp/browser_demo.hpp>` beside it and calls `native_answer` fails with
  `no member named 'native_answer' in namespace 'webcpp::browser_demo'`.
- **A program that needs exceptions says so.** A test or an example that
  throws, tries or catches on purpose declares `<exception-handling>on` in
  its requirements, as the fixture demo's
  `webcpp.example catches.cpp : <exception-handling>on ;` does: b2 then
  builds it with exceptions whatever the build asks, a user's
  `exception-handling=off` included, and the lint analyses it with them
  alone and names it ("built with exceptions whatever the build asks").
- **RTTI** is never restricted by webcpp, on any target, and no variant is
  built without it; a user imposes their own.

## 7. Doc Comments

How the API reference is generated from them, and where it sits, is
`AGENTS.md` chapter 2.

### The format

Doc Comments are Javadoc/Doxygen style, `/** ... */`, before the symbol they
document:

```cpp
/**
 Handles one message, the payload of `cause`.

 The scheduler calls it once for each message delivered to the actor, and
 delivers the actor's next message only after it returns.

 @param turn What the actor may do while it handles the message.
 @param cause The message, in the envelope that says who sent it.
 @return Success, or an error of any category, which ends the actor with
 the status @ref status::error.
 @note An error ends this actor and only it.
 @see "Writing an actor logic", in the guide.
*/
virtual result<void> handle(xactor::turn<Message>& turn, const envelope<Message>& cause) = 0;
```

### What every public symbol needs

A public symbol is one at namespace scope of `webcpp::<name>`, or a public
member of a public class, outside every namespace `detail`. Every one is
fully documented: functions, classes, structs, enums and enumerators,
aliases, concepts, variables, data members and macros.

- **A brief,** the first paragraph, which is a single sentence: MrDocs makes
  the whole first paragraph the brief, and `doc_comments.py` fails a brief of
  more than one sentence (an abbreviation such as `e.g.` and a code span do
  not count).
- **`@param`** for every parameter, **`@tparam`** for every named template
  parameter (of a function, class, partial specialization, alias, variable or
  concept, hidden friends and member templates included), and **`@return`**
  for every function that returns a value. MrDocs reports a missing `@param`
  or `@return`; `doc_comments.py` reports a missing `@tparam`, which MrDocs
  does not.
- **A deleted function takes no `@return`.** Nobody can call it, so a
  `@return` would say nothing, and MrDocs accepts its absence:
  `actor_logic& operator=(const actor_logic&) = delete;` has a brief and no
  `@return`.
- **`@throws`, `@pre`, `@post`, `@note`, `@see` and `@code`** where they
  apply.
- **Each enumerator and each data member has its own Doc Comment.** clang
  attaches one comment to every declarator up to the next `;`, `{`, `}`, `#`
  or `@`, so in `/** A. */ a, b,` the enumerator `b` has `a`'s comment, and in
  `/** The x. */ int x, y;` so does `y`. `doc_comments.py` reports the second
  as undocumented, public or `detail`. Comment each one itself, and declare
  one data member per declaration.
- **A `detail` symbol** needs only its brief.

## 8. Tests

- Unit tests use Boost.Core's lightweight_test,
  `<boost/core/lightweight_test.hpp>`, declared with `webcpp.run`. `main`
  runs the cases and returns `boost::report_errors()`. A main that can suspend
  under Asyncify returns `webcpp::test::exit_status(boost::report_errors())`,
  so the Node runner observes its actual result (AGENTS.md chapter 4).
- A case that cannot go on after a failed check returns:
  `if (!BOOST_TEST(x.has_value())) { return; }`. A helper, which cannot
  return from its case, calls `require(BOOST_TEST(...))`, which ends the
  program with the errors counted so far
  (`libs/xactor/test/require.hpp`): a user may build a test without
  exceptions.
- Boost.Test is for a test that needs it (fixtures, data-driven suites),
  declared with `webcpp.boost-test`, natively only. The CI installs no
  compiled `unit_test_framework`: the suite compiles Boost.Test's header-only
  framework, `tools/boost_test_runner.cpp`, as an object of its own.
- A test that reads files at run time is given their directory by a
  `path-constant`, a `WEBCPP_TEST_*` define with forward slashes, quoted
  whole, `[ webcpp.data <directory> ]` in its requirements, and a
  `<dependency>` on the files it reads (a `glob-tree-ex` of them), so that a
  changed file runs it again; `/webcpp/third_party//json-schema-test-suite`
  gives all four for the JSON Schema Test Suite.
- Every test runs on every target its Jamfile declares. What a target cannot
  build is excluded by declaration (`: native`), and inside a program by the
  same condition the library uses (`#ifndef __wasi__`), never by skipping
  silently.
- A user's Jamfile of a library whose own tests cannot express it (b2's raw
  `exe`, a refusal on one target) is a fixture of the tools' test, not a
  library's test: `tools/test/fixtures/<library>_jamfiles/<case>/` holds the
  case's `Jamfile`, its sources and `<case>.outcome`, and
  `tools/test/<library>_jamfiles_test.py` builds each case on a scratch
  superproject, with b2 as a user runs it, once per target, in a build
  directory the cases of a target share, through `tools/test/user_jamfiles.py`,
  which every such test shares. The outcome file's lines starting
  with `#` are comments; a block `[all]`, `[native]`, `[native-linux]`,
  `[native-darwin]`, `[native-windows]`, `[native-arm64]`, `[native-x86_64]`,
  `[wasip2]`, `[wasip3]` or `[emscripten]` applies by the target, the system
  and the machine's architecture (`[all]` and each block that matches apply).
  `targets: <target> ...` (native only without it) names the targets the case
  is built for; `build: succeeds` or `build: fails` is b2's exit status; after
  `build: fails` every other line must be a whole line
  of b2's output (trailing spaces aside), in any order; a line of one
  lowercase word and a colon is reserved for these directives, and
  `line: <text>` states a literal output line, empty for a blank one, also for
  a line that starts with `#`, `[` or such a word,
  and `contains: <text>` (after `build: fails`) a text that one line of b2's
  output contains, for a line that starts with a path of the machine;
  `not-contains: <text>` (after `build: fails`) states that no line of b2's
  output contains the text, and `not-contains: <text> unless <allowed>` that
  every line containing it also contains the allowed text;
  `run: <program>`, after `build: succeeds`, runs the program as its lane runs
  one and every other line is its standard
  output, exactly; `arguments: <word> ...` gives b2 words for this case alone
  (`@scratch` is the case's scratch directory); `same-as: <case>/<file> <file>`
  states that the case's file is a byte-identical copy of another case's,
  checked when the outcome files are read (a copy, never a symbolic link,
  which a checkout on Windows reads as a text file). The fixtures sit outside
  `libs/*/test/`, so the raw-rules lint does not apply to them. The tools job
  of the CI runs the test; the `[native-darwin]` blocks apply only to a run on
  macOS, and the MSVC cases are `webcpp.compile-fail` and `webcpp.link-fail`
  of the library's tests.
- A test moved from the original's or another suite records the conversion,
  case by case, and each converted case is seen failing on a planted defect
  where the old one had a pinning test (`libs/xactor/test/CONVERSION.md`).

## 9. What the lint enforces

`tools/lint/lint.sh` lints the superproject and every library of `libs/` that
is a repository: what git tracks and what it would track (untracked, not
ignored), so a new file is linted before it is added, but nothing under
`third_party/libs/`, third-party code that keeps its own style and licence
(chapter 10). It prints each rule's section and ends with `lint: clean`, or
with `lint: failed: <rule>` for each rule that failed.

| Rule | What fails |
| --- | --- |
| clang-format | a C++ file not formatted as `.clang-format` says (Google-based, 4 spaces, 100 columns); `clang-format -i` fixes it |
| clang-tidy | a finding of `.clang-tidy` (every warning is an error) in the compilation database `tools/lint/compile_commands.py` writes from b2's dry runs, one per target the libraries declare: every test and example natively, with every program an own lane builds on that target, or on none (a served component, which only its own lane builds, among them; a served program in no own lane fails it, as it fails `b2 declared-lanes`), and each source that no native program compiles with the command of the first target that compiles it (wasip2, wasip3, else emscripten). A native command is told the host compiler's target and, on macOS, its SDK, and on arm64 `-DBOOST_UNORDERED_DISABLE_NEON`, since wasi-sdk's clang-tidy ships x86's intrinsics headers alone and Boost.Unordered includes `<arm_neon.h>` there (`lint_test.py`). A WebAssembly command names wasi-sdk's `clang++`, with that target's `--target`, to which the lint adds no host target or SDK, once the dry run of that target has generated the bindings its commands include (so the lint needs wit-bindgen and the WIT, `AGENTS.md` chapter 1); an emscripten command names Emscripten's `em++`, which clang-tidy cannot run, and is analysed with wasi-sdk's `clang++` in its place (the one beside the lint's clang-tidy), after the words `em++ <its options> --cflags` prints (the target `wasm32-unknown-emscripten`, the sysroot in Emscripten's cache, the `-iwithsysroot` directories compat and fakesdl, and the words of its exceptions), less the settings of em++ alone (`-sWASM_WORKERS`), which it reads and clang refuses, so the lint needs the emscripten toolset when a library declares emscripten. Plus each library's aggregate translation units, through which every public header is analysed, each compiled as a headers-alone translation unit of its target: a library whose public headers one target builds whole has one, of every header (`bin/aggregate/<name>.cpp`), natively, or, for a library whose headers build only for WASI, on wasip2 and on wasip3, each reading its version's branch; a library whose headers no single target builds (a native backend against a dependency of the host's, a browser backend for emscripten) has one per target its headers-alone units run on, of the headers that target builds (`bin/aggregate/<name>-native.cpp`, `<name>-emscripten.cpp`). Every command, a program's and an aggregate's, on every target, has its twin: the same translation unit as b2 compiles it with `exception-handling=off` on the same target (natively with the handler `tools/throw_exception.cpp`), so that what only a user's build without exceptions compiles (`#ifdef BOOST_NO_EXCEPTIONS`) is analysed too, and a `throw`, `try` or `catch` outside it fails, in a template where a test or an example instantiates it; a program that declares `<exception-handling>on` has none, and an aggregate's twin leaves out each header whose headers-alone call declares it (then a translation unit of its own, `<aggregate>-exception-handling-off.cpp`); the database names both. A public header without a headers-alone translation unit on any target, a declared target whose toolset is not configured, and a WebAssembly command whose compiler is neither wasi-sdk's `clang++` nor, on emscripten, Emscripten's `em++` (the lint would analyse it as a native command), fail it by name. Findings are reported in a library's public headers, in the headers of its tests and examples (`libs/xactor/test/require.hpp`) and in those of its JavaScript module (`libs/document/js/binding.hpp`), never in Boost's, the standard library's or a dependency's (`.clang-tidy`'s `HeaderFilterRegex`) |
| io_context::run | a call of Boost.Asio's `run`, `run_one` or `run_for`, which block, on an `io_context` however its type is qualified (`boost::asio::io_context`, `asio::io_context` through a namespace alias, `io_context` after a using); a driver drains with `poll` and `poll_one`. A program whose purpose is network I/O says why on the line, after `lint-run:` (`io.run_for(timeout);  // lint-run: the memory relays post to it`); a library has no blanket exemption |
| fluent chains | three calls chained in one expression |
| returns `*this` | a function other than an assignment operator, a prefix `operator++` or `operator--` (the iterator requirements make them return `*this`), or a function whose head follows a line `// lint-std: <reason>` naming the member of the standard it reproduces (`std::basic_regex::assign`), returning `*this`; the reason holds none of `;`, `{`, `}`, `#` or `@`, so that clang and MrDocs still attach the Doc Comment above the line to the function |
| em dash | U+2014 in any file |
| JSON literals | a raw JSON literal laid out otherwise than chapter 4 says |
| licence notice | a source file (C++, JavaScript, AsciiDoc, Python, shell, Jam, YAML, HTML) that does not open with the notice (chapter 2) |
| banned word | the word that the pattern `veru[s]` matches, in any case, in a file, a file name or a commit (its author, committer or message) of any repository |
| no clock, disk or network | a library header that names a clock, a file, a socket, a process, a thread, the environment or entropy (`random_device`, `getentropy`, `getrandom`, `arc4random`, OpenSSL's `RAND_bytes`, `<sys/random.h>`) without `lint-world:` |
| entropy sources | a library header whose path ends `entropy.hpp` or `random_device.hpp` that names `rand`, `srand`, `random`, `rand_r`, a `rand48` function, `seed48`, `lcong48`, a standard engine (`mt19937`, `minstd_rand`, `ranlux`, `knuth_b`, `default_random_engine`), `time`, `clock` or RDRAND (`_rdrand32_step` and its kin, the builtins, `rdrand` in asm), even with `lint-world:` |
| raw b2 rules | `run`, `run-fail`, `compile`, `compile-fail`, `exe`, `unit-test`, `link` or `link-fail` in a library's test or example Jamfile (`AGENTS.md` chapter 4) |
| Doc Comments | a command webcpp does not allow, a bare `@`, or a colon after a reference (chapter 7) |
| Pyright | an error or a warning in any Python file, with `pyrightconfig.json` (unused imports and variables are errors) |
| Python line length | a Python line over 100 columns |
| Python blank lines | a top-level `def` or `class` without two blank lines before it, its decorators and the comments just above it |
| Jam comment width | a comment line of a Jam file (`.jam`, `Jamroot`, `Jamfile`) over 80 columns, the width Jam comments are wrapped at |
| octal escapes | an octal escape of a C or C++ literal followed by a decimal digit (`"\\2200"`), which C++ reads as `"\\220"` and `"0"` and MSVC's warning C4125 refuses under `/WX` |
| path.exists native | a `path.exists` of a Jam file given a path other than `[ path.native ... ]`: b2's builtin asks the system about the path as written, and b2's form of a Windows path, `/D:/a/...`, names no file there |
| include boundaries | an `#include` that crosses a boundary the library declares in its `meta/include-boundaries.json` (below), at its line, with the boundary's reason; and a malformed file, or a glob that matches no file of the library |
| bare throw | a `throw` expression in a library's public header (`libs/*/include/**`), outside comments and literals, at its line: inside `#ifndef WEBCPP_<NAME>_NO_EXCEPTIONS` too, in a template that nothing instantiates, which clang-tidy's analysis without exceptions does not see, and as a rethrow, `throw;`; `boost::throw_exception` is the one way to raise, `std::rethrow_exception` the one way to rethrow (above) |
| changelog form | a library's changelog or a version's release notes out of `AGENTS.md` chapter 5's form: a section or a region missing or out of order, a line that starts with no verb of the list, a cross-reference, an inline anchor such as `[[nodiscard]]` outside a passthrough, more than ten lines for a library and a version, text outside a bullet |
| canary pins | a `WEBCPP_CRYPTO_<NAME>_COMMIT` of crypto's `detail/canary.h` that is not the first seven digits of the commit the superproject records for its submodule (`ctaes`: `bitcoin`) |
| nodiscard results | a function of a library's `include/` that returns `boost::system::result` without `[[nodiscard]]`, at its line, when the library asks for the rule in its `meta/lint.json` (`"nodiscard-results"` and its reason; asio, beast, cobalt, crypto, hash, trystero and webrtc do): `boost::system::result` carries no `[[nodiscard]]` of its own; and a malformed file or an unknown key |

A source b2 expects not to compile (`webcpp.compile-fail`), and one that
must stop with the error it states (`webcpp.compile-diagnostic`), are left
out of clang-tidy only; every other rule reads them.

The compilation database prepares generated inputs before analysis. Public
header units prepare their dependencies; programs that select another OpenSSL
configuration prepare that exact configuration through B2 as well, including
their exception-off twins. A dedicated preparation target resolves each original
request with its own defaults and returns only the requested provider headers.
B2 updates those artifacts and their dependencies even when headers already
exist, without compiling or running the consumers used to discover the variants.
OpenSSL has a separate header action using Configure and `make build_generated`
with the same source verification, compiler properties and configuration as the
archive action. Header preparation neither builds archives nor runs the upstream
suite and publishes no build or test proof. Full consumers depend on those headers
and still require the complete archive action, including `alltests` when requested.
The archive action leaves identical headers untouched and replaces changed files
atomically before publishing archives. A compiler may already have mapped a header
from the preparation action; truncating that file during the archive action can
invalidate the mapping and crash the compiler. After successful header preparation,
that action refreshes its output timestamps without rewriting identical bytes, so
B2 can record that changed prerequisites have been processed.
The compilation database reuses each dry-run result for dependency discovery rather
than repeating the same full build-graph traversal.

**A library's include boundaries.** Every header compiles alone, so only a
boundary check sees a part of a library start to depend on another. A
library declares its boundaries in `meta/include-boundaries.json`, each a set
of headers (a `headers` glob, less an `except` glob, each matched against the
whole path under `libs/<name>/`, a `*` within one path segment) that must not
include a path starting with one of its `must-not-include` prefixes, and
`why`. xstate's keeps its machine core free of xactor and of the actor layer:

```json
{
    "boundaries": [
        {
            "headers": ["include/webcpp/xstate.hpp", "include/webcpp/xstate/*.hpp"],
            "except": ["include/webcpp/xstate/actors.hpp"],
            "must-not-include": ["webcpp/xactor", "webcpp/xstate/actors"],
            "why": "the machine core runs without xactor and the actor layer"
        }
    ]
}
```

**A directory's own `.clang-tidy`.** A library's tests or examples may need
one that inherits the root's (`InheritParentConfig: true`) and switches off
what does not apply to them, each with its reason in a comment. xactor's
`test/.clang-tidy` turns off `bugprone-unchecked-optional-access` (a test
asserts with `BOOST_TEST` before it reads, which the check does not see) and
`bugprone-exception-escape.CheckMain` (a test's `main` lets an exception end
the process, which fails the test as it should); `example/.clang-tidy` turns
off the second. The library's headers are still analysed with every check,
through the aggregate translation unit. A check that applies to a library
header is never switched off for a directory, since a header's templates are
analysed only where a test or an example instantiates them: the header states
its exemption on the line clang-tidy reports, `NOLINT(<check>)` (or
`NOLINTNEXTLINE(<check>)` on the line above, when that line has no room; a tag
comment between it and its function cancels the suppression), or, when a
page's listing must hide the exemption, with `NOLINTBEGIN(<check>)` and
`NOLINTEND(<check>)` around the exempt function or functions alone. The
reason still goes in the comment above, in every form.

**Sharding.** `--shard K/N` analyses the K-th of N interleaved slices with
clang-tidy, and runs every other rule; the N shards together analyse every
file once.

### The style and the checks: `.clang-format` and `.clang-tidy`

The two files at the superproject's root are every repository's: a library
adds a directory's own `.clang-tidy` only as above, and never a style of its
own. Their decisions, with the reasons each file records:

- **Google's style, at 4 spaces and 100 columns.** `.clang-format` is based on
  Google's, for C++20, with an indent of 4, a continuation indent of 4, no
  tabs, access modifiers at the class's indentation and pointers bound to the
  type (`int* p`). Short functions stay on one line only when they are
  defined in the class; an `if` or a loop never does; a short `case` may.
  Definitions are separated by a blank line, always. (Reason not recorded.)
- **Includes are kept in the blocks their author wrote, sorted within each.**
  A reader sees the product's own dependencies first, then Boost, then the
  standard library (`IncludeBlocks: Preserve`, `SortIncludes: CaseSensitive`).
- **A comment line that starts with `|` is a row of a table.** clang-format
  neither splits it at the column limit nor joins it with the next
  (`CommentPragmas`), since a table is read by its columns.
- **clang-tidy runs `bugprone-*`, `cert-*`, `misc-*`, `modernize-*`,
  `performance-*` and `readability-*`, with six checks of the core
  guidelines,** `cppcoreguidelines-avoid-non-const-global-variables`,
  `-init-variables`, `-pro-type-cstyle-cast`, `-pro-type-member-init`,
  `-slicing` and `-virtual-class-destructor`, and every warning is an error
  (`WarningsAsErrors: '*'`).
- **Findings are reported in webcpp's own headers only:** a library's public
  headers and those of its tests, examples and JavaScript module
  (`HeaderFilterRegex`), never in Boost's or the standard library's, which
  webcpp does not change.
- **Identifiers are `snake_case`, macros `UPPER_CASE`, a private member ends
  in `_`.** It is the libraries' rule and Boost's convention (chapter 3).
  Template parameters are not constrained, so they keep the standard's form
  (`Allocator`).
- **A function's cognitive complexity is at most 25**
  (`readability-function-cognitive-complexity.Threshold`). (Reason not
  recorded.)
- **`performance-enum-size` is off:** a library's error enum has to be `int`,
  since `boost::system::error_code::value()` returns `int`, and a narrower
  base type would only move the conversion.
- **`misc-header-include-cycle` is off:** it reports Boost's `.ipp` idiom, a
  header that includes an implementation file that includes it back behind
  an include guard; webcpp's own headers are flat and have no cycle.
- **`readability-redundant-member-init` is off:** every aggregate member a
  user can designate-initialize has a `{}` default member initializer, so
  that a designated initializer that leaves members out never triggers GCC's
  `-Wmissing-field-initializers` in a user's own `-Wextra` build; the check
  would ask for those initializers to be removed again.
- **Seven more checks are off,** `bugprone-easily-swappable-parameters`,
  `misc-include-cleaner`, `misc-non-private-member-variables-in-classes`,
  `modernize-use-trailing-return-type`, `readability-identifier-length`,
  `readability-magic-numbers` and `readability-uppercase-literal-suffix`.
  (Reason not recorded.)
- **Three rules have no clang-tidy check:** the ban on `io_context::run`,
  `run_one` and `run_for`, the ban on fluent chains that return `*this`, and
  the em dash. The lint enforces them by pattern (the table above).

## 10. Choosing and registering a port

### Choosing

- **What.** A library widely used for the web in another language, ported at
  an exact version of the original: a tag or a published release, recorded in
  `meta/libraries.json` and in the library's `AGENTS.md`. A port follows that
  version; moving to another one is a change of its own, with its evidence.
- **The licence.** An original under a licence compatible with BSL-1.0 can be
  ported: MIT, BSD and Apache-2.0. GPL cannot. MPL is decided case by case,
  by the owner. A port that derives from the original's code keeps the
  original's notice, unchanged, in `LICENSE-<ORIGIN>.txt` (`LICENSE-XSTATE.txt`,
  `LICENSE-TRYSTERO.txt`), and its README names the parts that derive from
  it. That adds no licence to webcpp's code: every file of webcpp is BSL-1.0
  only, and no repository has a `LICENSE-MIT.txt`. A library of webcpp's own,
  like xactor and pratt, has no `LICENSE-<ORIGIN>.txt`.
- **The name.** `[a-z][a-z0-9_]*`, the name of the original where it has one
  (xstate, trystero). `index` is reserved, in any case: the index page is the
  doc build's page `index`, and the report refuses a library of that name,
  nor `target`, `has`, `no`, `lib` or `version`, which config's macros take
  (`WEBCPP_TARGET_*`, `WEBCPP_HAS_EXCEPTIONS`, ...), nor `test`, which the
  test-only macros take (`WEBCPP_TEST_*`): the index refuses each.

### The checklist of a new library

Each item is done before the port's first green CI; the first two are the
owner's:

1. **The repository** `webcpporg/<name>`, public from its first commit, made
   by the owner. An agent never creates a remote repository, never pushes,
   and never changes a GitHub setting. Until the repository exists, the
   library is a local repository at `libs/<name>` (`git init`), which the
   lint and the build already treat as a library.
2. **The submodule**, added by the owner once the repository exists, with a
   URL relative to the superproject's, as Boost's `.gitmodules` writes its
   libraries' (`libs/xactor` is `../xactor.git`), so that a clone fetches
   the libraries over the same protocol as the superproject:

   ```
   git submodule add ../<name>.git libs/<name>
   ```

   Never `git add -A` or `git add libs` in the superproject: a library is a
   repository of its own, and the superproject records only its commit.
3. **`meta/libraries.json`**, Boost's file, with webcpp's `"port-of"`:

   ```json
   {
       "key": "xstate",
       "name": "xstate",
       "authors": ["R"],
       "description": "One sentence that says what the library is.",
       "category": ["State"],
       "maintainers": ["R <github.overboard312@passmail.net>"],
       "cxxstd": "20",
       "port-of": {
           "name": "XState",
           "language": "TypeScript",
           "version": "5.33.2",
           "url": "https://github.com/statelyai/xstate",
           "licence": "MIT"
       }
   }
   ```

   `"port-of"` is `null` for a library of webcpp's own (xactor's is). `name`,
   `description` and `port-of` are required, and every field of `port-of`,
   whose `url` is an `https` URL; `tools/doc/libraries.py` fails the doc build,
   naming the file and the field, otherwise.
4. **`build.jam`**, which the Jamroot finds by its glob `libs/*/build.jam` and
   registers as `/webcpp/<name>`. It declares one target, named after the
   library, that adds its headers and its dependencies:

   ```
   # Copyright (c) 2026 WebCpp.org
   # ... the licence notice (chapter 2)

   project /webcpp/<name> ;

   alias <name> : : : : <include>include <library>/boost//headers <library>/webcpp/config//config ;
   ```

   Every library adds config's target, `<library>/webcpp/config//config`,
   since its `config.hpp` includes `<webcpp/config.hpp>` (chapter 3). A
   dependency on another library is written as its target,
   `<library>/webcpp/xactor//xactor`. A compiled Boost library is built by
   webcpp from Boost's sources (`AGENTS.md` chapter 1): a library that needs
   Boost.URL adds `<library>/webcpp//boost_url` to its target's usage
   requirements, static, built once per variant with Boost.URL's own macros;
   never `/boost//url`, which would link the system's, nor
   `/webcpp/boost-libraries//boost_url`, which the Jamroot's alias checks the
   sources' version for. Boost.Charconv and Boost.Locale likewise,
   `<library>/webcpp//boost_charconv` and `<library>/webcpp//boost_locale`:
   Boost.Locale without ICU, with what it gives on each target in this table:

   | Target | `/webcpp//boost_locale` | `/webcpp//boost_charconv` |
   | --- | --- | --- |
   | native Linux (gcc, clang, glibc) | backends posix and std; iconv from glibc; no ICU (measured) | yes (measured) |
   | native macOS (Apple clang, gcc) | backends posix and std; iconv from the system's libiconv, `-liconv` given by the target; no ICU (measured) | yes (measured) |
   | native Windows (MSVC) | backends winapi and std, no iconv, no ICU: Boost's own configuration on Windows. Not measured here: no Windows machine; the first CI run that builds it is its measurement, and a failure is reported to the owner, never hidden | yes; not measured here |
   | wasip2, wasip3 | backends posix and std; iconv from wasi-libc; number, currency and date formatting in the C locale's form (no locale data, no ICU); a catalog is read from a directory the test gives (`webcpp.data`) (measured) | yes (measured) |
   | emscripten | backends posix and std; iconv from Emscripten's libc; a catalog is read from the host's files, as natively; single-threaded: Boost.Locale's sources alone are compiled with `BOOST_HAS_PTHREADS`, so that Boost.Thread's mutex, which three of them include, builds against Emscripten's pthread functions, which do nothing there; no program gets it, nor `-pthread`, and no public header of Boost.Locale depends on it, which `tools/test/boost_libraries_test.py` checks by preprocessing every one with it and without (measured) | yes (measured) |
   | any target, `exception-handling=off` | refused by name: Boost.Locale throws and catches unguarded (61 `throw`, 14 `try` in its sources, 8 `throw` in its headers) | yes (measured natively and on wasip2) |

   Since Boost.Locale needs exceptions, a program that names
   `/webcpp//boost_locale`, directly or through a library, declares
   `<exception-handling>on` in its own requirements, which keeps it with
   exceptions in a build without them, the lint's twins included (chapter 6):
   b2 ignores it as a usage requirement, and the refusal stops the whole
   build, naming that fix but not the program, which b2 does not give it.

   A library that needs Boost.JSON adds `<library>/webcpp//boost_json` to its
   target's usage requirements, as xstate's `build.jam` does: the Jamroot's
   `boost_json`, `tools/boost_json.cpp`, compiles Boost.JSON's definitions
   (`<boost/json/src.hpp>`, as Boost.JSON documents for a header-only build)
   into a static library, once per variant, so a user's build without
   exceptions gets them built without exceptions too. A library that builds
   WebAssembly components declares the C bindings of its worlds there too,
   with `webcpp.wit-bindings` (`AGENTS.md` chapter 4), as wasi's `build.jam`
   does for the world of each WASI version under its `wit/`. Nothing else
   registers a library: the test, example and doc directories join the
   aggregates `test`, `example` and `doc` by themselves, and
   `include/webcpp/**` joins `install`.
5. **`test/Jamfile`, `example/Jamfile` and `doc/Jamfile`**, with the rules of
   `AGENTS.md` chapters 4 and 3.
6. **The files of the repository:** `LICENSE_1_0.txt`, `README.md` (what the
   library is, how to build and test it inside the superproject, where its
   page is published, its licence), `AGENTS.md` (only what is specific to it,
   with links to the superproject's `AGENTS.md` as `../../AGENTS.md` and to
   this file as `../../CODING-GUIDELINES.md`), `doc/changelog.adoc` (its
   changelog, the page's last appendix, `AGENTS.md` chapter 5),
   `.gitattributes`, and a `.gitignore` that holds at least `doc/html/`, and
   for a library with an oracle `node_modules`, the link to the installed
   packages, which a pattern with a slash would miss, and `.node-modules/`,
   where `tools/node/install.py` installs them: the superproject's own
   `.gitignore` names only its top-level `doc/html/`.
7. **CI.** `.github/workflows/ci.yml`, which calls the superproject's reusable
   workflow (`AGENTS.md` chapter 4), as `libs/xactor/.github/workflows/ci.yml`
   does:

   ```yaml
   jobs:
     ci:
       uses: webcpporg/webcpp/.github/workflows/library.yml@main
       with:
         library: <name>
   ```

8. **The index page.** It lists every library of `libs/` from its
   `meta/libraries.json`, so the entry exists once the file does, and `b2 doc`
   shows it in `doc/html/index.html`, linked to the library's page, and its
   line under New Libraries in the release notes of the version in
   preparation. A library without a page fails the index.
9. **`LICENSE-<ORIGIN>.txt`**, where the port derives from the original's
   code (above).

### Third-party code

What a library or its tests use and webcpp does not own is never copied into
a library: it is a submodule under `third_party/libs/<name>`, pinned at a
commit, with the URL of its own repository, and `third_party/Jamfile`
declares it. The Jamroot registers the project under both ids,
`/webcpp/third_party//<target>` and `/third_party//<target>`, the latter the
form a user's Jamfile writes (chapter 5, rule 5); the target's usage requirements
give a program what it needs. It keeps its own licence and notices, and the
lint never reads it (chapter 9). Adding one is the owner's decision; moving
its pin is a change of its own, with its evidence. A target whose submodule
is not checked out stops the build that needs it, naming `git submodule
update --init third_party/libs/<name>`; a build that needs none never looks.

| Target | What it is | Licence |
| --- | --- | --- |
| `bearssl` | BearSSL from webcpp's unmodified mirror `webcpporg/bearssl` at `7bea48e`; a static library built file by file by `third_party/Jamfile` with webcpp::crypto's and webcpp::hash's canaries (hash's when `libs/hash` is checked out), on every target; `WEBCPP_CRYPTO_HAS_BEARSSL=1`, and `WEBCPP_HASH_HAS_BEARSSL=1` with hash's canary | MIT |
| `bips` | `bitcoin/bips` at `927b6de9`, shallow, test data: crypto's tests read BIP340's `bip-0340/test-vectors.csv` and BIP341's `bip-0341/wallet-test-vectors.json` at run time under the directory its define `WEBCPP_TEST_BIPS` gives, on every target (wasmtime is given it, `webcpp.data`), and run again when it changes | BSD-2-Clause, as BIP340's header states |
| `blake2_vectors` | BLAKE2's reference code package `BLAKE2/BLAKE2` at `ed1974e` (2023-02-12), the submodule `third_party/libs/blake2`, shallow, test data that nothing compiles: hash's tests read `testvectors/blake2b-kat.txt` and `testvectors/blake2-kat.json` at run time under the directory its define `WEBCPP_TEST_BLAKE2_VECTORS` gives, on every target (wasmtime is given it, `webcpp.data`), and run again when one of them changes | CC0-1.0 |
| `blake3` | BLAKE3 1.8.7 at `f3149ec`; `third_party/Jamfile` compiles `c/blake3.c`, `blake3_dispatch.c` and `blake3_portable.c` on every target, the intrinsics files on their instruction sets alone (an exception to chapter 5 rule 2), with webcpp::hash's canary; `WEBCPP_HASH_HAS_BLAKE3=1` | CC0-1.0, Apache-2.0, or Apache-2.0 with LLVM exception |
| `blake3_vectors` | BLAKE3's official vectors, `test_vectors/test_vectors.json` of the submodule `third_party/libs/blake3` at `f3149ec`, test data: hash's tests read it at run time under the directory its define `WEBCPP_TEST_BLAKE3_VECTORS` gives, on every target (wasmtime is given it, `webcpp.data`), and run again when it changes | CC0-1.0, Apache-2.0, or Apache-2.0 with LLVM exception |
| `ca_certificates` | Dated Mozilla/curl CA data snapshot under `third_party/ca_certificates`, verified against its manifest and embedded by a build-generated header; updated explicitly by `tools/ca_certificates/update.py` | MPL-2.0 |
| `ctaes` | `src/crypto/ctaes` of `bitcoin/bitcoin` v31.1 at `9be056a` (commit `9be056a8a72b624dae9623b2f7bded92c2a21c91`), the submodule `third_party/libs/bitcoin`, shallow; `third_party/Jamfile` compiles its `ctaes.c` alone, with webcpp::crypto's canary, on every target (`WEBCPP_CRYPTO_HAS_CTAES=1`); the tree's `src/secp256k1/` subtree is never on an include path and no glob over `third_party/libs` reaches it | MIT |
| `ed25519-speccheck` | `novifinancial/ed25519-speccheck` at `65519336` (2021-02-26), shallow, test data: crypto's tests read the twelve Ed25519 edge cases of "Taming the many EdDSAs", its `cases.json`, at run time under the directory its define `WEBCPP_TEST_ED25519_SPECCHECK` gives, on every target (wasmtime is given it, `webcpp.data`), and run again when it changes | Apache-2.0 |
| `json-schema-test-suite` | the JSON Schema Test Suite at `5b0ee16` (2026-09-21), test data: a test that names it reads the suite at run time from the directory its define `WEBCPP_TEST_JSON_SCHEMA_TEST_SUITE` gives, on every target (wasmtime is given it, `webcpp.data`), and runs again when a file of the suite changes | MIT |
| `libdatachannel` | libdatachannel 0.24.6 at `6b1e2e620f1e37f0eafeee702eaea0043cb305fd`, with pinned libjuice, libsrtp, plog and usrsctp sources; static native archives built by upstream CMake through B2 against the same source-built OpenSSL | MPL-2.0 and the nested dependencies' own licences |
| `nativejson-benchmark` | Milo Yip's nativejson-benchmark at `478d572` (2022-10-28), test data: document's benchmarks (`libs/document/bench`) read its `data/canada.json`, `data/citm_catalog.json` and `data/twitter.json` at run time under the directory its define `WEBCPP_TEST_NATIVEJSON_BENCHMARK` gives, on every target (wasmtime is given it, `webcpp.data`), and run again when one of them changes; its own submodules are never checked out | MIT |
| `openssl` | OpenSSL 3.5.9 at `45e844fa2a14ec92d146bd8f5778ac130b6625fb`; static libssl/libcrypto and matching generated headers, built by upstream Configure/Make through B2 for native Clang/GCC/MSVC, WASIp2 single and WASIp3 single/cooperative | Apache-2.0 |
| `secp256k1` | libsecp256k1 v0.8.0 at `6e2c8bc`; a static library built file by file by `third_party/Jamfile` (`src/secp256k1.c` and its two precomputed tables, every module on) with webcpp::crypto's canary, on every target; its tables by `webcpp-secp256k1-tables` (`auto`: small on Emscripten, large elsewhere); `WEBCPP_CRYPTO_HAS_SECP256K1=1` | MIT |
| `sodium` | libsodium 1.0.22 at `77e1ce5`, the submodule `third_party/libs/libsodium`; a static library built file by file by `third_party/Jamfile` (every `.c` of `src/libsodium/`, no assembly, the defines libsodium's configure finds on each target, upstream's `builds/msvc/version.h` copied into the build directory) with webcpp::hash's canary and webcpp::crypto's (`libs/crypto/src/canary_sodium.c`, configuration `portable`), on every target; `WEBCPP_HASH_HAS_SODIUM=1` and `WEBCPP_CRYPTO_HAS_SODIUM=1`; `sodium-test-config` gives a program its private headers and test defines; shared with webcpp::crypto | ISC |
| `sodium_vectors` | libsodium's own tests' expected outputs, `test/default/*.exp` of the submodule `third_party/libs/libsodium` at `77e1ce5`, test data: hash's tests read `generichash3.exp`, `kdf.exp`, `pwhash_argon2i.exp`, `shorthash.exp` and `siphashx24.exp` at run time under the directory its define `WEBCPP_TEST_SODIUM_VECTORS` gives, on every target (wasmtime is given it, `webcpp.data`), and run again when it changes | ISC |
| `wycheproof` | C2SP's Wycheproof at `12fd3aaf` (2026-10-06), shallow, test data: crypto's tests read its `testvectors_v1/` at run time under the directory its define `WEBCPP_TEST_WYCHEPROOF` gives, on every target (wasmtime is given it, `webcpp.data`), and run again when one of its files changes | Apache-2.0 |
| `xkcp` | XKCP (the Keccak team's code package) at `d20c8fc` (2026-11-10, no release tags); `third_party/Jamfile` compiles its `KeccakP-1600-opt64.c` (Keccak-p[1600], the generic64 profile) and the high-level files over it, `KeccakSponge.c`, `KeccakHash.c` (FIPS 202), `SP800-185.c`, `TurboSHAKE.c` and `KangarooTwelve.c` (serial: no times-N permutation), with webcpp::hash's adapter, `config.h` (`XKCP_has_KeccakP1600`, `_Sponge_Keccak`, `_TurboSHAKE`, `_FIPS202`, `_SP800_185`, `_KangarooTwelve`) and canary, on every target; `WEBCPP_HASH_HAS_XKCP=1` | CC0; `brg_endian.h` under Brian Gladman's terms |

OpenSSL builds from a checkout or a source distribution. Before Configure, its
builder stages the distributable tree and checks a digest of paths, Git file
modes and file content hashes. Dot paths and the exact nested repositories in
`tools/openssl/pin.json` are omitted from both the distribution and that staging
tree. A Git checkout also requires the pinned revision and unchanged tracked
files. Missing, additional or altered distributable files fail the build.
After explicitly updating the source commit, regenerate this metadata with
`python3 tools/openssl/update.py`; never edit the generated inventory by hand.
The pinned commit timestamp supplies the default reproducible-build epoch.

Libdatachannel follows the same source-integrity boundary with
`tools/libdatachannel/pin.json`. Its required nested repositories are included
at their pinned gitlinks in source archives; only the explicitly listed unused
nested sources are omitted. A checkout needs recursive initialization, while an
archive builds without Git. B2 invokes upstream CMake for separate static
archives, with system dependency discovery disabled and the exact OpenSSL
provider's headers and archive hashes checked first. Native consumers select
`threading=multi` and matching compiler/runtime settings. This provider decision
permits Asio, Beast and native Trystero in one program; it does not complete
Trystero's later API migration or prove libdatachannel's upstream test suite.

The CA bundle is an authorized exception to the source-submodule rule: curl
publishes dated PEM artifacts, preserved byte-for-byte with source URL, SHA-256,
certificate inventory and MPL notices. It is data, not copied implementation
code. Normal builds verify and embed the pin without network access. Updating
it is a reviewed trust-policy change, including removals. Preserve its license
and corresponding PEM source when distributing binaries. Never manually edit
its PEM, manifest or generated header; use the updater and generator.

`b2 install` also generates and installs `webcpp_ca_certificates.hpp` at the
include root, with the exact PEM, manifest, README and MPL license under
`include/webcpp/ca_certificates`. Keep this independent of OpenSSL compilation.
The installed data consumer test must compile without checkout include paths.

## 11. Fidelity

- A port behaves as the original, at the version it ports: the same results,
  the same order of events, the same errors, for the same inputs.
- Every difference is a decision, recorded in the page's appendix
  "Differences": what the original does, what the port does, and why. A
  difference forced by C++ (no garbage collector, value types where the
  original shares objects) is still recorded.
- Each difference has an example `example/diff_<topic>.cpp`, with its
  `.expected`, and its twin in the original's language (chapter 12), which
  shows the original's behaviour; the page shows both outputs side by side.
  xstate is the model, with its `diff_spawn_id`: XState keys a child spawned
  without an id as `"undefined"`, the port as an empty string, and the page
  shows the two outputs, each printed by its program.
- No divergence goes unrecorded. A difference found later, in a test, a
  review or a user's report, is either fixed or recorded in the same change
  that finds it.

## 12. Evidence: oracle and twins

A port's evidence is the original itself. The port's tests do not state by
hand what the original does: the pinned original runs the same cases and the
twins of the examples, and the port must produce what it produced. The
oracle that does it is shared by every port, in `tools/oracle/`; xstate is
its first user, and the model:

| Shared, in `tools/oracle/` | Per library, in `libs/<name>/test/oracle/` |
| --- | --- |
| the twin runner, `twins.py`, with its agreeing, divergent and without-twin bookkeeping | the pinned original (`package.json` and `package-lock.json`, for JavaScript) |
| output and tree comparison, `twins.py` and `compare.py` | the oracle scripts that drive the original over the cases (xstate's `oracle.mjs` and `actors.mjs`) |
| `update-expected`, with its refusals | the cases, and their C++ runner, under the library's `test/` |
| the `.jam` module of rules, `oracle.jam`, that the library's `test/oracle/Jamfile` calls | the twins, `twins/`, with `without-twin.txt` |
| the CI action that installs the language's runtime, `tools/ci/actions/node` | |

- **Cases.** The original's tests are ported as data-driven cases, which the
  C++ runner runs against the port.
- **Expected results.** The oracle runs the pinned original over the same
  cases and writes the expected results. The port must produce them.
- **Twins.** Every documented example has a twin in the original's language,
  `<name>.mjs` beside the C++ program in the library's twin directory, which
  the page includes through `{twins}`. A twin either agrees (prints exactly
  what the C++ example prints), or diverges, with the original's output
  recorded as its own `.expected` and the difference in the appendix
  (chapter 11), or is listed as without a twin, with the reason, as a line
  `<path>: <reason>` of the twin directory's `without-twin.txt`. A program
  with a twin has its `.expected`; one without may have none, as a program
  `webcpp.link` links and never runs prints nothing to compare.
- **Nothing expected is written by hand.** Only `update-expected` writes an
  expected result, and it refuses to write a twin's output for a twin that
  agrees, since that output must be the C++ example's. Nor is a generated
  file: only `update-generated` writes it (`AGENTS.md` chapter 4).
- **How the original runs.** Each library declares it: for JavaScript and
  TypeScript, `node --conditions=development`.

### The rules (`tools/oracle/oracle.jam`)

A library's `test/oracle/Jamfile` declares its oracle with four rules of
`tools/webcpp.jam`. xstate's, whole after its licence notice and its first
comment:

```
import webcpp ;

webcpp.original node --conditions=development ;
webcpp.twins ../../example : twins : .mjs
  : --test-reporter=spec --test-reporter-destination=stderr ;
webcpp.cases machines : oracle.mjs : ../fixtures/cases : ../fixtures/expected ;
webcpp.cases actors : actors.mjs : ../fixtures/actors/cases : ../fixtures/actors/expected ;
webcpp.lane oracle : twins cases-machines cases-actors ;
```

| Rule | What it declares |
| --- | --- |
| `webcpp.original <word> + [ : <directory> ] ;` | how a program of the original's language runs, once and first; and the target `node-modules`, which installs what `package-lock.json` beside the Jamfile, or in the `<directory>` given (relative to the Jamfile: document's `test/js` runs the tests of `js/`, whose package pins Playwright and TypeScript), pins with `npm ci`, through `tools/node/install.py`: once per lockfile under `.node-modules/`, linked at `node_modules`, so that runs at once never install over each other |
| `webcpp.twins <examples> : <twins> : <suffix> : <extra-word> * ;` | the target `twins`: `twins.py` runs the twin `<twins>/<path><suffix>` of every program `<examples>/<path>.cpp`, at any depth, with the original's words and the extra words, and compares what it prints with the program's `.expected`, or with the twin's own `.expected` for a difference, which must then differ from the program's. Declared once per library: the page shows and counts its twins (`AGENTS.md` chapter 3) |
| `webcpp.cases <name> : <script> : <cases> : <expected> ;` | the target `cases-<name>`: the original runs `<script> <cases> <output>` into the build directory, and `compare.py` finds the output equal to `<expected>`, file by file and byte by byte. The Jamfile stops loading at a cases directory that does not exist, and at an expected directory whose removal would take the oracle's directory or the cases |
| `webcpp.lane <name> : <b2-target> + : <target> * ;` | an own lane of the library, the explicit alias `<name>` over the b2 targets, each a main target of the same Jamfile, which the lane makes explicit too, so that the ordinary lanes never build them; the alias compiles nothing, and leaves the Jamroot's check of Boost to the targets it names; `b2 declared-lanes` lists it and the CI runs it (`AGENTS.md` chapter 4). An oracle's names no target. One that names targets runs on each, as the CI's lane of that target does, and its tests reach the report: each is one of the Jamfile's `webcpp.targets` (`native` without any), or the build stops naming it. Every lane-only program, of `webcpp.serve`, `webcpp.serve-script` or `webcpp.drive`, must be named by a lane of its Jamfile on every target it is built for, or `b2 declared-lanes`, and with it the CI's plan, stops naming it. Only a Jamfile under the library's `test/` or `example/` declares one |

The first `webcpp.twins` or `webcpp.cases` also declares the target
`update-expected`, which writes every expected directory again from the
original, and each divergent twin's own output (`twins.py --update`, which
refuses one that agrees). Directories are relative to the Jamfile.

Every target is explicit: only a request by name, or a lane that names it,
runs Node, and `b2 test` never does. Node and npm are looked for on `PATH`
when an oracle target runs, and the build stops, naming the one that is
missing. The targets compile nothing, but they sit in the library's test
project and inherit its requirements, with the Jamroot's check of Boost, so
an oracle lane needs Boost and a toolset beside Node and npm.

| Command | What it does |
| --- | --- |
| `b2 -a libs/<name>/test/oracle//oracle` | the oracle lane, from scratch: every case and every twin on the original, compared |
| `b2 libs/<name>/test/oracle//twins`, `//cases-<name>` | one part of it, while working on it |
| `b2 libs/<name>/test/oracle//update-expected` | the original's results written again, over the committed ones; never a check |
| `python3 tools/oracle/twins.py --list --suffix .mjs --examples libs/<name>/example --twins libs/<name>/test/oracle/twins` | each program as agreeing, divergent or without twin, and their total, running nothing |

**What a port proves.** Its cases pass natively and on every target it
declares, against expected results the original wrote; its oracle lane is
green, so the original still writes every committed expected result and
every twin agrees, or diverges as recorded; and its page shows each twin's
code and each difference's two outputs. The runner accounts for every
program by name, so a twin that is no longer compared fails the lane rather
than leave it green on the rest.

## 13. Porting a library, step by step

1. Choose it, check its licence, and pin its version (chapter 10).
2. Make `libs/<name>` with its checklist files (chapter 10), and see `b2
   libs/<name>/test` build the headers-alone tests of an empty convenience
   header.
3. Port the original's tests as cases, and the oracle that writes their
   expected results from the pinned original (chapter 12); see them fail.
4. Port the code, header by header, with its Doc Comments (chapter 7), until
   the cases pass natively, then on every declared target.
5. Write the page: the guide with its examples and twins, the guarantees, the
   testing chapter, the reference and the differences (chapter 11 and
   `AGENTS.md` chapter 3).
6. Run the definition of green above, from scratch.

## 14. The organization's design

The decisions that shape the whole collection, each with its reason and its
source, then the site's. A source is a path in its repository at the commit
this chapter was written from: `webcpp` is the superproject at `ddb6cb2`,
where `AGENTS.md` was the rulebook before this file took its rules, and its
chapters are cited by the numbers they had there; `site` is the site's
repository at the commit the superproject pins; `proposals` is
[webcpporg/proposals](https://github.com/webcpporg/proposals). Where a source
records no reason, the bullet says so.

### The organization

The choices that shape the whole collection, each with its reason as its
source writes it, checked against the superproject's `main` at `ddb6cb2`.
Where a source and the tree disagree, the bullet says what the tree does. The
site's own decisions follow in the next sections.

**The superproject.**

- **webcpp is organized as Boost is: the superproject `webcpporg/webcpp` plays
  the part of `boostorg/boost`, and each library is a repository of its own, a
  submodule under `libs/<name>`.** Independent repositories, each with a build
  of its own, were rejected: they would let the rules drift and make a
  cross-library change two unrelated commits with no joint CI.
  Source: `organization/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **Every library is header-only C++20 under the Boost Software License 1.0,
  and every file webcpp writes is BSL-1.0 only.** (reason not recorded) A port
  that derives from its original's code keeps the original's notice in
  `LICENSE-<ORIGIN>.txt`, which adds no licence to webcpp's code.
  Source: `AGENTS.md` (webcpp).
- **webcpp brings to C++ the libraries other languages use for the web, each
  ported at an exact version of an original and proven against it, or a
  library of webcpp's own.** It builds infrastructure in both directions: the
  best of C++ within reach of the web, compiled to WebAssembly, and the
  libraries web developers use most brought to C++, so that programs written
  in C++ and compiled to WebAssembly have them.
  Source: `AGENTS.md` (webcpp).
- **A library's submodule has a URL relative to the superproject's
  (`../<name>.git`), and the superproject records only the library's commit.**
  A clone then fetches the libraries over the same protocol as the
  superproject, and a library stays a repository of its own, so `libs` is
  never staged as a whole. The site's submodule is the exception in the tree:
  its URL is the absolute SSH address
  `git@github.com:webcpporg/webcpporg.github.io.git`.
  Source: `AGENTS.md` (webcpp); `.gitmodules` (webcpp).
- **`main` is the only branch: a library's commit reaches its own `main`, then
  a superproject commit moves the submodule by path, and the superproject's CI
  tests every library at the commits its submodules record.**
  (reason not recorded) What fails there is fixed with a test, by more commits
  on `main`.
  Source: `AGENTS.md` (webcpp).
- **A repository whose code was moved from elsewhere starts from one import
  commit, without the history of the code it was moved from.**
  (reason not recorded) The tree's `AGENTS.md` limits the rule to moved code;
  the organization's specification and `CONTRIBUTING.md` still say every
  webcpp repository, and the superproject's own history has 276 commits.
  Source: `AGENTS.md` (webcpp).
- **`libs/config` is a library of its own, as Boost.Config is Boost's, and
  every library's `config.hpp` includes `<webcpp/config.hpp>` first.** The
  owner decided it on 2026-10-08, in the philosophy of `boost/config.hpp`: one
  header gives every library the target, whether webcpp has exceptions, and
  the version. In the tree every library but wasi includes it; wasi reads
  `WEBCPP_NO_EXCEPTIONS` itself until its redesign.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/release-design.md`
  (proposals).
- **One rulebook for every library, and each rule a tool can check is
  checked by one: the lint, a Jam rule that refuses a wrong declaration, or
  the report, each pinned by a test of `tools/`.** One rulebook, one build and
  one lint for every library keep a rule enforced by a tool rather than by
  memory; a rule that needs judgment is the reviewer's, and says so.
  Source: `organization/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **The rulebook is two files: `CODING-GUIDELINES.md`, the single source of
  the rules on how code is written and of every design decision with its
  reason, and `AGENTS.md`, how to work in the tree.** A contributor, human or
  agent, reads in one place how code is written and why it is designed as it
  is, and a decision written once does not drift; `AGENTS.md` keeps what an
  agent needs to run anything. Until 2026-10-26 `AGENTS.md` alone was the
  rulebook, and the decisions were spread over the proposals, each library's
  `AGENTS.md` and its pages.
  Source: `organization/openspec/changes/coding-guidelines/design.md`, D1 and
  D2 (proposals).
- **Third-party code a library or its tests use is never copied into a
  library: it is a submodule under `third_party/libs/<name>`, pinned at a
  commit, and `third_party/Jamfile` declares it as
  `/webcpp/third_party//<target>`.** It keeps its own licence and notices, the
  lint never reads it, and moving its pin is a change of its own, with its
  evidence.
  Source: `AGENTS.md` (webcpp).
- **What a library builds on follows one order: what webcpp has, then Boost,
  the C++ Alliance's libraries, the standard library, an outside library that
  follows their standards, a C++ port of a widely used C library, and only
  then code of its own.** The aim is that every library carries the quality
  and the peer review of Boost and the standard; an outside library is wrapped
  behind an interface that follows its standard or Boost counterpart, so that
  it can be replaced.
  Source: `CONTRIBUTING.md` (webcpp).

**The build.**

- **b2 builds, tests, documents, serves and releases everything; a Python or
  Node script is a procedure a b2 target runs, never another entry point.** A
  CMake or Makefile front end was rejected: Boost's own libraries do not need
  one, and it would hold a second copy of the build knowledge.
  Source: `organization/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **The superproject's `Jamroot` is the single build configuration: a library
  has no Jamroot, and its `build.jam` is found by the glob `libs/*/build.jam`
  and registered as `/webcpp/<name>`.** A library is developed inside a
  checkout of the superproject, as a Boost library is developed inside Boost,
  and nothing else registers it: its test, example and doc directories join
  the aggregates by themselves.
  Source: `AGENTS.md` (webcpp).
- **Boost 1.92 or newer is required, and the Jamroot refuses an older or
  unreadable Boost before it compiles anything, printing the `using boost`
  line to add.** (reason not recorded)
  Source: `organization/openspec/specs/organization/spec.md` (proposals).
- **The compiled Boost libraries a library needs, Boost.URL, Boost.Charconv,
  Boost.Locale without ICU and Boost.Cobalt, are built by webcpp from Boost's
  own source archive for their supported targets, as `/webcpp//boost_url` and
  its kin.** Each archive follows its consumer's target, macros and compiler
  configuration. Cobalt's independent library now ships its pinned upstream
  native sources and adapted Wasm sources; Asio ships its Wasm backend too.
  Maintainer imports record original and resulting hashes, while consumer
  builds apply no patches. Other compiled Boost dependencies still require the
  matching source archive: an installed Boost cannot be relied on for sources
  (Homebrew's has no `libs/url/src`).
  Source: `organization/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **Boost.JSON's definitions and Boost.Test's header-only framework are
  objects of webcpp's own build, `/webcpp//boost_json` and
  `tools/boost_test_runner.cpp`.** Boost.JSON is built once per variant, so
  that a user's build without exceptions builds it without exceptions too, and
  the Boost.Test object spares the CI any compiled `unit_test_framework`.
  Source: `AGENTS.md` (webcpp).
- **A tool the build looks up itself is taken from its `-s` option on b2's
  command line, else from `.local/`, else from `PATH`, and never from the
  environment.** A variable a shell keeps from another day would replace
  `.local/` without a word, and b2 tells the command line's value apart only
  through `ARGV`.
  Source: `AGENTS.md` (webcpp).
- **Every b2 run refuses a shell that sets `CPATH`, `CPLUS_INCLUDE_PATH` or
  `C_INCLUDE_PATH`.** The compiler would read another Boost from them before
  the configured one, without a word; Homebrew's shell often sets them.
  Source: `AGENTS.md` (webcpp).
- **Each toolchain is installed by hand and registered in `user-config.jam`,
  and the lines that register the WASI and emscripten toolsets are tagged
  regions of `tools/ci/wasi-sdk.jam` and `tools/ci/emsdk.jam`.** The CI writes
  a lane's toolset from those regions and a page includes them, so that
  neither drifts from the other; bundled toolchains are on the roadmap.
  Source: `AGENTS.md` (webcpp).
- **A library webcpp does not build yet (none today: trystero links
  `/third_party//secp256k1`) is declared with `webcpp.external`: a build that
  does not find it leaves its owner out with one line, and the CI and the
  lint, with `webcpp-require-external=on`, stop instead.** Left out, every
  other library still builds with `b2 test`; required, a library not found
  stops the build rather than leave the library out. `EXTERNAL_DEPENDENCIES`
  in `tools/ci/matrix.py` is empty and the machinery stays for a later
  library; a CI action of the library's name would build it. libsecp256k1,
  OpenSSL and native libdatachannel use pinned source targets.
  Source: `AGENTS.md` (webcpp).

**Targets and toolchains.**

- **webcpp builds for three families of targets, each with a purpose:
  `emscripten` (the browser), `wasip2` and `wasip3` (WASI components run by
  wasmtime and by clouds) and `native` (a program that integrates closely with
  its operating system).** A C++ program becomes a web page with everything
  the browser offers, and a WASI component is a container lighter than Docker,
  for distributed computing at scale.
  Source: `AGENTS.md` (webcpp).
- **A program's targets are declared in its Jamfile, the target of a build is
  told by `<toolset>` and its version alone, and a program not declared for a
  target gets `<build>no`.** `<build>no` conditioned on a derived feature such
  as `<target-os>` never settles in b2's evaluation of conditional
  requirements; the declarations are what `b2 declared-targets` prints, from
  which the CI plans its lanes.
  Source: `AGENTS.md` (webcpp).
- **On emscripten every program is wasm32, single-threaded and static.**
  Browsers do not all run memory64, pthreads need cross-origin isolation in a
  page, and Emscripten's shared libraries are experimental.
  Source: `AGENTS.md` (webcpp).
- **On emscripten a program links at the level of optimization it compiles
  at: `-O3` in a release build, `-O0` in a debug one.** b2 5.5.3's emscripten
  toolset gives `<optimization>` to the compile alone, and `em++` given no
  level links at `-O0`: a release program was linked without optimization,
  Binaryen's wasm-opt never ran on it, and Asyncify instrumented it
  unoptimized (asio's deepest suspension wrote 2,900 bytes, against 388
  linked with `-O3`). The Jamroot gives the link its compile's level, before
  a program's own `<linkflags>`, whose `-O<n>` still wins. A release link
  also turns Emscripten's `ASSERTIONS` off and drops the runtime JavaScript
  the program never calls (`AGENTS.md` chapter 4).
  Source: `AGENTS.md` (webcpp); `Jamroot` (webcpp).
- **wasip2 and wasip3 are b2's `clang` registered against wasi-sdk
  (`clang-wasip2`, `clang-wasip3`), linked statically, and the Jamroot adds
  `<target-os>wasi` only after the toolsets have loaded.** wasm32-wasip2 and
  wasm32-wasip3 are no system b2 knows and have no shared libraries, and the
  late value keeps gcc's Unix link options (`--start-group`, `-Bstatic`,
  rpath), which wasm-component-ld rejects, from being chosen.
  Source: `AGENTS.md` (webcpp); `Jamroot` (webcpp).
- **A wasip2 or wasip3 program built without debug symbols, as a release
  is, carries no debug information: the Jamroot links it with
  `-Wl,--strip-debug` (its region `wasi-strip-debug`); a debug build keeps
  its DWARF.** The owner decided it on 2026-11-17. wasi-sdk's prebuilt
  libc++, libc++abi and libunwind carry DWARF, which wasm-ld copied into
  every program: a release example of xactor was 3,489,365 bytes on wasip2,
  397,678 without it.
  Source: `AGENTS.md` (webcpp); `Jamroot` (webcpp).
- **Every target builds with exceptions on and RTTI is never restricted; a
  build without exceptions is its builder's choice, which every library
  supports.** Whether a program uses exceptions is the choice of whoever
  builds it, never an imposition of a library or of webcpp.
  Source: `organization/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **On wasip2 and wasip3 exceptions are standard WebAssembly exceptions
  (exnref): compiled with
  `-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false`, linked with
  `-fwasm-exceptions -lunwind`.** wasi-sdk 34 emits the legacy encoding by
  default, which wasmtime 47 refuses to run ("legacy_exceptions feature
  required"); a program that throws then needs wasmtime 47 or later, jco with
  exnref, or another Wasm 3.0 engine.
  Source: `AGENTS.md` (webcpp);
  `organization/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **Every tool has one pinned version: Boost 1.92.0 and the b2 it bootstraps
  (B2 5.5.3), wasi-sdk 34, wasmtime 50.0.1, wit-bindgen 0.62.0 with the WASI
  WIT of the crates `wasip2` 1.0.4 and `wasip3` 0.9.0, Emscripten 6.0.11,
  MrDocs 2026.9.29 and Node 26.7.0.** The lint takes clang-format and
  clang-tidy from the pinned wasi-sdk so that every machine and the CI lint
  with one version, and the reference refuses an emsdk that is not 6.0.11; why
  each of these versions was chosen is not recorded.
  Source: `organization/openspec/specs/organization/spec.md` (proposals).
- **Every archive the CI downloads is checked against a recorded SHA-256,
  every third-party action is pinned by its full commit SHA, and a tool
  fetched with git is checked against its pinned commit.** emsdk checks none
  of its downloads itself. Source dependencies also validate their required
  nested gitlinks before building. The interop lanes get a
  pinned chrome-headless-shell so that a red lane is never a browser nobody
  chose.
  Source: `AGENTS.md` (webcpp).

**Documentation.**

- **Each library's API reference is generated by MrDocs from its Doc Comments,
  always to one AsciiDoc page that the library's page includes, with every
  warning an error.** The owner decided MrDocs, always to AsciiDoc; the single
  page (`multipage: false`, `embedded: true`) is included into the
  hand-written page with no warning, where the multipage output's `xref` links
  are Antora's, and `auto-function-metadata` and `auto-relates` are off
  because at their defaults they hid 48 findings on the first library
  measured.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/research/MRDOCS_FOR_WEBCPP.md`
  (proposals).
- **Each library has one AsciiDoc page, converted by Asciidoctor.js: its
  guide, its numbered guarantees, its testing chapter, the reference, the
  differences of a port and its changelog.** A guarantee keeps its number and
  anchor forever, since code, tests and comments cite them; why AsciiDoc and
  Asciidoctor.js were chosen is not recorded.
  Source: `AGENTS.md` (webcpp).
- **Documentation is generated and checked, never typed twice: every listing
  is a compiled example, every shown output a `.expected` file, every count
  computed by the build and every link between pages checked.** No listing,
  output or count then drifts from the tree, and a page includes the build's
  own configuration by its tag, never a copy.
  Source: `organization/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals); `AGENTS.md` (webcpp).

**Tests and CI.**

- **A port's evidence is the pinned original itself: a shared oracle in
  `tools/oracle/` runs the original over the port's cases and the twins of its
  examples, and only `update-expected` writes an expected result.** The port's
  tests never state by hand what the original does; a library of webcpp's own
  is proven by its tests and the oracles that fit it, and each difference from
  an original is a recorded decision with an example and a twin.
  Source: `organization/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **Unit tests use Boost.Core's lightweight_test, and Boost.Test is kept for a
  test that needs it, natively only.** lightweight_test was measured to
  compile and report correctly with `-fno-exceptions -fno-rtti` and on
  wasm32-wasip2 under wasmtime, where Boost.Test 1.92 does not compile.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/research/BOOST_REGRESSION_MATRIX.md`
  (proposals).
- **Only a build from scratch, `b2 -a`, counts as evidence.** b2 compares
  timestamps, so an incremental build misses an edit made in the same second
  as the last build and can leave a stale result in place.
  Source: `AGENTS.md` (webcpp).
- **A lane builds and runs one library's tests and examples for one toolset,
  from scratch, with `--dump-tests` and `--out-xml`, in a build directory of
  its own.** `testing.launcher` applies to every toolset of one b2 request, so
  a lane is always one toolset; `--dump-tests` lists the tests a lane skips
  too, and two concurrent b2 runs never share a build directory.
  Source: `AGENTS.md` (webcpp).
- **The test matrix is written by webcpp's own `tools/report/report.py` from
  b2's `--out-xml`, and its exit status is the verdict.**
  boostorg/regression's tool chain was rejected: it needs Python 2 or a
  rewrite, a Boost checkout with five compiled libraries and manual
  workarounds, and its `library_status` mislabels columns; with `--out-xml` b2
  exits 0 even when a test fails.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/research/BOOST_REGRESSION_MATRIX.md`
  (proposals).
- **A driven test contains its descendants before starting its driver.**
  The shared keeper uses a POSIX process group or a Windows Job Object with
  kill-on-close. The owner holds its lifetime pipe; timeout, driver exit and
  owner termination stop the entire tree. Windows assigns the keeper before
  spawning children and keeps its job handle non-inheritable. Failure to establish
  containment fails closed. This avoids POSIX-only signal and process-group APIs
  in the Windows runner while preserving bounded cleanup. The Windows compiler
  jobs run the real process-tree regressions, including nested jobs.
  The build reuses an existing executable with its object dependencies when the
  producer also returns symbols or component metadata. Extra outputs must not
  cause the test generator to link a new executable without its fixture code.
  Source: `tools/component/process_tree.py`, `tools/drive/drive_test.py`,
  `tools/drive/drive.jam` (webcpp).
- **What an ordinary lane must not run is an own lane of its library
  (`webcpp.lane`): an oracle, a served component, a driven test or the check
  of generated files; a lane-only program in no lane stops the CI's plan.** An
  oracle needs Node where a toolset lane does not, a generator may need the
  network, and a served or driven program left out of every lane would go
  untested rather than fail before any job runs.
  Source: `AGENTS.md` (webcpp).
- **The CI is one reusable workflow, `.github/workflows/library.yml`, which
  every library's `ci.yml` calls with its name and the superproject's `ci.yml`
  without one, and it runs exactly the commands the rulebook documents.** A
  lane is then run locally exactly as the CI runs it; why one reusable
  workflow serves every repository is not recorded.
  Source: `AGENTS.md` (webcpp).
- **The CI never lists a library's targets by hand: its plan job reads
  `b2 declared-targets` and `b2 declared-lanes`, and a target the CI has no
  lane for fails the plan by name.** A lane is then never left out.
  Source: `organization/openspec/specs/organization/spec.md` (proposals).
- **The lanes `gcc-14` and `clang-linux-18` run in a Linux container with no
  network but the loopback, built from an image whose every package comes from
  one dated Ubuntu snapshot.** A test that reaches beyond the machine fails
  there, which every library's tests hold and trystero's guarantee 6 rests on;
  the snapshot makes one Dockerfile one set of packages.
  Source: `AGENTS.md` (webcpp).
- **CI preparation is explicit and separate from ordinary pull-request tests.**
  A trusted dispatch publishes native and Linux-X64 tool images, then separate
  jobs verify anonymous digest pulls and smoke checks. Reviewed generated pins
  bind the images to their recipes. Ordinary jobs neither build missing images
  nor run apt; only their two container consumers need the native image.
  The full lane set and report still fail on missing test results.
- **Tool caches hold verified input archives, never test verdicts.** Each cache
  read verifies SHA-256 and each write is atomic. Linux-X64 wasi-sdk, Wasmtime,
  wit-bindgen, WASI WIT and MrDocs cold caches use prepared public bundles and
  installation stays offline. Other hosts and Chrome retain checked upstream
  downloads with bounded retries. Chrome binaries are not republished as public
  packages; their terms differ from the CfT repository's license. Every original
  installer still runs, so PATH, environment exports and version checks remain.
  Source: `tools/ci/environment.py`, `tools/ci/download.sh`,
  `.github/workflows/prepare-environments.yml`, `AGENTS.md` (webcpp).
- **The native lanes are GCC 14 and 15, Clang 18 and 22 on libstdc++, Apple
  Clang and MSVC 14.3 and 14.5, beside one lane each for emscripten, wasip2
  and wasip3.** The Clang lanes on libstdc++ stay because a regression of
  xactor's guarantee 28 is caught only there; why the other compilers were
  chosen is not recorded.
  Source: `AGENTS.md` (webcpp).
- **A run on `main` is never cancelled by the next, and a pull request's newer
  push cancels its older run.** A run on `main` is the record of `main`, and
  it publishes the site.
  Source: `organization/openspec/specs/organization/spec.md` (proposals);
  `.github/workflows/ci.yml` (webcpp).

**Releases.**

- **webcpp has one version for the whole collection, written once as
  `WEBCPP_VERSION` in `<webcpp/version.hpp>` of `libs/config`, with Boost's
  formula (0.1.0 is `100`); a library has no version of its own.** Unlike
  Boost, which repeats its version by hand, the header is the only place, read
  by the Jamroot and by the release tooling; a port records its original's
  version elsewhere.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/research/BOOST_RELEASE_NOTES.md`
  (proposals).
- **The version moves to the next one in the commit right after a tag, which
  also opens the next notes from `tools/release/template.adoc`.** `main` then
  always names the release in preparation.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/research/BOOST_RELEASE_NOTES.md`
  (proposals).
- **Every change a user can see adds its changelog line in the same commit,
  and agents write the changelogs, which replaces for webcpp the global rule
  never to edit one.** The owner decided on 2026-10-08 that changelogs are
  written with every change, so that they are ready when a release comes; a
  library's changelog is the base of the release's "What's new".
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/release-design.md`
  (proposals).
- **A library's changes are written once, in its `doc/changelog.adoc`, and the
  release notes include that region by its tag instead of a copy.** Boost
  keeps two hand-written copies, a library's changelog and its entry in the
  release notes, and they drift; webcpp keeps one source per fact.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/research/BOOST_RELEASE_NOTES.md`
  (proposals).
- **The release notes follow Boost's sections, with a section Removed
  Libraries that Boost does not have.** The owner wants what went out written
  down.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/research/BOOST_RELEASE_NOTES.md`
  (proposals).
- **A version's Compilers tested lists only the CI lanes actually tested for
  that release, a nonempty ordered subset of the CI's lanes.** A local-only
  release does not claim coverage of other CI lanes; 0.1.0's lists GCC 15 and
  Emscripten 6.0.11.
  Source: `AGENTS.md` (webcpp).
- **`b2 check-release` fails a release in which a library changed since the
  last tag has no changelog line, besides checking the notes, the version and
  their form.** It is the check the owner asked for, and Boost has no
  equivalent.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/research/BOOST_RELEASE_NOTES.md`
  (proposals).
- **`b2 dist` writes a byte-for-byte reproducible `webcpp-<version>.tar.gz`
  and its `sha256sum` file, read from git's objects at the recorded commits,
  with the built pages and no dot file.** Anyone can rebuild it from the tag
  and compare the hash; it takes GitHub's form of name, since webcpp publishes
  on GitHub and the tag names it.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/research/BOOST_RELEASE_NOTES.md`
  (proposals).
- **The archive also carries the sources and upstream licences of the pinned
  submodules `site` and `third_party/libs/<name>` at their recorded commits,
  and refuses any other submodule by name.** Required sources are then never
  silently omitted.
  Source: `AGENTS.md` (webcpp); `tools/release/release.py` (webcpp).
- **A release is the tag `webcpp-<version>`, on the superproject and on every
  library at the commit the superproject records, and a GitHub Release that
  carries the archive and its checksum.** A library's release state is then
  found by its tag.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/research/BOOST_RELEASE_NOTES.md`
  (proposals).
- **Every release has a "What's new", the body of its GitHub Release, whose
  skeleton `b2 whats-new` writes from the release notes in Boost's form, with
  at most five highlights that an agent drafts and the owner approves before
  the tag.** The owner decided that every release has one, with what came in
  and went out, in the pattern of Boost's release notes.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/release-design.md`
  (proposals); `AGENTS.md` (webcpp).
- **Nothing is released until the owner asks, and whether a tag is signed is
  the owner's decision then.** (reason not recorded) 0.1.0 is prepared in the
  tree, and no tag names it yet.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/release-design.md`
  (proposals).

**Proposals and decisions.**

- **Every library, and every change to one, begins as an OpenSpec proposal in
  `webcpporg/proposals`, and enters webcpp only once it is accepted, built
  from that proposal.** (reason not recorded) The superproject's
  `CONTRIBUTING.md` still sends a new library to an issue on
  `webcpporg/webcpp`.
  Source: `CONTRIBUTING.md` (proposals).
- **The organization and each library are OpenSpec roots of their own
  (`organization/openspec/`, `libraries/<name>/openspec/`), and the
  organization's specification states as checkable requirements what every
  library inherits.** A library's proposal then states only what is specific
  to it, and an agent finds the rule it needs instead of reading the rulebook
  from the top.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/proposal.md`
  (proposals).
- **A library is of one of three kinds, `own`, `port` or `wrapper`, and each
  kind is proven by its own evidence.** A library of webcpp's own is proven by
  its specification, its tests and the references it cites; a port by its
  pinned original, run as an oracle; a wrapper by the wrapped library's own
  behaviour on every target webcpp builds for.
  Source: `CONTRIBUTING.md` (proposals).
- **A proposal carries its reference code before it is proposed, with its
  original specification and plan when there are any and a
  `reference/STATUS.md` of where the work stands.** The implementer starts
  from that code, and `STATUS.md` says how to resume the work.
  Source: `README.md` (proposals).
- **A proposal moves through draft, proposed, accepted, implementing and
  implemented, and a rejected or withdrawn one is archived with that status.**
  The reasons then stay readable.
  Source: `CONTRIBUTING.md` (proposals).
- **A proposal is implemented when its code is merged into the `main` of its
  repository, the superproject's `main` records that commit or a later one,
  and every GitHub check of both passed; no release is needed, and `release`
  names the version the change enters.** The status says what is built, and a
  release waits for the owner.
  Source: `CONTRIBUTING.md` (proposals).
- **The maintainers decide a proposal after its public discussion on its pull
  request, until a governance of the members, through grants and a DAO, is
  specified by a proposal of its own.** (reason not recorded)
  Source: `CONTRIBUTING.md` (proposals).
- **Outward actions belong to the owner: an agent never pushes, merges,
  creates a repository, changes a GitHub setting or touches a credential, and
  a plan names each such act as a gate the owner resolves.**
  (reason not recorded)
  Source: `organization/openspec/specs/organization/spec.md` (proposals);
  `organization/openspec/changes/site-increments-4-5/specs/site/spec.md`
  (proposals).
- **History and recorded material are not rewritten: existing commits,
  archived proposals and recorded patches keep what they were made with.**
  They are records of what was done, and changing them would make them
  disagree with the commits they describe.
  Source:
  `organization/openspec/changes/archive/2026-10-13-contributor-identity/design.md`
  (proposals).

**Agents.**

- **The rules are written for coding agents and humans alike, so that an agent
  with no other context can port a library by following them, and nothing in
  webcpp depends on one agent system.** Each library is ported with the help
  of coding agents; an agent system that reads `AGENTS.md` at a repository's
  root finds it there, and others are pointed at it.
  Source: `CONTRIBUTING.md` (webcpp); `AGENTS.md` (webcpp).
- **Every contributor, human or agent, commits under their own git identity,
  an agent under that of the account it acts for or its own, never another
  person's; the rules fix no address.** A fixed identity cannot be followed by
  a second maintainer or an agent of another account without impersonation,
  and keeps a personal address in the rules; a shared organization identity
  was rejected because it hides who made a change, which the review and the
  history need.
  Source:
  `organization/openspec/changes/archive/2026-10-13-contributor-identity/design.md`
  (proposals).
- **A commit carries no trailer of any kind, stages explicit paths and has a
  plain subject prefixed by the part it touches.** These rules serve the
  history's readability, whoever's name is on a commit.
  Source:
  `organization/openspec/changes/archive/2026-10-13-contributor-identity/design.md`
  (proposals).
- **Agent skills live in `.agents/skills/<name>/SKILL.md`, the vendor-neutral
  layout, in the superproject and in the proposals repository only.** Several
  agents read that layout and OpenSpec writes its own skills there; one
  directory per agent product was rejected as a copy of every skill, and a
  library keeps what is specific to it in its own `AGENTS.md`.
  Source:
  `organization/openspec/changes/archive/2026-10-13-agent-skills/design.md`
  (proposals).
- **A skill points to the chapter that holds a rule and lists the steps and
  commands of its task; it never restates the rule, and the rule wins where
  the two disagree.** A skill that copied the rules would drift from
  `AGENTS.md` at the first change of a rule.
  Source:
  `organization/openspec/changes/archive/2026-10-13-agent-skills/design.md`
  (proposals).
- **The skill `webcpp-text-and-commits` is one file written twice, identical
  in both repositories, and a change to either is compared with `cmp` and made
  to both.** A symbolic link across repositories does not exist in a clone,
  and an agent reads the files of the repository it is in.
  Source:
  `organization/openspec/changes/archive/2026-10-13-agent-skills/design.md`
  (proposals).
- **OpenSpec's six skills are generated by OpenSpec 1.10.0 in a copy of the
  proposals repository and committed with two edits, keeping their MIT front
  matter; `openspec init` never runs in the repository itself.** `init` would
  create a root `openspec/`, which the repository's several roots rule out,
  and the kept front matter leaves the origin of the text visible.
  Source:
  `organization/openspec/changes/archive/2026-10-13-agent-skills/design.md`
  (proposals).
- **CI parses every skill's front matter as YAML and refuses a name that
  differs from its directory and a missing or blank description.** It catches
  the unquoted colons in descriptions that the review found.
  Source:
  `organization/openspec/changes/archive/2026-10-13-agent-skills/design.md`
  (proposals).

### The site (webcpporg.github.io; increment 1 built)

Increment 1 of the site's specification of 2026-10-10, as built: the site's
repository at `f1b4832`, which the superproject's `site/` records at
`ddb6cb2`, the superproject's `tools/site/` and `tools/ci/assemble.py`, and
the CI's jobs `site`, `publish` and `pages`. Increments 2 to 8 are the
roadmap; 4 and 5 are the next section.

**The repository and the build.**

- **The site is a repository of its own, `webcpporg/webcpporg.github.io`,
  checked out in the superproject as the submodule `site/`, as a library is
  under `libs/`.** The site is webcpp built with webcpp, a project that uses
  webcpp's libraries the way any user would, so that anyone who opens its
  repository on GitHub sees it. Unlike a library's, its submodule URL in
  `.gitmodules` is the absolute SSH address
  `git@github.com:webcpporg/webcpporg.github.io.git`, not a relative one.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals); `.gitmodules` (webcpp).
- **The whole site is built by one command at the superproject's root,
  `b2 site`, which calls the site's npm scripts through one wrapper rule,
  `site.npm`, and never reimplements them; only `b2 site`'s output is ever
  deployed.** (reason not recorded) It is the owner's decision 13 of
  2026-10-10: b2 also drives Emscripten for the site's C++, and npm alone
  still builds and runs the JavaScript parts for work on the site.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).
- **What the superproject holds of the site is its assembly, `tools/site/` and
  `tools/ci/assemble.py`, and the libraries' pages stay Asciidoctor's, given
  the site's header and `assets/chrome.css` alone.** The libraries'
  documentation system stays one, the site's frame around it being OpenUI's,
  and a page Asciidoctor styled keeps its look.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals); `organization/openspec/specs/site/spec.md` (proposals).
- **Every step of `b2 site` writes `bin/site.tmp`, and the finished build
  moves into `bin/site.builds/`, onto which the link `bin/site` is swapped in
  one rename.** A server on `bin/site` reads one build or the other whole,
  never half of one, and a failed step leaves the last good build in place.
  Source: `AGENTS.md` (webcpp).
- **Every page of `bin/site` is valid HTML, checked by html-validate in two
  passes, the site's own pages against `htmlvalidate.json` and the libraries'
  Asciidoctor pages against `htmlvalidate.docs.json`, each rule turned off
  with its reason in the `Jamfile`.** The two configurations have no leading
  dot since the site's commit `d113e38`, so that a source release, which
  carries no dot file, keeps them; the specification still names them
  `.htmlvalidate.json` and `.htmlvalidate.docs.json`.
  Source: `Jamfile` (site).
- **No build or test reaches the network beyond `npm ci` from the lockfile;
  `npm run dev` alone downloads the examples' wasm from the preview, checked
  against the preview's `precache.json`.** (reason not recorded) A downloaded
  wasm whose hash `precache.json` does not list is refused.
  Source: `organization/openspec/specs/site/spec.md` (proposals).

**Channels, indexing and search.**

- **The site has two channels from the same command: the preview, built from
  every push to `main` and served at https://webcpporg.github.io/, and the
  release, built from a release tag for https://webcpp.org/.**
  (reason not recorded) They are the owner's decisions of 2026-10-10; the
  release channel is built but not published, and waits for the first release
  and the move of the domain's DNS.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).
- **The preview is never indexed: every page of it, the libraries' and the
  report's included, carries `noindex`, it writes no `sitemap.xml`, and its
  `robots.txt` still lets every crawler in.** The preview is the development
  version (owner, 2026-10-11), and a crawler let in reads each page's
  `noindex`; Google's search and Search Console belong to webcpp.org.
  Source: `organization/openspec/specs/site/spec.md` (proposals).
- **The release's `robots.txt` allows every crawler, `Google-Extended`
  included, and names its `sitemap.xml`.** Google's AI then learns webcpp's
  documentation.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).
- **Search is Google's, restricted to the site: until the owner creates the
  Programmable Search engine for webcpp.org, the search page is a form whose
  hidden `q` is `site:<channel host>`.** (reason not recorded) The engine and
  its id are the owner's to create, with the release site.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).
- **SEO is part of done: every page's head is written from its `Page(...)` and
  the catalogue, and `seo/queries.json` names the searches each page answers,
  which a test holds to the page's title, `<h1>` or description.** The owner's
  aim is that Google ranks webcpp for C++ developers who search for what
  exists to develop C++ for the web.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).

**Pages.**

- **Every page is written in OpenUI Lang and rendered by the site's React
  components, each with its props validated by a zod schema, at build time
  with `renderToString` and in the browser by hydration; without JavaScript a
  reader gets one `<noscript>` message.** The owner decided that the site is a
  JavaScript application whose content OpenUI renders, its components the
  design system Claude Design imports; the first paint shows the page before
  the scripts run and lets a crawler that runs no script read it.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).
- **The site is static files: no server, no runtime API, no cookie and no
  analytics, and its one third-party destination is Google's search, reached
  on the reader's submit.** (reason not recorded) It is the owner's decision 7
  of 2026-10-10.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).
- **The bundles are production builds, OpenUI's lang-core telemetry is
  replaced by a module that does nothing, and `npm ci` runs with telemetry
  off.** In development OpenUI's web entry mounts a devtools widget fetched
  from a CDN, and lang-core posts to PostHog when the environment asks; with
  the replacement no reader's browser and no build can reach them.
  Source: `organization/openspec/specs/site/spec.md` (proposals).
- **Every link between pages is relative; the indexing files' base URL is the
  one place a URL of the site is absolute.** The site serves from whichever
  path it is published under, as under `/webcpp/` during the move or a fork's
  `/<repo>/`.
  Source: `AGENTS.md` (site);
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-plan.md`
  (proposals).
- **No value the build knows is typed on a page, and no page shows a number or
  an example that does not exist: the catalogue is read from every library's
  `meta/libraries.json` and its declared targets, and live examples appear
  only as a roadmap.** (reason not recorded)
  Source: `AGENTS.md` (site);
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-plan.md`
  (proposals).
- **Layouts are written mobile first, from 360 px up, with breakpoints at 768,
  1280 and 1440 px, in light and dark themes.** The owner wants the site
  mobile first and good on the desktop too, where developers read most.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).
- **The social cards and the icons are rendered by the build from the logo's
  SVG, with a pinned font and no system font.** A card is then the same bytes
  on every machine, and no image is drawn twice.
  Source: `organization/openspec/specs/site/spec.md` (proposals).

**Readers.**

- **The site speaks to four readers, C++ developers, JavaScript developers,
  crypto developers and AI agents, through a libraries page listed as Boost
  lists its own and three doors, `cpp/`, `javascript/` and `ai/`.** The site
  is where webcpp shows its idea, where C++ and the web meet, and leads its
  reader to the libraries' documentation; the owner wants a section for
  JavaScript developers always.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).
- **The site writes `llms.txt` and `libraries.json` at its root for agents.**
  AI agents are first-class readers of webcpp: they use what it publishes to
  find libraries of high quality.
  Source: `organization/openspec/specs/site/spec.md` (proposals).
- **The site's repository has two ways in, each for its reader: a JavaScript
  developer works with npm alone, or builds the whole project step by step,
  and a C++ developer uses b2 alone; `test/readme_test.mjs` keeps the README
  so.** Neither reader is sent through the other's tools, and a JavaScript
  developer changes pages, components and the examples' JavaScript without a
  C++ toolchain.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).

**Publication.**

- **The superproject's CI builds the site on every run, a red matrix included,
  and on a push to `main` publishes it as the one commit of an orphan
  `gh-pages` branch of the site's repository, with that repository's deploy
  key.** The matrix is there to show what fails; `gh-pages` is build output,
  replaced whole, and the runs on `main` queue rather than cancel, so that an
  older site never replaces a newer one.
  Source: `.github/workflows/ci.yml` (webcpp).
- **The old address, https://webcpporg.github.io/webcpp/, redirects every path
  to the same path at the root, its query and fragment kept.** No published
  link breaks.
  Source:
  `organization/openspec/changes/archive/2026-10-07-genesis/reference/site-spec.md`
  (proposals).

## 15. The libraries' design

The design decisions of each library of the superproject, as its tree has
them, each with its reason and its source. A source is a path in its
repository: `libs/<name>` is the library's repository at the commit the
superproject pins, `webcpp` the superproject at `ddb6cb2`, and `proposals`
[webcpporg/proposals](https://github.com/webcpporg/proposals), under
`libraries/<name>/openspec/` unless the path says otherwise. A library's own
`AGENTS.md` holds what an agent needs to work on it, with the rules of its own
that its specification asks of it; the decisions behind them, with their
reasons, are here. Where a design document, or the library's `AGENTS.md`,
disagrees with the tree, the section says what the tree does, and chapter 19
records the disagreement.

### config (the collection's configuration macros; own; implemented in 0.1.0)

config is webcpp's counterpart of Boost.Config: `<webcpp/config.hpp>` names
the target a program is built for and says whether webcpp has exceptions, and
`<webcpp/version.hpp>` gives webcpp's version. Every webcpp library's
`<webcpp/<name>/config.hpp>` includes `<webcpp/config.hpp>` first, so config
is read before anything else of webcpp.

**Scope and dependencies.**

- **config is a library of webcpp's own, with a repository, a `build.jam`,
  metadata, a page and a CI file like every other library.** Every library
  needs the same three answers (the target, exceptions, the version) before it
  compiles a line of its own. The rejected alternative, each library reading
  `__wasip2__` and `BOOST_NO_EXCEPTIONS` itself, repeats the logic in every
  library and lets the answers drift apart.
  Source:
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **`<webcpp/config.hpp>` includes `<boost/config.hpp>` and adds only what is
  webcpp's.** What Boost.Config already answers (compilers, the standard
  library, `BOOST_NO_*`) is not repeated, and a program that includes config
  has Boost.Config's macros too.
  Source: `include/webcpp/config.hpp` (libs/config);
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **config is macros only: it declares no namespace, no type and no
  function.** Boost.Config is macros only, and config is to cost nothing: the
  same on native, wasip2, wasip3 and Emscripten, with nothing beyond Boost's
  headers.
  Source: `libraries/config/openspec/specs/config/spec.md` (proposals);
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **`/webcpp/config//config` is an alias with no sources whose usage
  requirements are `<include>include` and `<library>/boost//headers`.** config
  needs Boost's headers and nothing to build or link.
  Source: `build.jam` (libs/config).

**Names.**

- **config's macros are the collection's, `WEBCPP_*`, never `WEBCPP_CONFIG_*`,
  and its include guards are `WEBCPP_CONFIG_HPP` and `WEBCPP_VERSION_HPP`.**
  Boost.Config's macros are `BOOST_*` in the same way. It is the one exception
  to `WEBCPP_<NAME>_*` and to a library's namespace, and the reference tooling
  treats config's prefix as `WEBCPP_` and requires no namespace of it.
  Source: `AGENTS.md` (libs/config); chapter 3 (this file).
- **config reserves the macro families `WEBCPP_HAS_*`, `WEBCPP_LIB_*`,
  `WEBCPP_NO_*`, `WEBCPP_TARGET_*` and `WEBCPP_VERSION*`, so no library is
  named `target`, `has`, `no`, `lib`, `version` or `test`, alone or followed
  by an underscore and more, in any case.** Such a library's `WEBCPP_<NAME>_*`
  macros would meet config's, or the tests' `WEBCPP_TEST_*`;
  `tools/doc/libraries.py` refuses the name.
  Source: `doc/introduction.adoc` (libs/config); `tools/doc/libraries.py`
  (webcpp).
- **config has exactly two public headers, `<webcpp/config.hpp>` and
  `<webcpp/version.hpp>`, named as `<boost/config.hpp>` and
  `<boost/version.hpp>` are, and `<webcpp/version.hpp>` lies outside
  `webcpp/config/`.** So does `<boost/version.hpp>` in Boost. The
  headers-alone test therefore does not take it, and the test `version`
  compiles it alone, as the first include of its translation unit.
  Source: `AGENTS.md`, `test/Jamfile` (libs/config).

**Targets.**

- **`<webcpp/config.hpp>` defines exactly one of `WEBCPP_TARGET_WASIP2`,
  `WEBCPP_TARGET_WASIP3`, `WEBCPP_TARGET_EMSCRIPTEN` and
  `WEBCPP_TARGET_NATIVE`, each a plain definition without a value, testing
  `__wasip2__`, then `__wasip3__`, then `__EMSCRIPTEN__`, and naming the
  target native when the compiler defines none of them nor `__wasm__`.** A
  library chooses its code by one macro of webcpp's rather than by the
  compiler's own; the order of the tests has no recorded reason. Measured with
  wasi-sdk 34 on 2026-10-09: wasm32-wasip2 defines `__wasi__`, `__wasm__` and
  `__wasip2__`, wasm32-wasip3 likewise with `__wasip3__`, and Emscripten
  6.0.11 defines `__EMSCRIPTEN__`.
  Source: `include/webcpp/config.hpp`, `doc/targets.adoc` (libs/config);
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The target macros come from the compiler's own macros alone, never from
  the build system.** A program compiled by hand, with a plain `clang++` or
  with wasi-sdk's, gets the macro b2 would give it.
  Source: `doc/targets.adoc`, `AGENTS.md` (libs/config).
- **A WebAssembly build for none of the three WebAssembly targets (the
  compiler defines `__wasm__`: wasm32-wasip1, wasm32-unknown-unknown) stops
  with the preprocessor error "unsupported target: webcpp builds for
  wasm32-wasip2, wasm32-wasip3, Emscripten and natively".** Read as native, it
  would compile code for a system the program does not run on (owner,
  2026-10-09). A new target gets a macro, a branch and a test of its own.
  Source: `include/webcpp/config.hpp` (libs/config);
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The target block comes before `#include <boost/config.hpp>`, and a test
  pins the order.** wasm32-unknown-unknown has no C++ standard library, and
  Boost.Config stops there at a header that is not there: config's message
  must come first.
  Source: `include/webcpp/config.hpp`, `doc/targets.adoc`, `test/Jamfile`
  (libs/config).
- **A target macro or `WEBCPP_HAS_EXCEPTIONS` defined before the header stops
  the build with the single error "WEBCPP_TARGET_* and WEBCPP_HAS_EXCEPTIONS
  are defined by <webcpp/config.hpp> alone", and the rest of the header is the
  `#else` of that test.** No macro is then defined a second time, and that
  message is the only one the build reports.
  Source: `include/webcpp/config.hpp` (libs/config);
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).

**Exceptions.**

- **`WEBCPP_HAS_EXCEPTIONS` is defined when neither `BOOST_NO_EXCEPTIONS` nor
  `WEBCPP_NO_EXCEPTIONS` is defined.** Boost.Config already reads whether the
  compiler has exceptions (`-fno-exceptions`, which b2's
  `exception-handling=off` gives), so config adds only the developer's switch,
  and every library tests one macro of webcpp's.
  Source: `include/webcpp/config.hpp`, `doc/exceptions.adoc` (libs/config).
- **`WEBCPP_NO_EXCEPTIONS` is the developer's alone: config never defines it,
  and, defined on the command line or in a b2 requirement, it turns off the
  exceptions of every webcpp library at once, even in a build that has them.**
  A program sets it once, for every library alike, without knowing which of
  them throws; the rejected alternative, a per-library switch only, would make
  it know (owner, 2026-10-09, option (a)). A developer may still define one
  library's `WEBCPP_<NAME>_NO_EXCEPTIONS` alone.
  Source: `doc/exceptions.adoc` (libs/config);
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **`WEBCPP_NO_EXCEPTIONS` does not define `BOOST_NO_EXCEPTIONS`: Boost's own
  code keeps the exceptions the compiler has.** The rejected alternative would
  change the behaviour of Boost's headers in a build whose compiler supports
  exceptions. The test `exceptions_developer_off` pins it.
  Source: `doc/exceptions.adoc`, `test/exceptions_test.cpp` (libs/config);
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).

**Version.**

- **`WEBCPP_VERSION` is a number, `major * 100000 + minor * 100 + patch`
  (0.1.0 is `100`, 1.2.3 is `100203`), and a macro rather than a constant.**
  It is numbered as `BOOST_VERSION` is, and a macro so that `#if` compares it.
  Source: `include/webcpp/version.hpp`, `doc/version.adoc` (libs/config).
- **`WEBCPP_LIB_VERSION` is a string literal, `"<major>_<minor>"`, with
  `"_<patch>"` after it only when the patch level is not 0 (`"0_1"` is
  0.1.0).** It is written as `BOOST_LIB_VERSION` is.
  Source: `include/webcpp/version.hpp`, `doc/version.adoc` (libs/config).
- **The version has three numbers, and its tag is `webcpp-0.1.0`.** Boost's
  tags have three numbers (`boost-1.92.0`).
  Source:
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The version is written in one place, the line `#define WEBCPP_VERSION` of
  `include/webcpp/version.hpp`, and nothing follows the number on that line.**
  The Jamroot and `tools/release/release.py` read that line itself and refuse
  anything else on it, a trailing comment included: hence the
  `NOLINTNEXTLINE(modernize-macro-to-enum)` on the line above it.
  Source: `include/webcpp/version.hpp` (libs/config); `AGENTS.md`, chapter 5,
  "Releases" (webcpp).
- **The version moves to the next one only by the release procedure, right
  after a tag.** Between two releases it names the version in preparation.
  Source: `AGENTS.md`, `doc/version.adoc` (libs/config).

**Documentation.**

- **`config.hpp` holds an `#ifdef __MRDOCS__` block that defines and at once
  undefines `WEBCPP_TARGET_WASIP2`, `WEBCPP_TARGET_WASIP3`,
  `WEBCPP_TARGET_EMSCRIPTEN` and `WEBCPP_NO_EXCEPTIONS`, each under its Doc
  Comment.** MrDocs parses webcpp natively and with exceptions, where only
  `WEBCPP_TARGET_NATIVE` and `WEBCPP_HAS_EXCEPTIONS` are defined, and the
  reference lists all eight macros.
  Source: `include/webcpp/config.hpp` (libs/config).
- **A compiler's macro in a Doc Comment is written with an escaped leading
  underscore, `\__wasip2__`.** Asciidoctor then keeps both underscores in the
  reference.
  Source: `include/webcpp/config.hpp` (libs/config);
  `libraries/config/openspec/specs/config/spec.md` (proposals).

**Evidence.**

- **Every test is compiled and never run, with three rules of
  `tools/webcpp.jam`: `webcpp.headers-alone`, `webcpp.compile` (checks by
  `#error` and `static_assert`) and `webcpp.compile-diagnostic` (clang
  `-verify` against the error a source states).** What config does, it does
  when a program is compiled.
  Source: `test/Jamfile`, `doc/testing.adoc` (libs/config).
- **The diagnostic tests, `predefined_*` and `unsupported_*`, are built on
  b2's clang toolsets alone, and GCC, MSVC and Emscripten skip them, as grey
  cells of the test matrix.** `-verify` is clang's; the macros they pin are
  the same source on every compiler.
  Source: `doc/testing.adoc` (libs/config);
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **Each `predefined_*` test is built with warnings as errors off.** A macro
  that config went on to define a second time is then a warning `-verify`
  sees, not an error it ignores.
  Source: `test/Jamfile` (libs/config).
- **The unsupported-target tests build wasm32-wasip1 and
  wasm32-unknown-unknown with wasi-sdk's clang (on the wasip2 target, with an
  added `--target`), and `__wasm__` defined alone natively.** The native one
  runs in every native clang lane; the wasm32-unknown-unknown one pins that
  the target block comes before Boost.Config. The order of the two `--target`
  options on the compile line was measured first, so that clang takes the
  added one.
  Source: `test/Jamfile` (libs/config);
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/tasks.md`
  (proposals).
- **The test `target` is told the toolset by `test/Jamfile`
  (`WEBCPP_TEST_TARGET_*`) and requires the matching `WEBCPP_TARGET_*`, and
  exactly one.** The toolset tells the test, and the compiler tells config.
  Source: `test/Jamfile`, `test/target_test.cpp` (libs/config).
- **`exceptions_test.cpp` is built three times (as the build asks, with
  `exception-handling=off`, with `WEBCPP_NO_EXCEPTIONS`), and the build
  without exceptions first requires `BOOST_NO_EXCEPTIONS`.** A flag that was
  not applied is refused rather than passed as a build without exceptions; the
  two builds without the developer's macro also refuse a
  `WEBCPP_NO_EXCEPTIONS` that config defined itself.
  Source: `test/Jamfile`, `test/exceptions_test.cpp` (libs/config).
- **`version_test.cpp` checks by `static_assert` that `WEBCPP_LIB_VERSION` is
  digits separated by single underscores, names `WEBCPP_VERSION`'s major and
  minor numbers, and holds the patch level exactly when it is not 0.** The two
  macros must name one version.
  Source: `test/version_test.cpp` (libs/config).
- **Every test and the example are declared for the four targets,
  `webcpp.targets native wasip2 wasip3 emscripten`.** config is to be the same
  on every target webcpp builds for.
  Source: `test/Jamfile`, `example/Jamfile` (libs/config);
  `libraries/config/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).

### xactor (a deterministic actor system; own; implemented in 0.1.0)

xactor runs actors that handle one message at a time, on the host's thread, in
an order that depends on the order of enqueuing alone; every execution is paid
from a budget of fuel, and time is a number the host brings. Its code is the
actor layer of an earlier private project, moved, renamed `webcpp::xactor` and
re-tested; webcpp's asynchronous libraries are to be built on it.

**Scope and dependencies.**

- **xactor is a library of webcpp's own, not a port, and its evidence is its
  own tests, with no oracle.** It ports nothing, so there is no original to
  run its cases: its tests came with its code from the earlier project and
  were converted with an equivalence record.
  Source:
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **xactor stands alone: no header, comment or example of it names another
  webcpp library, and its code depends on Boost's headers and config alone.**
  The libraries built on xactor depend on it, never the reverse, and every
  asynchronous library webcpp ports or writes is to run on it; the page names
  xstate once, as a library that builds on it.
  Source: `AGENTS.md` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/proposal.md`
  (proposals).
- **`/webcpp/xactor//xactor` is an alias that adds `include`,
  `/boost//headers` and `/webcpp/config//config`: xactor uses Boost.System for
  `result` and the error codes, Boost.Asio for `asio_driver` alone, and
  compiles nothing.** Boost.System gives the `result` every fallible call
  returns; only the driver that runs turns as Asio handlers needs Boost.Asio,
  so only it includes Boost.Asio.
  Source: `build.jam`, `doc/introduction.adoc` (libs/xactor).
- **What an actor system may add on top of xactor is left out: threads and a
  clock of its own, a child's end reaching its parent, a registry of actors by
  name, the inspection of what each actor does, supervision, and the
  persistence of actors.** They are left to the program or to a library built
  on xactor (reason not recorded). A child that must tell its parent that it
  ended sends it a message, to `turn.parent()`, in the turn it ends.
  Source: `doc/introduction.adoc` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).

**Model and interface.**

- **The program's messages are one closed `std::variant` of plain structs, and
  every type of xactor that carries a message is a template over it.** Closed
  means every message is known when the program is compiled, so `std::visit`
  checks that every alternative is handled, and the log records which
  alternative arrived by its `index()`.
  Source: `doc/model.adoc` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **xactor asks of `Message` only that it be a `std::variant` that can be
  moved: it need be neither copyable nor default-constructible.** The library
  names no message, id or error of any user (guarantee 28). The requirement is
  stated in the documentation, and the templates are unconstrained (reason not
  recorded).
  Source: `doc/guarantees.adoc`, `include/webcpp/xactor/scheduler.hpp`
  (libs/xactor).
- **An actor's behaviour is a class derived from `actor_logic<Message>`, whose
  one pure virtual function is
  `result<void> handle(turn<Message>&, const envelope<Message>&)`.** Any class
  with a `handle` is an actor, whether its behaviour is decided at run time or
  is a state machine compiled into the program, so xactor needs no adapter for
  a state machine library.
  Source: `include/webcpp/xactor/actor_logic.hpp`, `doc/static-actors.adoc`
  (libs/xactor).
- **`actor_logic` is neither copyable nor movable, and the scheduler owns each
  logic through a `std::unique_ptr`, where it was constructed, and never moves
  it.** A test that constructs a logic and hands it to `spawn` keeps a pointer
  to it and reads its members after each delivery.
  Source: `include/webcpp/xactor/actor_logic.hpp`, `doc/drivers.adoc`
  (libs/xactor).
- **A logic never sees the scheduler, its mailbox or the driver: all it does,
  it does through its `turn`, which lives for one `handle` and holds
  references to the scheduler and to the message.** The turn knows the actor
  that acts and the execution of the message, so a message the actor sends
  carries it as its sender and is paid from that execution. A logic keeps
  neither the turn nor a reference into the message beyond the call.
  Source: `doc/turns.adoc`, `include/webcpp/xactor/scheduler.hpp`
  (libs/xactor).
- **What a logic is constructed with is the actor's input and its members are
  the actor's state: `create_actor<Logic>(system, inputs...)` and
  `turn.spawn_child<Logic>(inputs...)` forward their arguments to the
  constructor of `Logic`.** `create_actor` deduces `Message` from the
  scheduler, so a call names the logic alone.
  Source: `doc/logic.adoc`, `include/webcpp/xactor/scheduler.hpp`
  (libs/xactor).
- **An actor is `active` as soon as it is created, with no separate start.**
  (reason not recorded) A caller that needs a start delivers the actor its
  first message.
  Source: `include/webcpp/xactor/scheduler.hpp` (libs/xactor).
- **An actor's address, an execution and a message's place are distinct
  structs, `actor_ref` (a `std::uint32_t`), `correlation_id` and
  `sequence_number` (each a `std::uint64_t`), not plain integers.** An address
  is then never passed where an execution is expected. The widths have no
  recorded reason.
  Source: `include/webcpp/xactor/ids.hpp` (libs/xactor).
- **An `actor_ref` is a number, not a handle: addresses start at 1 in spawn
  order, address 0 names no actor and is the `from` of a message the host
  sent, and an address is never reused.** It keeps nothing alive, and an actor
  that has ended keeps its address and its status, which `status_of` reports.
  Source: `include/webcpp/xactor/ids.hpp` (libs/xactor).

**Scheduling and concurrency.**

- **Each actor has a FIFO mailbox, and the actors with messages waiting wait
  in one FIFO queue, each at most once; `run_one` takes the actor at the
  front, hands it the first message of its mailbox, and puts it back at the
  end while its mailbox holds more, so a message sent in a turn is never
  handled inside that turn.** The order of deliveries is then a function of
  the order of enqueuing alone, which makes a run deterministic and lets every
  driver write one log, and no actor starves another however much it sends
  itself.
  Source: `include/webcpp/xactor/scheduler.hpp`, `doc/scheduler.adoc`
  (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **xactor runs on one thread, the host's: the scheduler starts no thread, no
  turn blocks, and it keeps no static mutable state.** A run is a function of
  its deliveries, and xactor runs unchanged on wasm32-wasip2 and
  wasm32-wasip3, where there is no thread to lean on; two schedulers in one
  process are independent.
  Source: `doc/scheduler.adoc`, `doc/determinism.adoc` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/proposal.md`
  (proposals).
- **The scheduler keeps each actor in a slot of one `std::vector`, at the
  index of its address minus one, with its logic, its parent, its children in
  spawn order, its mailbox (a `std::deque`), its status, its output and its
  error.** Addresses are never reused and an ended actor keeps its status,
  output and error. A pointer `output_of` returns stays valid only until the
  scheduler takes in another actor, since the vector may grow then.
  Source: `include/webcpp/xactor/scheduler.hpp` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).

**Drivers.**

- **`scheduler::run_one` is the one step, and a driver only decides when to
  call it.** The scheduler decides what a turn is and the driver when it
  happens, so the same actors run under a plain loop, one step at a time in a
  test, or as Asio handlers, and record one envelope log.
  Source: `include/webcpp/xactor/drivers.hpp`, `doc/drivers.adoc`
  (libs/xactor).
- **`fifo_driver` offers `run_until_idle(log)` and `run_turn(n, log)`, which
  delivers at most `n` messages.** `run_turn` serves a host that has to take
  the thread back between turns.
  Source: `include/webcpp/xactor/drivers.hpp` (libs/xactor).
- **`test_driver` offers `step()` and `step(log)`, each one `run_one`, and
  nothing else.** A test sees exactly what one delivery changed; messages and
  time reach the scheduler through `deliver`, `clock_tick` and `release_next`.
  Source: `include/webcpp/xactor/drivers.hpp`, `doc/drivers.adoc`
  (libs/xactor).
- **`asio_driver` owns an `io_context` of concurrency hint 1, a work guard and
  a strand, posts each `run_one` onto the strand, and drains the context with
  `poll`, never with `run`, `run_one` or `run_for`; the context offers no
  executor.** Under the work guard `run` would never return, and `run_one` and
  `run_for` would block waiting for more work, so a turn never blocks. The
  context is the driver's alone: a program's own I/O objects run on a context
  of their own.
  Source: `include/webcpp/xactor/drivers.hpp`, `doc/drivers.adoc`
  (libs/xactor).
- **`asio_driver` and Boost.Asio's headers are declared only under
  `#ifndef __wasi__`, each include marked
  `// lint-world: posts handlers only`.** Boost.Asio 1.92 does not compile for
  wasm32-wasip2 or wasm32-wasip3 with wasi-sdk 34 (no `ESHUTDOWN`, no
  `::pause`, and a `signal.h` that stops with `#error`). The driver posts
  handlers and makes no I/O object, so it reaches no clock, file or socket.
  Source: `include/webcpp/xactor/drivers.hpp`, `example/Jamfile`
  (libs/xactor).
- **`run_one` returns a `result<bool>`, and the drivers forward its failure,
  though no failure of the scheduler exists today.** A failure of the
  scheduler itself then has a channel the drivers already forward; a handler's
  error ends its actor, not the run.
  Source: `include/webcpp/xactor/scheduler.hpp`, `doc/scheduler.adoc`
  (libs/xactor).
- **An `envelope_log` entry, `logged_envelope`, holds the sequence number,
  `to`, `from`, the correlation, the execution's fuel at delivery and the
  payload's `index()`, never the message; `run_one` records it before the
  actor handles the message, and nothing for a message dropped.** An entry has
  a fixed width, the log is one type whatever the `Message`, and two logs
  compare cheaply, with `==`, which is how two runs or two drivers are shown
  to deliver alike.
  Source: `include/webcpp/xactor/envelope_log.hpp`, `doc/drivers.adoc`
  (libs/xactor).

**Fuel.**

- **Every message belongs to an execution, all the messages one host delivery
  causes, named by the `correlation_id` the host chooses; an execution's fuel,
  `budgets::fuel` (a `std::uint32_t`, 1,000,000 by default), opens with the
  first `deliver`, `clock_tick` or `release_next` that names it.** Every
  execution ends: no chain, fan-out or ping-pong of messages runs forever.
  Fuel is kept for each execution, not globally, so one input's work is
  bounded whatever another input does, and a host gives each input a
  correlation of its own.
  Source: `include/webcpp/xactor/budgets.hpp`, `doc/fuel.adoc` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **Nothing refills an execution: the scheduler keeps every execution it
  opened in a `std::map` keyed by correlation, and a later delivery with the
  same correlation shares what is left.** The work of one execution is then
  bounded, whatever its actors send.
  Source: `include/webcpp/xactor/budgets.hpp`,
  `include/webcpp/xactor/scheduler.hpp` (libs/xactor).
- **`send`, `reply` and `wake_at` cost one unit, `spend(n)` costs n units, and
  every other call of a turn, a host's delivery and the release of a timer
  cost nothing.** Releasing a timer is free since arming it was paid, and
  `spend` lets an actor that computes without sending bound its work too. Why
  a host's delivery is free is not recorded.
  Source: `doc/fuel.adoc`, `include/webcpp/xactor/scheduler.hpp`
  (libs/xactor).
- **Payment is all or nothing: a call the execution cannot pay fails with
  `errc::resource_limit` and enqueues, arms and spends nothing, and a refused
  keyed `wake_at` leaves the timer under its key armed.** A refusal is a value
  the logic decides about: it goes on, or returns the failure to end its actor
  with it.
  Source: `doc/fuel.adoc`, `doc/guarantees.adoc` (libs/xactor).
- **A message to an actor that has ended is dropped and the call succeeds, a
  `send` being paid all the same, while a call that names no actor fails with
  `errc::invalid_argument`, and a `send` so refused is not paid.** The sender
  cannot know that the receiver has ended, so dropping is not an error of the
  sender's.
  Source: `include/webcpp/xactor/scheduler.hpp`, `doc/turns.adoc`
  (libs/xactor).

**Time and timers.**

- **xactor reads no clock: time is a `std::uint64_t` that the host brings with
  `clock_tick` or `release_next`, in a unit of the host's choosing, and no
  timer fires without one of them.** A run with timers is then as repeatable
  as one without, and a test moves time by any amount at once.
  Source: `doc/timers.adoc`, `include/webcpp/xactor/scheduler.hpp`
  (libs/xactor).
- **Armed timers live in one `std::map` keyed by (deadline, arming sequence),
  and due timers are released in deadline order, equal deadlines in arming
  order.** No two entries collide, and a tick releases timers in one defined
  order on every platform.
  Source: `include/webcpp/xactor/scheduler.hpp` (libs/xactor).
- **`clock_tick` releases every due timer, and `release_next` only the
  first.** A host that runs the system between two calls of `release_next`
  lets one timer's handling cancel or replace a later timer of the same tick,
  which `clock_tick`, releasing them all before any is handled, cannot.
  Source: `include/webcpp/xactor/scheduler.hpp`, `doc/timers.adoc`
  (libs/xactor).
- **A released timer's message belongs to the execution the releasing call
  names, and its sender is the actor itself.** (reason not recorded) Its
  release costs nothing, since arming it was paid.
  Source: `doc/timers.adoc`, `doc/guarantees.adoc` (libs/xactor).
- **`wake_at(deadline, payload, key)` replaces the same actor's timer under
  `key`, the replacement taking a new arming order, and `cancel_timer(key)`
  removes it for free.** Keys belong to their actor, so two actors may use the
  same key; why a replacement takes a new arming order is not recorded.
  Source: `include/webcpp/xactor/scheduler.hpp`, `doc/timers.adoc`
  (libs/xactor).
- **A tick earlier than the current time is not refused: time and `now()` move
  back.** (reason not recorded) A host that wants time to move forward only
  never brings an earlier time.
  Source: `doc/timers.adoc` (libs/xactor).
- **`timer::payload` has no default member initializer.** A `Message` need not
  be default-constructible, and with libstdc++ `std::erase_if` asks whether a
  timer is, which makes Clang instantiate the initializer; a move-only message
  test (guarantee 28) and the Clang lanes on libstdc++ catch a regression.
  Source: `include/webcpp/xactor/scheduler.hpp`, `test/CONVERSION.md`
  (libs/xactor); `AGENTS.md`, chapter 4 (webcpp).

**Lifecycle.**

- **An actor is `active`, `done`, `error` or `stopped`, an
  `enum class status : std::uint8_t` with the fixed values 1 to 4, and the
  three last are final: an actor that ends loses its pending messages, its
  place in the queue and its timers, and every later message to it is dropped,
  never delivered and never logged.** The values never change and are never
  reused, because a system that persists its actors rebuilds them from these
  numbers.
  Source: `include/webcpp/xactor/status.hpp`, `doc/lifecycle.adoc`
  (libs/xactor).
- **An actor spawned in a turn is a child of that turn's actor, recorded in
  spawn order, and `scheduler::stop` and `turn::stop_child` stop a whole
  family, each actor after its own descendants, siblings in spawn order, and
  return the actors stopped in that order.** The order is one a caller may
  rely on, and an explicit stack (a preorder that visits the last child first,
  reversed) follows a family of any depth without recursion.
  Source: `include/webcpp/xactor/scheduler.hpp` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **`turn::stop_child` accepts only a child of the caller, and a member of the
  family that has already ended stays as it ended while its descendants are
  still stopped.** (reason not recorded) The caller itself, a grandchild and
  an address that names no actor are refused with `errc::invalid_argument`,
  which changes nothing.
  Source: `include/webcpp/xactor/scheduler.hpp`, `doc/lifecycle.adoc`
  (libs/xactor).
- **`turn::finish` and `turn::stop` end the calling actor alone, its children
  running on, and xactor does not tell a parent that a child ended.** (reason
  not recorded) The children are the ending logic's to stop with `stop_child`,
  and a child that must tell its parent sends it a message.
  Source: `doc/lifecycle.adoc` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **An actor ends once: a second `finish` or `stop` fails with
  `errc::invalid_argument`, and an error its `handle` returns after the turn
  ended it changes nothing.** (reason not recorded) The actor stays as it
  ended, with its output or none, and `error_of` stays empty.
  Source: `include/webcpp/xactor/scheduler.hpp`, `doc/lifecycle.adoc`
  (libs/xactor).
- **In the rest of the turn that ended its actor, a logic can still `send`,
  paid as usual, but `wake_at` and `spawn_child` fail with
  `errc::invalid_argument` before anything is paid or constructed.** (reason
  not recorded)
  Source: `doc/turns.adoc`, `include/webcpp/xactor/scheduler.hpp`
  (libs/xactor).

**Errors and exceptions.**

- **xactor's own errors are two, `errc::invalid_argument = 1` (a call that
  names what it cannot act on) and `errc::resource_limit = 2` (the execution
  has no fuel left for it), and a call that fails with either changes
  nothing.** The values start at 1, so an `error_code` of value 0, which
  `error_of` returns for an actor that has not failed, is no error; they are
  fixed and never reused.
  Source: `include/webcpp/xactor/errors.hpp` (libs/xactor).
- **The category `webcpp.xactor` is a `constexpr` constant with the fixed
  identity `0x786163746f720000`, the ASCII of "xactor" followed by two zero
  bytes.** It holds no mutable state.
  Source: `include/webcpp/xactor/errors.hpp` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **A `handle` may return any `error_code`, of xactor's category or of its
  own, which ends its actor alone with the status `error` and which the
  scheduler keeps as it is for `error_of`.** Every other actor keeps its turns
  and the run goes on: `run_one` still returns `true`.
  Source: `include/webcpp/xactor/actor_logic.hpp`, `doc/logic.adoc`
  (libs/xactor).
- **xactor catches nothing: an exception that a `handle` throws leaves
  `run_one` and the driver in the middle of the run.** (reason not recorded)
  The page's rules of determinism tell a handler to return an error instead.
  Source: `doc/determinism.adoc` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **Where exceptions are on, the operations that allocate (`spawn`, `deliver`,
  `send`, `wake_at`, the log's `record`) can still throw `std::bad_alloc`.**
  They do as a standard container does; the guarantee without exceptions is
  that xactor compiles without them, which the lint checks.
  Source: `doc/guarantees.adoc`, `doc/changelog.adoc` (libs/xactor).
- **`WEBCPP_XACTOR_NO_EXCEPTIONS` is defined as for every library although it
  changes nothing in xactor.** xactor raises no exception of its own; the
  macro exists so that one setting serves every webcpp library alike.
  Source: `include/webcpp/xactor/config.hpp`, `doc/testing.adoc`
  (libs/xactor).
- **xactor makes no promise about running without RTTI, and is built with
  it.** The promise was removed before 0.1.0, a breaking change, when the
  owner decided on 2026-10-08 that no variant is built without RTTI.
  Source: `doc/changelog.adoc`, `test/CONVERSION.md` (libs/xactor);
  chapter 6 (this file).

**Memory.**

- **Every allocation goes through the standard allocator (`std::make_unique`,
  `std::vector`, `std::deque`, `std::map`, `std::string`), and xactor takes no
  allocator or memory resource from its user.** xactor predates chapter 4's
  allocation rule, which a review is to bring it to first; actors' state and
  messages in a shared or relocatable segment are not part of 0.1.0.
  Source: `include/webcpp/xactor/scheduler.hpp` (libs/xactor); chapters 4 and 16
  (this file).

**Targets.**

- **xactor's tests and examples are declared for native, wasip2 and wasip3,
  and `xactor_asio` for native alone.** xactor must run unchanged natively and
  on WebAssembly, where Boost.Asio does not compile; why emscripten is not
  declared is not recorded.
  Source: `test/Jamfile`, `example/Jamfile` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/proposal.md`
  (proposals).

**Static actors.**

- **A logic that runs a state machine holds it as a member and hands it each
  message wrapped in an event type of the program's, `on<Event>`, which holds
  the message and the turn by reference.** Nothing in xactor knows the
  machine's library and that library does not know xactor, so any library
  whose machines take typed events joins the same way; the `on<Event>` lives
  for one call of the machine, so its references never outlive the turn.
  Source: `doc/static-actors.adoc`, `example/xactor_msm.cpp` (libs/xactor).
- **The example machine is written with Boost.MSM, used through its headers
  alone, never through `/boost/msm//boost_msm`.** Boost.MSM is one of Boost's
  libraries; its b2 target brings every library MSM depends on,
  Boost.Serialization among them, which is compiled.
  Source: `doc/static-actors.adoc` (libs/xactor).

**Evidence.**

- **The tests are Boost.Core lightweight_test programs, one per subject
  (`scheduler`, `lifecycle`, `fuel`, `create_actor`, `errors`,
  `sequence_and_log`), each case a function of the file's anonymous namespace
  named after the rule it checks, called from `main`.** lightweight_test is
  one header and builds on WASI too, where the tests run; a `static` function
  would have the same linkage, but clang-tidy's `misc-use-anonymous-namespace`
  rejects it.
  Source: `test/Jamfile`, `test/CONVERSION.md` (libs/xactor);
  `libraries/xactor/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **A case that cannot go on after a failed check returns,
  `if (!BOOST_TEST(...)) { return; }`, and a helper calls
  `webcpp::test::require`, which ends the program with
  `std::exit(boost::report_errors())`.** A helper cannot return from its
  caller's case, and a test program may be built without exceptions, so it
  cannot throw out of it either.
  Source: `test/require.hpp`, `test/CONVERSION.md` (libs/xactor).
- **The suites converted from Boost.Test carry an equivalence record,
  `test/CONVERSION.md`: 55 cases, 295 assertions in the source and 636 at run
  time, old and new equal, and three planted defects that fail the same cases
  in both suites.** The conversion can then be reviewed assertion by
  assertion.
  Source: `test/CONVERSION.md` (libs/xactor).
- **Determinism is proven by equal envelope logs: a `fifo_driver` and an
  `asio_driver` run of the same deliveries, a run cut by `run_turn` against
  one stepped by `test_driver`, and two runs of one input.** Two schedulers
  built with the same budgets and fed the same deliveries record equal logs
  (guarantees 15 and 17), and the log records every delivery as it was made.
  Source: `test/scheduler_test.cpp`, `example/xactor_drivers.cpp`,
  `example/xactor_testing.cpp` (libs/xactor).
- **The programs that use `asio_driver` sit under the header's own condition,
  `#ifndef __wasi__`, and every other test and example includes
  `<webcpp/xactor.hpp>`.** The WASI build of every other program is then the
  check that nothing of Boost.Asio enters a WASI build.
  Source: `doc/testing.adoc`, `AGENTS.md` (libs/xactor).

**Documentation.**

- **The page states 36 numbered guarantees under the anchors
  `xactor-invariant-<n>`, which tests and code cite as
  `(doc: #xactor-invariant-<n>)`, and the doc build fails on a citation that
  names no anchor.** A guarantee keeps its number forever, since code, tests
  and comments cite it; a new guarantee takes the next number.
  Source: `doc/guarantees.adoc` (libs/xactor); `AGENTS.md`, chapter 3
  (webcpp).
- **Every listing of the page includes a compiled example by `tag::` markers
  and every output its `.expected` file, and the page states no count of the
  tree's.** `example/Jamfile` runs every program the page shows and compares
  its output; a count typed by hand goes stale.
  Source: `AGENTS.md`, `example/Jamfile` (libs/xactor).
- **The reference is built strict, and `doc/mrdocs.yml` sets
  `show-enum-constants: true`.** The values of `errc` and `status` are fixed,
  and the enum's table of members would show each enumerator's brief alone.
  Source: `doc/mrdocs.yml`, `AGENTS.md` (libs/xactor).

### xstate (machines and actors; port of XState 5.33.2; implemented in 0.1.0)

webcpp::xstate runs the JSON configs of XState's `createMachine` in C++20, in
two layers: a machine core, `<webcpp/xstate.hpp>`, that steps a machine by
XState's pure functions or one microstep at a time with a macrostep cursor,
and an actor layer, `<webcpp/xstate/actors.hpp>`, that runs machines as
XState's actors on webcpp::xactor. It is the model port of webcpp's oracle and
twins, and its appendix "Where xstate differs from XState" lists each of its
departures, every one of which is a decision below.

**Scope.**

- **xstate ports XState 5.33.2's algorithm function by function, and each
  ported function names in its Doc Comment the TypeScript function it ports.**
  A difference from XState then points at one function on each side; xstate
  has no semantics of its own.
  Source: `doc/introduction/overview.adoc` (libs/xstate).
- **The original is pinned exactly, the npm package `xstate` at 5.33.2 with
  its lockfile, and moving to another version of XState is a change of its
  own.** The machine semantics, the order of actions and microsteps, and the
  errors follow that version, and the oracle's new expected results are the
  evidence for a move.
  Source: `AGENTS.md` (libs/xstate).
- **0.1.0 leaves out what a JSON config and a single-threaded, queued actor
  system cannot or did not yet carry: `enqueueActions`, callback and
  observable actors, `fromTransition`, the persistence of actors, `toPromise`
  and `waitFor`, `syncSnapshot`, `spawn` inside `assign`, `machine.provide()`,
  `options.maxIterations`, `xstate/graph` and the SCXML converter.** What is
  not ported is a gap, not a divergence, so the overview lists it rather than
  the appendix of differences; a stored snapshot comes back through
  `resolve_state`, a second `create_machine` with other implementations stands
  for `provide`, and a test walks a machine with `get_next_transitions` and
  `get_next_snapshot`.
  Source:
  `libraries/xstate/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **Two gaps let a config load and then run otherwise than in XState, and the
  appendix names them: an invoke's `onSnapshot` loads as transitions on
  `xstate.snapshot.<id>` that no child's snapshot ever takes, and an
  `xstate.init` or `xstate.stop` sent from outside selects transitions as any
  other event does.** XState's `syncSnapshot` is not ported, and its
  macrostep's special handling of those two events is not followed yet;
  whether `onSnapshot` should rather be refused at creation is an open
  question.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **Compile-time state machines are left to libraries such as Boost.MSM, run
  as xactor actors; xstate interprets machines that are data.** Those
  libraries already do it well and a third inside xstate would duplicate them,
  and xactor needs no adapter, since an actor logic is any class with a
  `handle`.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).

**Machines as data.**

- **A machine is a `boost::json::value` in XState's config format, read when
  the program runs.** It can come from a file, a request or Stately Studio's
  export, and XState can run the same config, which is what lets XState judge
  the port; a machine described in C++, by a builder or a table of types, was
  rejected because it cannot come from a file or from Stately Studio and
  XState cannot run it.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).
- **Every value a machine holds (its config, context, an event's payload, an
  action's `params`, a state value, an input and an output) is a Boost.JSON
  value.** Boost.JSON's `object` keeps its members in the order they were
  written, which the key-order rules need; its limits (a hashed index, numbers
  as doubles, a value that holds pointers) are accepted for 0.1.0, and a
  document type of webcpp's own is the owner's direction for a later change.
  Source:
  `libraries/xstate/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **What JSON cannot hold is C++ registered by name in `implementations`, as
  XState's `setup()` registers it, in seven members: `context`, `actions`,
  `actors`, `guards`, `delays`, `inputs` and `outputs`.** A name is the bridge
  between the data and the code, and XState already joins them by name, so a
  config written with `setup()` keeps its shape in xstate.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).
- **An action name the implementations do not hold is a custom action,
  returned as `{type, params}` with `builtin` false, for the caller to
  perform; it is not an error.** What a machine does to the world belongs to
  the program that runs it: the machine says what is to be done, and the
  program decides how.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).
- **An implementation receives an `action_args` (the context, the event and
  the params) and returns a `result`; it receives no actor and no system,
  where XState's does.** A context is JSON and holds no actor, and an effect
  that needs one is a custom action, which the host performs, or an
  `emit_action`; the cost is that a custom action carries its fixed `params`
  alone.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **Where XState's config holds a function, xstate's holds another form:
  `params` are fixed JSON, an invoke's `src` is the string name of an `actors`
  entry (any other `src` is `invalid_config`), and the context function
  receives the input only.** A function cannot be JSON, logic cannot be JSON,
  and a reference to an actor is not data.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **XState's higher-order guards are JSON objects of xstate's own, `{"type":
  "xstate.not", "guards": [...]}` (and `xstate.and`, `xstate.or`) and
  `{"type": "xstate.stateIn", "stateValue": ...}`, which `to_json` writes.**
  JSON holds no function and XState has no JSON for them; writing them lets a
  machine loaded back from its definition keep them.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **A `sendTo` target is a string (a child's id, `#_<id>`, `#_parent`,
  `#_internal` or `#system:<systemId>`), and an event or an input carries no
  actor reference.** JSON holds neither a reference nor a function; a child
  answers its parent through `#_parent`, and any other actor is named by its
  id or its systemId.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **JavaScript's `undefined` is an empty `std::optional`: a `value_maker`
  returns `result<std::optional<boost::json::value>>`, a member computed as
  none is left out, and a null input is the same as no input.** JSON has
  `null` only, and a member left out is how XState itself writes `undefined`.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **An event is `struct event { std::string type; boost::json::object payload;
  }`, read from and written to XState's flat form by `event_from_json` and
  `to_json`.** Transitions match the type, and the payload is data for the
  implementations.
  Source: `doc/state-machines/transitions.adoc` (libs/xstate).
- **`create_machine` checks all it can when the machine is created, and
  refuses configs XState accepts and fails on later: an `initial` that names
  no child, a guard or a named `after` delay without an implementation, a
  default entry that leads back to its state, a null `entry`, `exit` or
  `actions`, an unknown actor, a malformed history target or `tags`.** The
  moment a machine is loaded is the moment its author can be told what is
  wrong with it, not when an event reaches the broken part, long after and
  perhaps in production.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **Two things are checked only when they are used, as in XState: the `#id` of
  a `stateIn` guard, which fails the macrostep with `unknown_state`, and the
  default of a history state at the root, which fails it with
  `unknown_target`.** XState accepts both configs, and a history at the root
  has no parent to resolve its default against.
  Source: `libraries/xstate/openspec/specs/xstate/spec.md` (proposals).
- **Implementations that hold an empty `std::function` refuse the machine with
  `invalid_config`.** Calling one would abort in a build without exceptions.
  Source: `include/webcpp/xstate/implementations.hpp` (libs/xstate).
- **A `machine` is a handle to immutable data shared by every copy,
  `std::shared_ptr<const detail::machine_data>`, with no default constructor
  and no `provide`.** A copy is cheap, so a cursor, an actor and a
  `machine_actor` each keep one; a program that runs a config with other
  implementations creates a second machine from it with the first's
  `registry()` changed.
  Source: `include/webcpp/xstate/machine.hpp` (libs/xstate).
- **A `machine_actor` holds its machine through a `std::shared_ptr<const
  machine>`.** A machine holds its implementations, which may hold this actor.
  Source: `include/webcpp/xstate/implementations.hpp` (libs/xstate).
- **A machine's nodes are one list in document order, named by index; its
  guards are one flat list, a higher-order guard naming its operands by index;
  and every recursion of the core is an explicit list or stack.** The tree
  holds no pointer and copies as a value, and a machine as deep as its JSON
  never exhausts the stack.
  Source:
  `libraries/xstate/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **`to_json` writes the definition XState's `machine.toJSON()` writes, and
  `create_machine_from_definition` loads one back, given the implementations
  and the context.** A definition holds names, not code, and no context, so
  both are given again; a machine written so becomes data that can be stored
  and loaded.
  Source: `libraries/xstate/openspec/specs/xstate/spec.md` (proposals).

**Fidelity to JavaScript.**

- **Where XState's observable behaviour is a property of JavaScript, xstate
  states it as a rule; the first is that object keys are enumerated array
  indices first, by number, then in insertion order, for `states`, `on`,
  `after`, state values and `children`.** A port must reproduce it to match
  the oracle: it decides the document order, the order of a state's
  transitions and the order of the raises an `after` schedules.
  Source:
  `libraries/xstate/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **The active nodes are an insertion-ordered set, `node_set`, and a microstep
  that leaves the machine done lists them by descending `order`.** XState
  sorts its array of active nodes in place when the machine is done, and the
  order decides which eventless transition a parallel region takes first.
  Source: `doc/guarantees.adoc` (libs/xstate).
- **XState's comparison of snapshots by identity is stated as "changed": after
  an eventless microstep, the eventless transitions are selected again only
  when the active nodes, the history, the context, the children or the status
  changed.** That is what XState's loop does, which selects them again when a
  microstep returned another snapshot than the one it began from.
  Source: `doc/guarantees.adoc` (libs/xstate).
- **Timers of equal deadline fire by (deadline, scheduling order), in the
  core's `simulated_clock` and in the actor layer's `clock_tick`, and the
  latest timer armed under an id is the one a cancel finds.** XState's order
  comes from V8's sort with a comparator that never returns 0; xstate states
  the result instead of leaving it to a sort.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **A snapshot's status is `active`, `done` or `error`, without XState's
  `stopped`; `actor_system::status_of` tells that an actor stopped.** xstate
  runs `xstate.stop` as any other event, where XState gives `stopped` to a
  snapshot that receives it.
  Source: `include/webcpp/xstate/snapshot.hpp` (libs/xstate).
- **A config's context that is not an object is kept as written, and an
  `assign` on it fails with `implementation_failed`; a null or absent context
  is `{}`.** Truthiness and the spreading of a string are properties of
  JavaScript, a JSON machine whose context is not an object has a fault,
  reported where it shows, and `null` is how JSON writes no value.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **A state's `meta` that is null is no meta, and a state's `description` that
  is not a string is left out.** A `null` stands for no value, and a
  description is text, as XState's own type declarations make it.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **A child spawned without an id is keyed `""`, where XState keys it
  `"undefined"`, and a `stop_child_action` of `""` removes it.** A C++ string
  has no undefined: an id left out holds the empty string, a key a stop can
  name.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **The core returns a `sendParent` as `xstate.sendTo` to `#_parent` even for
  a machine without a parent, where XState's pure functions throw; the actor
  layer fails a root that sends to its parent with `unknown_target`.** Whether
  a machine has a parent depends on where it runs, not on the machine, and the
  pure functions describe the machine.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **xstate makes, in every build, the three checks of XState's development
  build that a JSON machine can meet (an external event of the type `*`, a
  truthy `cond`, a `forwardTo` to no actor), and writes no warning.** Each
  check stops an error that the production build lets through to do something
  worse, and xstate writes to no stream: what it has to tell its caller comes
  back as a value.
  Source: `doc/appendices/differences.adoc` (libs/xstate).

**Errors.**

- **`errc` has ten values, from `invalid_config` (1) to `system_id_taken`
  (10), and no `invalid_argument`: the actor layer refuses a call it cannot
  take with xactor's `invalid_argument`, and `system_id_taken` is its one
  refusal of its own.** The values start at 1 so that the empty `error_code`
  of a snapshot that has not failed is no error, and the actor layer refuses a
  call as xactor would.
  Source: `include/webcpp/xstate/errors.hpp` (libs/xstate).
- **The category's `message(int)` is the enumerator's spelling,
  `"implementation_failed"`, and `"unknown"` for any other value; a failed
  machine child sends its parent its `error_value` when an unhandled error
  event failed it, else that name, and its snapshot keeps both the code and
  the reported error.** An `error_code` carries no value of its own, where
  XState's implementation may throw any value, so the code's name is the JSON
  that says which failure it was, and a grandchild's error climbs unchanged.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **A failure settles the macrostep at once with the snapshot it began from,
  its `status` `error` and its `error` the code, in the pure functions as in
  an actor; the failing microstep reports no action, and
  `progress::resolved_before_failure` holds what it resolved before the
  failure.** That snapshot is the one XState's actor keeps when an
  implementation throws, a failure in it cannot pass unseen, and a cursor's
  caller learns what a running actor of XState has already run.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **An implementation may fail with any `error_code`, which becomes the
  snapshot's `error` as it is.** A program tells its own failures apart, and a
  code carries its category, so the code of another library's call travels
  unchanged.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).

**The cursor and time.**

- **The macrostep cursor is the core's one primitive: `begin` and
  `begin_initial` return a `macrostep` whose `next()` runs exactly one
  microstep, `settled` is true on the closing microstep and no other, and
  XState's pure functions are the cursor run to its end.** A program that runs
  machines it did not write cannot know that each one settles, so the caller
  decides how much work an event may cost; the unit is XState's microstep, so
  a run stops only between two of its steps.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).
- **A cursor is a value, holding a copy of its machine handle, its snapshots
  and its queue, so a copy resumes exactly where the original stopped.**
  Stopping keeps the work: a caller that runs out of fuel keeps the cursor and
  resumes it later, perhaps in a later request.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).
- **The core never stops a macrostep on its own, and XState's
  `options.maxIterations` is not read.** A bound written in the config is its
  author's, unset by default, and ends the macrostep with a thrown error; the
  bound belongs to the program that runs the machine.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **The core reads no clock: a delayed transition comes back as a built-in
  `xstate.raise` with a delay, for a clock its caller owns.** Time is an
  input, so a delayed transition is tested without waiting, and the program
  decides what time is.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).
- **The core's `simulated_clock` holds events, not functions: `apply`
  schedules the built-in delayed raises and applies the cancels, `pop_due()`
  hands the caller each due event, and `set` refuses a time before `now()`
  with `invalid_config`.** A clock that called a function would run the
  machine from inside the clock's call; one that hands over each due event
  lets the caller apply what its delivery returns before it takes the next,
  and a refusal is a value.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **Time is whole milliseconds and a delay a `std::uint64_t`; an `after` key
  is a number only when it is digits alone, and any other key that starts with
  a digit, a sign or a dot is `invalid_config`, even when a delay of that name
  is registered.** xactor's timers count whole milliseconds, which keeps every
  deadline an exact integer; a fraction has no timer to hold it, and a
  negative delay has no meaning.
  Source: `doc/appendices/differences.adoc` (libs/xstate).

**The actor layer.**

- **The library has two layers behind two convenience headers: the machine
  core knows XState's actors as data and resolves an invoke or a spawn into
  `xstate.spawnChild` and `xstate.stopChild` actions, and the actor layer,
  whose header includes the core's, executes them.** XState splits `resolve`
  from `execute` at the same place, and a program that only steps machines
  needs no scheduler and includes nothing of xactor or Boost.Asio.
  Source: `doc/introduction/overview.adoc` (libs/xstate).
- **The boundary is mechanical: `meta/include-boundaries.json` forbids the
  core's headers to include `webcpp/xactor` or `webcpp/xstate/actors`, which
  the lint enforces by file and line, and `test/core_alone.cpp` fails on any
  of their include guards.** The core stays usable by a program that does not
  want a scheduler.
  Source:
  `libraries/xstate/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **The actor layer runs on xactor rather than on an actor system of its own:
  each machine actor is an xactor actor whose logic drives the cursor, and the
  layer adds a child's done and error events, invoke, the systemId registry,
  emitted events and inspection.** A second system would duplicate xactor's
  scheduler, timers and fuel, and a machine's actor inherits xactor's
  determinism and bound on work.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).
- **A delivery between actors is queued, never nested in the sender's call, so
  the order across actors can differ from XState's, never within one actor.**
  Queues make a run deterministic and replayable, keep one actor's work from
  nesting inside another's, and let fuel bound each turn.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **Every microstep, every message an actor sends and every timer it arms
  costs one unit of the execution's one reservoir of fuel; an actor that
  cannot pay parks, and `resume()` continues it.** A machine loaded at run
  time cannot hang the host, and one reservoir for each execution bounds a
  fan-out, whose every branch would start with almost the whole budget under a
  count for each message.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).
- **While an actor is parked, the host's `start`, `send`, `clock_tick`,
  `resolve` and `reject` are checked, held in order and applied by `resume()`;
  `stop` is never held.** No event starts before the macrostep in progress has
  settled, and `stop` is how the host ends an actor that would never settle.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **`create_actor` runs nothing: the root is constructed, its initial
  macrostep run, on `start`.** Construction runs a macrostep, which costs
  fuel, and fuel is paid inside an execution, which only a host call that
  delivers something opens.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **The roots of one `actor_system` share one system, its systemIds and its
  count of session ids `x:<n>`, where XState gives each root a system of its
  own.** An `actor_system` owns one xactor scheduler, with its registry and
  its counter, and nothing of it is global; a program that wants XState's
  arrangement gives each root an `actor_system` of its own.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **`actor_system` is neither copyable nor movable, and one thread runs it.**
  Every actor holds a reference to the system's shared state.
  Source: `include/webcpp/xstate/actors/actor_system.hpp` (libs/xstate).
- **`clock_tick` accepts a time earlier than the last one and moves the time
  back, where the core's `simulated_clock` and XState refuse it.** The actor
  layer's timers are xactor's and keep xactor's rule; the core's clock ports
  XState's `SimulatedClock` and keeps its refusal.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **The host's callbacks run inside an actor's turn, and a call from one of
  them that changes the system returns xactor's `invalid_argument` and changes
  nothing; the `const` readers are free.** A call made inside a run cannot
  know that run's outcome, and running the system again from inside a turn
  would nest one run in another, where xactor runs one turn at a time.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **A `host_actor` stands for `fromPromise`: once started it is a pending
  `host_request`, which the host answers with `resolve` or `reject` when it
  chooses.** The host does the work a promise would do, and a test is the host
  and has nothing to wait for.
  Source:
  `libraries/xstate/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).
- **Effects cross between the system and the host as data alone: custom
  actions reach the one `on_action` callback, logs the one `on_log` callback,
  emitted events their actor's `on_emitted` listeners, and snapshots its
  subscribers.** The host owns the effects, and nothing else crosses.
  Source: `doc/actors/actors.adoc` (libs/xstate).
- **`on_emitted` adds one kind of listener, which hears every event the actor
  emits in the order the listeners were added, an event of the type `*`
  once.** One kind of listener, heard in the order the program added it, is
  the whole rule, a type is one test inside it, and hearing an event twice, as
  XState's lookup makes a listener do, is a defect.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **The layer does not reproduce four of XState's accidents: it stops the
  unstarted children of a failing macrostep, drops every timer of an actor
  that ended, fires a timer that falls due during a `clock_tick` in the same
  call, and stops a root's whole family, a failed member's children
  included.** A child never started and never stopped would hold its systemId
  for good, an actor that has ended sends nothing, whether a due timer fires
  cannot depend on how many timers a flush had left to visit, and a stop that
  leaves actors running does not end the family.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **A `sendTo` that names an invoke of the state being entered carries
  `action::bound_at`, and the actor fails with `unknown_target` when no child
  has that id where XState binds it, where XState relays the event to
  `undefined` and throws a `TypeError`.** A send to an actor that is not there
  is an error of the machine, reported with the code of every other target
  that names no actor.
  Source: `doc/appendices/differences.adoc` (libs/xstate).
- **`actor_message` is a `std::variant` of nine alternatives in a fixed
  order.** xactor names an alternative in its log by its index, so the order
  is part of a recorded run.
  Source: `include/webcpp/xstate/actors/message.hpp` (libs/xstate).

**Build and targets.**

- **xstate is header-only, and the one part a program compiles is Boost.JSON's
  definitions, once, in a translation unit that includes
  `<boost/json/src.hpp>` (webcpp's `/webcpp//boost_json`).** The same headers
  build with every C++20 compiler and for WebAssembly with no binary to match,
  a build's flags (no exceptions, a sanitizer) are the library's, and xactor's
  scheduler and logic are templates in any case.
  Source: `doc/appendices/rationale.adoc` (libs/xstate).
- **The one b2 alias, `/webcpp/xstate//xstate`, brings xactor to every user,
  so a program of the machine core depends on xactor in name only.**
  (reason not recorded)
  Source: `libraries/xstate/openspec/specs/xstate/spec.md` (proposals).
- **The tests and examples are declared for native, wasip2 and wasip3;
  Emscripten is not a target of 0.1.0.** (reason not recorded)
  Source: `libraries/xstate/openspec/specs/xstate/spec.md` (proposals).
- **The code is under the Boost Software License alone, and what derives from
  XState (the ported semantics, the transcribed test cases, the twins and the
  shared examples) keeps XState's MIT notice, unchanged, in
  `LICENSE-XSTATE.txt`.** The derived parts carry their original's notice,
  which adds no licence to xstate's own code.
  Source:
  `libraries/xstate/openspec/changes/archive/2026-10-07-genesis/design.md`
  (proposals).

**Evidence.**

- **The oracle runs XState's development build only, `node
  --conditions=development`, and `test/oracle/development.mjs` refuses any
  other by checking that an event of the type `*` throws.** XState's own tests
  run that build, and xstate makes the checks it makes.
  Source: `test/oracle/development.mjs` (libs/xstate).
- **`oracle.mjs` runs each machine case's macrosteps after the initial one
  through `machine.transition` with an actor scope of its own whose actor has
  a parent, takes the initial microsteps from `getInitialMicrosteps`, and
  delivers delayed events from XState's `SimulatedClock`.** XState's pure
  functions cannot serve: their actor has no parent and throws on
  `sendParent`, and XState's inspection does not report the first initial
  microstep.
  Source: `doc/testing.adoc` (libs/xstate).
- **`actors.mjs` writes, for every actor keyed by its path of ids and a rank
  (`root/n#2`), the events it processed with each snapshot, the events it
  emitted and its status, never the order between two actors.** xactor's
  queues may change that order, while no nesting of deliveries changes the
  keys.
  Source: `doc/testing.adoc` (libs/xstate).
- **XState's tests are ported as JSON cases, one file per XState test file,
  each listing every test it leaves out under `excluded` with its reason;
  files of xstate's own pin what XState does where its tests are silent, and
  the implementations a case names come from a vocabulary written twice, in
  `test/oracle/vocabulary.mjs` and `test/vocabulary.hpp`.** A test that cannot
  be ported is never dropped in silence.
  Source: `doc/testing.adoc` (libs/xstate).
- **The suite `cases` runs each macrostep through the cursor, one microstep a
  call and at most 10,000, and compares every microstep with XState's, then
  the definition, then, where the definition holds the whole machine, the
  machine loaded back from it.** It runs a machine as a caller that pays fuel
  runs one.
  Source: `doc/testing.adoc` (libs/xstate).
- **The two case suites are Boost.Test programs built natively only, and every
  other test is a lightweight_test program run on native, wasip2 and wasip3.**
  The suites read the fixture files at run time, which a wasm program cannot
  without a directory its runtime opens, and register one test case per case
  so that a failure names it; a lightweight_test program runs as it is in a
  build without exceptions.
  Source: `doc/testing.adoc` (libs/xstate).
- **Every example has a twin on XState that agrees or diverges on purpose, 114
  and 22 of the 146, or a line in `without-twin.txt`, 10: the cursor, fuel, a
  machine reloaded from its definition, an event read from JSON and the
  registry of inputs and outputs.** The twins hold the page to XState, and
  what XState has no counterpart for cannot have a twin.
  Source: `test/oracle/twins/without-twin.txt` (libs/xstate).
- **The twins of the testing chapter are tests of Node's own runner,
  `node:test` with `node:assert`, where Stately's page uses Vitest.** So that
  each runs on Node alone.
  Source: `doc/testing.adoc` (libs/xstate).
- **The five actor test programs and `actors_cases` are built with `/bigobj`
  on MSVC, a decision made from section counts taken with Clang 18 and GCC
  14.** Their objects stay near the COFF limit of 65,279 sections that the old
  suite needed `/bigobj` for, and MSVC was not available to measure them.
  Source: `test/CONVERSION.md` (libs/xstate).
- **The actor layer's 73 test cases are split by responsibility into five
  programs, `actors_lifecycle`, `actors_sending`, `actors_children`,
  `actors_time` and `actors_host`, each case in exactly one.**
  (reason not recorded)
  Source: `test/CONVERSION.md` (libs/xstate).

**Documentation.**

- **The page's guarantees are numbered, 1 to 24 for the core and A1 to A12 for
  the actor layer, each under an anchor that code and tests cite as `(doc:
  #xstate-invariant-13)`; the doc build fails on a citation that names no
  anchor.** A guarantee keeps its number so that a comment can cite it, and a
  citation of nothing is caught.
  Source: `doc/guarantees.adoc` (libs/xstate).
- **A Doc Comment that names xactor's API names it in full,
  `webcpp::xactor::scheduler`, and the page links xactor's page where the
  layer leans on it.** MrDocs cannot link into another library's reference.
  Source: `libraries/xstate/openspec/specs/xstate/spec.md` (proposals).

### pratt (Pratt parser engine with a calculator; own; implemented in 0.1.0)

webcpp::pratt is a header-only engine for Pratt parsing (top-down operator
precedence) that knows no token, operator, tree or number type, with a
calculator, `calc`, built on it that computes exactly in decimal by default.
It was designed from an owner's draft with a verified reference
implementation, is the model of a library whose engine and user-facing
component are kept apart, and seeds a future parser of openui-lang.

**Scope and layers.**

- **pratt is a library of webcpp's own (`"port-of": null`): it has no oracle,
  no twins and no appendix of differences, and its page, with the Doc Comments
  of its headers, is what a change is checked against.** It ports nothing, so
  there is no original to judge it.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The engine is the Pratt loop and nothing else: not a parser generator, a
  grammar DSL, a lexer toolkit or an AST; it builds whatever node the grammar
  says and does nothing else with it.** Pratt parsing turns precedence and
  associativity into numbers and a new operator into a new answer to one
  question, where a hand-written recursive-descent parser spreads them over
  one function per level.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/proposal.md`
  (proposals).
- **The engine and the calculator are one library kept apart by an include
  boundary: the engine's headers, `pratt.hpp`, `errors.hpp` and `parser.hpp`,
  may not include `webcpp/pratt/calculator` or `boost/decimal`, and the
  convenience header `<webcpp/pratt.hpp>` includes the engine only.** The
  engine knows no grammar and no number type, and a program of the engine
  alone never reads Boost.Decimal, a heavy dependency; the calculator is
  included by its own name.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).

**Interface.**

- **A token stream models the concept `token_stream` (`token_type`, `peek()
  const`, `advance()`, `at_end() const`) and a grammar models `grammar_for<G,
  S>` (`node_type`, `lbp(t)`, `nud(p, t)`, `led(p, t, left)`), with no base
  class, no virtual function, no `std::function` and no type erasure between
  them and the engine.** A base class of tokens and nodes, the alternative
  rejected, would make every program pay for a hierarchy and fix the node
  type; with concepts a grammar that consults run-time tables stays possible.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **`parser<Grammar, Stream>` holds a pointer to the grammar, the stream by
  value and two integers, and its constructor from a `const Grammar&&` is
  deleted; `parse` takes the grammar by `const&` and accepts a temporary.** A
  temporary grammar would leave the parser's pointer dangling, while the
  parser that `parse` builds lives only for the call.
  Source: `doc/grammar.adoc` (libs/pratt).
- **`parse` parses `expression(0)` and returns `trailing_input` when tokens
  remain; a program may build the `parser` itself.** Building it lets a
  program call `expression` with another power, or go on reading the stream
  after one expression.
  Source: `doc/grammar.adoc` (libs/pratt).
- **The six helpers, `literal`, `prefix`, `infix_left`, `infix_right`,
  `postfix` and `grouping`, each parse their operands through `expression`
  alone and call a `make` of the grammar's that builds the node; `infix_right`
  parses its right operand with `bp - 1`.** Every helper recursing through
  `expression` alone, a grammar written with them routes every token through
  its nud and its led and is bounded whole by the depth limit; `bp - 1` is the
  canonical Pratt way to make an operator of equal power on the right take the
  operand.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The parser offers `peek()` and `advance()` to a nud or a led.** A nud or a
  led that reads past its own token needs them, such as the argument loop of a
  call.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).

**Errors.**

- **One enumeration, `pratt::error`, in the engine's header, holds the draft's
  seven errors and two more, `nesting_too_deep` (8) and `division_by_zero`
  (9), values 1 to 9, fixed and never reused; the engine produces three of
  them, and the others are there for a grammar to use.** A value stored or
  sent keeps its meaning from one version to the next, 0 is no error, and the
  calculator and the micro-subset report their own failures with them.
  Source: `doc/errors.adoc` (libs/pratt).
- **The category follows xactor's form, not the draft's function-local static:
  a `constexpr` object with the fixed identity `0x7072617474000000` (the ASCII
  of "pratt" and three zero bytes), the name `webcpp.pratt`, prose messages
  ("expression nested too deeply"), "unknown webcpp.pratt error" for any other
  value, and both `message` forms.** A category constructed `constexpr` with a
  fixed identity holds no mutable state.
  Source: `libraries/pratt/openspec/specs/pratt/spec.md` (proposals).
- **The engine and the calculator build an error into a `result` in place,
  `{boost::system::in_place_error, error::...}`.** A node type may convert
  from an error too, as a Boost.Multiprecision number does, and `result` then
  refuses the implicit conversion as ambiguous.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **An error of another category that a grammar or an environment returns is
  passed on unchanged; the engine never reads it.** An environment can refuse
  with an error of its own, such as a fixed storage that is full.
  Source: `doc/errors.adoc` (libs/pratt).

**Limits.**

- **The parser counts its active `expression` calls with an RAII guard and
  refuses the call that would exceed `max_depth` with `nesting_too_deep`,
  before it reads a token; a negative limit behaves as 0, and the limit is a
  constructor argument that `parse` and `calc::evaluate` forward.** Pratt
  recursion costs stack for each nesting level, so ten thousand `(` would
  overflow a stack, a crash rather than an error, and wasm's default stack is
  64 KiB.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **`default_max_depth` is 64, measured rather than chosen: the largest power
  of two at most half of the deepest parse that wasm's default 64 KiB stack
  holds in a debug build, in the costliest shape of the calculator's grammar
  and of openui-lang's (203 calls; half is 101).** A parse at the default
  depth then uses at most half the stack in the worst shape and the slowest
  build, on every target pratt is tested on.
  Source: `doc/limits.adoc` (libs/pratt).
- **The measurement is a table above the constant in `parser.hpp`, repeated
  verbatim in the "Limits" chapter, and `depth_test` is its canary: twice the
  default must still fit.** The canary fails on wasm, as a trap, the day the
  margin is gone, and the table, the value and the chapter then move together.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The limit bounds the recursion through `expression` alone: a nud or a led
  that recurses through functions of its own bounds that recursion itself.**
  The limit counts `expression` calls only, which is the whole recursion of a
  grammar whose operands all go through `expression` or the helpers.
  Source: `doc/limits.adoc` (libs/pratt).

**The calculator.**

- **The calculator is a grammar written with the engine's helpers alone and
  adds no parsing of its own.** Everything goes through the engine, which
  stays the only place that decides.
  Source: `doc/calculator.adoc` (libs/pratt).
- **Its lexer, `calc::stream`, is lazy: it holds the source, a position and
  one token of lookahead, and no vector of tokens exists.** Lexing everything
  first, the alternative rejected, would find an invalid character before any
  other error and allocate a token vector.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **A character that starts no token is a token of kind `invalid`, one
  character long, whose lbp is `std::numeric_limits<int>::max()` and whose nud
  and led return `invalid_character`.** The engine reaches it wherever it
  stands, so `1 $ 2` is `invalid_character` rather than `trailing_input`, and
  the engine stays the only place that decides.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The first error in reading order is the one returned, and a write made
  before it stays made; nothing is undone.** Undoing the writes of a failed
  evaluation is a non-goal: a caller that needs all or nothing evaluates in a
  copy of the environment and keeps it on success.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The calculator computes in any type that models `calc::number`: copyable,
  constructible from `int`, `+ - * /`, unary `-`, the six comparisons, and
  `pow`, `fmod` and `trunc` found by ADL after `using std::pow;` (the two-step
  call), each returning exactly the type; every `calc` template is constrained
  by it.** The calculator never computes through another type,
  `boost::decimal`'s overloads serve its types and `std::`'s the builtin
  floating-point ones; so `int` does not model it, nor a type with expression
  templates.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The default number type is `boost::decimal::decimal64_t`.** A decimal
  fraction written in the input is then exactly that number: `0.1 + 0.2 ==
  0.3` holds.
  Source: `doc/calculator.adoc` (libs/pratt).
- **The lexer builds a literal in the number type's own arithmetic, never
  through `double`: its first `digits10 + 1` significant digits (or
  `max_digits10`) make one integer mantissa, divided once by ten to the number
  of fraction digits; in a binary type a scaled-up mantissa is computed to
  twice the precision with Dekker's split and product.** A decimal fraction is
  exact in a decimal type and the nearest value in `double`, where a division
  by ten per digit misses `1.005` and `0.07` by one unit in the last place,
  and the largest `double` written out in full stays finite.
  Source: `libraries/pratt/openspec/specs/pratt/spec.md` (proposals).
- **Every multiplication and addition of the lexer, of the twofold product and
  of the power is a statement of its own.** No compiler then contracts them
  into a fused multiply-add, which would round differently on each target; a
  build with `-ffp-contract=fast` or `-ffast-math` may still change a `double`
  in its last place, which the page says.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **An integral exponent is computed by repeated squaring in the number type;
  `pow` is called only for a non-integral exponent, or a negative one whose
  positive power is out of range.** Every product is exact while it fits the
  precision, and the result is the same bits on every platform, where a
  library's `pow` may round differently; the price, documented, is that past
  the precision the relative error grows with the exponent.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **An integer whose successor rounds back to it counts as even when the power
  takes its sign.** Boost.Decimal's `fmod` is inexact past the precision, and
  such an integer is a multiple of its radix.
  Source: `include/webcpp/pratt/calculator.hpp` (libs/pratt).
- **`/` and `%` by zero, and `0 ^ -n`, return `division_by_zero`.** A
  floating-point type would answer an infinity or a NaN that the next line
  computes on; the calculator stops at the line that asked.
  Source: `doc/calculator.adoc` (libs/pratt).
- **The calculator's language, kept from the owner's draft, is numbers,
  variables and C's arithmetic and comparison operators with `^` for the
  power: `=` 10 (right), comparisons 20 giving 1 or 0, `+ -` 30, `* / %` 40
  (the remainder taking the left operand's sign), a unary sign 45, so that `-2
  ^ 2` is -4, `^` 50 (right), and `++ --` as in C, on variables only, 70 after
  an operand.** (reason not recorded)
  Source: `doc/calculator.adoc` (libs/pratt).
- **A node is a value, a `has_value` flag and, for a bare variable, its name
  as a view; a grouping keeps the name, a name the environment does not hold
  is an error only where it is read, and `=` checks its target before it reads
  its right operand.** The name is what `=`, `++` and `--` write, so `(a) = 1`
  writes `a`, and `a = 5` defines a name the environment does not hold yet.
  Source: `doc/calculator.adoc` (libs/pratt).
- **Where the variables live is a concept, `environment_for`: `number_type`,
  `lookup(std::string_view) const` returning `const number_type*`, and
  `assign(std::string_view, number_type)` returning `result<void>`.** An
  environment can refuse a write, a fixed storage that is full, with an error
  of its own category, which the calculator returns unchanged; the number type
  follows the environment.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **`calc::environment<Number, Allocator>` is a `std::map` with `std::less<>`
  whose nodes and keys allocate through `Allocator` rebound, its key a class
  of its own around a `std::basic_string`.** A lookup by `std::string_view`
  builds no key, an allocator written for any type serves, and a class key
  avoids libstdc++'s `std::pair` making clang instantiate a default argument
  that is a hard error for an allocator without a default constructor.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **`calc::environment::assign` always returns success, and a failure to
  allocate is the allocator's.** As in any standard container.
  Source: `include/webcpp/pratt/calculator.hpp` (libs/pratt).

**Memory.**

- **The engine allocates nothing, the calculator's parse allocates nothing
  (its tokens and nodes are views and numbers), and only an environment that
  stores names allocates, through the user's allocator.** pratt is born with
  webcpp's allocation rule: avoid allocation as far as the job allows, and let
  the user choose the allocator of what is allocated.
  Source: `doc/allocation.adoc` (libs/pratt).
- **`allocation_test` replaces the global `operator new`, over-aligned forms
  included, for its own program and counts zero calls over a fixed-storage
  environment and only the allocator's own over `calc::environment`; a test or
  example compares what a step adds and never states how many allocations a
  standard library makes.** MSVC's map allocates when it is built, and a debug
  build adds proxies, so totals differ between standard libraries.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).

**Targets and exceptions.**

- **The tests and examples are declared for native, Emscripten, wasip2 and
  wasip3, each proven by a lane; Emscripten joined once the superproject had
  its lane.** Every target pratt declares is proven by a lane, so Emscripten
  waited for the superproject's.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **No header contains `throw`, `try` or `catch`, and
  `WEBCPP_PRATT_NO_EXCEPTIONS` changes nothing in pratt.** The same headers
  serve a build with exceptions and one without, and the macro exists so that
  a program can set it for every webcpp library alike.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).

**Evidence.**

- **Three grammars prove the engine generic: the engine test's `table`
  (binding powers from a table, tokens `char`, nodes `std::string`), the
  draft's `sexpr`, and the openui-lang micro-subset of the examples.** Each
  has token and node types of its own and reaches the engine unchanged.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The openui-lang micro-subset gives `(` both of Pratt's denotations, a
  grouping as nud and a call of power 90 as led, whose argument loop reads
  `expression(0)`, `peek` and `advance` inside the led; its node is a
  `std::string`.** It proves that the engine parses calls, named arguments and
  assignments with no recursive descent around it; the string is the examples'
  output format, and the parser of openui-lang to come defines a tree of its
  own.
  Source: `doc/openui.adoc` (libs/pratt).
- **The two REPLs share one line loop and run as examples fed an `.input`
  file, an extension made to the superproject's `webcpp.example`, and
  `.gitattributes` keeps `*.input` byte for byte.** A REPL needs standard
  input to be tested as an example, and an input holds lines that end in
  `\r\n` on purpose.
  Source:
  `libraries/pratt/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The language is named openui-lang, alone, in every file and commit.**
  (reason not recorded)
  Source: `AGENTS.md` (libs/pratt).

**Documentation.**

- **Each `@see "<title>"` of a Doc Comment names a top-level chapter of the
  page, which doc-check enforces.** Renaming a chapter then renames its `@see`
  lines in the same commit, or the doc build fails.
  Source: `AGENTS.md` (libs/pratt).

### wasi (the HTTP handler a WebAssembly component exports, wasip2 and wasip3; own; implemented in 0.1.0)

`webcpp::wasi::http` exports the `wasi:http` handler of a component on
wasip2 (WASI 0.2.12) and wasip3 (WASI 0.3.0): a program writes one function
that turns a request's method and target into a response, and wasi reads the
request, calls it and writes the answer. It was moved into webcpp on
2026-10-08 from an earlier private project; its redesign, accepted and not
built, is recorded apart.

**Scope.**

- **One header serves both versions of WASI, its two handlers chosen by
  `WEBCPP_WASI_HTTP_P2` or `WEBCPP_WASI_HTTP_P3`, and a program's main is
  the same on both.** One header per version was rejected: a program would
  have to choose between them.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The handler hands the main the method and the target alone, and sends a
  status, a `content-type` header and a body: no request header, no request
  body, no other response header, no trailers, no streamed body.** (reason
  not recorded) The genesis lists each as a non-goal, a change of its own.
  Source: `doc/limits.adoc` (libs/wasi).
- **The handler parses, decodes and routes nothing: the target reaches the
  main as it was sent.** Routing, URL parsing and JSON belong to the
  libraries that exist for them: a main parses the target with Boost.URL's
  `parse_origin_form` and writes JSON with Boost.JSON.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **wasi exports the HTTP handler's world alone; a program whose world
  exports more uses the headers-alone target `/webcpp/wasi//wasi` and
  generates its own bindings, renamed `webcpp_wasi_http` too.** (reason not
  recorded)
  Source: `doc/build.adoc` (libs/wasi).
- **wasi targets `wasi:http` 0.2.12 and 0.3.0 alone, as measured with
  wasi-sdk 34, wit-bindgen 0.62.0 and wasmtime 50.0.1, and the page names
  each version as measured.** WASI 0.3 is young: a toolchain update may move
  the names the bindings' glue calls.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).

**Interface.**

- **The program writes its main between `WEBCPP_WASI_HTTP_MAIN_BEGIN(method,
  target)` and `WEBCPP_WASI_HTTP_MAIN_END()`, which expand the `extern "C"`
  export and the head of `webcpp::wasi::http::http_main`.** The program
  defines the handler once, and the header holds only inline functions and
  macros, so every translation unit may include it (guarantee 2); a function
  the program registers was rejected, since it needs a global. The cost: the
  body is inside a function of `webcpp::wasi::http`, so it names its own code
  with a full namespace or an alias, and `.clang-format` names the two macros
  as `MacroBlockBegin` and `MacroBlockEnd` to indent it.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The main receives the method by its name on the wire (an extension
  method as it was sent) and the target as sent (`"/"` when the request
  carried none), two `std::string_view` that view the request.** The
  handler's own code allocates nothing: it views the request's strings where
  the bindings put them, and the main copies what it keeps beyond the
  request.
  Source: `libraries/wasi/openspec/specs/wasi/spec.md` (proposals).
- **`response` is an aggregate of three members with defaults, in this
  order: `unsigned status = 200`, `std::string_view content_type{}`,
  `std::string body{}`.** A designated initializer names only what differs
  (`{.status = 404}`); the order is an HTTP response's and the initializer's,
  and the reference keeps it with `sort-members: false`.
  Source: `doc/mrdocs.yml` (libs/wasi).
- **`content_type` is a view and `body` a copy.** A content type is nearly
  always a literal, which a view holds for nothing, where a `std::string` of
  16 characters allocates on wasm32 (libc++ keeps 10 inline); the body is
  sent after the main has returned, so it must not point into the main's
  strings.
  Source: `include/webcpp/wasi/http/response.hpp` (libs/wasi).
- **`<webcpp/wasi/http/response.hpp>` includes nothing of the component ABI
  and compiles natively; its test runs natively and on both versions.** The
  rest of a program builds responses, holds them and passes them around (as
  messages between actors) and is tested natively, without a WASI toolchain.
  Source: `include/webcpp/wasi/http/response.hpp` (libs/wasi).
- **The handler's names are in the nested namespace `webcpp::wasi::http`,
  and its headers under `<webcpp/wasi/http/>`.** wasi is a collection of
  helpers for C++ built as components, and the HTTP handler is its first
  part.
  Source: `meta/libraries.json` (libs/wasi).

**Bindings and build.**

- **The header includes the generated `webcpp_wasi_http.h`, and the build
  generates every world's C bindings with `--rename-world
  webcpp_wasi_http`.** Every generated name the header uses
  (`webcpp_wasi_http_string_t`, `WEBCPP_WASI_HTTP_WAITABLE_STATUS_BLOCKED`)
  is then the same whatever the program's world is called.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The bindings are generated into the build directory, never committed and
  never edited.** (reason not recorded)
  Source: `AGENTS.md` (libs/wasi).
- **`build.jam` declares a standard world per version, exporting the HTTP
  handler and nothing else, and the target `/webcpp/wasi//http`, which adds
  the headers, the bindings of the target's world and the target's macro.**
  A program that exports the handler and nothing else links that one target
  and is done; there is no compiled library of wasi's.
  Source: `build.jam` (libs/wasi).
- **The build defines the version's macro (`<toolset>clang-wasip2` gives
  `WEBCPP_WASI_HTTP_P2`), and the entry point stops with one `#error` under
  neither or both, before it includes the bindings.** The entry point
  compiles only for WASI and for one version (guarantee 1), and the refusal
  tests pin that one message; why the build rather than the compiler names
  the version is not recorded.
  Source: `include/webcpp/wasi/http/entrypoint.hpp` (libs/wasi).
- **A component is linked as a reactor, `-mexec-model=reactor`.** It exports
  a handler and has no C `main`. Historical tests with wasmtime 47 also
  served it linked as a command; current webcpp builds and tests reactors.
  Source: `doc/build.adoc` (libs/wasi).
- **b2 looks for wit-bindgen, the `wasi:http` WIT and wasmtime only when a
  target needs them, each at its `-s` variable first, then under `.local/`
  or on `PATH`, and stops naming the tool and every place it looked.** A
  native build of the response and the configuration needs none of them.
  Source: `doc/build.adoc` (libs/wasi).

**Behaviour.**

- **A status outside 100 to 599 is not sent: the handler answers an internal
  error instead, before anything is committed, on both versions.**
  `set-status-code` refuses some statuses and leaves the response at 200, and
  the status's 16 bits read 65736 as 200, so a main's bug would reach the
  client as a success; clamping the status was rejected because it alters
  the response.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **A content type the host refuses as a field value (a CR, an LF, a NUL)
  answers an internal error instead of the response; a tab is sent as it
  is.** Dropping the header was rejected: a response is sent as the main
  wrote it or refused, never altered (guarantee 9).
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The handler frees the method, the target and the request only after the
  response is written.** A `content_type` that views the method or the target
  is then still valid when it is sent; a first version freed them earlier,
  and the host refused the overwritten content type.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The results of `set-status-code` and of `outgoing-body.finish` are not
  read.** `set-status-code` fails only outside 100 to 599, which the guard
  refused, and `finish` fails only when the body disagrees with a
  `content-length`, which the response never sends.
  Source: `include/webcpp/wasi/http/entrypoint.hpp` (libs/wasi).
- **On wasip2 the body is written in chunks of at most 4096 bytes through
  `blocking-write-and-flush`, then finished with no trailers.** 4096 bytes is
  the most `blocking-write-and-flush` accepts per call.
  Source: `include/webcpp/wasi/http/entrypoint.hpp` (libs/wasi).
- **On wasip3 the handler returns the response, then writes to the body's
  stream until the stream has taken every byte, then resolves the trailers
  future.** Historical tests with wasmtime 47 took a whole body, 1 MiB too,
  in one write; the loop stands for a host that takes less per write. The
  50.0.1 regression verifies delivery, not a particular number of writes.
  Source: `doc/guarantees.adoc` (libs/wasi).
- **On wasip3 the future of whether the host sent the response is dropped
  unread.** The guest could change nothing about a response already sent.
  Source: `include/webcpp/wasi/http/entrypoint.hpp` (libs/wasi).
- **The wasip3 handler is lifted asynchronously (`--async` on its bindings),
  waits for each blocked write inside the task on a waitable set, and always
  returns `EXIT`; the exported callback exists and returns `EXIT`.** Context
  slot 0 belongs to wasi-libc on wasip3, and using it trapped (measured); the
  callback exists because the glue calls it.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **A failure before the commit answers an internal error; after it, wasip2
  drops the body without `finish` and wasip3 resolves the trailers future
  with an internal error.** Once committed nothing can be taken back, and
  each is how its version tells the host the response failed (guarantee 6).
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).

**Exceptions and configuration.**

- **The handler throws, tries and catches nothing: an exception that escapes
  the main traps the instance, and wasmtime 50.0.1 answers its own HTML 500 and
  keeps serving.** The owner decided it on 2026-10-08, settling the open
  item of catching `std::exception` in the handler to print its `what()`:
  the host answers, and wasi needs neither exceptions nor RTTI and imposes
  neither.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **wasi's programs, and the by-hand commands its page shows, build wasip2
  with exceptions as wasip3: `-fwasm-exceptions -mllvm
  -wasm-use-legacy-eh=false`, linked with `-fwasm-exceptions -lunwind`.**
  Wasmtime 50.0.1 runs the exnref encoding with its default flags. Historical
  measurements with wasmtime 47 showed rejection of the legacy encoding
  wasi-sdk 34 emits by default, about 20% extra stripped component size
  with exceptions and no measured warm-start cost. Those measurements were
  not repeated for the runtime upgrade. The absence of exceptions cost
  Boost.Locale, a second Boost configuration and a wasip2-only path in
  every header.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/reference/research/WASIP2_EXCEPTIONS_SPIKE.md`
  (proposals).
- **`<webcpp/wasi/config.hpp>` includes nothing and derives
  `WEBCPP_WASI_NO_EXCEPTIONS` itself, from `WEBCPP_NO_EXCEPTIONS`,
  `BOOST_NO_EXCEPTIONS`, `__cpp_exceptions` and `_CPPUNWIND`.** A deviation
  from the configuration rule: wasi includes neither Boost nor
  `<webcpp/config.hpp>` until its redesign, and the macro, which changes
  nothing in wasi, exists so that a program sets it for every webcpp library
  alike.
  Source: `include/webcpp/wasi/config.hpp` (libs/wasi).

**Dependencies.**

- **The headers include only the standard library and the bindings
  wit-bindgen writes, and name no other webcpp library; the target `wasi`
  still carries Boost's headers, as every library's target does.** wasi is
  to impose nothing on a component: no exceptions, no RTTI, no Boost in its
  headers.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **wasi takes no allocator: the request's strings come through the
  bindings' `cabi_realloc` and the body through `std::allocator`.** (reason
  not recorded) A caller-supplied allocator is a non-goal of 0.1.0, and the
  page says a program cannot yet give one.
  Source: `doc/limits.adoc` (libs/wasi).
- **wasi names nothing of the programs that use it: the only generated names
  it uses are the standard interfaces' and the rename's.** It was first
  written for one program, whose name the lint's banned-word rule refuses in
  every file and commit (guarantee 8).
  Source: `doc/guarantees.adoc` (libs/wasi).

**Evidence.**

- **Every guarantee is held by a component that `wasmtime serve` runs on
  wasip2 and wasip3, sent the requests of `<stem>.requests` and compared,
  byte for byte, with `<stem>.expected`.** Every guarantee is proven by a
  test that fails when it breaks, served by a real host.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The transcript writes each request as the curl command that sends it
  (`curl -I` for `HEAD`), leaves out `date` and `transfer-encoding`, and
  writes the host and port fixed.** A shell runs it as written (`curl -X
  HEAD` waits for a body that never comes), and one transcript holds on every
  machine and every lane.
  Source: `doc/testing.adoc` (libs/wasi).
- **The served programs run in the own lane `http`, one CI job per
  target.** The owner's decision C11 of 2026-10-08, since stage 4 needs the
  same for a browser lane; it keeps them out of the ordinary lanes.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The two refusals, `neither_target_refused` and `both_targets_refused`,
  pass only on the guard's own error (`expected-error` of clang's
  `-verify`).** A compile that fails for another reason fails the test.
  Source: `libraries/wasi/openspec/specs/wasi/spec.md` (proposals).
- **`http_bad_status` and `http_bad_content_type` hold wasmtime 50.0.1's HTML
  500 verbatim.** They fail when wasmtime changes how it answers an internal
  error, and are regenerated knowingly.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **Guarantee 6, and the second turn of wasip3's write loop, are held by
  review.** wasmtime offers no way to make a write fail on demand, and takes
  the whole body in one write.
  Source: `doc/guarantees.adoc` (libs/wasi).
- **The page states nine guarantees, each keeping its number and its anchor
  `wasi-invariant-<n>`, and `b2 libs/wasi/doc` fails on a citation that
  names no anchor.** The code and the tests cite a guarantee as
  `(doc: #wasi-invariant-<n>)`.
  Source: `doc/guarantees.adoc` (libs/wasi).
- **The README's example and the by-hand build are tests: doc-check compares
  the README's copies with `example/http_hello.*`, and `by_hand` runs
  `example/by_hand/build.sh` on both versions and serves what it builds.** A
  page that shows a command that stopped working fails the lane.
  Source:
  `libraries/wasi/openspec/changes/archive/2026-10-08-genesis/design.md`
  (proposals).
- **The reference parses the entry point natively with wasip2's bindings and
  macro, and checks the Doc Comments of the wasip3 branch with its own.** The
  entry point builds only for WASI.
  Source: `doc/Jamfile` (libs/wasi).
- **The page's chapter "Building for WASI with Boost" includes the
  superproject's configuration by tag through `{webcpp-root}`.** doc-check
  accepts only a tagged region of a tracked file, so a region renamed there
  fails the page rather than leave it stale.
  Source: `AGENTS.md` (libs/wasi).

### idna (internationalized domain names: Punycode, UTS 46 and IDNA2008 over generated Unicode 17.0.0 tables; own; implemented in 0.1.0)

idna judges and converts domain names: Punycode (RFC 3492), UTS 46's ToASCII
and ToUnicode (revision 35), and IDNA2008's validity (RFC 5890 to 5893). It
was specified and built from 2026-10-09 to 2026-10-12 as the library under
webcpp::lexical's JSON Schema formats `hostname`, `idn-hostname`, `email`
and `idn-email`.

**Why a library of its own.**

- **idna implements Punycode, UTS 46 and IDNA2008 itself, rather than wrap
  ICU or libidn2 or take ada-url/idna as it is.** Of the JSON Schema
  suite's `idn-hostname` cases, ada fails 16.3% and upa 15.2%; ICU (4.3%)
  and libidn2's registration check (2.2%) fail fewer but are compiled
  dependencies, not header-only, and no header-only C++ IDNA2008 library
  exists.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **ada-url/idna is read as a reference for algorithms and table packing
  only: nothing of it is copied, and no file of it enters the repository.**
  It is one of the owner's binding decisions of 2026-10-09, once taking ada
  as a dependency was rejected (above).
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/reference/spec.md`
  (proposals).
- **idna implements both standards, UTS 46's processing and IDNA2008's
  validity.** UTS 46 says how a typed name is mapped and IDNA2008 which
  labels are valid, and they disagree: UTS 46 accepts `¡` and has no
  CONTEXTO rules, while JSON Schema asks for IDNA2008's strictness.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/proposal.md`
  (proposals).
- **IDNA2003, registry-specific rules, confusable detection (UTS 39), the
  WHATWG URL host parser and DNS lookups are out of scope.** RFC 5891
  section 4.3 leaves registry rules to registries, a later URL library may
  build on `to_ascii` with its own options, and idna judges and converts
  strings only.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).

**Interface.**

- **The default `idna::options{}` is the strict profile: UTS 46 with every
  check on, nontransitional, the DNS lengths verified, and `idna2008 =
  true`; the default never becomes looser.** UTS 46 alone accepts the code
  points it marks NV8 and XV8 and every CONTEXTO violation; UTS 46 alone as
  the default was rejected, since every consumer would have to turn on the
  check it needs.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **`options` is an aggregate of eight `bool`s, UTS 46's seven flags named
  after them and idna's own `idna2008`.** A caller names only what changes
  with a designated initializer: `idna::options{.idna2008 = false}` is
  UTS 46 alone.
  Source: `include/webcpp/idna/options.hpp` (libs/idna).
- **Every conversion has a span form, the primitive, which writes into the
  caller's `std::span` and allocates nothing, and a pmr form, which returns
  a `std::pmr` string from a memory resource (by default
  `std::pmr::get_default_resource()`) and allocates from it alone.** "Nothing
  allocates" then holds for every name the DNS accepts, whose sizes are
  bounded; an API of `std::string` alone was rejected, since it cannot honour
  it.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The span forms take their output first, `to_ascii(output, domain)`, as
  Boost.URL's encoders do.** No call is then ambiguous between the two
  forms.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The conversions (`uts46.hpp`) map a name first; the validators
  (`validity.hpp`: `check_label`, `check_domain`, `is_valid_label`,
  `is_valid_domain`) check it as given, map nothing, take no output and never
  allocate.** A program needs the validators when a name must already be in
  its final form, as a hostname's A-labels must.
  Source: `doc/validity.adoc` (libs/idna).
- **`check_domain` splits at U+002E alone, and `check_label` refuses a
  U+002E as `disallowed`.** The other full stops, U+3002, U+FF0E and
  U+FF61, separate labels only after UTS 46's mapping, so as given they are
  code points UTS 46 maps.
  Source: `doc/validity.adoc` (libs/idna).
- **An A-label is `xn--` in either ASCII case, must be ASCII, is decoded,
  validated as a U-label (NFC and nontransitional processing included) and
  encoded again, and is refused as `invalid_punycode` unless the round trip
  gives it back, compared in lowercase.** RFC 5890 compares an A-label in
  either case, and RFC 5891 section 5.4 asks for the round trip.
  Source: `doc/validity.adoc` (libs/idna).
- **`to_unicode` returns a struct of what it wrote and an `error_code`, goes
  on after an error, and puts no U+FFFD in place of what failed; in its span
  form `output_too_small` takes the place of any other error.** UTS 46 asks
  that the conversion be performed as far as possible, so that a name can be
  shown even when it is not valid; a caller whose span is too small needs a
  larger one before anything else.
  Source: `doc/converting.adoc` (libs/idna).
- **Under the DNS lengths `to_ascii` writes at most 253 chars, so a
  `std::array<char, idna::max_domain_length>` always holds the result, and
  it reports `output_too_small` last.** A span too small for a name that is
  too long anyway reports the name (guarantee 4).
  Source: `doc/converting.adoc` (libs/idna).
- **A final empty root label is `empty_label` in `to_ascii` under the DNS
  lengths and no error in `to_unicode`.** UTS 46 revision 35 disallows the
  empty root label under VerifyDnsLength, and its X4_2 exempts a final empty
  label in the Unicode form.
  Source: `libraries/idna/openspec/specs/idna/spec.md` (proposals).
- **Punycode's functions, in the nested namespace `webcpp::idna::punycode`,
  work without the `xn--` prefix: the encoder writes lowercase digits, the
  decoder reads digits in either case and copies basic code points as given,
  and a delimiter at the very start consumes nothing.** The basic code points
  keep RFC 3492's mixed-case annotation, and `-9uc` is refused, as RFC 3492
  says, so that `xn---9uc` is never read as `xn--9uc`.
  Source: `doc/punycode.adoc` (libs/idna).
- **The signatures of `errors.hpp`, `options.hpp`, `punycode.hpp`,
  `validity.hpp` and `uts46.hpp` are a contract, changed only with an
  announcement to webcpp::lexical; `detail` changes freely.** lexical was
  specified in parallel and codes against them.
  Source: `AGENTS.md` (libs/idna).

**Errors.**

- **Every fallible operation returns `idna::result<T>`, Boost.System's
  `result`, and its errors are the 19 values of `idna::error`, one per family
  of rules rather than one per UTS 46 status code.** IdnaTestV2 itself says
  an implementation "need only record that there is an error".
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The values start at 1, never change and are never reused; a new error
  takes the next value.** An `error_code` of value 0 is no error, and a
  stored value keeps its meaning across versions.
  Source: `include/webcpp/idna/errors.hpp` (libs/idna).
- **The category is one `constexpr` object, `detail::the_category`, with
  the fixed name `webcpp.idna` and the fixed identity `0x69646E6100000000`,
  the ASCII of "idna", in pratt's form.** idna then holds no mutable state.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The category overrides `message(int, char*, std::size_t)`, which copies
  the message into the caller's buffer, cut to fit, and is `noexcept`.**
  `message(int)` returns a `std::string` as Boost.System declares it and may
  throw what `operator new` throws; the buffer form throws nothing
  (guarantee 2).
  Source: `doc/guarantees.adoc` (libs/idna).
- **The first error is reported, in a fixed order: the first label's first
  fault, labels in order, a label's rules in UTS 46's order with IDNA2008's
  last; then `bidi`; then `domain_too_long`; `output_too_small` last in
  `to_ascii`.** Tests pin the order, so that lexical returns the same reason
  on every target.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The span forms and the validators are `noexcept`, the pmr forms are not,
  and a test's `static_assert`s state it.** A pmr form throws only what its
  memory resource throws, and idna raises nothing of its own (guarantee 2).
  Source: `libraries/idna/openspec/specs/idna/spec.md` (proposals).
- **A `noexcept` function reads a `result` it has checked with
  `unsafe_value()`, never with `operator*`.** Boost 1.92's `operator*`
  calls `value()`, which throws, and clang-tidy's `bugprone-exception-escape`
  then fails the function.
  Source: `AGENTS.md` (libs/idna).

**Memory.**

- **A single driver, `detail/process.hpp`, streams UTS 46 section 4 label by
  label for both the conversions and the validators, into a sink that takes
  the ASCII form, the Unicode form or nothing.** One label is held at a
  time, so the working storage is one label's whatever the name's length.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **A label is held in fixed storage of 256 code points,
  `detail::max_label_code_points`.** Every label the DNS lengths accept fits:
  an A-label of 63 octets decodes to at most 59 code points, and the longest
  full canonical decomposition of Unicode 17.0.0 is 4 code points (U+1FAF),
  which the generator measures and checks.
  Source: `include/webcpp/idna/detail/label_buffer.hpp` (libs/idna).
- **A label beyond the storage is `label_too_long` under the DNS lengths and
  `storage_exhausted` without them in a span form or a validator, while a pmr
  form grows it into its memory resource.** Such a label is no name the DNS
  can hold, and a span form allocates nothing.
  Source: `doc/limits.adoc` (libs/idna).
- **In the ASCII form under the DNS lengths, a pmr form holds a label to the
  inline capacity too.** No label past it passes the DNS lengths, so both
  forms report the same first error.
  Source: `include/webcpp/idna/detail/process.hpp` (libs/idna).
- **A label beyond the storage is reported while it is gathered, before its
  rules, and stops the driver, keeping an error recorded before it.** No form
  can go on without the label.
  Source: `include/webcpp/idna/detail/process.hpp` (libs/idna).
- **Canonical ordering sorts a run of up to 32 non-starters by insertion, a
  run up to 256 by counting through a never-inlined buffer on the stack, and
  a longer one by counting through the label's memory resource.** Each step
  of NFC then does a bounded amount of work per code point, and the stack
  holds the buffer only while such a run is sorted.
  Source: `include/webcpp/idna/detail/nfc.hpp` (libs/idna).
- **Hangul syllables are decomposed and composed by the arithmetic of Unicode
  section 3.12.** They take no table space.
  Source: `doc/unicode.adoc` (libs/idna).
- **idna does not recurse, and holds about 1.3 KiB of inline storage per
  call; its deepest call measured about 11 KiB of stack in a debug wasm
  build, with no margin promised.** idna runs inside a WebAssembly program,
  whose default stack is 64 KiB.
  Source: `doc/limits.adoc` (libs/idna).

**Limits.**

- **The conversions bound a label's Punycode at 256 code points, past which
  it is `punycode_overflow` whatever `ignore_invalid_punycode` says.**
  RFC 3492's encoder and decoder work in time that grows with the square of a
  label: at 256 the worst label costs about 4 times a linear one, where 1,024
  code points cost 14 times and 4,096 cost 43; a limit of the implementation
  is no invalid Punycode.
  Source: `include/webcpp/idna/detail/process.hpp` (libs/idna).
- **`punycode::encode` and `punycode::decode` are the primitive and have no
  such bound.** A span form stops when the caller's span is full, and the
  page tells a program to bound input it does not trust before a pmr form.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **CONTEXTJ reads Joining_Type from the generated table, never from a list
  of joining scripts.** A hand-written list misses scripts, NKo, Mandaic and
  Phags-pa among them, and those a later Unicode adds.
  Source: `include/webcpp/idna/detail/context.hpp` (libs/idna).
- **CONTEXTO's rules A.7 to A.9 read facts gathered in one pass over the
  label, never a pass per occurrence.** A pmr form may hold a label far
  beyond a DNS label's length, and the check stays linear in it.
  Source: `include/webcpp/idna/detail/context.hpp` (libs/idna).
- **The Bidi rules' direction is that of the label's first code point, and
  an empty label is neither right-to-left nor in breach.** Rule 1 leaves
  only L, R and AL first, so the verdict is RFC 5893's; whether a label may
  be empty is the caller's question.
  Source: `include/webcpp/idna/detail/bidi.hpp` (libs/idna).
- **`check_domain` does a bounded amount of work per label.** A test holds
  a name of 65,536 one-letter labels under 20 times a name as long made of
  labels of 255 letters, where a pass over the name per label would exceed
  100 times.
  Source: `libraries/idna/openspec/specs/idna/spec.md` (proposals).

**Data.**

- **`tools/generate_tables.py` (Python 3.9, standard library only) writes
  the tables and the conformance vectors from Unicode's files, pinned by URL
  and SHA-256 in `tools/unicode.json`; the Unicode files are not
  committed.** No Unicode data is written by hand; committing the files was
  rejected, since it would copy Unicode's data into the repository.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The tables are `constexpr` arrays of sorted runs searched by binary
  search, 147,324 bytes, never compressed and never built at run time.**
  Nothing is allocated and nothing is shared mutable state, so any number of
  threads may call idna at once.
  Source: `doc/unicode.adoc` (libs/idna).
- **Only `detail/properties.hpp` includes the tables, and refuses to compile
  while their `unicode_version` differs from `idna::unicode_version`;
  `punycode.hpp`, `errors.hpp` and `options.hpp` never reach them.** The
  tables cost about 0.7 s and 188 KB natively in a translation unit that
  calls `to_ascii`, and a move to another Unicode changes both versions
  together.
  Source: `doc/unicode.adoc` (libs/idna).
- **IDNA2008's property is derived from UTS 46's table (PVALID, CONTEXTJ or
  CONTEXTO exactly when valid or deviation without an NV8 or XV8 mark), and
  the generator compares the derivation with IANA's `idna-tables-12.0.0` on
  every run; no IANA table is shipped.** UTS 46's NV8 and XV8 marks carry
  IDNA2008's difference, and IANA's tables stop at Unicode 12.0.0, so they
  serve as a check, which agrees on every code point IANA assigns, U+002E
  aside.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **`detail/context.hpp` hard-codes the rules of RFC 5892 appendix A, and
  the generator stops if IANA's CONTEXTJ and CONTEXTO code points differ from
  that appendix's.** RFC 5892 fixes the two sets and their rules, and IANA's
  12.0.0 table agrees, which the check repeats on every run.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/reference/spec.md`
  (proposals).
- **The generator checks every assumption idna makes of the data before it
  writes (five statuses, at most 4 code points per decomposition, no Hangul
  decomposition, every property value known), and stops naming the one that
  fails.** A value a new Unicode version adds or renames is looked at, never
  absorbed as other.
  Source: `tools/generate_tables.py` (libs/idna).
- **A download is checked against its digest before it is kept, nothing is
  written unless every check passed, and two runs write the same bytes.** A
  moved URL leaves nothing in the cache, and the committed files are exactly
  the generator's output (guarantee 5).
  Source: `tools/generate_tables.py` (libs/idna).
- **The vectors of IdnaTestV2.txt and NormalizationTest.txt are generated as
  C++ data under `test/generated/`.** No test reads a file on any target.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The vectors' strings are `sv` literals, printable ASCII as is, every
  other byte a three-digit octal escape, and a digit right after an escape
  escaped too.** A view made from a pointer counts its characters in the
  array's constant evaluation, where Clang on libstdc++ runs out of steps;
  MSVC's warning C4125 refuses a digit after an octal escape.
  Source: `tools/generate_tables.py` (libs/idna).
- **The own lane `tables` runs the generator into the build directory and
  compares its outputs byte for byte; `update-generated` is the one writer of
  the generated files, and the ordinary lanes never run the generator.** It
  may need the network until its cache is filled.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The tables follow Unicode 17.0.0 (UTS 46 revision 35), not 18.0.0.** The
  owner chose 17.0.0; a move is a change of its own, which the page's
  section "Moving to another version of Unicode" lists file by file.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The Unicode License v3 notice is whole in the page's appendix "Unicode
  data", each generated file names it in one comment line, and no separate
  licence file is added; idna's code is BSL-1.0 alone.** The licence asks for
  its notice with the copies or in the documentation, while every file of
  webcpp is BSL-1.0 only.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).

**Dependencies and targets.**

- **idna needs Boost's headers (Config, System, Core, Assert) and
  webcpp::config, and nothing built or linked; its include boundary forbids
  `boost/url`, `boost/json` and `webcpp/lexical`.** idna depends on
  webcpp::config and header-only Boost alone, and lexical is its
  consumer.
  Source: `meta/include-boundaries.json` (libs/idna).
- **Every test and example runs on native, wasip2, wasip3 and Emscripten
  with the same vectors.** The same input and options give the same output
  and error on every target (guarantee 3).
  Source: `test/Jamfile` (libs/idna).
- **The tests that compile the generated vectors are built with `/bigobj`
  on MSVC.** MSVC compiles those large files of data only with it.
  Source: `test/Jamfile` (libs/idna).

**Evidence.**

- **idna has no oracle, no twins and no "Differences" appendix; its evidence
  is Unicode's IdnaTestV2.txt and NormalizationTest.txt, RFC 3492's samples,
  RFC 5892's and RFC 5893's rules case by case, and, through lexical, the
  JSON Schema test suite.** It ports nothing; IdnaTestV2 does not test
  CONTEXTO, and nothing official tests the combination of the two
  standards.
  Source:
  `libraries/idna/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **`uts46_test` runs all 6,391 lines of IdnaTestV2 under UTS 46 alone, then
  the strict profile over the 3,084 lines whose toUnicode holds no NV8, XV8
  or CONTEXTO code point, in both forms.** The file assumes UTS 46 alone, an
  IDNA2008 implementation skips NV8 and XV8, and the file does not test
  CONTEXTO.
  Source: `libraries/idna/openspec/specs/idna/spec.md` (proposals).
- **A line with a lone surrogate is refused as `invalid_utf8`, and writes
  nothing.** No UTF-8 string holds a lone surrogate, UTS 46 works on code
  points, and the file allows the refusal.
  Source: `doc/testing.adoc` (libs/idna).
- **`test/known_failures.json` is empty, may hold only a failure that comes
  from a difference between two versions of Unicode, and a test fails on a
  listed line that passes as on an unlisted line that fails.** The list never
  lies, and IdnaTestV2 is written for the same Unicode version as the
  tables.
  Source: `doc/testing.adoc` (libs/idna).
- **The Punycode tests pin four inputs, checked against Python's codec,
  beside RFC 3492's nineteen samples.** The samples leave alike what the
  four tell apart in the bias (damp against damp + 1, adapt's loop ending at
  455, the thresholds under biases of 70 and 83).
  Source: `libraries/idna/openspec/specs/idna/spec.md` (proposals).
- **Every test builds with libc++'s extensive hardening and libstdc++'s
  assertions.** A read past the end of a view traps instead of reading a
  neighbour's memory.
  Source: `test/Jamfile` (libs/idna).
- **The allocation test replaces the global `operator new` for its program
  alone, and its counting resource takes from that `operator new`, not from
  `std::pmr::new_delete_resource()`.** Every span form and validator must
  call it zero times (guarantee 1); MSVC defines `new_delete_resource` in its
  runtime's DLL, whose calls never reach the program's replacement.
  Source: `test/allocation_test.cpp` (libs/idna).
- **A test that guards a complexity bound compares with a baseline of the
  same size in the same run, the fastest of three, never with an absolute
  time.** A machine's load moves an absolute time but hardly a ratio: a
  loaded machine took the CONTEXTO ratio to 41, against a bound of 1,000 and
  the 30,000 a pass per occurrence would pass.
  Source: `libraries/idna/openspec/specs/idna/spec.md` (proposals).
- **The page states five numbered guarantees with the anchors
  `idna-invariant-1` to `idna-invariant-5`, which keep their numbers
  forever.** Code, tests and comments cite them.
  Source: `doc/guarantees.adoc` (libs/idna).
- **The reference gives each enumerator a section of its own
  (`show-enum-constants: true`).** The values of `error` are fixed, and the
  enum's table of members would show each enumerator's brief alone.
  Source: `doc/mrdocs.yml` (libs/idna).

**Sources.**

- **A narrow string literal spells a byte above 0x7F as a three-digit octal
  escape, a `U""` literal uses `\u` and `\U`, and a default `options` is
  written `idna::options()`.** A hex escape runs into the letters after it,
  MSVC reads raw UTF-8 in the machine's code page, and clang-tidy's
  `readability-trailing-comma` misreads an empty `options{}` followed by a
  comma.
  Source: `AGENTS.md` (libs/idna).
- **An A-label in the page's prose is written `` `+xn--bcher-kva.example+` ``,
  with the plus passthrough.** Asciidoctor replaces `--` between two word
  characters with an em dash, inside backticks too, and no check of the build
  sees it.
  Source: `AGENTS.md` (libs/idna).

### lexical (JSON Schema's string formats; own; implemented in 0.1.0)

lexical answers whether a string is a well-formed instance of each of the 19
string formats JSON Schema names, as its RFC or ECMA-262 defines it, through a
validator `is_<name>` and, but for `regex`, a Boost.URL grammar rule. It was
specified on 2026-10-09 as webcpp::formats, the format layer of
webcpp::json_schema, and published as lexical in 0.1.0 on 2026-10-13. A source
in proposals is given relative to `libraries/lexical/openspec/`.

**Scope.**

- **lexical is a library of webcpp's own (`"port-of": null`) and ports
  nothing: its evidence is the RFCs it cites, its unit tests, the official
  JSON-Schema-Test-Suite run against its validators, and V8 for `regex`.** No
  C++ library answered, for every string format JSON Schema names, exactly as
  the RFCs and ECMA-262 define it, without allocating and without exceptions,
  natively and on WebAssembly; webcpp::json_schema needs one for its `format`
  keyword.
  Source: `changes/archive/2026-10-09-genesis/proposal.md` (proposals);
  `AGENTS.md` (libs/lexical).
- **lexical checks the lexical space of a format and nothing beyond it: it
  never resolves a URI, looks up a host, checks a mailbox, compiles or runs a
  pattern, or computes with a date beyond the days of its month.** (reason not
  recorded)
  Source: `changes/archive/2026-10-09-genesis/design.md`, D1 and Non-Goals
  (proposals).
- **The library was renamed from formats (`webcpp::formats`,
  `<webcpp/formats/...>`) to lexical on 2026-10-13, and no name of the old
  spelling remains.** "formats" read as Boost.Format or `std::format` to a C++
  developer.
  Source: `changes/archive/2026-10-09-genesis/design.md`, Context (proposals).
- **JSON Schema v1's RFC 9557 `date-time-ext` suffixes and its "published leap
  seconds", the formats of v1's registry beyond the 17 of its body (`int32`,
  `base64url`), and the content keywords are out of scope.** v1 is unpublished
  and drifting and no test covers them; when it is published, lexical adds
  them as a contract extension, a new function or policy and never a changed
  default; content is json_schema's.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 1
  and risk 8 (proposals).

**Interface.**

- **Each format is a validator `is_<name>(std::string_view)` returning `bool`,
  `[[nodiscard]]`, its hyphens written as underscores, and, but `regex`, a
  Boost.URL rule in `webcpp::lexical::grammar`.** A rule composes with
  Boost.URL's combinators into a program's own grammar; validators of their
  own beside Boost.URL, the alternative rejected, would compose with nothing.
  Source: `changes/archive/2026-10-09-genesis/design.md`, D2 (proposals).
- **A validator is its rule parsing the whole string,
  `boost::urls::grammar::parse(s, x_rule).has_value()`, so the validator
  refuses trailing input with `error::leftover` while the rule, inside a
  grammar, stops where its format ends.** The function and its rule then never
  disagree (the page's invariant 1), which each unit test checks on every
  input it holds.
  Source: `specs/lexical/spec.md`, "Library: Trailing input is refused through
  leftover" (proposals); `doc/guarantees.adoc` (libs/lexical).
- **Rule types are public, `<name>_rule_t`, each with an `inline constexpr`
  object `<name>_rule`, and documented as a contract.** A rule that takes a
  parameter is then spelled without a factory
  (`time_rule_t{leap_seconds::refused}`, `iri_rule_t{&resource}`); Boost.URL
  hides its own rule types as `implementation_defined`.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, P2
  (proposals).
- **A rule yields the text it matched, `grammar::text`, an alias of
  `boost::core::string_view`; only `uri_rule` and `uri_reference_rule` yield
  Boost.URL's `url_view`.** It is Boost.URL's text type, which converts to
  `std::string_view`; parsed values (a date's fields) are out of scope, and
  adding them later is new rules, not a change of these.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, P1
  (proposals); `include/webcpp/lexical/grammar.hpp` (libs/lexical).
- **`ipv4` and `ipv6` have no rule of lexical's: `is_ipv4` and `is_ipv6` parse
  with Boost.URL's `ipv4_address_rule` and `ipv6_address_rule`, which a
  program's grammar names directly.** The owner decided that ASCII grammars
  are written with Boost.URL's grammar library, reusing its IP rules, which
  refuse a leading zero and fail no test of the suite.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 2.1
  item 5 and section 5.5 (proposals).
- **`regex` has no rule.** A pattern has no grammar of its own inside a longer
  input, so `is_regex` judges a whole string.
  Source: `specs/lexical/spec.md`, "Regex: no rule" (proposals);
  `doc/regex.adoc` (libs/lexical).
- **What differs between JSON Schema's dialects is two policy enumerations,
  never a dialect argument: `leap_seconds` for `time` and `index_manipulation`
  for `relative-json-pointer`, both defaulting to `allowed`, each a public
  member of its rule type.** v1's suite inverts six leap-second tests of
  `time` ("This MUST NOT include leap seconds"); drafts 7 and 2019-09 cite
  draft-handrews-relative-json-pointer-01, which has no index manipulation,
  and 2020-12 and v1 draft-bhutton-relative-json-pointer-00, which has it.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, P4, section
  1 and section 5.4 (proposals).
- **`date-time` allows a leap second in every dialect, v1 included.** The
  suite's `date-time` tests of every dialect, v1's among them, say so.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, P4
  (proposals).
- **An index manipulation is accepted before `#` too (`1-1#`).** The draft's
  own example `0-1#` puts it there though its ABNF omits it, so lexical takes
  the union of what the draft treats as valid.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 5.4
  (proposals); `doc/identifiers.adoc` (libs/lexical).
- **`<webcpp/lexical.hpp>` includes every format but `regex`, whose header is
  included by name.** `<webcpp/lexical/regex.hpp>` brings the Unicode tables
  of ECMA-262's classes, which a program that never validates a pattern should
  not compile.
  Source: `include/webcpp/lexical.hpp` (libs/lexical).

**Errors and exceptions.**

- **lexical has no error category of its own: a rule answers Boost.URL's
  `error::mismatch`, `error::invalid` or `error::leftover`, or the
  `webcpp::idna` error that refused a name.** `mismatch` is kept for text that
  cannot start the format, so that a `variant_rule` tries its next
  alternative; `invalid` says the format started and broke a constraint; an
  internationalized rule hands idna's reason (`contexto`, `bidi`) to its
  caller.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, P3 and
  section 6 (proposals).
- **A rule validates the whole run it takes and fails with `error::invalid`
  rather than match a shorter prefix; a rule over a run takes every byte its
  format may hold.** A grammar that composes the rule then meets a failure,
  not a silent short match.
  Source: `specs/lexical/spec.md`, "Library: A rule fails whole rather than
  match a prefix" (proposals).
- **A rule that fails leaves its iterator where it was, and a rule reads `[it,
  end)` alone, never a byte at or past `end`.** (reason not recorded)
  Source: `changes/archive/2026-10-09-genesis/design.md`, D2 (proposals);
  `doc/guarantees.adoc` (libs/lexical).
- **Where each rule stops inside a longer input is part of its contract, and
  an internationalized rule's run ends only at an ASCII byte outside letters,
  digits, `-` and `.`.** UTS 46 may map any non-ASCII code point, so every
  non-ASCII byte belongs to the name; likewise `json_pointer_rule` runs to the
  end of the input once a `/` starts it, since a token holds every character a
  grammar could continue with.
  Source: `doc/composing.adoc`; `include/webcpp/lexical/detail/idn_scan.hpp`
  (libs/lexical).
- **The e-mail rules look for `[` themselves and ask the address literal's
  rule or the host rule, rather than make the domain an alternative of a
  `variant_rule`, and turn the host rule's `mismatch` into `invalid`.**
  Boost.URL's `variant_rule` answers `mismatch` when every alternative fails,
  whatever each said, which would lose idna's reason for refusing the domain;
  once a local part and `@` matched, the Mailbox has started.
  Source: `include/webcpp/lexical/email.hpp` (libs/lexical);
  `changes/archive/2026-10-09-genesis/reference/spec.md`, section 4.3
  (proposals).
- **`is_regex` has neither a `grammar::result` nor an error code: a refusal is
  `false`, and the reason for the first fault, with a verdict of three values
  (`valid`, `invalid`, `beyond_bounds`), stays in `detail::check_regex` for
  tests and diagnostics.** Every byte string, a pattern past a bound included,
  is then answered with a value (the page's invariant 6).
  Source: `specs/lexical/spec.md`, "Regex: the verdict of the reader" and
  "Regex: always answers, never fails" (proposals).
- **lexical raises nothing of its own, so `WEBCPP_LEXICAL_NO_EXCEPTIONS`
  changes nothing in it; every validator and rule is `noexcept` but the four
  IRI functions and the two IRI rules.** Only an IRI's mapped copy beyond its
  inline buffer allocates, and a memory resource that refuses throws what it
  throws (`std::bad_alloc`), which lexical lets through rather than answer a
  verdict without the mapped copy.
  Source: `changes/archive/2026-10-09-genesis/design.md`, D7 (proposals);
  `include/webcpp/lexical/config.hpp` (libs/lexical).

**Memory.**

- **Nothing allocates but an IRI whose mapped URI exceeds 1,024 octets, which
  takes one buffer of its mapped length from the `std::pmr::memory_resource`
  given to an overload or a rule's `resource` member, else from
  `std::pmr::get_default_resource()`, and gives it back before it returns.**
  Boost.URL parses a contiguous `string_view`, so the mapped URI needs
  storage: an ASCII IRI is parsed as it is, never copied, and the inline
  buffer holds any IRI of up to 341 octets, since mapping at most triples a
  length; json_schema passes its validation's resource.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, P5
  (proposals); `include/webcpp/lexical/detail/iri_mapping.hpp` (libs/lexical).
- **An IRI's code points are all checked before anything is mapped.** An IRI
  refused for a code point takes no buffer, so even a resource that refuses
  every allocation gets that answer.
  Source: `specs/lexical/spec.md`, "URIs: The mapped URI buffer holds 1,024
  octets" (proposals).
- **A `range_rule` takes a nested rule through `boost::urls::grammar::ref`.**
  Boost.URL keeps a rule larger than 128 bytes in `recycled_ptr`, a
  process-wide pool that allocates outside any resource and is static mutable
  state; the allocation test fails if the pool is ever reached.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, risk 3
  (proposals); `doc/composing.adoc` (libs/lexical).
- **Where the URI template's ABNF repeats, a `detail::repeat_rule` of
  lexical's own matches the repetitions and yields their text, in place of
  Boost.URL's `range_rule`.** `range_rule` builds a type-erased range through
  a virtual call for each repetition, about 30 ns per variable of a template,
  while `repeat_rule` keeps no value of its parts.
  Source: `include/webcpp/lexical/detail/rules.hpp`;
  `include/webcpp/lexical/uri_template.hpp` (libs/lexical).
- **idna works in fixed storage: an A-label is lowercased into a 63-octet
  stack buffer, and `to_ascii` writes into a `std::array<char,
  idna::max_domain_length>`.** No host rule allocates, and a hostile label of
  100,000 octets is stopped at that storage with
  `idna::error::label_too_long`.
  Source: `specs/lexical/spec.md`, "Hosts: hostile and oversized IDN input"
  (proposals).
- **`is_regex` takes no memory resource and stores nothing of the pattern:
  what it needs of the whole pattern (the count of its groups, the group a
  `\k` names, where two groups of one name sit) it reads again from the
  text.** It allocates nothing on any target, its state on the stack to the
  depth `max_regex_nesting` allows.
  Source: `include/webcpp/lexical/detail/regex_validator.hpp` (libs/lexical);
  `specs/lexical/spec.md`, "Regex: no allocation and no exceptions"
  (proposals).

**URIs and IRIs.**

- **`uri` and `uri-reference` are Boost.URL 1.92's `parse_uri` and
  `parse_uri_reference`, which lexical composes and never modifies, patches or
  copies; where Boost.URL is more liberal than RFC 3986, lexical guards it and
  offers the fix upstream.** The owner ruled lexical faithful to RFC 3986, the
  reference JSON Schema names for these formats (2026-10-09).
  Source: `changes/archive/2026-10-09-genesis/design.md`, D3, and
  `reference/spec.md`, P11 (proposals).
- **Four guards of `detail/uri_guard.hpp` refuse, after Boost.URL's rule
  succeeds, what Boost.URL accepts and RFC 3986 refuses: a relative reference
  whose path after an authority is neither empty nor led by `/`, `[` or `]` in
  a query, `#` in a fragment, and a zone identifier in an IP literal.** RFC
  3986 4.2 gives that path `path-abempty`, 3.2.2 holds brackets only around an
  IP literal, 3.5 holds a second `#` only as `%23`, and RFC 9844 (2025)
  obsoleted RFC 6874's zone identifier and reverted its change to RFC 3986.
  Source: `include/webcpp/lexical/detail/uri_guard.hpp`; `AGENTS.md`
  (libs/lexical).
- **A fifth guard, `refuses_authority_before_segment`, makes both URI rules
  refuse with `error::invalid` a reference that ends at its authority before a
  character that starts a path segment.** Boost.URL stops a URI at the second
  `@` of `http://a@b@example.com/`, so its rule would match `http://a@b`
  inside a larger grammar; this guard stays when Boost.URL refuses the
  relative forms, since a fixed Boost.URL still stops there.
  Source: `specs/lexical/spec.md`, "URIs: Guard against a reference that ends
  at its authority before a path segment" (proposals).
- **Each guard has a test that pins Boost.URL's wrong verdict
  (`boost_url_still_*`) and fails the day the configured Boost changes it; the
  guard then leaves in a change of its own with a changelog line, and the test
  of the RFC's verdict stays.** A Boost release that fixes or regresses a
  verdict is seen, and each guard leaves apart from the others.
  Source: `changes/archive/2026-10-09-genesis/design.md`, D3 (proposals);
  `AGENTS.md` (libs/lexical).
- **lexical never loosens Boost.URL: an `IPvFuture` led by an uppercase `V`
  stays refused, though RFC 5234 makes the ABNF's `"v"` case-insensitive, and
  is listed in the page's "Known deviations".** (reason not recorded) A test
  pins the verdict, which flips to RFC 3986's the day Boost.URL takes it.
  Source: `doc/uris.adoc`; `AGENTS.md` (libs/lexical).
- **An IRI is checked code point by code point, mapped to a URI with each
  octet of a non-ASCII code point as `%XX`, and parsed by `uri_rule` or
  `uri_reference_rule`, guards included; its host takes no IDNA.** Boost.URL
  parses RFC 3986 only, and `%XX` is valid exactly where RFC 3987 allows
  `ucschar`, so Boost.URL judges the structure, refuses a non-ASCII scheme or
  port, and every guard applies to the IRIs alike.
  Source: `changes/archive/2026-10-09-genesis/design.md`, D4 (proposals);
  `AGENTS.md` (libs/lexical).
- **A non-ASCII code point inside an IP literal is refused before anything is
  mapped.** RFC 3987 takes its IP literal from RFC 3986, ASCII alone, and
  refusing it there keeps that verdict independent of the zone guard.
  Source: `AGENTS.md` (libs/lexical).
- **`iprivate` is valid in the query alone, the query being the text after the
  first `?` that precedes the first `#`, and the bidirectional formatting
  characters are refused anywhere, the query included.** No valid IRI holds a
  `?` before its query or a `#` before its fragment (RFC 3986 appendix B); RFC
  3987 4.1 forbids the formatting characters outside its ABNF.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 5.8
  (proposals).
- **An IRI rule takes the run up to the first byte no IRI holds and validates
  it whole; `iri_reference_rule` matches empty text there, and never answers
  `mismatch`.** A rule fails whole rather than match a shorter prefix, and the
  empty string is an IRI reference.
  Source: `specs/lexical/spec.md`, "URIs: Where an IRI ends inside a larger
  grammar" (proposals).

**Host names and e-mail addresses.**

- **A `hostname` label that starts with `xn--`, in any case, is lowercased and
  judged by `idna::check_label`, so an A-label is valid in `hostname` exactly
  when it is valid as a one-label `idn-hostname`.** `XN--NXASMQ6B` is then
  valid in both formats, its case folded as UTS 46 maps an ASCII label.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, P9
  (proposals); `doc/addresses.adoc` (libs/lexical).
- **An R-LDH label (`ab--cd`) is a valid `hostname` and an invalid
  `idn-hostname`.** RFC 1123 allows it and draft 4's suite says so, while RFC
  5890's R-LDH labels are not NR-LDH; the page shows the two verdicts side by
  side, so that the difference reads as a decision, not a bug.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, P9 and risk
  11 (proposals).
- **`hostname` judges each A-label alone, and only `idn-hostname` checks RFC
  5893's Bidi rule across the labels of a name.** (reason not recorded) The
  page states it as a decision of lexical's own.
  Source: `doc/addresses.adoc` (libs/lexical).
- **`idn-hostname` hands its whole run to `idna::to_ascii` with idna's default
  options (UTS 46's mapping, nontransitional processing, every check,
  `verify_dns_length`, CONTEXTO, NV8 and XV8 refused), so a name's lengths are
  those of its ASCII form.** The suite's mapping cases and its strict cases
  (the DISALLOWED exceptions, CONTEXTO, CONTEXTJ, the Bidi rule across labels)
  are all idna's to answer.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 5.10
  (proposals).
- **Besides `.`, exactly U+3002, U+FF0E and U+FF61 end a label, and
  `hostname_test` converts every code point between two letters to keep it
  so.** They are the only code points UTS 46 maps to a sequence holding a dot
  in idna's tables (Unicode 17.0.0), so a label the rule accepts is one label,
  and a version of idna that adds one fails the test.
  Source: `include/webcpp/lexical/detail/idn_scan.hpp`; `AGENTS.md`
  (libs/lexical).
- **`idna_label_rule`, a terminal of lexical's own, judges one
  internationalized label alone; a grammar that joins labels checks the Bidi
  rule across them and the name's 253 octets itself, or hands the whole name
  to `idn_hostname_rule`.** A grammar then joins labels with separators of its
  own.
  Source: `doc/composing.adoc`; `include/webcpp/lexical/hostname.hpp`
  (libs/lexical).
- **lexical asks `webcpp::idna` through its public interface alone, and a
  verdict of idna's that a test of lexical finds wrong becomes a test in idna,
  red first, never a workaround in lexical.** No library reaches into
  another's `detail`, which an include boundary checks; a red test in idna is
  idna's own process (its specification, section 9).
  Source: `AGENTS.md` (libs/lexical);
  `changes/archive/2026-10-09-genesis/reference/spec.md`, P12 and section 9.3
  (proposals).
- **`email`'s domain is `hostname_rule`, A-labels included, and its address
  literals are `[` IPv4 `]` and `[IPv6:` IPv6 `]` alone, the tag in any
  case.** RFC 5321's General-address-literal needs a tag registered with IANA,
  and `IPv6` is the only one, so `[RFC-5322-domain-literal]` is invalid, as
  the suite says.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, P10
  (proposals).
- **An address literal's address is judged by Boost.URL's IP rules, not by RFC
  5321 4.1.3's `Snum` and `IPv6-comp`, which changes two verdicts:
  `[001.2.3.4]` is invalid and `[IPv6:1:2:3:4:5:6::8]` valid.** The owner
  decided that ASCII grammars are written with Boost.URL's grammar library,
  reusing `ipv4_address_rule` and `ipv6_address_rule`, the latter for e-mail's
  `[IPv6:...]` too; RFC 4291 allows `::` for one group.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 2.1
  item 5 (proposals); `doc/addresses.adoc` (libs/lexical).
- **A Mailbox is at most 254 octets, and its local part at most 64, a
  Quoted-string's quotes counted.** RFC 5321 4.5.3.1.3 bounds a path at 256
  octets with its two angle brackets, and 4.5.3.1.1 a local part at 64.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 5.11
  (proposals); `include/webcpp/lexical/email.hpp` (libs/lexical).
- **An internationalized Mailbox's 64 and 254 octets are measured as written,
  in UTF-8, while its domain's DNS lengths are those of its ASCII form.** RFC
  6531 sets no limit of its own, RFC 5321's are octets, and an SMTPUTF8
  envelope carries the address as written.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 5.11
  (proposals).
- **An internationalized local part holds any well-formed non-ASCII UTF-8, C1
  controls and noncharacters included, and is not normalized, while a quoted
  pair stays ASCII.** RFC 6532 3.1 adds `UTF8-non-ascii` to `atext` and
  `qtextSMTP` alone, and the suite holds a local part not in NFC valid.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 5.11
  (proposals).

**Dates, identifiers and templates.**

- **The date and time rules take ASCII digits only, `T` and `Z` in either
  case, and a duration's designators in either case.** RFC 3339's note allows
  either case of `T` and `Z`, and RFC 5234 2.3 makes ABNF's quoted strings, a
  duration's designators among them, case-insensitive.
  Source: `doc/dates.adoc` (libs/lexical).
- **Second 60 is valid when the time, moved to UTC by its offset, is 23:59,
  and its date is never checked against IERS's list of leap seconds.** RFC
  3339 5.7 allows a leap second there; with no table, the answer is the same
  every year.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 5.1
  (proposals); `doc/dates.adoc` (libs/lexical).
- **The duration rule is RFC 3339 appendix A's ABNF, one rule per production
  in its order, and a duration's numbers, like a time's fraction, are never
  converted.** Any number of digits is then valid, and nothing overflows or
  allocates however long it is.
  Source: `include/webcpp/lexical/date_time.hpp`; `doc/dates.adoc`
  (libs/lexical).
- **A UUID is checked for its shape alone, hexadecimal digits in either case,
  its version and variant nibbles unchecked.** The suite accepts version 15
  and an undefined variant.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 5.2
  (proposals).
- **A JSON Pointer is decoded as strict UTF-8, a NUL is a valid character of a
  token, and its rule never answers `mismatch`, matching empty text where no
  `/` starts the input.** RFC 6901's `unescaped` is every code point but `/`
  and `~`, `%x00` included, and the empty string is a JSON Pointer.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 5.3
  (proposals); `include/webcpp/lexical/json_pointer.hpp` (libs/lexical).
- **A URI template is checked at any level of RFC 6570 without being expanded,
  with erratum 6937's apostrophe as a literal, the reserved operators of
  `op-reserve` accepted, and `ucschar` and `iprivate` code points as
  literals.** The suite holds `a'b` valid, the ABNF admits the reserved
  operators, and a template of an IRI is valid too.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, section 5.9
  (proposals); `doc/templates.adoc` (libs/lexical).

**Regular expressions.**

- **`is_regex` is a syntax validator of lexical's own, a recursive-descent
  reader of well-formed UTF-8 that answers whether a pattern is ECMA-262's
  `Pattern[+UnicodeMode]`, early errors included, with ECMAScript 2025's
  modifiers and duplicate group names.** The owner abandoned SRELL and
  webcpp::regex, which the first `is_regex` compiled with, on 2026-10-12;
  Boost.Regex was rejected as the validator because it allocates outside any
  memory resource and its syntax is not ECMA-262's.
  Source: `changes/archive/2026-10-09-genesis/design.md`, D6 (proposals).
- **Valid means that the syntax and the early errors accept the pattern, and
  nothing more: `is_regex` compiles nothing, runs nothing, reads no flag but
  `u`, so the `v` flag's class sets are not read, and takes a lookbehind of
  any width.** JSON Schema's `regex` is judged as `new RegExp(pattern, "u")`
  judges it, and ECMA-262 allows a lookbehind of any width, which a validator
  that compiles nothing never measures.
  Source: `specs/lexical/spec.md`, "Regex: what is not judged" (proposals);
  `doc/regex.adoc` (libs/lexical).
- **`is_regex` has two bounds and no other: a pattern longer than
  `max_regex_length` (65,536 bytes) is answered `false` unread, and one whose
  groups, lookarounds and modifier groups nest deeper than `max_regex_nesting`
  (32) is answered `false` unjudged.** The validator reads parts of a pattern
  again, so the length bounds its time, and it reads a group by calling
  itself, so the nesting bounds its stack: 32 levels were set so that the
  deepest pattern, met in a hostile JSON instance, fits wasm32-wasip2's 64 KiB
  stack at `-O0`; alternatives, quantifiers and classes cost neither.
  Source: `specs/lexical/spec.md`, "Regex: pattern length bound", "Regex:
  group nesting bound" (proposals);
  `changes/archive/2026-10-09-genesis/reference/STATUS.md`, item 4
  (proposals).
- **The reader clamps any nesting it is asked for to `nesting_limit`, 64.**
  The functions that find the disjunctions holding a group keep their places
  in fixed arrays of `nesting_limit + 1` entries on the stack.
  Source: `include/webcpp/lexical/detail/regex_validator.hpp` (libs/lexical).
- **The reader never backtracks on a pattern's structure; it rereads the
  pattern with one reader of single tokens (`next_token`, which takes an
  escape or a whole class as one) for each group counted, each `\k` and each
  named group.** Its work is then bounded by a polynomial of the pattern's
  length, which `max_regex_length` bounds.
  Source: `specs/lexical/spec.md`, "Regex: bounded time on hostile patterns"
  (proposals).
- **Two groups share a name only when some disjunction holds them in different
  alternatives, which the reader checks for each named group against the last
  earlier group of that name.** That is ECMA-262 2025's rule (22.2.1.1): no
  match can hold both; and checking each group against the last earlier one
  checks every pair.
  Source: `include/webcpp/lexical/detail/regex_validator.hpp` (libs/lexical).
- **A pattern that is not well-formed UTF-8 is refused before its grammar is
  read, a NUL is a literal, and a code point above U+FFFF is one atom.** Every
  format reads code points through lexical's strict decoder, so that a verdict
  never depends on an ill-formed sequence being repaired or skipped.
  Source: `specs/lexical/spec.md`, "Library: UTF-8 rule shared by all" and
  "Regex: well-formed UTF-8 and NUL" (proposals).
- **The names `\p{...}` accepts and the ranges of ID_Start and ID_Continue are
  sorted tables generated from Unicode 17.0.0's data files, the ranges packed
  as `(first << 21) | last`, read through `detail/regex_unicode.hpp` alone; a
  `\p{...}` body over 64 bytes names nothing.** The data are idna's Unicode
  version, pinned by SHA-256, and the generated file is checked byte for byte
  against its generator (the page's invariant 7); past 64 bytes, no body names
  a property.
  Source: `specs/lexical/spec.md`, "Regex: unicode tables" and "Regex: reading
  the tables" (proposals); `include/webcpp/lexical/detail/regex_validator.hpp`
  (libs/lexical).
- **The script `Katakana_Or_Hiragana` has no name in the tables, and `Unknown`
  has one although no data file names it.** ECMA-262's table of the values of
  Script leaves out the script no code point has, and names `Unknown`, the
  value of the unassigned code points.
  Source: `tools/generate_tables.py` (libs/lexical).

**Dependencies and targets.**

- **lexical depends on Boost.URL and Boost.System (Boost 1.92 or newer),
  Boost's headers, webcpp::config and webcpp::idna, and on no regex library
  and no JSON library, which include boundaries enforce.** `is_regex` is
  lexical's own validator, and JSON is the tests' alone (`/webcpp//boost_json`
  in `regex_v8` and `suite`); each boundary states its reason, which the lint
  prints.
  Source: `build.jam`; `meta/include-boundaries.json` (libs/lexical).
- **A program links Boost.URL's compiled part, `/webcpp//boost_url`, built
  from Boost's sources for every target, never an installed `libboost_url`.**
  `ipv4_address`'s constructor from bytes and its `to_bytes()` live in
  Boost.URL's compiled sources, and on MSVC, which never defines
  `BOOST_URL_HAS_CXX20_CONSTEXPR`, even the grammar's error category; one set
  of sources serves native, wasip2, wasip3 and emscripten (measured: a
  stripped wasip2 program that calls `is_uri` is 85,625 bytes larger than an
  empty one).
  Source: `specs/lexical/spec.md`, "Library: Boost.URL's compiled part"
  (proposals); `changes/archive/2026-10-09-genesis/reference/spec.md`, section
  8.2 and the owner's decision on S4 (proposals).
- **lexical has a strict UTF-8 decoder of its own, `detail::decode_utf8`,
  about 20 lines on RFC 3629's table, rather than idna's.** No library reaches
  into another's `detail`.
  Source: `changes/archive/2026-10-09-genesis/reference/spec.md`, P12
  (proposals); `include/webcpp/lexical/detail/utf8.hpp` (libs/lexical).
- **The tests and the examples take `/bigobj` on MSVC.** A program that
  includes `regex.hpp` holds the Unicode tables beside Boost.URL and idna,
  which MSVC compiles only with `/bigobj`.
  Source: `test/Jamfile`; `example/Jamfile` (libs/lexical).

**Evidence.**

- **The official JSON-Schema-Test-Suite's format tests run directly against
  the validators on every target, read at run time from the superproject's
  submodule, and no copy of its data is committed.** It is MIT data, and every
  file of webcpp is BSL-1.0; moving the submodule is a change of its own, with
  every new failure fixed or listed in it.
  Source: `AGENTS.md` (libs/lexical);
  `changes/archive/2026-10-09-genesis/reference/spec.md`, P8 (proposals).
- **Each dialect has a known-failure list that may name only a residue tied to
  a Unicode version, and the runner fails on an unlisted failure, on a listed
  test that passes or that the suite does not hold, on a test named twice and
  on an entry without its four fields.** A list then never lies; every list is
  empty, and the 3,540 string tests pass.
  Source: `specs/lexical/spec.md`, "Library: Known failures" (proposals);
  `AGENTS.md` (libs/lexical).
- **The runner calls the same validator in every dialect but where a dialect's
  text cites a policy, from a table each of whose entries must name a dialect
  and a format that exist.** The suite tests no index manipulation, so a
  misspelt entry would otherwise fall to the default validator without a word.
  Source: `specs/lexical/spec.md`, "Library: Dialect policies of the runner"
  (proposals).
- **The runner judges a test on its format alone: a non-string instance must
  expect valid and is counted apart, the `unknown` format is skipped by name,
  and a schema with a keyword besides `format` and `$schema` fails the run.**
  A format applies to strings only and an unknown format is json_schema's
  question, and a keyword that changes a verdict would be misread.
  Source: `specs/lexical/spec.md`, "Library: What the runner does not judge"
  (proposals).
- **V8 is `is_regex`'s oracle: the lane `oracle` runs `new RegExp(pattern,
  "u")` in the CI's Node (26.7.0, V8 14.6, Unicode 17.0), with no npm package,
  over the generated patterns, and `regex_v8` requires `is_regex` to give V8's
  verdict on all 24,297 of them, on every target.** Only `update-expected`
  writes V8's verdicts, with the CI's Node: a Node whose V8 or Unicode differs
  may write other verdicts, which is a change of its own.
  Source: `specs/lexical/spec.md`, "Library: The V8 oracle lane" (proposals);
  `test/oracle/Jamfile` (libs/lexical).
- **The patterns compared with V8 are generated: a grammar's, drawn from seeds
  2 to 9 of Python's `random.Random`, 3,000 each, 30% of them with one of 41
  defects; every name `\p{...}` accepts and the same names misspelt; every
  pattern of the suite; and edge cases the grammar does not draw.** The
  grammar's draws are those of the study of Boost.Regex as an ECMA-262 engine,
  four subjects drawn and dropped after each, so that the patterns are the
  study's.
  Source: `tools/generate_patterns.py` (libs/lexical).
- **The Unicode tables and the patterns are generated from Unicode files
  pinned by URL and SHA-256 in `tools/unicode.json`, never edited by hand, and
  compared byte for byte by the own lane `generated`; the ordinary lanes never
  run a generator.** A generator may need the network, and a digest that
  differs stops it before anything is written.
  Source: `specs/lexical/spec.md`, "Regex: the generated-file lane"
  (proposals); `doc/regex.adoc` (libs/lexical).
- **lexical's and Boost.URL 1.92's URI verdicts were compared on 2026-10-09
  with a transcription of RFC 3986's ABNF, on inputs that put every ASCII
  character but NUL and line feed into each part of a reference and on
  references generated at random.** The page's "Known deviations" then lists
  every difference found, each pinned by a test.
  Source: `doc/uris.adoc` (libs/lexical).
- **The allocation test replaces the global `operator new` and `operator
  delete`, plain and aligned and `BOOST_NOINLINE`, counts every call over
  every validator on long and hostile inputs (a megabyte of each family among
  them), and ends its memory resources in a resource of the program's own heap
  rather than `std::pmr::new_delete_resource()`.** MSVC's runtime library
  defines `new_delete_resource` in its DLL, whose calls of `operator new`
  never reach a replacement the program defines; GCC, inlining one operator,
  would pair its `malloc` with the other's `free` and warn.
  Source: `test/counting_resource.hpp`; `test/allocation_test.cpp`
  (libs/lexical).

### document (JSON with JavaScript's behaviour; own; implemented in 0.1.0)

document is a JSON document whose behaviour is JavaScript's (`JSON.parse`,
property access, assignment, `delete`, the array methods, `JSON.stringify`,
the same key order and the same text out), exact in decimal, whose tree lives
in one relocatable binary image that is copied, sent, opened in place and
shared, and which is also a JavaScript module and an npm package. A source in
proposals is given relative to `libraries/document/openspec/`.

**Scope and dependencies.**

- **document is webcpp's own library and ports nothing: its evidence is
  JavaScript itself, run in Node as an oracle.** The reasons it exists are
  properties of `boost::json::value` (key order, an `erase` that reorders,
  numbers as doubles, hashed objects, pointers), so there was nothing to port.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).
- **Of Boost.JSON it uses `basic_parser` alone, whose SAX handler builds the
  tree, and none of its value types; `build.jam` links `/webcpp//boost_json`
  for it.** Wrapping `boost::json::value` was rejected, as it cannot be made
  relocatable or exact; Boost.JSON's parser is not header-only.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).
- **Doubles are read and written through Boost.Charconv, so `build.jam` also
  links `/webcpp//boost_charconv`.** Xcode 16's libc++ deletes the
  floating-point `std::from_chars`, and one code path serves every target.
  Source: `include/webcpp/document/traits.hpp` (libs/document).
- **Of Boost.Interprocess only `offset_ptr.hpp`,
  `mem_algo/rbtree_best_fit.hpp`, `sync/null_mutex.hpp` and, for the
  `bad_alloc` its allocators throw, `exceptions.hpp` are included, with a
  mutex family of document's own, `detail::no_mutexes`; never
  `managed_external_buffer`, `segment_manager`, `allocators/allocator.hpp` or
  `sync/mutex_family.hpp`.** Those throw bare and do not compile without
  exceptions.
  Source: `include/webcpp/document/detail/heap.hpp` and
  `include/webcpp/document/detail/allocation.hpp` (libs/document).
- **0.1.0 leaves out BigInt and fixed 256-bit integers.** `decimal128_t` holds
  34-digit integers exactly, and Boost.Multiprecision's `int256_t` is 48
  bytes, not trivially copyable, with bytes that differ between compilers and
  targets (measured).
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **0.1.0 also leaves out `toJSON`, replacers and revivers other than
  `revive_dates` and `revive_bytes`, Map, Set, RegExp, prototypes, getters,
  symbols, JSON Pointer, JSONPath beyond the selectors, schemas, a document
  inside a segment of several documents, durability, and the recovery of a
  dead process's references.** Each is left to a later proposal (reason not
  recorded).
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).
- **Speed is a non-goal: 0.1.0 is not tuned against Boost.JSON or V8, and
  the page states where document loses, with measurements.** Every operation
  pays for JavaScript's behaviour, exact numbers and one relocatable image;
  honesty about that cost is a goal, and the profile names where tuning
  begins (the lookup by id behind every handle, the renumbering on a splice,
  the image `pop` allocates).
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).

**Behaviour.**

- **JavaScript's behaviour is the contract: the same key order, the same
  `JSON.stringify` bytes, the same array methods and index rules, each
  JavaScript name a member function of the same meaning.** A C++ program that
  must agree byte for byte with a JavaScript peer needs a document that makes
  JavaScript's decisions; one that knows JavaScript then knows document.
  Source: `changes/archive/2026-10-12-genesis/proposal.md` (proposals).
- **`set` of a handle or a document stores a deep copy, never an alias, and
  reads its source before it changes anything, so a value may be copied into
  its own subtree and `a.splice(0, 1, a)` inserts a copy.** A document is a
  tree, as JSON is: no value is shared and no cycle exists.
  Source: `doc/javascript.adoc` (libs/document).
- **`undefined` is never stored: `set(wd::undefined)` erases a member, stores
  `null` in an element, and makes a root hold `undefined`, which writes no
  text.** The text is the one `JSON.stringify` writes; only `Object.keys`
  would differ.
  Source: `doc/javascript.adoc` (libs/document).
- **Arrays are dense, `wd::dense` being the one array policy: a longer
  length or a write past the end fills with `null`, so `pop` or `shift` of a
  former hole returns `null`.** JSON has no holes and writes one as `null`, so
  the text is the same.
  Source: `doc/arrays.adoc` (libs/document).
- **A key reaches only a member and an index only an element: `arr["0"]` and
  `obj[3]` name nothing.** A handle names a member or an element, never both.
  Source: `doc/javascript.adoc` (libs/document).
- **`pop`, `shift`, `splice`, `slice` and `concat` return what they remove or
  copy in a new owned document of the source's allocator, an external
  source's included, as a `result`, which holds `undefined` for an empty
  array.** The elements then outlive the array; the cost, an
  image allocated per `pop`, is measured and named as a place to tune.
  Source: `doc/arrays.adoc` (libs/document).
- **Indices follow ECMA-262's relative index: a negative index counts from
  the end, clamped at 0, an index past the length is the length, and
  `INT64_MIN` and `INT64_MAX` clamp.** Indices follow JavaScript exactly.
  Source: `doc/arrays.adoc` (libs/document).
- **`==` compares structurally, key order aside: numbers by value, strings,
  dates and bytes by value, arrays element by element.** JavaScript has no
  deep equality, so this one is the document's, a ruling of the owner (reason
  not recorded).
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **`value_or(fallback)` is `??`, and also gives the fallback when the value
  cannot be read as the fallback's type.** (reason not recorded)
  Source: `include/webcpp/document/value.hpp` (libs/document).
- **`wd::object` and `wd::array` write JSON in C++ as `{...}` and `[...]`
  are written in JavaScript; a `wd::literal` converts implicitly from each
  value it holds and owns what it holds.** JavaScript's `[1, "x"]` needs no
  conversion written, and neither does `wd::array{1, "x"}`.
  Source: `include/webcpp/document/literal.hpp` (libs/document).

**Numbers.**

- **The default traits store a number exactly, in one of two forms chosen by
  value, never by spelling: an integer that fits `std::int64_t` is an
  `integer`, any other number a normalised `decimal128_t`; `-0` is `0`.**
  What is stored is what was sent, and `1`, `1.0` and `1e0` are one stored
  value as they are one number in JavaScript; `JSON.stringify(-0)` writes
  `0` too.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).
- **Number text is read into its decimal digits by `scan_number`, never
  through a double; more than 34 significant digits or an exponent past
  `decimal128_t` is `errc::range`, and `1e999` is stored exactly.** The
  default traits keep what was sent and refuse what they cannot hold exactly;
  a JavaScript peer reads `1e+999` as `Infinity`.
  Source: `doc/numbers.adoc` (libs/document).
- **Numbers are written by ECMA-262's Number::toString on the stored digits,
  four rows on `k` and `n`, into a `number_text` of 64 characters held by
  value.** Every number `JSON.stringify` writes is then written back byte for
  byte, a number a double cannot hold stays exact, and writing a number or a
  date allocates nothing.
  Source: `include/webcpp/document/number.hpp` (libs/document).
- **`js_traits` hold JavaScript's own doubles: a number rounds as
  `JSON.parse` rounds it, is stored as an `integer` when that double is
  integral and fits, and NaN and the infinities are stored and written
  `null`.** A number then writes back as Node writes the double, and agrees
  with JavaScript on every digit.
  Source: `doc/numbers.adoc` (libs/document).
- **`get<T>()` never truncates or rounds: a number `T` cannot hold exactly is
  `errc::range`, a character type is no number, and a floating-point type
  converts only when the traits' `number` is binary.** A program cannot lose
  digits by accident.
  Source: `include/webcpp/document/detail/convert.hpp` (libs/document).

**Strings, dates and bytes.**

- **The traits' `string` is the stored encoding of strings and keys, `utf8`
  by default or `utf16` in `js_traits`; `length()` counts UTF-16 code units
  either way.** `utf16` is how JavaScript holds strings, and JavaScript counts
  a length in UTF-16 code units.
  Source: `doc/strings.adoc` (libs/document).
- **Text is validated where it enters, by the parser and by `set`
  (`errc::type`); a view reads only the stored encoding, and `std::string`
  and `std::u16string` transcode.** A view reads a string as it is stored and
  cannot transcode.
  Source: `doc/strings.adoc` (libs/document).
- **The parser refuses a lone surrogate with either encoding; `set` keeps one
  under `utf16`, and `stringify` writes it as `\u` and four digits.**
  Boost.JSON's parser cannot deliver one: it refuses it or, with
  `allow_invalid_utf16`, replaces it with U+FFFD, which would change the text
  silently, so the limit is documented and not worked around.
  Source: `doc/parsing.adoc` (libs/document).
- **Dates and bytes are kinds of their own beside JSON's.** JavaScript
  programs send dates and bytes through JSON, as text.
  Source: `doc/strings.adoc` (libs/document).
- **A date is a `date_ms`, milliseconds since the epoch within JavaScript's
  8.64e15 ms either way, written as `Date.prototype.toJSON` writes it, with
  Howard Hinnant's calendar algorithms.** That is how a JavaScript `Date`
  holds a date; `std::chrono::year` does not reach every year a 64-bit count
  of milliseconds does.
  Source: `include/webcpp/document/traits.hpp` (libs/document).
- **Bytes are stored raw and written by the traits' bytes policy: `base64`
  by default, `base64url`, or `javascript_bytes` (`{"0":1,...}`) in
  `js_traits`.** Bytes travel in the image as they are, and
  `javascript_bytes` restores JavaScript's text (reason for base64 as the
  default not recorded).
  Source: `doc/strings.adoc` (libs/document).
- **A parse keeps every string a string unless `revive_dates` or
  `revive_bytes` asks; `get<date_ms>()` and `get<std::vector<std::byte>>()`
  convert a string of the exact format anyway.** JSON has no dates and
  `JSON.parse` keeps strings.
  Source: `doc/strings.adoc` (libs/document).

**Key order.**

- **The traits' object policy orders keys: `javascript_order` by default
  (array-index keys, 0 to 4,294,967,294, ascending, then the others as
  created), `insertion_order`, or `sorted` by UTF-16 code units.**
  JavaScript's OrdinaryOwnPropertyKeys is not insertion order; `sorted` is
  the order of `sort()` and RFC 8785, for canonical JSON, signatures and
  hashes.
  Source: `doc/order.adoc` (libs/document).
- **Assigning a key keeps its place, erasing and creating it again puts it
  where a new key goes, and a key repeated in text, a literal or
  `assign_from` keeps the last value in the first one's place.** It is what
  JavaScript and `JSON.parse` do (the owner's approvals).
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **An object's members are kept in ordered indices, never in a hashed one;
  no hashed container is used anywhere.** Keys come from untrusted text: a
  crafted 4 MB input took Boost.JSON 9.23 s to parse, and no input makes an
  ordered lookup slower than its logarithm.
  Source: `doc/order.adoc` (libs/document).

**Traits.**

- **Traits choose the stored types: `document_traits` fixes `boolean`,
  `integer` and `date` to `bool`, `std::int64_t` and `date_ms`, lets `number`
  be any `stored_scalar` with a `number_codec`, and allows `dense` arrays
  only.** (reason for fixing the others not recorded)
  Source: `include/webcpp/document/traits.hpp` (libs/document).
- **A `stored_scalar` is trivially copyable, of 1, 2, 4, 8 or 16 bytes, and
  stored by its `scalar_codec` least significant byte first; `bool` takes one
  byte.** A scalar's bytes are then the same on every target, and the
  standard does not fix the size of `bool`.
  Source: `include/webcpp/document/traits.hpp` (libs/document).
- **The traits are part of the image: an FNV-1a hash of each codec's name and
  size and of the policies' names, with the sizes and alignments of the
  node, the container and the heap, is the header's layout tag.** An image of
  other traits or another layout is refused with
  `errc::incompatible_document`, never read wrongly.
  Source: `include/webcpp/document/detail/tree.hpp` (libs/document).

**Handles.**

- **A handle (`value`, `const_value`) holds the document's address and node
  ids, never a pointer into the tree, and resolves its place again at every
  call.** It stays valid when the image grows and moves, reads what is there
  now, and reads `undefined` once its node is erased.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).
- **A handle names a node, a missing member or element of a container that
  exists, which `set` creates, or nothing; `operator[]` and `at` never
  fail.** JavaScript reads `undefined` where nothing is there, and `set`
  through nothing is `errc::type`, JavaScript's `TypeError`.
  Source: `doc/handles.adoc` (libs/document).
- **A handle is invalid once its document is moved from or destroyed, and a
  `std::string_view` read from a value is valid until the next change.** As a
  container's iterators are, a ruling of the owner.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **Assignment to a handle writes to its place and never rebinds it, so a
  handle is not a regular value and must not be swapped or sorted.** `h = x`
  is JavaScript's `v.key = x`, which writes; `std::swap` of two handles
  therefore writes through both.
  Source: `doc/handles.adoc` (libs/document).
- **`WEBCPP_DOCUMENT_NO_DANGLING` marks the handles, the ranges of a
  container's children and their iterators `[[gnu::no_dangling]]` on GCC 14
  and later.** Otherwise `-Wdangling-reference` takes
  `for (auto key : doc["a"].keys())` for a dangling reference.
  Source: `include/webcpp/document/config.hpp` (libs/document).

**Errors and exceptions.**

- **The core never throws an error of its own: every operation that can fail
  returns `result`, and every writing function is `[[nodiscard]]` and
  completes or changes nothing, a full heap included, in a build with
  exceptions and in one without; an allocator's failure is below.** The
  parser's input is the network's, and a failure is a value the program
  tests, not a crash.
  Source: `doc/introduction.adoc` (libs/document).
- **`errc` names JavaScript's errors first, `syntax`, `type` and `range`,
  then `capacity`, `not_a_document`, `incompatible_document` and
  `damaged_document`, which JavaScript has no error for; the category's
  fixed identity is `0x646f63756d656e74`, the ASCII of "document".** The
  first three are the errors JavaScript throws for the same faults, and a
  fixed identity keeps the category free of mutable state.
  Source: `include/webcpp/document/errors.hpp` (libs/document).
- **The exception types are JavaScript's (`syntax_error` with the byte
  offset, `type_error`, `range_error`), with `capacity_error` and
  `image_error`, all derived from `error`, a `std::runtime_error` holding the
  code, and exist only with exceptions.** The sugar throws as JavaScript
  throws.
  Source: `doc/exceptions.adoc` (libs/document).
- **The sugar (`h = x`, `h = other`, `as<T>()`, `as_string()`, `as_bool()`,
  `parse_or_throw`, the owned document's default and copy constructors) is
  each a core function followed by `detail::raise`, with exceptions only.**
  It reads as JavaScript reads, and only what cannot return a `result` (an
  assignment, a constructor) needs exceptions, the owner's decision.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **Without exceptions the sugar stays declared, constrained by the concept
  `detail::exceptions_enabled<T>`, `exceptions_on && sizeof(T) != 0`; only
  its definitions sit behind `#ifndef WEBCPP_DOCUMENT_NO_EXCEPTIONS`.** A call
  then fails where it is made with a diagnostic that names the constraint, a
  generic program can ask with the concept whether the sugar is there, and
  the test `no_exceptions` holds the diagnostics.
  Source: `include/webcpp/document/config.hpp` (libs/document).
- **An allocator's failure is an error value: with exceptions, an operation
  catches `std::bad_alloc`, a type derived from it, or Boost.Interprocess's
  `bad_alloc` where it can still return (`detail::unless_allocation_fails`),
  and returns `errc::capacity` with the document's content as it was, since a
  change allocates all its working state before its first change; anything
  else an allocator throws, and any allocator's failure without exceptions,
  ends the program, as it does for a standard container.** A full resource is
  then what a full image is, a value the program tests: only the bytes of
  the heap's free space may differ, and a failed `parse_into` leaves its
  buffer formatted, with the part of the document it built.
  Boost.Interprocess's allocators throw a `bad_alloc` of their own, derived
  from `std::exception` alone, and anything else leaves a `noexcept`
  operation. `stringify`, whose result is its text, and the move assignment
  between allocators that neither propagate nor are always equal, which has
  no result, throw `std::bad_alloc`; the sugar throws `capacity_error`; and
  the standard allocator's image, from the aligned `operator new` that
  returns null, is `errc::capacity` in either build.
  Source: `doc/allocation.adoc` and
  `include/webcpp/document/detail/allocation.hpp` (libs/document).
- **An allocation in the image that fails after its probe passed is reported
  through `boost::throw_exception(std::bad_alloc())`.** It is a bug of the
  library, never a run-time event, since every operation finds its room
  first.
  Source: `include/webcpp/document/detail/heap.hpp` (libs/document).

**The image.**

- **A document is one image: a 64-byte header, then a Boost.Interprocess
  `rbtree_best_fit` heap, used directly and 16-aligned, holding one
  Boost.MultiIndex container of nodes.** One relocatable image can be copied,
  sent, opened in place, shared between threads and processes and handed to
  a Worker without a parse; a `boost::json::value` holds pointers and can do
  none of it.
  Source: `changes/archive/2026-10-12-genesis/proposal.md` (proposals).
- **Every pointer in an image is an `offset_ptr<T, std::int64_t,
  std::uint64_t, 8>` and every size a `std::uint64_t`.** The image then works
  at any 16-aligned address and has the same bytes on 64-bit native and
  wasm32 (measured: one digest on Clang, GCC, wasip2 and Emscripten).
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).
- **The header holds the magic `WCPPDOC`, the format version, a byte-order
  mark, four reserved zero bytes, the layout tag, the size, the container's
  offset (always the heap's first block), the next node id and the seal, in
  the writer's byte order; another version, byte order, layout or nonzero
  reserved bytes is refused, never converted.** (reason for refusing rather
  than converting not recorded)
  Source: `include/webcpp/document/image.hpp` (libs/document).
- **The format version, `format_version` (1), is the library's own constant
  and the header carries no Boost version; a layout change raises it with a
  migration, and `format_test` compares golden compact images under both
  traits on every toolset.** Boost releases often and the structures the
  image holds rarely change, so a Boost upgrade must not change the format,
  and the goldens catch the release that does; they are written again only
  with a raised version.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).
- **The tree is one `multi_index_container` with three ordered indices:
  `by_id`, `by_order` on parent, group and ordinal, and `by_key` on parent
  and key, by UTF-16 code units whatever the encoding.** `by_id` serves a
  handle's lookup, `by_order` an element by index and members in the
  policy's order, `by_key` a member by key and the key-ordered queries.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **Node ids are unique and never reused; the root's is 1.** Handles and
  iterators hold ids, so no change makes one name another node.
  Source: `specs/document/spec.md` (proposals).
- **A node takes 192 bytes whatever it holds, with a 16-byte scalar, and a
  string's or a key's bytes take a block of exactly their size, a
  `detail::byte_string`, never a `boost::container::string`.** A
  `boost::container::string` may allocate past the size and throws on
  failure.
  Source: `include/webcpp/document/detail/heap.hpp` (libs/document).
- **Free memory is zero: a buffer is zeroed when made or grown, the allocator
  zeroes each block it hands out and frees, nodes are built in place by
  `emplace`, and each index's empty key extractor and comparator carries a
  zeroed byte.** An erased value, a secret among them, leaves none of its
  bytes, and the image is a function of the operations alone; the byte is
  there because MSVC copies an empty temporary's byte without writing it,
  which put stack garbage in the image.
  Source: `include/webcpp/document/detail/tree.hpp` (libs/document).
- **An image is trusted input: opening checks the header, the heap's own
  sanity and the offsets to the root, not every offset inside the tree, and
  untrusted data enters as JSON text.** Those checks cannot prove every
  offset sound, so the page says "never open an image from a source you do
  not trust" wherever images appear.
  Source: `doc/images.adoc` (libs/document).

**Memory and storage.**

- **Storage is the second template parameter, `basic_owned<Allocator>`, the
  document's own 16-aligned buffer, which starts at 4,096 bytes and grows to
  twice its size or what an operation needs, up to `max_bytes` (1 GiB by
  default), or `basic_external<Allocator>`, a caller's `std::span<std::byte>`
  such as a browser's memory, which never grows, each of any allocator of
  `std::byte`: `owned` and `external` are the standard allocator's, and
  `wd::pmr` names a memory resource's (`pmr::owned`, `pmr::external`,
  `pmr::document`, `pmr::basic_document`, `pmr::value`, `pmr::const_value`,
  `pmr::parser`).** A document can live in memory it does not own, where a
  full buffer is `errc::capacity` and changes nothing; and chapter 4 asks
  for an allocator, which trystero needs to keep every allocation of a room
  in the room's resource (the 1 GiB default and the 4,096 start: reason not
  recorded).
  Source: `doc/allocation.adoc`, `doc/images.adoc` and
  `include/webcpp/document/storage.hpp` (libs/document).
- **The allocator, rebound by construction, holds the owned image and the
  working state of every operation, owned or external: the records a change
  stages, the stacks of a deep copy and a compaction, the parser's frames,
  path, pending text and selectors, the writer's frames and held piece past
  its own room, a missing member's key, the buffers a value is prepared in,
  and the keys `Object.assign` takes.** A rebound allocator is constructed
  from the document's, as the Allocator requirements ask, so one whose
  rebinding constructor is explicit serves as well; for an external document
  the working state is all the allocator holds.
  Source: `doc/allocation.adoc` (libs/document).
- **An owned image is allocated in blocks of 16 bytes, so that a resource is
  asked for an alignment of 16, and a buffer given misaligned is given back
  at once and is `errc::capacity`; the region keeps the allocator's own
  pointer to it, and every pointer inside the image is an `offset_ptr`.** The
  image's heap needs 16-aligned addresses, which are over-aligned where
  `std::max_align_t`'s alignment is 8, as on arm64 macOS and MSVC, so an
  allocator that ignores the request is refused rather than trusted; an
  allocator whose pointer carries a segment or a tag gets back what it
  handed out; and the standard allocator's image keeps the global aligned
  `operator new` that returns null.
  Source: `doc/allocation.adoc` and `include/webcpp/document/detail/heap.hpp`
  (libs/document).
- **A document is allocator-aware as the standard containers are: a move
  takes the allocator; a move assignment between allocators that neither
  propagate nor are always equal copies the owned image into the target's
  and frees the source's, and is `noexcept` for allocators that propagate or
  are always equal and for every external document; the copy constructor
  asks `select_on_container_copy_construction`; `clone()` keeps the
  document's allocator, and `clone(alloc)`, `create`, `parse`, `parse_into`,
  `from_image`, `format`, `open` and `nothing` take one.** A program that
  keeps a document in a resource of its own copies it there with `clone()`,
  while the copy constructor gives what a standard container's copy gives,
  the default resource for a polymorphic allocator; an external image, which
  no allocator holds, is taken as it is.
  Source: `doc/allocation.adoc` and `include/webcpp/document/document.hpp`
  (libs/document).
- **Most `const` reads ask the allocator for nothing, `stringify` among them,
  whose text and stack are in the standard allocator; `stringify_to` past
  its own room (deeper than 16 containers, or a piece over 4096 bytes),
  `operator[]` of a missing member whose key is longer than a short string
  holds, and each copy of that handle, `clone`, `slice`, `concat` and
  `compact_into` do, so that threads using those on one document at once
  need a resource safe for several threads.** A standard container
  allocates nothing in a `const` member, and several threads read it at
  once whatever its resource; a document's reads keep that promise but for
  those, which the page lists.
  Source: `doc/allocation.adoc` (libs/document).
- **The image is the shareable type; a `basic_document`, its handles, its
  parsers, its writers and the views of the pools hold the process's
  addresses, the image's and the allocator's, and are not.** Each process
  that maps an image opens it with a document of its own.
  Source: `doc/allocation.adoc` (libs/document).
- **Every change finds its room first: it lists its blocks (a node bounded by
  `node_probe_bytes`, `sizeof(node) + 128`, a string at its exact size),
  probes the heap with the non-throwing `allocate` and frees the probes,
  grows an owned region or returns `errc::capacity`, stages its working
  state in the document's allocator, then allocates for real and rearranges
  by steps that cannot allocate; a change that its place cannot take is
  refused before its value is prepared, and an erasure lists the nodes it
  erases through those nodes themselves, so it cannot run out of room,
  though it still returns `errc::type` or `errc::range`.** A full heap is
  then an error value and the document is unchanged; Boost.MultiIndex does
  not name its node type, hence the bound, and the heap is deterministic, so
  the probed blocks are found again. A refusal that allocates nothing keeps
  the promise that a document holding nothing allocates nothing, and a
  lookup by key and `==` allocate nothing either.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals);
  `doc/allocation.adoc` (libs/document).
- **A `modify` only swaps prepared values.** Boost.MultiIndex erases an
  element whose `modify` throws.
  Source: `AGENTS.md` (libs/document).
- **`reserve` and `capacity` are `std::vector`'s for an image, and
  `shrink_to_fit` gives back only the free tail.** A batch of a known size
  then moves the image once; blocks never move, so a shrink cannot pack.
  Source: `doc/images.adoc` (libs/document).
- **`compact()` rebuilds an image in document order, ids renumbered, blocks
  one after another with no hole, so equal content gives byte-identical
  images and a compact image compacts to itself.** The owner asked that an
  image on the wire carry no waste and that equal documents have equal bytes,
  which can then be compared, hashed, stored and sealed by their bytes.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **`compact()` builds the new image before it replaces the old one, not in
  place.** That gives the strong guarantee; an in-place compaction would move
  blocks that handles point into.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **`compact_size()` is exact and allocates nothing, its block sizes taken
  from `rbtree_best_fit`'s arithmetic and a scratch heap on the stack, and
  `compact_into(buffer)` writes the compact image into a caller's buffer.**
  A program sizes a block with it; the figure follows the build's Boost
  release with no constant repeated, and `compact_into` serves documents
  that cannot reallocate, leased or shared.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).

**Seal.**

- **An image may be sealed: the CRC-32C of the whole image (Boost.CRC's
  header-only `crc_optimal`), its own eight bytes taken as zero, at header
  offset 48 with the high bit as a marker; any later change clears it.** It
  catches bytes changed by accident (a flipped bit, a torn or stray write),
  and a cleared seal means an image is never wrongly sealed.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **Opening (`open`, `from_image`, the image reader, `shared_document`)
  checks a sealed image first, before any other header field is trusted,
  unless `verify::none`; `async_write_image` seals before it writes.** A
  change anywhere, magic and size included, then reads as
  `errc::damaged_document`; `verify::none` is for a program that trusts its
  memory, as a check costs a pass over the image (about 600 MB/s).
  Source: `include/webcpp/document/image.hpp` (libs/document).
- **A seal is a checksum, not authentication.** Anyone can compute a valid
  seal for any bytes, so an image stays trusted input.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).

**Parsing and selectors.**

- **`parse` is `JSON.parse` over RFC 8259 and accepts nothing more: no
  comments, no trailing commas, whitespace of space, tab, LF and CR, and
  anything but whitespace after the text is `errc::syntax`.** It accepts what
  `JSON.parse` accepts.
  Source: `doc/parsing.adoc` (libs/document).
- **`basic_parser` takes text in chunks split anywhere, feeds Boost.JSON's
  `write_some` with numbers left as text, and builds the document node by
  node by ids.** The document may grow and move between chunks, numbers stay
  exact, and any split gives the document a whole parse gives.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).
- **A text given whole, to `parse`, `parse_into` or the `finish_with(last)`
  of a parser given no text before, never suspends Boost.JSON's parser; a
  parse fed in chunks makes it allocate its suspension stack in the global
  heap, once at the first suspension and again at each deeper one, the one
  allocation of a parse outside the document's allocator; `finish()` keeps
  its published signature.** Boost.JSON offers no way to place that stack;
  and `finish_with` is a member of its own, since an overload of `finish`
  would have `&basic_parser::finish` compile no more without a cast.
  Source: `doc/allocation.adoc` and `include/webcpp/document/parser.hpp`
  (libs/document).
- **A parser that failed, by its text, a limit or a callback's failure or
  exception, stays failed, and a finished one takes no more text, until
  `reset()`.** (reason not recorded)
  Source: `include/webcpp/document/parser.hpp` (libs/document).
- **`parse_options` defaults to `max_depth` 256, `max_bytes` unlimited and
  counting every chunk, and `max_document_bytes` 64 MiB, where a document
  from `create` keeps 1 GiB.** A value takes at least 192 bytes of image: 2 MB
  of `[0,0,...]` made 268 MB, and under 1 GiB 11 MB of such text took 9 s and
  2.2 GB before failing where 64 MiB fails 700 KB in 0.4 s (the depth of 256
  is a ruling, reason not recorded).
  Source: `include/webcpp/document/parse.hpp` (libs/document).
- **Selectors are a subset of JSONPath: `$`, `.name`, `['name']`, `[n]`,
  `[*]` and `.*`; other text is `errc::type`.** A ruling of the owner;
  JSONPath beyond it is a non-goal (reason not recorded).
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **`on` delivers each matching value when it completes and erases it, its
  blocks zeroed and freed; `observe` delivers it and keeps it; a callback
  gets a `const_value` and the path in the text.** A stream of a million
  elements then needs the memory of one, and a callback cannot change the
  document being built: it copies what it keeps.
  Source: `doc/selectors.adoc` (libs/document).
- **`path_view::to_string()` escapes only `'` and `\`, so it is not RFC
  9535's normalized path.** Those are the two escapes the selectors read, so
  the text parses back as the selector of that place.
  Source: `include/webcpp/document/parser.hpp` (libs/document).

**Writing JSON.**

- **`stringify` returns a `std::string` of `JSON.stringify(v, null,
  indent)`'s bytes, the indent clamped to 10, and no text for `undefined`,
  and keeps its stack in that string's allocator, asking the document's for
  nothing.** `JSON.stringify` clamps its third argument to 10 and returns no
  text for `undefined`; and a `const` read that asks a document's resource
  for nothing can run on several threads at once.
  Source: `include/webcpp/document/detail/writer.hpp` and
  `include/webcpp/document/stringify.hpp` (libs/document).
- **`stringify_to` writes the same bytes to a sink, a callable returning
  `void` or `result<void>` used in place and never copied, in pieces of at
  most `chunk` bytes (4096 by default), every piece but the last full, and
  allocates in the document's allocator only past its own room, for a value
  nested deeper than 16 or a piece held back over 4096 bytes.** A sink's
  failure stops the writing and is returned unchanged, as an allocator's is
  as `errc::capacity`; a value nested 16 deep or less, in pieces of at most
  4096 bytes, allocates nothing, so a dozen small texts take nothing of a
  small arena (the 4096 default is a ruling, reason not recorded).
  Source: `include/webcpp/document/stringify.hpp` and `doc/stringify.adoc`
  (libs/document).
- **`quote` is `JSON.stringify` of a string alone: it appends the string as a
  JSON string literal, its quotes included, to any string the caller gives
  (`std::string`, `std::pmr::string`, or any type with
  `append(const char*, std::size_t)`), with the bytes `stringify` writes of
  the same string, from the same code, and that string is the only thing
  that allocates.** A JSON text of a fixed shape is then written field by
  field into memory the program chooses, without a document, as trystero
  writes its protocol's texts. UTF-8 text that is not valid, which no
  JavaScript string is, returns `errc::type` and leaves the string as it
  was; UTF-16 text writes a lone surrogate as `\u` and four lowercase hex
  digits, as JavaScript does since ES2019.
  Source: `doc/stringify.adoc` (libs/document).
- **The writer walks with a stack of its own that holds node ids, never
  recursion and never nodes, its first 16 frames in room of its own.** A
  document's depth is then bounded by memory, not by the thread's stack,
  nothing the walk holds is stale when the image moves, and a shallow value
  is written with no allocation.
  Source: `include/webcpp/document/detail/writer.hpp` (libs/document).

**Streams of documents and Boost.Asio.**

- **`basic_stream_parser` is sans-IO, with three framings, `concatenated`,
  `lines` (NDJSON) and `rfc7464`, each document parsed as `parse` parses one
  text, under the same limits per document, taken by `next()` or pushed to a
  callback.** Sans-IO serves any source: a socket read by hand, a file, an
  actor's messages, JavaScript through Emscripten.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **A bad document either stops the stream until `reset()` or, with `skip`,
  is dropped and its error delivered in its place; `skip` with
  `concatenated` makes every call return `invalid_argument`.** Concatenated
  JSON has no place to go on from after a bad document.
  Source: `doc/streams.adoc` (libs/document).
- **With `lines`, a document ends at its line's raw `\n`, and a line with two
  documents or an incomplete one is an error for that line.** JSON never holds
  a raw `\n` inside a string, so a raw `\n` always ends a line; indented JSON
  is therefore not NDJSON.
  Source: `doc/streams.adoc` (libs/document).
- **`asio.hpp` is the one header that includes Boost.Asio; the convenience
  header leaves it out, and every program that includes it is declared
  `native`.** Boost.Asio builds natively only.
  Source: `AGENTS.md` (libs/document).
- **`async_read_document` takes both of Asio's dynamic-buffer models,
  `DynamicBuffer_v1` by reference and `DynamicBuffer_v2` by value, reads a
  buffer of several pieces without joining them, and asks reads of 512 to
  65,536 bytes.** A body Beast left in a `multi_buffer` after a header is
  read with no byte lost, and reads are sized as Boost.Asio's own.
  Source: `include/webcpp/document/asio.hpp` (libs/document).
- **No completion is called inside its initiating function (it goes through
  `async_immediate` or a post), and a stream that ended completes with `eof`
  without another read.** Linux's epoll reactor does not retry a read that
  returned no bytes, so a second read of an ended socket never completed.
  Source: `specs/document/spec.md` (proposals).
- **`async_write_images` seals every document first, then writes all the
  images in one gather write with no copy.** (reason not recorded)
  Source: `doc/wire.adoc` (libs/document).

**Images on the wire.**

- **An image frames itself, its header stating its size, so a stream of
  images needs no separator and no length prefix.** A reader with the first
  64 bytes of an image knows where it ends.
  Source: `doc/wire.adoc` (libs/document).
- **`image_pool` allocates its blocks once, in one allocation; each image is
  read straight into a leased block and opened there as a `leased_document`,
  and a block given back is zeroed.** The receiver parses nothing and
  allocates nothing per message, and the next holder finds none of the last
  one's bytes.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **A full pool is `errc::capacity`, and the stream is not read until a
  block comes back.** That is the backpressure of a stream of images.
  Source: `doc/wire.adoc` (libs/document).
- **`basic_image_reader` is sans-IO with `prepare` and `commit`, checks a
  header before it takes another byte, and stops at its first refusal until
  `reset()`.** `prepare` and `commit` let a socket read straight into the
  block, and a stream that lost its framing cannot find the next header.
  Source: `specs/document/spec.md` (proposals).
- **An `image_pool` is not thread-safe.** (reason not recorded; a
  `shared_pool` is the pool for threads and processes)
  Source: `include/webcpp/document/image_stream.hpp` (libs/document).

**Sharing.**

- **`shared_pool` formats memory the program gives, the process heap or a
  shared-memory segment, as a 64-byte header and blocks of a 64-byte header
  and one image, and works through offsets from the region's start, never
  addresses.** Every process that maps the region, at whatever address, then
  uses the same pool.
  Source: `include/webcpp/document/shared.hpp` (libs/document).
- **A block's reference count is a lock-free `std::atomic<std::uint64_t>`
  in the block's header, never in the image, and the free blocks are a
  lock-free stack whose top carries a 32-bit tag against ABA;
  `is_always_lock_free` is asserted.** A lock-free atomic is address-free, no
  lock is held so no thread or process waits and a dying one leaves none
  behind, and the image stays the document's content: a count inside it
  would mean nothing elsewhere.
  Source: `include/webcpp/document/shared.hpp` (libs/document).
- **`shared_document` is `std::shared_ptr` for a document, and
  `make_mutable()` copies the image into a block of its own when others hold
  it.** Readers share one image in place, and a writer changes its copy while
  the others keep the document as it was.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **The library does not synchronise writers.** The owner's ruling: the
  process controls the memory.
  Source: `changes/archive/2026-10-12-genesis/reference/spec.md` (proposals).
- **A reference crosses processes by offset, `release` and `adopt`, and
  `shared_pool::drop(offset)` gives one back without opening the image.** A
  broken header then cannot make a block leak.
  Source: `specs/document/spec.md` (proposals).
- **A process that dies holding references leaves their blocks counted for
  good; recovering them is the program's.** Boost.Interprocess's own
  `shared_ptr` does the same, and recovery is left out of 0.1.0.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).

**Containers.**

- **`as_object()` and `as_array()` give views with the standard containers'
  interface, map-like and vector-like, two words that own nothing, ranges
  that are views and borrowed ranges, whose iterators hold ids.** A C++
  program walks a document with the standard algorithms, and since ids are
  never reused an insertion and any growth keep every iterator valid.
  Source: `include/webcpp/document/containers.hpp` (libs/document).
- **The views' iterators are bidirectional, not random access.** An index
  costs O(log n), since the tree finds an element by its index.
  Source: `specs/document/spec.md` (proposals).
- **`by_key()` gives an object's members in UTF-16 code-unit order with
  `lower_bound`, `upper_bound` and `equal_range`; a prefix query is two
  bounds.** The `by_key` index is already ordered, so nothing is sorted,
  where a JavaScript program sorts every key at each query.
  Source: `doc/containers.adoc` (libs/document).

**The JavaScript module and the npm package.**

- **The JavaScript API is the library compiled with Emscripten and embind,
  `js/binding.cpp` over `default_traits`, wrapped by `js/webcpp-document.mjs`
  in `Document` and `StreamParser`.** A JavaScript program keeps its values
  and errors and gets what JavaScript lacks: exact numbers (`getDecimal`),
  ordered-key queries (`keysInRange`), images, memory it frees.
  Source: `doc/js-module.adoc` (libs/document).
- **Nothing throws into JavaScript: each native call returns an `Outcome`
  (code, message, value), and the wrapper throws `SyntaxError`, `RangeError`
  for `range` and `capacity`, or `TypeError` for `type` and the image
  errors.** Each is the error JavaScript throws for the same fault, and the
  binding uses no sugar, so the module builds and passes without exceptions.
  Source: `js/binding.hpp` (libs/document).
- **A `Document` is addressed by paths, arrays of string keys and
  non-negative integer indices, and `get` returns a container as a copy.**
  (reason not recorded)
  Source: `doc/js-module.adoc` (libs/document).
- **`free()` releases a document at once, and a `FinalizationRegistry`
  releases one never freed.** The collector runs when the engine chooses, not
  when the program needs the memory, so the registry is a safety net and not
  a plan.
  Source: `doc/js-module.adoc` (libs/document).
- **An image goes to a Worker as a copy, `image().slice()`, in a transferred
  `ArrayBuffer`, and is opened there with one memory copy and no parse.** A
  view of WebAssembly memory cannot be transferred, and a transfer moves in
  constant time where `postMessage` of an object clones every node.
  Source: `doc/js-module.adoc` (libs/document).
- **A second module, `js/shared/`, runs on one `SharedArrayBuffer` with Wasm
  Workers on pthreads, a fixed 128 MiB memory, 64 blocks of 512 KiB, 32
  Worker slots and 1,024 tokens; a document crosses as a token adopted
  once.** Growing a shared memory would make every Worker refresh its views,
  and with fixed memory a full heap is an error, not an abort; Wasm Workers
  alone cannot link C++ exceptions in Emscripten 6.0.11.
  Source: `js/shared/Jamfile` (libs/document).
- **`join.js` reads internals of Emscripten 6.0.11 (`createWasm`,
  `wasmMemory`, `updateMemoryViews`), which ties the shared module to that
  version.** An accepted risk until it is checked against another version.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).
- **`@webcpp/document` is staged from the `-O3` build with TypeScript
  declarations written by hand, has no dependencies and needs Node 22 or
  newer.** embind's own declarations describe the module the wrapper uses,
  not the wrapper; Emscripten's floor is Node 18.3, but the tests use
  `import.meta.resolve` and `node:test`.
  Source: `.github/workflows/npm.yml` (libs/document).
- **The package is published from a tag `v<version>` by npm trusted
  publishing (OIDC, no token secret), with provenance; the first
  publication is the owner's, by hand.** A trusted publisher can be added
  only to a package that exists.
  Source: `.github/workflows/npm.yml` (libs/document).

**Targets and portability.**

- **Tests and examples run natively (Clang, GCC), on Emscripten, wasip2 and
  wasip3; a program that needs Boost.Asio, Cobalt, Beast, threads or shared
  memory is native, and the xactor example native, wasip2 and wasip3.**
  Boost.Asio builds natively only.
  Source: `test/Jamfile` (libs/document).
- **`wd::array{wd::array{1}}` is `[1]` under MSVC and Clang before 20 and
  `[[1]]` elsewhere; the Doc Comment of `array` states it and the tests nest
  through `wd::literal`.** Those compilers apply CWG 1467 to every class and
  read a one-element nested braced list as a copy; recorded as an accepted
  risk.
  Source: `include/webcpp/document/literal.hpp` (libs/document).

**Evidence.**

- **Node is the oracle: a case is a JSON text, an indent and operations,
  each value written as JSON text; `oracle.mjs` writes Node's bytes and
  return values, which are committed, and `oracle_cases` must reproduce them
  under both traits.** The behaviour is proven by running the same cases in
  Node and in C++ and comparing bytes, and values as text keep either side
  from reading a number through a double.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).
- **54 cases are written by hand and 200 generated from a fixed seed; a case
  of numbers a double does not keep runs under `js_traits` alone, and the
  script refuses a case that holds a difference made on purpose.** Those
  differences are listed in the page's table instead, since the two sides
  differ by design.
  Source: `specs/document/spec.md` (proposals).
- **Compound changes are tested in external buffers of every size, and every
  text split at every byte and one byte at a time.** A review named these,
  with growth, look-alike keys and limits, as its focus areas.
  Source: `specs/document/spec.md` (proposals).
- **Allocation-freedom is proven by tests that replace the global
  `operator new` and `operator delete`, aligned forms included, and count
  calls: reading a stream of images and every shared-pool operation make
  none.** The replacements are the test program's instrument, the one place
  a mutable global is allowed.
  Source: `specs/document/spec.md` (proposals).
- **The `allocator*` tests run every operation in a counting resource over a
  monotonic buffer whose upstream is the null resource: no global
  `operator new` but exactly Boost.JSON's stack's in a chunked parse and
  `stringify`'s own, every byte given back, and with exceptions each operation
  failed at each of its allocations in turn, every failure `errc::capacity`
  or a throwing place's `std::bad_alloc`, with the document's content as it
  was and nothing it took kept; both traits and all three key orders; and
  allocators of the tests' own: one that under-aligns, one whose pointer is
  tagged, a resource that throws Boost.Interprocess's `bad_alloc`, one whose
  rebinding constructor is explicit, one that propagates on a move
  assignment, and one stateful but always equal.** Every allocation then has
  a place the page names, a failure at any of them is shown to be a value,
  and a leak on a path of failure fails.
  Source: `doc/allocation.adoc`, `test/allocator_test.cpp` and
  `test/counting.hpp` (libs/document).
- **Each example's `.expected` is what Node prints for the same JavaScript,
  checked against Node before it is committed, and `document_image.expected`
  holds a digest of an image.** The page's output is then JavaScript's, and
  the digest, the same on every target, proves the image's bytes are.
  Source: `AGENTS.md` (libs/document).

**Benchmarks.**

- **Seventeen operations are timed three ways, Boost.JSON, document and V8's
  objects, the C++ natively and as WebAssembly in the same Node and Chrome:
  fourteen from recognised suites over nativejson-benchmark's files and
  seeded synthetic objects, and three of binary transmission.** Each row
  compares the three where a web application runs them; operations and data
  never come from document's own tests, and binary transmission, which no
  suite times, is the case the image is built for.
  Source: `doc/benchmarks.adoc` (libs/document).
- **Every implementation must give the same answer before it is timed,
  loading is never timed, the first pass is timed alone, and a result is the
  median of 10 samples of at least 10 ms.** A run whose implementations
  disagree writes no results, and the first pass shows the code before the
  JIT or the caches have seen it.
  Source: `doc/benchmarks.adoc` (libs/document).
- **The sizes on the wire, raw, gzip and brotli, of the text and of the image
  are measured apart, and the page says compressed JSON is the smaller
  payload on a network.** Honesty about cost is a goal.
  Source: `changes/archive/2026-10-12-genesis/design.md` (proposals).

### trystero (serverless WebRTC rooms; port of Trystero 0.26.0; implemented in 0.1.0)

trystero ports Trystero 0.26.0: the peers of a room meet over public Nostr
relays and talk over WebRTC data channels, on Trystero's wire byte for byte,
over webcpp::webrtc: natively libdatachannel's WebRTC and in the browser the
page's own. The decisions are those of the tree the superproject records for
webcpp 0.1.0 (trystero `e9326e9`), which includes the change
`shared-connection` (trystero `2e2dcd4`, webcpp `1a0dcac` and `d9e5fa6`,
2026-10-14), implemented and archived on 2026-11-14, and of webrtc's
increment 3 (trystero's branch `webrtc-backend`, 2026-11-14), which moved both
backends' WebRTC onto webcpp::webrtc and trystero's Asio onto webcpp::asio,
and of trystero's refactor onto webcpp's libraries and Boost (trystero's
branch `refactor`, at `459b08c` on 2026-11-15). The refactor moved the
browser onto webcpp::asio's run model, the native relays onto webcpp::beast
and Boost.URL, and what the core wrote itself onto Boost; replaced the two
backends by one platform backend; moved the core's times, then the backend
interface's clocks, onto `std::chrono` and its integers to a fixed meaning;
gave the examples a relay of their own and twins on Trystero JS; read and
wrote every JSON text with webcpp::document, in the room's resource since
document took an allocator; and bounded what a relay's refused handshake
makes a room read, through webcpp::beast's bounded handshake layer.

**Scope and differences from Trystero JS.**

- **Only what rooms of messages need is ported: the Nostr strategy, the
  signaling, the password handshake, the action wire and the room API; audio
  and video are not, and a room ignores a frame of `@_stream`, `@_track` or
  `@_signal`.** Media is the largest part left: in the browser the page's
  `MediaStream` objects, natively libdatachannel's RTP tracks, whose capture,
  encoding and decoding would be the application's.
  Source: `doc/differences.adoc` (libs/trystero).
- **Nostr is the one strategy; BitTorrent, MQTT, Firebase, Supabase, IPFS and
  the WebSocket relay are not ported.** Each is a strategy of its own to port,
  and Nostr's public relays need no account and no server of the application's
  own.
  Source: `doc/differences.adoc` (libs/trystero).
- **Request actions, `onReceive`, the progress callbacks, cancelling with an
  `AbortSignal`, `onPeerHandshake` and passive rooms are left for later.**
  Meanwhile a room accepts every transfer for an action with a receiver within
  `max_receive_bytes`, as Trystero does when no `onReceive` is set, reports a
  transfer only when it completes, and always announces itself.
  Source: `doc/differences.adoc` (libs/trystero).
- **`trickleIce: false`, `turnConfig` and `rtcPolyfill` are not ported.**
  Candidates are always trickled, as Trystero's Nostr strategy does by
  default; `ice_servers` names every STUN and TURN server; the backend is what
  a polyfill would be.
  Source: `doc/differences.adoc` (libs/trystero).
- **The relay controls (`getRelaySockets`, pausing and resuming reconnection,
  `manualReconnection`, `warnOnRelayFailure`) are not ported.** A room
  reconnects with its own backoff and reports what its relays do through its
  log.
  Source: `doc/differences.adoc` (libs/trystero).
- **`on_peer_join` does not replay the peers already joined.** A join is
  reported from the executor after `join` has returned, so a handler set right
  after `join` sees every join; `peers()` lists the joined peers for a handler
  set later.
  Source: `doc/differences.adoc` (libs/trystero).
- **`peers()` lists ids, not connections.** A connection is the backend's
  object, webcpp::webrtc's over a page's or libdatachannel's, and the room
  does not hand it out.
  Source: `doc/differences.adoc` (libs/trystero).
- **A send to a peer that has not joined completes with `error::no_such_peer`,
  where Trystero warns and resolves.** An operation that fails says so with
  its error code.
  Source: `doc/differences.adoc` (libs/trystero).

**Protocol and wire compatibility.**

- **The wire is Trystero 0.26.0's, byte for byte, and never changes: the topic
  prefixes `"Trystero@"` and `"Trystero:"`, the handshake's `"__trystero_pw"`,
  every constant and layout under `protocol/`, the default relays in their
  order, and the names the chat's page calls (`joinRoom`, `sendText`) and the
  interop page's `window.leave`.** A room joined from C++ and the same
  room joined from Trystero JS must be one room; the `oracle` lane fails when
  Trystero's own values differ from the committed ones.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **A rename never replaces the word `trystero` by pattern: it uses the exact
  C++ patterns (`namespace webcpp::trystero`, `<webcpp/trystero/`,
  `WEBCPP_TRYSTERO_`) and changes a string literal only when it is not on the
  wire.** The wire's strings must survive any rename; the error category
  `webcpp.trystero` and the examples' app ids are the literals that were
  renamed.
  Source: `AGENTS.md` (libs/trystero).
- **The protocol layer is pure functions over bytes and text, with no I/O and
  no platform, and takes every source of randomness as a parameter.** It
  builds on both targets, and its tests compare its values, byte for byte,
  with those Trystero JS computed from the same inputs.
  Source: `doc/protocol.adoc` (libs/trystero).
- **Every text the protocol writes is appended field by field into one
  reserved buffer, its strings quoted by `webcpp::document::quote`, never
  built as a document, and a Nostr event's id is hashed over those same
  bytes.** The texts are fixed shapes of a few strings and numbers; `quote`
  is `JSON.stringify`'s own quoting, from document's writer, where a document
  would copy every string into a node of some 200 bytes and write it again;
  and hashing the written bytes keeps the id and the text from ever
  disagreeing.
  Source: `doc/design.adoc` (libs/trystero).
- **A self id that is not UTF-8 is set aside for a random one when the app is
  made, with a configuration report to `app::on_error`, and a local
  candidate that is not UTF-8 is not reported.** `quote` refuses invalid
  UTF-8, which no JavaScript string holds, and the self id is the only string
  a program gives that a signal writes.
  Source: `doc/protocol.adoc` (libs/trystero).
- **The relay shuffle computes `sin(seed++) * 10000` with `std::sin`.** Every
  peer of an app, Trystero JS included, must pick the same relays; this relies
  on `std::sin` and V8's `Math.sin` agreeing on these inputs, which the
  oracle's fixtures check.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **`str_to_num` sums the UTF-16 code units of a text, as JavaScript's
  `charCodeAt` sees them.** The Nostr kind and the relay shuffle's seed derive
  from that sum, so a non-ASCII id must count as in JavaScript.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **Of two peers, the lower id offers, on the relay that carried the other's
  announcement.** Trystero answers only on the relay that delivered the
  message; the spike's probe, which published every candidate on every relay,
  was rate-limited by one.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-10-09-genesis/reference/research/TRYSTERO_CPP_SPIKE/FINDINGS.md`
  (proposals).
- **A sealed signal carries a 16-byte IV, not the usual 12.** It is the IV
  Trystero draws (`protocol::seal_iv_size`), so that each side opens what the
  other sealed.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **An offer's size is read as a `std::uint64_t` on every target and refused
  beyond 2^53 - 1, as Trystero refuses it.** A float64 size does not fit a
  32-bit `std::size_t`: Emscripten read 2^53 - 1 as 4294967295 (measured).
  Source: `doc/protocol.adoc` (libs/trystero).

**Layers and the backend interface.**

- **The library is layered (protocol, backend interface, app, room, the
  backend's WebRTC, and the platform backend), and the core above the
  interface never includes the platform backend, the backend's WebRTC,
  webcpp::webrtc, libdatachannel, OpenSSL or Emscripten.** The same room runs
  over the browser's WebRTC and libdatachannel's, both through webcpp::webrtc,
  and over the tests' memory relays, on both targets;
  `meta/include-boundaries.json` states the boundary and the lint fails an
  include that crosses it.
  Source: `doc/design.adoc` (libs/trystero).
- **The backend is a handful of abstract classes, not template parameters.**
  Each operation is a call into JavaScript or a network stack, so a virtual
  call costs nothing measurable, while the room stays free of templates over
  the platform and of `#ifdef`, and the tests' memory relays and the platform
  backend are interchangeable at run time.
  Source: `doc/design.adoc` (libs/trystero).
- **Every handler a backend invokes, and every completion of the library, runs
  on the executor after the call that caused it has returned, even when its
  result is known at once.** The room calls these operations from inside
  handlers whose state a completion run there would change under them.
  Source: `doc/design.adoc` (libs/trystero).
- **Text crosses the backend interface as views valid for the call; a data
  channel message is the one value handed over, as `backend::bytes`.** The
  receiver keeps the frame, and taking ownership of it is what spares a copy.
  Source: `include/webcpp/trystero/backend.hpp` (libs/trystero).
- **The backend factory gives a room its randomness and its clocks, and its
  `random` fills from a cryptographically secure source.** The bytes become
  secret keys and nonces.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **The core and the backend interface keep their times as `std::chrono`
  and their integers at a fixed meaning: a time of the backend's monotonic
  clock is a `std::chrono::steady_clock::time_point` (`detail::time_point`),
  which `backend::factory::steady_now()` returns from an origin of the
  backend's, and a delay a `std::chrono::milliseconds`; a Nostr event's
  `created_at` and a subscription's `since` are `std::chrono::sys_seconds`,
  which `backend::factory::unix_now()` returns; a Nostr kind and a counter
  are `std::uint32_t`, an index or a count a `std::size_t`; and the
  backend's clocks reach the core only through `detail::steady_now` and
  `detail::unix_now`, which return the seam's values unconverted.** Chapter
  4's types of a fixed meaning. Every value is Trystero's number, truncated
  where Trystero's is, so nothing a peer sees changes. `double` stays where
  it is JavaScript's Number on Trystero's side, which the oracle's fixtures
  pin: `str_to_num` and the sum of UTF-16 code units it takes, the relay
  shuffle, and the action wire's float64 sizes and offsets. The seam's two
  methods lost the unit their names carried (`now_ms`, `unix_seconds`) when
  their types took it, and the memory backend's virtual clock is a time
  point from the steady clock's epoch, so that its tests compare durations
  exactly.
  Source: `include/webcpp/trystero/backend.hpp`,
  `include/webcpp/trystero/detail/clock.hpp` and
  `include/webcpp/trystero/protocol/nostr.hpp` (libs/trystero).
- **ICE servers are checked in the core: an unusable URL, or a TURN server
  without credentials, is dropped when the app is made and reported, and every
  scheme is lowercased.** WebRTC would refuse them; dropped at once, the app
  goes on with the others on every backend.
  Source: `include/webcpp/trystero/options.hpp` (libs/trystero).

**The backend's WebRTC.**

- **The platform backend makes its peer connections and data channels in
  `webrtc/`, on both targets: `webrtc::peer_connection` and
  `webrtc::data_channel` hold webcpp::webrtc's `basic_peer_connection` and
  `basic_data_channel` over a `std::pmr::polymorphic_allocator` on the app's
  resource, and implement the abstract `backend::peer_connection` and
  `backend::data_channel`.** webcpp::webrtc gives both targets one interface,
  so trystero keeps only its policies over WebRTC, the same on both. The
  abstract classes stay: the tests' memory relays implement them for whole
  rooms on both targets, where node has no WebRTC, and the interop's native
  peer wraps the platform backend's.
  Source: `doc/design.adoc` (libs/trystero).
- **Each keeps a wait of every kind pending on webcpp::webrtc's object,
  re-armed on the executor, and reports what it completes with through the
  backend's handlers: one state that merges the connection's state and its
  ICE state, failed, closed, disconnected, connected (or ICE completed),
  connecting (or ICE checking) and new, as a page sees both.** A failure may
  show in either state first, and the room acts on one: it ends a connection
  failed or closed, and gives a disconnected one 5 s. The browser backend
  merged them so already; natively the merge is new with webcpp::webrtc.
  Source: `doc/design.adoc` (libs/trystero).
- **A local candidate leaves as the JSON of an `RTCIceCandidateInit`, and a
  remote one is read from that JSON, on both targets; natively a TURN URL
  with credentials is written `turn:user:credential@host` by webcpp::webrtc.**
  The first is the form Trystero JS adds with `addIceCandidate`, the second
  the form libdatachannel parses.
  Source: `doc/design.adoc` (libs/trystero).
- **A channel reads every message as it comes, with `async_receive`, into a
  vector of the app's resource, and drops a text message, or a binary one
  larger than any room frame, on the executor.** Neither can be a frame.
  webcpp::webrtc reads a text as the UTF-8 it holds, so the browser's old
  faults (the text `1e300` threw a `RangeError` out of `new Uint8Array`, and
  `300000000` made a 300 MB frame) cannot arise; and it bounds what it reads:
  natively libdatachannel cuts a message to 256 KiB, and in the browser a
  message past 256 KiB, or unread messages past 16 MiB, close the channel.
  Source: `doc/design.adoc` (libs/trystero).
- **Valid frames received before the message handler is installed wait in a
  FIFO bounded by 64 frames and 10 seconds, on both targets.** These are the
  original Trystero peer's pending-data bounds. Overflow or expiry closes the
  channel; a close releases the retained frames. Installing a handler
  schedules delivery on the executor, preserving order with later arrivals and
  rechecking the current handler and channel after each callback. It never
  calls a message handler synchronously from `set_handlers`, where adoption
  may still be initializing the shared connection. Queued frames use the
  supplied resource, and the expiry is a timer of the factory's.
  Source: `doc/design.adoc` (libs/trystero).
- **The channel reports the buffered amount falling to 64 KiB only after a
  send left it above, as `onbufferedamountlow` does.** webcpp::webrtc's wait
  completes whenever the amount is at or under the threshold, and the shared
  connection gives the bindings waiting to send their turn at each fall, as
  the browser's event did.
  Source: `include/webcpp/trystero/webrtc/data_channel.hpp` (libs/trystero).

**The platform backend.**

- **One class, `platform::backend` (`include/webcpp/trystero/platform/`),
  implements the backend interface on both targets, in place of
  `native::backend` and `browser::backend`, with no alias; the abstract
  classes of `backend.hpp` stay, for the memory relays and the interop's
  native peer (above).** The owner's decision 3 of trystero's refactor
  (2026-11-14): everything but WebRTC was written twice, and webcpp::asio,
  webcpp::beast and webcpp::webrtc now give both targets one interface. No
  version is released yet (0.1.0 is in preparation, chapter 19), so the
  rename costs no release.
  Source: `doc/design.adoc` and `doc/platform.adoc` (libs/trystero).
- **Two parts are the target's own, chosen by `WEBCPP_TARGET_EMSCRIPTEN`: the
  sealer, natively OpenSSL's AES-256-GCM and in a page `crypto.subtle`, and
  the source of randomness, natively OpenSSL's `RAND_bytes` and in a page
  `crypto.getRandomValues`; the WebRTC, the relays' session, the timer
  (`detail::timer`) and the clocks (`std::chrono::system_clock` and
  `std::chrono::steady_clock`) are one code on both.** Until webcpp::crypto
  is built (chapter 17), the platform's crypto is the target's own;
  Emscripten reads the standard clocks from the page's `Date.now()` and
  `performance.now()`, as the browser backend did through embind. A library
  chooses its code by config's target macro, not the compiler's (chapter 15,
  config).
  Source: `doc/platform.adoc` and `doc/design.adoc` (libs/trystero).
- **The platform's one source of randomness is checked wherever it is drawn:
  `random()` aborts the program without it, and a seal fails with
  `error::backend_failure`; in a page it is `crypto.getRandomValues`, called
  from JavaScript that catches what it throws, so that a page whose function
  is missing or throws has none.** Without secure randomness nothing is
  safe: the browser backend ignored a failed `getentropy` before trystero's
  refactor, as chapter 17 recalls, and that is not repeated; and Emscripten's
  `getentropy` lets the page's exception into WebAssembly, which no call may
  (below).
  Source: `include/webcpp/trystero/platform/entropy.hpp` and
  `include/webcpp/trystero/platform/backend.hpp` (libs/trystero).
- **The window of `backend_config::max_peer_connections_per_minute` (256)
  bounds the connections the backend makes for every app and room it serves,
  on both targets, beside its runtime's cap.** A room makes at most 64 in any
  57 s, so the default lets four rooms do so at once; and the window is a
  policy, not a platform's: in a page a collection frees closed connections
  from the census, after which only the window bounds how fast a flood makes
  new ones.
  Source: `doc/platform.adoc` and `doc/design.adoc` (libs/trystero).
- **The platform backend owns a webcpp::webrtc runtime, made with
  `backend_config::runtime` in `backend_config::memory`, at most 256
  connections alive at once, or takes the program's; each of its connections
  and channels keeps that runtime alive.** A connection that outlives the
  backend in a handler the `io_context` still holds must not outlive the
  runtime; and natively libdatachannel's state is the process's, which holds
  one runtime at a time, so a program with several backends, or with
  webcpp::webrtc beside trystero, gives each the one it made.
  Source: `doc/platform.adoc` (libs/trystero).
- **The platform backend's one timer, the core's `detail::timer`, over
  webcpp::asio's steady timer, on both targets, numbers its waits, so that a
  wait cancelled, restarted or destroyed never fires.** Asio may already have
  queued its expiry as a success; on emscripten the wait is in the reactor's
  timer queue, so it fires only while the program runs its `io_context`.
  Source: `include/webcpp/trystero/detail/timer.hpp` (libs/trystero).
- **The sealer is asynchronous on both targets: natively it works
  synchronously and posts its completion.** Web Crypto is asynchronous, so
  the interface is, and a completion never runs inside the call that started
  it.
  Source: `doc/platform.adoc` (libs/trystero) and
  `libraries/trystero/openspec/changes/archive/2026-10-09-genesis/reference/research/TRYSTERO_CPP_SPIKE/FINDINGS.md`
  (proposals).
- **The relays' WebSocket is one session of webcpp::beast on both targets,
  natively Boost.Beast's own WebSocket stream, over webcpp::beast's bounded
  handshake layer, and in a page webcpp::beast's page `WebSocket`: Asio
  operations composed by callbacks (resolve, connect, TLS, handshake, a read
  loop, one write at a time), each handler bound to the room's allocator,
  and a connection that ends during a write clears its queue while the write
  finishes on the text it moved out of it.** Beast
  allows one write at a time, and the write's completion must never touch
  the cleared container; callbacks rather than coroutines, so that no
  coroutine frame, and no read buffer, is allocated outside the room's
  resource. The session names webcpp::asio and webcpp::beast only, and
  serves both targets.
  Source: `include/webcpp/trystero/platform/websocket.hpp` (libs/trystero).
- **The session's reads and writes complete into a handler of its own, which
  carries the room's allocator and no executor, never into Asio's
  `any_completion_handler`, and which calls the session's member through a
  pointer.** An `any_completion_handler`'s executor is of another type than
  the stream's, so Asio made an `any_completion_executor` with `new` for each
  operation and wrapped each completion in a function object of its own
  (measured natively: six `operator new` for a text sent and its echo
  received, and none now, `platform_websocket_allocation`); and through the
  pointer misc-no-recursion sees no cycle through Asio's post, on either
  target.
  Source: `include/webcpp/trystero/platform/websocket.hpp` (libs/trystero).
- **A write that fails ends the connection at once, reporting one close,
  unless the session is already closing; and in a page
  `websocket_limits::max_queued_bytes` also bounds the page's
  `bufferedAmount`, through webcpp::beast's `queue_limits::send`.** A page's
  `WebSocket` writes at once, so what a relay does not read piles up there,
  not in the session's queue; webcpp::beast closes past its send limit, and
  the close event of a stalled socket may never come, as with the stand-in
  of `platform_page_websocket_bound`, whose close never completes. Writes
  that fail while the session closes are expected and change nothing, so a
  socket reports one close (`platform_page_websocket_late_events`).
  Source: `include/webcpp/trystero/platform/websocket.hpp` (libs/trystero).
- **A relay's binary message is dropped, on both targets.** NIP-01's
  messages are texts, and the room would drop a text that is no Nostr
  message.
  Source: `include/webcpp/trystero/platform/websocket.hpp` (libs/trystero).
- **A relay's URL is read with Boost.URL on both targets, by the same rules,
  as a page's `WebSocket` reads a `ws://` or `wss://` one: an IPv6 address in
  brackets reaches the resolver without them, the scheme in any case, a host
  name decoded and in lower case, the scheme's port by default; userinfo, a
  fragment, a port beyond 65535, an IPvFuture host, a host holding a byte
  that a page's URL parser refuses in a host, and `http://` and `https://`,
  which a page's `WebSocket` alone takes as `ws://` and `wss://`, are
  refused, and report a close.** Boost before one's own (chapter 4), and
  one reading of a relay URL on both targets, which refuses none of
  Trystero's default relays, all `wss://`; the hand-written parser kept the
  brackets, so a relay at an IPv6 address was unreachable.
  Source: `doc/platform.adoc` (libs/trystero).
- **A relay URL that a page's URL parser reads otherwise fails closed: an
  IPv4 address in another form than a dotted quad (`127.1`), and so any host
  whose last label is a number; an international name, which a page turns
  into its A-label and Boost.URL does not; a tab, a newline or a backslash
  anywhere in it; and a character that RFC 3986 allows in no path, as a
  space or `{`, which a page escapes and Boost.URL refuses.** `ws://127.1/`
  reached 127.0.0.1 through the system's resolver, and an international name
  went to it as raw UTF-8.
  Source: `doc/platform.adoc` (libs/trystero).
- **A relay over TLS is verified on both targets whatever the verify mode of
  the context: the session sets `verify_peer` on its stream before the
  handshake, and leaves the context as it is.** Asio's
  `ssl::context(tls_client)` is `verify_none`, and `set_verify_callback`
  does not change the mode, so natively a program's context made with
  `load_verify_file` alone accepted any certificate for any name; and
  webcpp::beast's page stream refuses a mode other than `verify_peer`, which
  it reads from the stream before the context, so in a page such a context
  failed every `wss://` relay, though the page's `WebSocket` always
  verifies.
  Source: `doc/platform.adoc` and
  `include/webcpp/trystero/platform/websocket.hpp` (libs/trystero).
- **No function of the platform backend throws, its constructors included: a
  TLS context OpenSSL cannot make, or a program's `result` that holds an
  error, is kept as that error, `tls_context()` returns it as a
  `boost::system::result<webcpp::asio::ssl::context&>`, and every `wss://`
  relay reports a close while `ws://` ones are still reached.** Chapter 6 (an
  API that throws sits behind `WEBCPP_TRYSTERO_NO_EXCEPTIONS`) and chapter 4
  (errors as values); `config.hpp`'s Doc Comment says trystero raises no
  exception of its own.
  Source: `doc/platform.adoc` (libs/trystero).
- **Every part of trystero, the platform backend included, works with
  exceptions and without them on both targets, and no program, test or
  headers-alone call asks for `<exception-handling>on`.** webcpp::webrtc
  calls libdatachannel's C API, which catches what libdatachannel throws and
  returns a code; every `platform_*` test but `platform_websocket` also runs
  with `exception-handling=off`, as the evidence.
  Source: `AGENTS.md` and `test/Jamfile` (libs/trystero).
- **The platform backend's headers and its WebRTC are compiled alone on both
  targets, and `platform/page.hpp` on emscripten only, which it refuses
  elsewhere with `#error`.** None needs exceptions, so the lint analyses them
  without exceptions too, and the lanes, not only the reference's parse,
  prove that each compiles on the targets that build it.
  Source: `test/Jamfile` (libs/trystero).
- **The platform backend names webcpp::asio and webcpp::beast everywhere.**
  The guide's reference reads every header for Emscripten's target, where
  both are their browser implementations, with the platform backend's target
  built natively, and the headers parse there with no configuration of
  Boost.Asio's.
  Source: `AGENTS.md` and `doc/Jamfile` (libs/trystero).

**The platform backend in a page.**

- **In a page the platform backend reaches the page's own `WebSocket` through
  webcpp::beast's page stream and `crypto.subtle` through webcpp::asio's
  `async_await`, its timers are webcpp::asio's, and it binds the page's
  `RTCPeerConnection` through webcpp::webrtc, not libdatachannel's
  WebAssembly port.** webcpp::webrtc's browser implementation binds the
  page's objects itself, so one peer connection and data channel serve both
  targets; datachannel-wasm has no media and hides the `RTCPeerConnection`
  it wraps.
  Source: `doc/platform.adoc` and `doc/design.adoc` (libs/trystero).
- **A page's program runs its io_context from `main` under a work guard, as
  webcpp::asio's model has it, and the page calls C++ only through
  `platform::page_call` (`platform/page.hpp`, emscripten only), which
  posts.** The owner's directive and decision of 2026-11-14 on trystero's
  refactor (its decision 1): chapter 15 asio says that nothing calls the run
  family from a JavaScript event and that use without `run` is unsupported;
  and under Asyncify an embind call made while `main` is suspended returns a
  promise that never settles, and its second call aborts a debug build
  (measured with Emscripten 6.0.11).
  Source: `doc/platform.adoc` (libs/trystero).
- **An event the page delivers while C++ is already running is posted, not
  run.** A handler never runs inside the call that caused it, as when node's
  WebSocket fires `close` from inside `close()`.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **trystero names Asio as webcpp::asio wherever it builds on emscripten:
  natively Boost.Asio itself, on emscripten the backend webcpp::asio ships,
  without threads when the program has no pthread ABI.** webcpp::webrtc's
  browser objects deliver their events through webcpp::asio's bridge, a
  service of their executor's `io_context`, so the room's executor must be
  webcpp::asio's; and Emscripten's threads need a cross-origin isolated page.
  `/webcpp/trystero//trystero` brings `/webcpp/asio//asio`, so a program on
  emscripten is built in one of its suspension variants, jspi by default or
  asyncify, and its `main` runs the `io_context`, which suspends there.
  Source: `doc/platform.adoc` and `AGENTS.md` (libs/trystero).
- **Page events reach C++ through webcpp::asio's bridge: a relay socket's
  through webcpp::beast's page stream, which also scopes each event to its
  connection, a `page_call`'s through one intrusive registration, removed
  when its object is destroyed, and Web Crypto promises through
  `async_await`.** A late event for a destroyed object finds nothing.
  Source: `doc/platform.adoc` (libs/trystero).
- **No JavaScript exception enters WebAssembly: calls that can throw are
  caught in JavaScript (`EM_ASM` in inline functions, trystero's and
  webcpp::beast's; Web Crypto inside an `async` function), and every event
  and page call enters C++ through webcpp::asio's bridge, which restores the
  stack pointer, catches a C++ exception in C++, and only posts.** Measured
  before the fix, each escape left 128 bytes of stack and the loop stopped
  after about 500; a C++ exception that reached JavaScript kept its object
  for good, so the bridge catches it first.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals)
  and `doc/platform.adoc` (libs/trystero).
- **Text crosses into JavaScript through `platform::js_string`, straight from
  WebAssembly memory, and a relay's text back through webcpp::beast's page
  stream, its UTF-8 length checked before any copy against
  `read_message_max` (1 MiB), which the session sets before the
  handshake.** No `std::string` is made to carry it, and a string over its
  bound is never copied into WebAssembly; a page can deliver a relay's first
  messages in the task of its open, before the handshake's completion runs,
  so a bound set after it had those checked against the stream's 16 MiB.
  Source: `doc/platform.adoc` and
  `include/webcpp/trystero/platform/websocket.hpp` (libs/trystero).
- **A page makes at most `runtime_options::max_peer_connections` (256 by
  default) peer connections across all its apps and rooms, the cap of the
  backend's webcpp::webrtc runtime over webcpp::webrtc's census of the page,
  which counts every connection it makes, with any runtime, from
  construction until the garbage collector frees it, and nothing without
  `FinalizationRegistry`; and at most 256 a minute, the backend's window.**
  Chromium counts a connection against its 500 until a collection (measured:
  the 501st throws "Cannot create so many PeerConnections"), the rest of its
  count stays free for what the page makes without a room, and a count that
  never comes down would stop the page for good.
  Source: `doc/platform.adoc` (libs/trystero).
- **A page's relay socket has no idle timeout.** A page's `WebSocket` cannot
  ping, and webcpp::beast's page stream refuses keep-alive pings, so the
  session sets none there.
  Source: `doc/platform.adoc` (libs/trystero).
- **A page's platform backend requires a secure context for its sealer.**
  `crypto.subtle`, which seals the signaling, exists only there; elsewhere
  every sealing operation fails with `error::backend_failure`.
  Source: `doc/platform.adoc` (libs/trystero).
- **In a page the sealer imports its key on its first operation and queues
  the operations that arrive while it imports.** (reason not recorded)
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **A page's sealer reads a Web Crypto settlement only when it is an
  `ArrayBuffer`, and fails the seal or the open with
  `error::backend_failure` otherwise.** Only a page whose `crypto.subtle`
  was replaced settles with another value, whose reading as one could throw
  (`new Uint8Array(-1)`) or read what it is not.
  Source: `include/webcpp/trystero/platform/sealer.hpp` (libs/trystero).
- **In a page, under webcpp::beast's default policy, a TLS context that asks
  for what a page cannot honour makes every `wss://` relay report a close:
  authorities added, a client certificate or key, options, a method other
  than `tls_client` or `sslv23_client`, or a verify callback other than
  `host_name_verification` of the relay's host.** The browser makes the
  handshake against its own authorities, and webcpp::beast's page stream
  refuses what it cannot honour unless `webcpp-beast-unsupported=ignore`
  leaves it to the browser (chapter 15, beast).
  Source: `doc/platform.adoc` (libs/trystero).
- **A `page_call`'s handler lets no JavaScript error out: it checks the type
  of the page's value before converting it, and reads a number as a
  `double`, checking its range before it becomes an integer.** A
  `BindingError` or a `TypeError` out of a handler leaves `run` with it, and
  the program's run never resumes (measured with Emscripten 6.0.11 under
  node, in either suspension variant), as webcpp::asio's guide says; before
  `page_call`, embind's typed functions refused a wrong type outside
  WebAssembly; and in a build with assertions embind's `as<std::int32_t>()`
  of a number beyond the type's range, as `1e10`, throws a `TypeError`.
  Source: `doc/platform.adoc` and
  `include/webcpp/trystero/platform/page.hpp` (libs/trystero).
- **A `page_call`'s resource holds each call the page made until the
  `io_context` runs it or is destroyed, so it outlives the `io_context`; and
  the handler reads the page's value as it is when the handler runs.** A
  call is an operation the `io_context` holds, which only its run or its
  destruction frees, and it carries a handle of the page's value, not a
  copy, so a JavaScript object the page changes meanwhile is seen changed
  (`platform_page_call`).
  Source: `include/webcpp/trystero/platform/page.hpp` (libs/trystero).

**The platform backend natively.**

- **Natively WebRTC is libdatachannel's, through webcpp::webrtc over its C
  API, the relays' WebSockets are Boost.Beast's own, through webcpp::beast,
  and TLS, AES-GCM and randomness are OpenSSL's, with libdatachannel built
  without its own WebSocket.** The relays then run on the room's executor
  like everything else, and the native peer connections are the browser's in
  interface.
  Source: `doc/platform.adoc` and `doc/building.adoc` (libs/trystero).
- **Natively the relays' WebSocket runs over webcpp::beast's
  `bounded_handshake_stream`, made with the room's allocator, with
  `response_limits::body` 0: a relay that refuses the upgrade has its
  response's header read, at most 8 KiB, and no byte of its body; in a page
  the browser reads its own response.** Beast's WebSocket stream reads the
  response with a parser of its own, whose limits none of its options
  reaches, so a refusal's body was read up to 8 MiB outside the room's
  resource (measured: a 4 MiB refusal had the room's thread allocate
  4,199,353 bytes, and 5,144 with the layer, `platform_websocket_allocation`).
  Source: `doc/platform.adoc` and
  `include/webcpp/trystero/platform/websocket.hpp` (libs/trystero).
- **webcpp::webrtc posts every event of libdatachannel to the executor,
  through a weak reference; no handler runs on libdatachannel's threads.** Its
  callbacks run on its own threads, and an event that arrives after its object
  is gone must do nothing; an application with several threads gives the app
  a strand.
  Source: `doc/platform.adoc` (libs/trystero).
- **What libdatachannel does is webcpp::webrtc's: its C API, its automatic
  negotiation off, and every object it hands out held until its owner lets it
  go.** An offer or an answer exists only when the signaling asks for one, as
  in the browser; libdatachannel keeps only weak references, and the spike
  lost tracks and WebSockets it did not retain.
  Source: `doc/platform.adoc` (libs/trystero).
- **Natively a URL libdatachannel cannot parse, as a `stuns:` one, is left out
  of the connection, each URL being tried alone; in the browser the page
  refuses the whole connection for a server it cannot use.** webcpp::webrtc
  refuses the whole configuration for one such URL, and a room has already
  dropped every server WebRTC refuses; libdatachannel knows no STUN over TLS.
  Natively only: in a page each probe would be a connection the census
  counts until a collection.
  Source: `doc/platform.adoc` and
  `include/webcpp/trystero/platform/backend.hpp` (libs/trystero).
- **A channel that closes during adoption before a room binds clears that
  room's negotiation and restarts its announcements.** No binding exists for
  the later connection-end callback to remove. Keeping the negotiation marked
  connected would prevent the room from ever reconnecting.
  Source: `include/webcpp/trystero/room.hpp` and `test/shared_test.cpp`
  (libs/trystero).
- **`backend_config::bind_address` binds every peer connection to one address;
  empty means every interface but the loopback.** Bound to 127.0.0.1, the
  peers of one machine connect with no other network, which a test wants.
  Natively only: a page cannot bind, and webcpp::webrtc refuses every
  connection a page asks it to bind.
  Source: `doc/platform.adoc` (libs/trystero).
- **Over TLS the connection names the host (SNI) through
  `webcpp::beast::set_server_name` only when it is a name once decoded, never
  an address, an escaped dotted quad among them, and checks the certificate
  against the URL's host, a name or an address, with Asio's
  `host_name_verification`.** RFC 6066 allows no address in SNI;
  `wss://%31%32%37.0.0.1/` sent `127.0.0.1` as one.
  Source: `doc/platform.adoc` (libs/trystero).
- **Relays are verified against the system's certificate authorities, through
  `platform::make_tls_context()` (TLS 1.2 or newer, peer verification,
  OpenSSL's default verify paths, the call Asio's non-throwing
  `set_default_verify_paths(ec)` makes), and a backend takes a program's own
  context instead: webcpp's embedded Mozilla roots
  (`webcpp::asio::make_tls_client_context()`), or a private authority.** The
  owner's decision of 2026-11-14 on trystero's refactor (its decision 2): no
  relay's trust changes. A relay whose certificate does not verify is
  unreachable, and the room retries it later as it would any other. In a
  page the context records the policy, a client that verifies its peer, and
  the browser verifies against its own authorities.
  Source: `doc/platform.adoc` (libs/trystero).
- **`platform::detail::openssl_error()` reports the error OpenSSL queued
  last, and `make_tls_context()` starts from an empty queue.** The queue's
  first error may be one an earlier call left behind; the last is the
  failure's.
  Source: `include/webcpp/trystero/platform/websocket.hpp` (libs/trystero).
- **On Windows the system's authorities are none unless `SSL_CERT_FILE` or
  `SSL_CERT_DIR` names some, so a Windows program gives the backend its own
  context.** OpenSSL's default verify paths there are under its build-time
  `SSL` directory, which neither Windows nor webcpp fills, and it reads no
  Windows certificate store.
  Source: `doc/platform.adoc` (libs/trystero).
- **Natively a relay that stops answering is dropped once
  `websocket_limits::idle_timeout` (30 s) passes with its keep-alive ping,
  sent halfway, unanswered.** Signaling texts are 2 to 4 KB, so a real room
  meets the cut only with a relay slower than about 200 B/s.
  Source: `doc/platform.adoc` (libs/trystero).

**Rooms, actions and errors.**

- **Every asynchronous operation (`async_send`, `async_receive`, `async_ping`,
  `async_leave`) is an Asio initiating function.** The spike made Boost's
  style a principle: Asio as the execution model, and a completion token on
  every asynchronous operation.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-10-09-genesis/reference/research/TRYSTERO_CPP_SPIKE/FINDINGS.md`
  (proposals).
- **An asynchronous operation owns its arguments: a value is taken by value, a
  view copied once at the call, a JSON document written at once, and a peer
  id copied.** A token such as `webcpp::asio::deferred` starts the
  operation after the call.
  Source: `doc/usage.adoc` (libs/trystero).
- **Text is a view and a copy is a decision: digests are fed the parts of
  their input, signals and relay messages are read as views into the parsed
  document, a frame is written once inside its room envelope and shared by
  every target, and a log sentence is composed only when there is a sink.** A
  string is made only where something must own the text: a map key, a member,
  a capture of a handler that runs later.
  Source: `doc/design.adoc` (libs/trystero).
- **A `room` is a move-only handle of one membership: destroying it, or
  assigning another room over it, leaves at once, without the 99 ms
  farewell.** Two handles to one membership would make leaving depend on
  another handle.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **An action's type sets Trystero's format and how a message arrives: owning
  types receive a copy or the moved buffer, while `std::string_view` and
  `std::span<const std::uint8_t>` read the frame in place during the
  handler.** A received frame becomes the buffer of the message delivered from
  it, so a view handler reads it without a copy.
  Source: `doc/design.adoc` (libs/trystero).
- **`async_receive` refuses a view type at compile time.** A received view
  would outlive the message.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **The JSON payload is document's own pair, `webcpp::document::document`,
  in the standard allocator, the user's choice, and
  `webcpp::document::pmr::document`, received in the room's resource; a C++
  peer sends what `JSON.stringify` writes of the document, and a rejected
  `async_receive` completes with document's `nothing()`, which allocates
  nothing.** The owner's decision 5 of trystero's refactor keeps no
  specialization for `boost::json::value`, and the owner's decision of
  2026-11-14 gave webcpp::document an allocator; the pair mirrors
  `std::string` and `std::pmr::string`, with no alias of trystero's, and a
  handle keeps document's rule: it refers to its document object, and moving
  the document invalidates it. A sent document is written into a string of
  the room's resource in pieces of 8 bytes, which no standard library's
  string keeps outside its own object.
  Source: `doc/usage.adoc`, `include/webcpp/trystero/room.hpp` and
  `include/webcpp/trystero/protocol/json.hpp` (libs/trystero).
- **A received JSON payload's image grows to at most 96 times its length and
  64 KiB, which every valid payload fits, and to at most
  `room_options::max_json_document_bytes`, webcpp::document's 64 MiB by
  default.** Each value is a node of 192 bytes and takes at least two bytes
  of text (measured on every shape, and pinned by the test `protocol`). A
  ceiling tied tighter to the text, as a protocol text's is, refused arrays
  of a few hundred numbers that Trystero JS delivers, so the program bounds
  the memory instead; the bound is a difference, which `diff_json_refused`
  shows.
  Source: `doc/protocol.adoc`, `doc/differences.adoc` and
  `include/webcpp/trystero/protocol/json.hpp` (libs/trystero).
- **Actions of different types may share a name, which has one receiver
  slot.** One may receive as views while another sends by moving strings, as
  the chat example does.
  Source: `doc/usage.adoc` (libs/trystero).
- **Frames of an action not made yet are kept, 64 per peer for 120 s, and
  messages without a handler queue up to 1024 per action, the oldest dropped
  and logged.** An action made late still receives what arrived before it; for
  the numbers, (reason not recorded).
  Source: `doc/usage.adoc` (libs/trystero).
- **`async_send` completes once each target's local data channel has taken the
  inline frame, or the last chunk of an accepted transfer, with the first
  failure if any.** That is when Trystero's `send` resolves; nothing confirms
  that the receiver has the message.
  Source: `doc/usage.adoc` (libs/trystero).
- **A frame or a chunk goes to the data channel only while it buffers at most
  64 KiB, and a send that waits longer than 10 s completes with
  `error::channel_stalled`.** The threshold is Trystero's
  `bufferedAmountLowThreshold`; for the 10 s bound, (reason not recorded).
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **A receiver takes one transfer per peer at a time, only for an action with
  a receiver, and reserves at most `max_receive_bytes` (256 MiB) across
  peers.** The bound is Trystero's `maxReceiveBytes`; for one transfer per
  peer, (reason not recorded).
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **A peer that breaks the action wire (a frame that does not decode, a
  duplicate offer, a chunk at the wrong offset) is kicked.** Trystero drops
  the peer for any wire error; over a shared connection the kick ends that
  room's binding only.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **A peer still in its handshake may send only `@_leave`, `@_hsdata` and
  `@_hsready`; its other frames are dropped.** (reason not recorded)
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **`error::handshake_failed` is reserved and reported by nothing; a handshake
  message of the wrong shape reports `error::wrong_password`.** Trystero's
  handshake reports it so, and the value 11 is kept so that the values after
  it do not move.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **The error category's `message(int, char*, std::size_t)` returns a static
  text and allocates nothing.** A room logs an error without allocating.
  Source: `include/webcpp/trystero/error.hpp` (libs/trystero).
- **Diagnostics go to one sink, `app_config::log`, with a category per part
  (`app`, `nostr`, `signal`, `webrtc`, `room`, `action`), and a sentence is
  composed from its parts only when there is a sink.** An app without a sink
  composes no text at all.
  Source: `include/webcpp/trystero/detail/log.hpp` (libs/trystero).

**The app and the shared connection, as built.**

- **Rooms are joined through an `app`: `app::join` returns
  `boost::system::result<room>`, and the standalone `room` constructor and
  `room_config` are removed.** One way to join, so no program falls back into
  one id per room, where two standalone rooms with one id meet a Trystero JS
  peer in one of them only; the standalone form can return later as an app of
  one room without breaking anything.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **Two peers in several rooms of one app share one WebRTC connection, each
  frame naming its room by its token.** Trystero does so, and the owner
  decided on 2026-10-11 that the difference goes away.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/proposal.md`
  (proposals).
- **Sharing is scoped by the `app` object the user makes: nothing is keyed by
  the backend or kept in static storage, and two apps of one app id in one
  process are two peers.** No static state, and several peers in one process,
  as the tests and the interop peers need; an id across apps is a program's
  choice.
  Source: `doc/differences.adoc` (libs/trystero).
- **The app owns the connections and a room its bindings: a room holds the app
  strongly, the app reaches rooms weakly, a binding holds its connection
  weakly, and a connection holds plain pointers to its bindings, which remove
  themselves before they go.** No cycle keeps the objects alive, and after a
  room has ended the app keeps no allocation of that room's resource.
  Source: `doc/design.adoc` (libs/trystero).
- **One self id per app, drawn once unless named, announces, signals,
  tie-breaks and handshakes in every room of the app.** Sharing a connection
  needs one id per app, as Trystero's one `selfId` per page; the program
  decides which rooms may be linked, and rooms that must stay unlinkable use
  separate apps.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **The password is the app's and immutable: `app_config::password` is copied
  into the app's resource, and `room_options` has no password.** The initial
  signaling sealed with it authenticates the domain before any connection is
  adopted, so a peer that reaches another room through presence already knows
  its password (owner amendment, 2026-10-14).
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/password-domains.md`
  (proposals).
- **Different passwords need separate apps with distinct self ids, whose
  connections, registries, presence and tokens are never shared.** A room
  token does not depend on the password, so isolation comes from scoped
  connections and registries, not from a new token format.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/password-domains.md`
  (proposals).
- **The room handshake stays Trystero's one-way handshake; no reciprocal room
  proof is added.** Reciprocal proofs would change compatibility with Trystero
  JS; a JS page that mixes passwords keeps its own exposure, which the page
  documents rather than repairs.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **A passwordless app's rooms are open, by token, to the peers connected
  through any of its rooms; no proof gate is added.** A gate by a message on
  the room's topics is passed by anyone who reads the relays, so it gave false
  assurance, and it cost up to 10 s against a Trystero JS peer that joined
  first; a room that must be private belongs to an app with a password.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **Adoption follows Trystero: the first connection registered wins, a second
  one to the same peer is closed and the room bound to the first, a stale one
  is ended before its replacement, and crossed connections are both lost and
  met anew.** Matching Trystero's rule keeps a C++ and a Trystero JS side
  agreeing; ending the stale one first fixes the plan's silent replacement, in
  which a late close erased the new entry.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **A room binds a connected peer only after that peer advertised the room's
  token itself on that connection.** An announcement or a signal forged in its
  name must not bind an innocent peer; in Trystero JS it binds the peer by
  reuse, which is kicked after its handshake timeout.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/specs/trystero/spec.md`
  (proposals).
- **A room frame of a room of the app that the connection keeps is the peer's
  own advertisement of the room, as its presence is.** Trystero sends a
  room's presence once per connection, and Chrome can drop what a page sends
  on an answering channel as it opens, so a room waiting for that presence
  alone would never bind a Trystero JS peer; only the peer writes its
  connection's frames, so a forged announcement still binds nothing.
  Source: `AGENTS.md` (libs/trystero).
- **A bound room keeps its negotiation entry marked connected, and binds by
  signaling reuse only on its first meeting with that peer over that
  connection.** Otherwise a room bound by presence or reuse would offer to the
  peer it is bound to, and later relay signals could shorten a backoff.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **A room that binds by reuse or at its rebinding time sends `presence(1, T)`
  on the connection.** It makes the other side, Trystero JS included, bind at
  once, with no answer on the relays.
  Source: `doc/differences.adoc` (libs/trystero).
- **A frame for a room of the app not bound yet is kept, 64 per connection,
  all dropped 10 s after the first, and a kept `@_leave` discards itself and
  what was kept before it.** A registered room may receive its handshake
  before signaling binds it, as Trystero's source notes; the frames before a
  kept `@_leave` belong to a binding of the other side that has ended.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **A bound room has no buffer for frames that wait for its handler, where
  Trystero keeps 64 for 10 s and then drops the connection.** A binding's
  delivery is set in the same call that makes it.
  Source: `doc/differences.adoc` (libs/trystero).
- **A frame for a token no room of the app has is dropped and the connection
  stays; a frame that does not decode, or a 65th advertised token, ends the
  connection for every room.** Presence and routing are Trystero's.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **A kick, a failed handshake or a peer's `@_leave` ends that room's binding
  only, and the other rooms keep the connection.** Each room's membership,
  handshake, actions, queues and bounds stay its own, so a failure in one room
  costs no other.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **After a binding ends over a live connection, the room rebinds one step
  later: the larger of `handshake_timeout` and 10 s, plus 1 s (11 s by
  default), doubling per further end to 5 minutes, until a completed handshake
  or the connection's end.** Rebinding on the next signal, as Trystero does,
  loops kicks, reports and announcements without end on a wrong proof; the
  added second lets a Trystero JS peer drop the frames it kept from the ended
  binding (10 s) before the next one.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **Meanwhile only the lower id refuses the peer and keeps its frames, while
  the higher id refuses nothing but drops the peer's frames of that room until
  it next sends presence.** Two honest peers cannot alternate kicks, and a
  stale frame of an ended binding is never answered in the next one; a wrong
  proof costs at most six reports in ten minutes, on the lower id only.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **The initiator accepts a correct answer to any of the last 8 challenges it
  sent the peer since their last completed handshake.** A response carries no
  challenge id, and each challenge is the initiator's own fresh nonce on a
  channel only the peer can write to, so any of them proves the password; a
  late answer of an ended binding no longer reports a false error.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **Announcements restart after a peer leaves only when no live connection to
  it remains.** Over a live connection every rebinding goes through the
  connection.
  Source: `doc/differences.adoc` (libs/trystero).
- **A connection with no binding left stays idle for
  `app_config::idle_timeout` (123,333 ms; 0 closes it at once) after a
  departure, and closes at once after a kick.** The idle time is Trystero's
  `sharedPeerIdleMs`, made a member for tests and programs that close sooner;
  closing after a kick is a bound: a failed peer holds no connection.
  Source: `doc/differences.adoc` (libs/trystero).
- **`join` of a room already joined in the app fails with
  `error::already_joined`, and joining an id in its 99 ms farewell finishes
  that farewell first.** A `room` is a move-only handle whose destruction
  leaves, so a second handle to one membership would make that depend on
  another; finishing the farewell sends the old room's `presence(0)` before
  the new one's `presence(1)`, as Trystero's rejoin does.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **An app holds at most `app::max_rooms` (64) rooms, a room counting until
  its `presence(0)` is sent.** A Trystero peer drops a connection whose remote
  advertises more than 64 tokens, so a 65th room would cost every connection
  of the app.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **The app handle and every room not yet ended are the users of the app's
  state: the last to go ends every connection at that call, and
  `detail::app_impl`'s destructor closes and posts nothing.** The destructor
  may run while the `io_context` is destroyed, from the last operation pending
  there, and then may only free.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **Relay sockets, subscriptions and the Nostr signing key stay per room,
  configured once for the app.** No peer sees the difference, and sharing
  sockets, batching topics and one key per app touch the strategy's bounds and
  reconnection tests, which deserve their own specification.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **The app's relays and ICE servers serve every room of it.** One
  configuration for what the rooms share, where Trystero takes the first
  room's relays and each negotiating room's RTC configuration.
  Source: `doc/differences.adoc` (libs/trystero).
- **What the app's configuration sets aside is reported to `app::on_error`
  after the constructor returns, once, to the handler current at delivery;
  `room::on_error` reports only problems with peers.** The app's constructor
  does not fail, and no handler can see a report made during construction.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **A send that must wait for the shared channel to drain waits in its
  binding, and at each drain the bindings take turns; an inline send while the
  channel buffers at most 64 KiB goes at once.** A room's chunked transfer
  then sends one chunk per drain while other rooms' waiting sends get their
  turn, and an inline flood, of pings for one, delays only traffic to the peer
  that provoked it.
  Source: `doc/protocol.adoc` (libs/trystero).
- **An app and all its rooms run on one executor, the app's, and nothing is
  locked.** The state is touched only there, so the resources need not be
  thread-safe on one thread; several threads need a strand.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **trystero runs on the Asio executor it is given, not on xactor.** How a
  library on Asio meets xactor is still to be designed, and the move onto
  webcpp::asio, webcpp::webrtc and webcpp::crypto is a change of its own,
  after this one.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **Two residual cases with a Trystero JS lower id are accepted: a reuse
  binding inside the higher id's dropping window, and a page whose timers run
  later than the 1 s margin.** In neither does the C++ side report anything
  false; the first joins by the second rebinding time (at most 43 s by
  default), the second costs one false error on the JS side, at most three
  times.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).

**Bounded signaling and security.**

- **Everything a peer or a relay can make a room hold is bounded.**
  Announcements are not sealed, and anyone who reads the relays can send any
  signal in any peer's name; Trystero JS bounds none of it.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **No signal changes a negotiation before it opens with the room key.** A
  forged answer sent in a peer's name must not reset an offer, and a forged
  offer must make no connection.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **Signals that do not open are reported paced: the first of a quiet 10 s at
  once, with its peer, and the others of those 10 s in one report, with their
  number.** A flood of fresh ids makes each a negotiation.
  Source: `doc/protocol.adoc` (libs/trystero).
- **A room remembers, by SHA-256, the opened text of the last 1024 offers and
  answers it made or acted on, and refuses one that comes back to it as a
  peer's.** A sealed offer or answer holds neither its offer id nor a peer id,
  so one recorded from the relays still opens when resent, as does the room's
  own; the digest is of the opened text, whose sealed encoding a resender can
  vary.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **A room holds at most 32 negotiations with peers it is not connected to:
  an idle one, holding no connection and no offer of its peer being opened,
  gives its place to a new peer, the one idle longest and, of those idle as
  long, the one the room took first; a refused peer is logged once.** Anyone
  who knows the app and room ids can announce any number of peer ids.
  Opening an offer is the sealer's asynchronous step (Web Crypto in a page).
  While it counted as idle, a tie in id order at one instant of a page's
  coarse clock let new ids arriving meanwhile have honest offers dropped
  unopened, their peers joining 2 s later, and let a flood of fresh ids have
  every offer opened at once (measured: `room`'s
  `an_offer_being_opened_keeps_its_place` and
  `a_flood_of_offers_at_one_instant_is_bounded`); now the room opens offers
  of at most 32 peers, one offer of each at a time.
  Source: `doc/protocol.adoc` (libs/trystero).
- **A negotiation opens one offer of its peer at a time, as Trystero answers
  one at a time: until it is opened, another offer in that name is ignored,
  and the same offer through another relay has the answer sent there too.**
  Each offer sent in a peer's name started an open of its own, holding its
  copy, up to 64 KiB, in the room's resource, which only the relays' rate
  bounded (measured: 42 offers in one name, 40 of them of 48 KiB, held 42
  opens and 1,976,152 bytes; `room`'s
  `offers_in_one_name_are_opened_one_at_a_time`). As with Trystero, a forged
  offer opened first has the peer's own wait until the peer sends it again,
  2 s later.
  Source: `doc/protocol.adoc` (libs/trystero).
- **A room makes at most 64 connections in any 57,333 ms, counted from when
  they were made.** A place freed early by a connection that failed or closed
  at once is not taken again until the window has passed.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **A room asks a peer below it to offer at most once a second per peer and
  relay, and once in 5.3 s, Trystero's announce interval, per relay.** A flood
  of low ids must not have the relays rate-limit the room.
  Source: `doc/protocol.adoc` (libs/trystero).
- **The strategy remembers the ids of the newest 4096 events whose ids it
  checked, and drops a repeated one, in a `boost::unordered_flat_set` hashed
  with SipHash under a key it draws when it is made.** A signal reaches the
  room on several relays and must reach the signaling once; an id is a
  relay's choice, and ids chosen to share a bucket of the standard library's
  unseeded hash cost 26.7 us an event against 0.12 us (measured).
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals)
  and `include/webcpp/trystero/detail/nostr_strategy.hpp` (libs/trystero).
- **A Nostr event is dropped as a repeat only when its id is checked to be
  its own, the SHA-256 of its NIP-01 serialization
  (`protocol::nostr::has_own_id`); any other event is acted on each time
  and its id never stored, as Trystero 0.26.0 acts on every event.** A relay
  chooses the id it sends, so trusting it would let one relay hide a genuine
  event behind a forged one sent first under its id; and a remembered id is
  then 64 bytes, whatever a relay sends.
  Source: `include/webcpp/trystero/detail/nostr_strategy.hpp` and
  `include/webcpp/trystero/protocol/nostr.hpp` (libs/trystero).
- **A lost relay is retried after a random share of a bound that starts at
  3.3 s and doubles to 60 s, and comes back down only after a connection
  lasted 60 s.** A relay that closes the room at once after each open is then
  tried less and less often.
  Source: `doc/protocol.adoc` (libs/trystero).
- **A relay that answers `rate-limited:` is skipped for 60 s, doubling to
  15 minutes, and one that answers `blocked:`, `restricted:`, `auth-required:`
  or `pow:` is retired.** A public relay rate-limited the spike's probe, and
  the library must respect the backoff.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-10-09-genesis/reference/research/TRYSTERO_CPP_SPIKE/FINDINGS.md`
  (proposals).
- **A relay's text is bounded at 1 MiB, a longer one closing its connection
  before it is copied, and what the room holds unsent for a relay at 4 MiB.**
  A relay is a third party too.
  Source: `AGENTS.md` (libs/trystero).
- **Each caller bounds the JSON text it reads, as `parse_options::max_bytes`:
  68,608 bytes for a relay's text, 66,560 for a signal, 1,024 for a
  handshake message, 16 KiB for a remote candidate; a longer text is refused
  before it is read, as a malformed one is: a relay's text or a signal
  dropped, a handshake failed, a candidate not added.** The bounds come from
  the fields' own bounds (a sealed offer or answer of 64 KiB with the
  longest ids, ten times Trystero's longest handshake message, the bound of a
  sealed candidate), as chapter 18's draft had them, so no text a Trystero
  peer writes is refused; document keeps no hashed index, so no key set,
  read twice or chosen to collide, makes a parse quadratic.
  Source: `doc/protocol.adoc` (libs/trystero).
- **A signal's fields are bounded: the peer id and the offer id at 64 bytes, a
  sealed offer or answer at 64 KiB, a sealed candidate at 16 KiB.** Trystero
  JS bounds none; the bounds refuse nothing a browser writes for a data
  channel, and a static assertion proves that every candidate Trystero accepts
  (8192 bytes of plaintext) fits sealed.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **What a flood or a watcher without the key can still do is stated on the
  page, not hidden.** Only a wire that seals the offer id and both peer ids,
  or announcements that prove the room key, closes it, a change Trystero would
  have to share (reported upstream).
  Source: `doc/protocol.adoc` (libs/trystero).

**Memory.**

- **An app's allocations go through `app_config::memory`, and a room's through
  `room_options::memory`, the app's resource when null.** The room keeps the
  resource the allocation rule gave it, while what the rooms share lives in
  the app's.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **The platform backend's own state, its copy of `bind_address`, its window
  of constructions and its own webcpp::webrtc runtime, is in
  `backend_config::memory`, the default resource unless the program gives
  one.** Chapter 4's allocation rule; both backends made their window and
  their runtime in the default resource. The test `platform_backend`, on both
  targets, makes a backend while a counting resource is the default one,
  which sees none of it.
  Source: `doc/platform.adoc` and `doc/allocation.adoc` (libs/trystero).
- **Peer connections, data channels and the frames received on them use the
  app's resource even while a room negotiates them; relay sockets, sealers and
  room timers use the room's.** A connection belongs to the app once adopted,
  and serves every room bound to it.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/design.md`
  (proposals).
- **A binding fails and frees its drain waiters, in the room's resource, when
  it detaches.** The waiters are the room's handlers, frames and timers; held
  by the app's connection, they would outlive a room with a resource of its
  own.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **A received binary payload moves out of its frame when the frame and the
  room share a resource, and is copied once otherwise; received text is always
  copied once.** A `std::pmr` container moved into another resource copies
  anyway; for text, (reason not recorded).
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **The log sink, and every sentence of the app and its rooms, are in the
  app's resource, the sink shared through a `std::shared_ptr`.** The sink then
  outlives a part that is still running when the app goes.
  Source: `include/webcpp/trystero/detail/log.hpp` (libs/trystero).
- **`handler<R(Args...)>` replaces `std::function` wherever trystero keeps a
  callable: move-only, inline when the target fits three pointers and is
  nothrow-movable, else in storage of its allocator.** `std::function` takes
  no allocator since C++17; the app moves `app_config::log` into its resource,
  which makes `app_config` move-only.
  Source: `doc/allocation.adoc` (libs/trystero).
- **Every JSON text a room reads is parsed by `webcpp::document::parse` into
  a `webcpp::document::pmr::document` of the room's resource, of the app's
  for a remote candidate, which holds its image and the parse's working
  state; a protocol text nests at most 16 deep, and its image grows in place
  to at most twice the caller's bound and 64 KiB; trystero keeps no owner of
  its own.** document's allocator holds every value and the working state,
  so neither is outside the resource; Trystero's texts nest 4 deep at most,
  and the image's bound refuses a text of thousands of values once it has
  cost that bound.
  Source: `doc/allocation.adoc`, `doc/protocol.adoc` and
  `include/webcpp/trystero/protocol/json.hpp` (libs/trystero).
- **A post goes through the `io_context`'s own executor when the room's
  executor is one, and in a page the sealer awaits each Web Crypto promise
  through it too, so that after a first seal and open a seal or an open
  allocates nothing outside the room's resource.** Through
  `webcpp::asio::any_io_executor`, Asio wraps a post in a function object
  allocated with `std::allocator` (measured: two `std::aligned_alloc` per
  post in every round of five, natively and on emscripten, and two for each
  seal and each open of a page's sealer); `platform_page_sealer_allocation`
  counts `operator new` and the C library's functions from the start of a
  seal or an open to its completion and sees none. The executor is the
  program's: on a strand over the `io_context` the wrapper stays Asio's, as
  the page lists.
  Source: `doc/allocation.adoc` and
  `include/webcpp/trystero/platform/sealer.hpp` (libs/trystero).
- **The room never binds its allocator over a user's completion handler, and
  records, when it erases the handler's type, whether its executor is the
  room's.** A completion handler is the user's, allocated as its own
  associated allocator says; telling the executor apart through the erased
  type cost two `operator new` calls per completion (measured).
  Source: `AGENTS.md` (libs/trystero).
- **`trystero::bytes` and `trystero::payload` keep `std::allocator`; every
  other container trystero declares is a `std::pmr` one or a Boost container
  over `std::pmr::polymorphic_allocator`.** Those two are the user's choice,
  as `webcpp::document::document` is, a received one holding its image and
  its parse's working state in the standard allocator, as document's
  `document` does; `std::pmr::string`, `pmr_bytes` and
  `webcpp::document::pmr::document` are the types that receive in the
  room's resource.
  Source: `doc/allocation.adoc` (libs/trystero).
- **libsecp256k1 signs with a context preallocated in the room's resource, and
  verifies with its static context.** No allocation of a room escapes its
  resource, and a verification allocates nothing.
  Source: `doc/allocation.adoc` (libs/trystero).
- **The allocations outside the resources are listed on the page, not claimed:
  libdatachannel's and OpenSSL's, with the copy libdatachannel's C API makes
  of a message, `emscripten::val`'s, Asio's once per context and its wrapper
  on an executor that is not an `io_context`'s, a strand for one, which
  webcpp::webrtc's completions get through `any_io_executor`; natively, for
  each relay connection, what Boost.Beast and Asio allocate of their own
  (the WebSocket's and the TCP stream's state, the WebSocket's write buffer,
  the TLS stream's two buffers, the resolver's state and results, the
  handshake's request and response, the response's header at most 8 KiB,
  which webcpp::beast's bounded handshake layer reads, keeping a split
  header line in the room's resource, and no byte of a refusal's body, the
  verify callback and its copy of the host, the waits of Beast's timers and
  each keep-alive ping's frame), where in a page the stream's state is in
  the room's resource; in a page, the strings embind makes of each event's
  type, two for a message; Emscripten's `select()`, Asyncify's unwind data
  when the run suspends, and the storage of the map in which webcpp::asio's
  bridge finds each pending Web Crypto promise.** They belong to a
  dependency or to Asio, and webcpp::webrtc's posts from libdatachannel's
  threads may not touch a resource used only on the executor. A page
  relay's embind strings stay, as the owner decided: each is freed at once,
  and avoiding them needs webcpp::beast's page stream to read an event's
  type without a `std::string`. webcpp::asio's page resolver holds its
  results' one entry in place, so that a page relay's resolution allocates
  nothing.
  Source: `doc/allocation.adoc` (libs/trystero).
- **No check catches a resource that ends too early: it is declared before the
  `io_context`, and its lifetime is the user's.** trystero holds a raw pointer
  and cannot see the resource end, and the late use comes from an operation of
  Asio's or the browser's after the room is gone; a resource that asserts
  nothing is out when it is destroyed is the user's check.
  Source: `doc/allocation.adoc` (libs/trystero).
- **A pool suits a long-lived app or room, and a monotonic resource a
  short-lived one or a test.** A room allocates and frees on every event: a
  frame, a parsed text, a post, a log line.
  Source: `doc/allocation.adoc` (libs/trystero).
- **The tests' `memory_network` allocates its relays in its own resource.**
  It is shared by every room of a test.
  Source: `doc/allocation.adoc` (libs/trystero).

**Build and dependencies.**

- **libsecp256k1 0.8.0, with `schnorrsig` and `extrakeys`, signs the Nostr
  events of every room, built with `ECMULT_WINDOW_SIZE=4` and
  `ECMULT_GEN_KB=2`.** The small tables keep the browser's download small: the
  spike measured 152 KB of WebAssembly against 1.30 MB with the default
  tables.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-10-09-genesis/reference/research/TRYSTERO_CPP_SPIKE/FINDINGS.md`
  (proposals).
- **trystero builds on webcpp::asio and webcpp::document, and its platform
  backend on webcpp::webrtc, webcpp::beast and Boost.URL:
  `/webcpp/trystero//trystero` is the rooms alone, which bring
  `/webcpp/asio//asio` and `/webcpp/document//document`, with Boost.JSON's
  and Boost.Charconv's definitions, and on no target webcpp::webrtc;
  `/webcpp/trystero//platform`, the backend's one target on both targets in
  place of `/webcpp/trystero//native`, adds `/webcpp/webrtc//webrtc` and
  `/webcpp//boost_url` on both, natively with libdatachannel (MPL 2.0) and
  OpenSSL (Apache 2.0) and, for the relays, `/webcpp/beast//tls` and
  `/webcpp/asio//tls`, whose embedded authorities a program may choose, and
  on emscripten `/webcpp/beast//browser`.** One target for one class, which
  a native program and a page's both name; a page's program links neither
  libdatachannel nor OpenSSL, as OpenSSL is optional for Asio.
  Source: `doc/design.adoc` and `build.jam` (libs/trystero).
- **Under Asyncify, `/webcpp/trystero//trystero` leaves Boost.JSON's
  recursive descent, the `parse_*` functions of its `basic_parser`, out of
  Asyncify's instrumentation (`-sASYNCIFY_REMOVE=@asyncify-remove.json`).**
  None of them suspends. Instrumented, a level of a parse took some 6.5 KB of
  node's stack in a debug build, so that a peer's first payload nested 256
  deep, document's default, overflowed node's 984 KB at about 150 levels;
  uninstrumented it reaches 400, and in a release build more than 1,000
  (measured). A program whose own parse suspends from a selector's callback
  cannot link this alias under Asyncify; under JSPI nothing is left out.
  Source: `build.jam` and `doc/protocol.adoc` (libs/trystero).
- **trystero links `/third_party//secp256k1`, webcpp's own build of
  libsecp256k1, and needs nothing provisioned outside the build.** Its
  tables follow the feature `webcpp-secp256k1-tables`: window 15 and comb 11x6
  natively, window 2 and comb 2x5 on emscripten (the earlier external build was
  window 4 and comb 2x5 on both). Native
  libdatachannel and its nested dependencies are pinned source targets, built
  statically against the same OpenSSL provider as Asio and Beast. The
  platform backend natively requires `threading=multi`, since libdatachannel
  runs worker threads, and no exceptions. Its WebRTC is webcpp::webrtc's, its
  Asio is named webcpp::asio and its relays' WebSockets are webcpp::beast's;
  natively its sealer and randomness are still OpenSSL's, whose migration
  remains.
  Source: `doc/building.adoc` (libs/trystero).
- **trystero's three source dependencies are initialised submodules, and a
  checkout without one stops the build naming it.** `third_party/libs/secp256k1`,
  `openssl` and `libdatachannel` are initialised with one `git submodule update
  --init --recursive`; no library is searched for, so none is left out.
  Source: `doc/building.adoc` (libs/trystero).
- **embind is linked as the flag `-lembind`, which `/webcpp/asio//asio`
  adds, not with b2's `<embind>on`.** `<embind>on` is not a free feature,
  and b2 ignores one among usage requirements (measured when trystero linked
  embind itself: a program then fails to link, `_embind_register_function`
  undefined).
  Source: `doc/building.adoc` and `AGENTS.md` (libs/trystero).
- **On MSVC `/third_party//secp256k1` gives `SECP256K1_STATIC` to trystero
  through its usage requirements, the source providers export their static `.lib` archives
  with the consumer's runtime settings, and tests and examples add `/bigobj`.** A static
  libsecp256k1 on Windows declares every function imported from a DLL without
  the define, and a test of rooms over Asio holds more sections than the
  default object format allows (C1128).
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **libdatachannel is built with the compiler and standard library of the
  programs that link it.** A program built with GCC and libstdc++ does not
  link against a libdatachannel built with libc++, though the platform
  backend's headers still compile alone.
  Source: `doc/building.adoc` (libs/trystero).

**Licensing.**

- **trystero's own code is under the Boost Software License, Trystero's MIT
  notice ships unchanged as `LICENSE-TRYSTERO.txt`, and the README names what
  derives from Trystero.** trystero ports Trystero's protocol and was written
  with Trystero's source open, so Trystero's notice comes with it.
  Source: `doc/design.adoc` (libs/trystero).

**Evidence.**

- **The `oracle` lane has Trystero 0.26.0's own functions, pinned by
  `package-lock.json`, compute every protocol value over the cases, with the
  action frames and envelopes captured from its action wire manager and
  `SharedPeerManager` over fake peers.** The wire is proven against Trystero
  itself, not against a reading of its source.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-10-09-genesis/design.md`
  (proposals).
- **The oracle fixes the sealed fixture's IV by replacing
  `crypto.getRandomValues` while Trystero's `encrypt` runs.** The sealed text
  is then the same on every run.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **The `interop` lane meets the C++ peers, the browser's in headless Chrome
  and the native one as a process, with Trystero JS peers over an in-memory
  Nostr relay on 127.0.0.1 that verifies every event's id and signature.**
  Guarantee 1 is proven against Trystero JS itself, through a relay that
  checks events as a public relay does.
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals).
- **Every interop peer gathers its ICE candidates on the machine alone, and
  the driver has Chrome resolve no host but 127.0.0.1.** The lanes then need
  no network beyond the machine (measured passing under
  `docker run --network none`), and the usual flags do not stop a full Chrome
  for Testing 156 from contacting Google (measured).
  Source: `AGENTS.md` (libs/trystero).
- **Each interop driver is bounded by 2400 s.** The bound covers the
  scenarios, Chrome's start, the wrong-password observation windows and the
  transient-handshake recovery, so a scenario that does not complete fails by
  name with what each peer saw.
  Source: `test/oracle/Jamfile` (libs/trystero).
- **An interop scenario that lets two rooms negotiate at once fails, naming
  the counts, when a side makes more than four connections.** A livelock of
  crossed adoptions then fails by name, not as flakiness.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **The unit tests run whole rooms in one process over
  `test/support/memory_backend.hpp`, every event posted, and reach nothing
  beyond the loopback.** A room is tested on both targets without the network;
  guarantee 6 is held by the `gcc-14` and `clang-linux-18` lanes, run in a
  container with no network but the loopback.
  Source: `doc/guarantees.adoc` (libs/trystero).
- **The memory backend has a virtual clock, a deliver, drop or hold frame
  filter, deferred opens, held sealer opens, injection, failure and a
  buffering channel; the cases whose outcome depends on time run on the
  virtual clock, which moves only from timer to timer, and a virtual run is
  bounded by 10^6 timers.** The sharing cases cannot be written without
  them; on a wall clock, scaled to run faster, a loaded or paused machine had
  the rooms' timers fire while a case waited, which changed what it
  compared, so those cases failed by chance; and a timer re-armed without
  delay fails a test by name instead of hanging it.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals); `test/support/memory_backend.hpp` and `test/room_test.cpp`
  (libs/trystero).
- **The hooks' storage uses the default resource, and only when a test sets
  them.** The allocation test sets none, so its counts do not change.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **Every test case with a password fixes which side has the lower id.** Only
  the handshake's initiator reports a wrong proof.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **A test in which a peer leaves and comes back with the same id destroys the
  peer's `app` between visits, or sets `idle_timeout` to 0.** An idle
  connection kept by the peer's app would replace the new negotiation.
  Source:
  `libraries/trystero/openspec/changes/archive/2026-11-14-shared-connection/reference/spec.md`
  (proposals).
- **The allocation test tracks every global allocation until it is freed:
  exchanging a `std::pmr::string`, a `pmr_bytes` or a
  `webcpp::document::pmr::document`, reading each protocol text, and both
  long cases see none, natively and on emscripten; a planted allocation is
  seen, so the zeros are not vacuous.** It replaces the global
  `operator new`, counts the C library's allocation functions where the
  platform shows them (not MSVC's, nor any under AddressSanitizer), keeps
  each global allocation by its address until it is freed, and makes Asio's
  once-per-context allocations before it counts: without them, the 6 they
  make would still be out at the drain.
  Source: `doc/allocation.adoc` and `test/allocation_test.cpp`
  (libs/trystero).
- **On Emscripten the allocation test replaces `select()` with one that keeps
  its array on the stack, and under Asyncify counts Asyncify's unwind data
  apart.** Emscripten's `select()` callocs an array on every call, and Asio's
  reactor calls it on every wait, so the count would see the C library's wait
  rather than the rooms'; the test's `run_for` suspends under Asyncify, whose
  unwind data the C library allocates, as webcpp::asio's own allocation test
  counts it.
  Source: `AGENTS.md` (libs/trystero).
- **On emscripten every test of the platform backend runs twice, with
  exceptions and without (`*_no_exceptions`).** No JavaScript exception may
  enter WebAssembly in either build (owner decision, 2026-10-10).
  Source: `libraries/trystero/openspec/specs/trystero/spec.md` (proposals)
  and `test/Jamfile` (libs/trystero).
- **Every emscripten suite runs in both of webcpp::asio's suspension variants,
  jspi and asyncify, and a test whose `main` runs the `io_context` ends with
  `webcpp::test::exit_status`.** trystero links webcpp::asio's runtime, and
  under Asyncify a `main` that suspended loses what it returns.
  Source: `AGENTS.md` (libs/trystero).
- **A test whose cases suspend runs each through `webcpp::test::run_case`
  (`test/cases.hpp`), in a frame of its own that `main`'s frame never holds,
  whatever the link; under Asyncify the room, `app_impl` and allocation tests
  run once more in a `release` build, with webcpp::asio's 8,192 bytes of
  Asyncify stack.** At `-O3` a case that `main` alone calls is inlined into
  it, and a program linked without optimization, as b2 linked a `release`
  build until the Jamroot gave the link its compile's level and as
  `<linkflags>-O0` still links one, then saves every case's locals in
  `main`'s frame at each suspension: the room test's `main` saved 29,776
  bytes so and the test stopped at its first suspension. Linked at `-O3`,
  the three tests' deepest suspensions write 564, 440 and 408 bytes, and a
  `main` with every case inlined fits too (616 for the room test); in
  `debug`, now the deepest build, 2,344, 2,068 and 2,020 (measured on
  2026-11-15 with Emscripten 6.0.11). The `release` runs stay as trystero's
  only runs under Asyncify in the CI's emscripten lane, which builds JSPI.
  Source: `test/cases.hpp`, `test/Jamfile` and `doc/testing.adoc`
  (libs/trystero).
- **`platform_websocket`, the native interop peer and `shared_hardened` are
  built with the standard libraries' own checks
  (`_LIBCPP_HARDENING_MODE_EXTENSIVE`, `_GLIBCXX_ASSERTIONS`).** A completion
  that touches a container its socket cleared, or a resource past its
  lifetime, fails at once.
  Source: `AGENTS.md` (libs/trystero).
- **Guarantees keep their numbers and anchors (`trystero-invariant-<n>`),
  which code and tests cite as `(doc: #trystero-invariant-3)`, and the page
  build fails on a citation that names no anchor.** A comment sends its reader
  to the promise it relies on, and a stale citation fails the build.
  Source: `doc/guarantees.adoc` (libs/trystero).
- **The examples that join a room run over a relay of their own, and every
  example that can have one has its twin on Trystero JS (the owner's
  decision 8 of trystero's refactor).** The quick start and each program of
  the appendix "Differences" that joins a room run natively in the own lane
  `relayed`: `example/run_over_relay.mjs` starts
  `test/oracle/interop/relay.mjs` on 127.0.0.1 and names it in
  `TRYSTERO_RELAY_URL`, which the program reads; their twins in
  `test/oracle/twins/` run in the `oracle` lane, the original as
  `node --conditions=development`, through `test/oracle/run_twin.mjs` over a
  relay of their own the same way. The public relays are a third party a
  build must not depend on, and a relay of the build's own runs Trystero's
  code unchanged. A twin's second peer is a second page, a worker thread
  (`test/oracle/page.mjs`), since Trystero JS has one `selfId` per page;
  Node's WebRTC is werift 0.24.4 as `rtcPolyfill`, which Trystero 0.26.0's
  README names for Node. Of 14 programs, the twins agree with 1, the quick
  start, and diverge from 11; the chat page and `diff_self_id_not_utf8` have
  none, each with its reason in `test/oracle/twins/without-twin.txt`.
  Source: `doc/testing.adoc` and `example/Jamfile` (libs/trystero).
- **One quick start, native and deterministic: two apps with self ids the
  program fixes meet in `lobby`, exchange one message each way, print them,
  leave and exit; without `TRYSTERO_RELAY_URL` they meet over Trystero's
  public relays, as a user's program does; its twin agrees.** An example
  whose output depends on who joins, and which runs until stopped, has
  nothing to compare. The chat page shows the browser, linked and without a
  twin: doc-check refuses an `.expected` beside a linked source, so one
  source cannot be both (chapter 19).
  Source: `example/quick_start.cpp` and `doc/testing.adoc` (libs/trystero);
  `tools/doc/doc-check.py` (webcpp).
- **A difference no program can show is recorded with its reason on the
  page.** Programs observe only through the public API, and through a
  forwarding `backend::factory` where a room hands out nothing.
  Source: `doc/differences.adoc` (libs/trystero).

### crypto (authenticated encryption, randomness and secp256k1 over C backends; own; implemented in 0.1.0)

webcpp::crypto gives C++20 programs on every target the primitives of
cryptography over widely used C libraries that webcpp builds from their
sources: AES-GCM and the AES block cipher, a `random_device` on the system's
generator, a constant-time `equal`, and secp256k1's BIP340 Schnorr and ECDSA
signatures, ECDH, strict DER and the x-only tweak. Version 0.1 is the
proposal's increments 1 and 2, as the owner set them on 2026-11-14; OpenSSL's
memory option is built after it (its block below, unreleased); what is decided
and not built is in chapter 17.

**Scope.**

- **crypto holds primitives only, grouped in namespaces whose headers mirror
  them: the root (`error`, `random_device`, `equal`, `config`), `backends`,
  `ciphers` (`aes128`, `aes192`, `aes256`, `gcm`, `aes128_gcm`, `aes256_gcm`,
  under `<webcpp/crypto/ciphers/>`) and `curves::secp256k1` (under
  `<webcpp/crypto/curves/>`).** The owner's rule of 2026-11-15: a protocol's
  steps (BIPs, EIPs, NIPs) belong to a domain library built on these
  primitives (a future webcpp::bitcoin, ethereum or nostr), so the Taproot
  functions became a generic x-only tweak and lax DER left the library; the
  removed code is kept on the library's branch `save/bitcoin-taproot`.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` (proposals).
- **Hashing and HMAC stay with Boost.Hash2, and HKDF, when a program needs
  it, is written on `boost::hash2::hmac`; every call is synchronous, and
  WebCrypto is not a backend.** The owner's amendment C1 of 2026-10-10; with C
  code on every target nothing waits.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  sections 1.1 and 1.2 (proposals).

**Interface.**

- **Algorithm types follow Boost.Hash2: sizes as `static constexpr` members,
  the output `result_type`, modes as templates over a cipher
  (`ciphers::gcm<ciphers::aes256<>>`), tags as `boost::hash2::digest<16>`,
  and the backend a template parameter defaulting to the default backend; a
  keyed object is built by `static make(...)`, which returns
  `boost::system::result<T>`, never by a constructor.** Boost's own shape is
  what a Boost user expects; a key can have the wrong size and a backend can
  fail to allocate, and the library works without exceptions.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D2
  (proposals); `include/webcpp/crypto/ciphers/gcm.hpp` (libs/crypto).
- **The algorithm types do every guard, the moved-from state, the
  incremental seal's state machine, the length accounting and the zeroing of
  a failed `open` once for every backend; a backend supplies only the traits
  `detail::block_state`, `block_engine`, `gcm_state` and `gcm_engine`.** The
  same guards on every backend are what lets the agreement tests compare
  them; a state trait never refuses, so `ciphers::aes256<backends::bearssl>`
  is a complete type `gcm` can name, and an engine trait refuses only where
  the algorithm is called.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D3
  (proposals); `include/webcpp/crypto/detail/engines.hpp` (libs/crypto).
- **A keyed object is move-only, its destructor wipes the key schedule, and a
  move leaves the source empty: every function of it but assignment and
  destruction returns `invalid_state` before it reads a secret byte.**
  Without that guard a moved-from BearSSL `gcm`, whose vtable survives the
  move, would seal under an all-zero key schedule.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 2.4 (proposals).
- **Data and keys are `std::span<std::uint8_t const>` and
  `std::span<std::uint8_t>`, sizes `std::size_t`, and a limit wider than
  `size_t` on wasm32 is a `std::uint64_t` compared through
  `detail::exceeds`.** No comparison is then tautological on wasm32, which
  clang refuses under `<warnings-as-errors>on`.
  Source: `include/webcpp/crypto/detail/limits.hpp` (libs/crypto).
- **One public header per responsibility; a backend's header checks that its
  library is linked; `config.hpp`, `error.hpp`, `equal.hpp`,
  `random_device.hpp` and `<webcpp/crypto.hpp>` compile with no backend
  linked.** A program that only draws random bytes or compares tags names no
  backend library, and one that only signs names `/third_party//secp256k1`
  alone.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 2.2 (proposals); `test/Jamfile`'s headers-alone list (libs/crypto).
- **`equal` compares in constant time: it reads every byte, accumulates the
  XOR of each pair in a `volatile` local read once after the loop and reduces
  it without a branch; spans of different sizes compare unequal without their
  contents being read.** Hash2's `digest<N>::operator==` is `memcmp`; a size
  is public.
  Source: `include/webcpp/crypto/equal.hpp` (libs/crypto).
- **`<windows.h>` is reached only through `detail/windows.hpp`, which defines
  `NOMINMAX` and `WIN32_LEAN_AND_MEAN` only when absent and undefines only
  what it defined, and every header writes `(max)()`, `(min)()` and
  `(std::numeric_limits<T>::max)()`; tests include every public header after
  a bare `<windows.h>` and before one.** `<windows.h>`'s `min` and `max`
  macros break any `max()` after them, and without `WIN32_LEAN_AND_MEAN` it
  brings `winsock.h`, which clashes with Boost.Asio's `winsock2.h`; only the
  MSVC lanes give the tests their teeth, since libc++ undefines the macros.
  Source: `include/webcpp/crypto/detail/windows.hpp`,
  `test/windows_h_before_test.cpp`, `test/windows_h_after_test.cpp`
  (libs/crypto).

**Authenticated encryption.**

- **`seal` and `open` work in place on `data`, with the tag apart; an AEAD
  copies the tag into a local array and consumes the IV and the additional
  data before it writes the first byte of `data`.** No buffer is copied, and a
  tag, IV or additional data in the same buffer as `data` gives correct
  results.
  Source: `libraries/crypto/openspec/changes/genesis/specs/crypto/spec.md`
  "GCM: in place, the tag apart" (proposals).
- **Every function checks its conditions first, in a fixed order (key size,
  moved-from, the incremental state, IV size, tag size, the length limits),
  and returns before it reads a secret byte; a refusal leaves `data`
  untouched.** The rulebook's rule that a function starts with its guards.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 2.4 (proposals).
- **A failed `open` zeroes the whole of `data` by `volatile` stores after any
  failure that follows the start of decryption; there is no incremental
  `open`.** Every backend decrypts and checks the tag in one pass, and not all
  of them clear what they decrypted; an incremental decryption would hand out
  plaintext before the tag is known.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D5
  (proposals).
- **The incremental seal is `begin_seal(iv, additional_data)`, `update(data)`
  and `result()`, and any error in it ends the message and wipes its state.**
  Additional data is taken whole, so no piece of it needs a growing buffer.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D6
  (proposals).
- **GCM accepts IVs of 1 to 128 bytes, keys of 16, 24 and 32 bytes and tags
  of 16 bytes on every backend, and refuses a message over 2^36 - 32 bytes
  and additional data over 2^61 - 1 bytes with `message_too_long`.** OpenSSL
  accepts no IV longer than 128 bytes, so without webcpp's cap the same call
  would succeed or fail by backend; the limits are NIST SP 800-38D's; the
  page says that a key meant for WebCrypto is of 16 or 32 bytes.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D7 and D8
  (proposals).
- **An AEAD object is used by one thread at a time, and the page says that an
  IV is never repeated under one key and gives the limit of 2^32 messages per
  key with random IVs.** It holds a message's state and a key; a repeated IV
  exposes the XOR of the plaintexts and lets an attacker forge tags.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 2.4 (proposals); `doc/aead.adoc` (libs/crypto).

**Block cipher.**

- **`ciphers::aes128`, `aes192` and `aes256` are complete types for every
  backend; `make`, `encrypt` and `decrypt` exist on ctaes and OpenSSL, and
  BearSSL's `make` stops with a `static_assert` that names them; the block
  cipher has no default backend of its own.** BearSSL exports AES only inside
  its modes; `aes256<>` stays the cipher of `aes256_gcm`, which a second
  default would break.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 2.3 (proposals).
- **webcpp builds no GCM on another library's AES:
  `ciphers::gcm<ciphers::aes256<backends::ctaes>>` does not compile, with a
  message that names the backends that export GCM.** That would be the port
  the owner refused.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 2.4 (proposals).

**secp256k1.**

- **libsecp256k1 v0.8.0 is the only secp256k1 backend, and its whole C API
  stays reachable through `<secp256k1*.h>`.** OpenSSL has ECDSA on secp256k1
  but no BIP340, and the owner named libsecp256k1.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 2.8 (proposals).
- **`curves::secp256k1::keypair::make` takes a `std::pmr::memory_resource*`,
  creates libsecp256k1's context in it with
  `secp256k1_context_preallocated_create`, aligned to
  `alignof(std::max_align_t)`, and randomizes it from `random_device`;
  `verify_schnorr` and `verify_ecdsa` use `secp256k1_context_static` after
  `secp256k1_selftest()` on every call and allocate nothing.** The resource
  serves the context alone, so that the counting test sees every allocation;
  a run-once flag would be the static mutable state the rulebook forbids.
  Source: `include/webcpp/crypto/curves/secp256k1.hpp` (libs/crypto).
- **`ecdh` takes the secret into a local array, wipes it on every path, and
  returns the SHA-256 of the compressed shared point.** libsecp256k1's
  default hash.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 2.8 (proposals).
- **ECDSA's DER is strict (`to_der`, `from_der`, at most 72 bytes) and
  `normalize_ecdsa` gives the low-S form; the x-only tweak takes any 32-byte
  tweak, as a free `tweak_xonly` on an x-only key, giving the key and its
  parity, and as `keypair::tweak_xonly` in place, and a tweak not below the
  group order is `invalid_secret_key` and wipes the key pair.** A wallet's
  needs without a protocol's rules: the caller computes BIP341's TapTweak,
  and BIP341's vectors test the tweak that way.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` (proposals);
  `test/secp256k1_xonly_tweak_test.cpp` (libs/crypto).

**Errors and exceptions.**

- **Every operation that can fail returns `boost::system::result<T>` or
  `result<void>`; the category `webcpp.crypto` declares the values 1 to 14,
  fixed and never reused; 13 and 14, reserved in 0.1, are OpenSSL's memory
  option's.** The owner's rule that every library works with exceptions on and
  off; a value once given is never given again.
  Source: `include/webcpp/crypto/error.hpp` (libs/crypto); a ruling of the
  plan's revision of 2026-11-14 (proposals, `reference/plan.md`).
- **One function throws, `random_device::operator()`, declared only with
  exceptions and raising through `boost::throw_exception`; `config.hpp`
  derives `WEBCPP_CRYPTO_NO_EXCEPTIONS` from `WEBCPP_HAS_EXCEPTIONS`.**
  `std::random_device`'s shape has no other way to report a failure.
  Source: `include/webcpp/crypto/config.hpp`,
  `include/webcpp/crypto/random_device.hpp` (libs/crypto).

**Backends.**

- **A backend is the C library itself, named after it (`backends::bearssl`,
  `openssl`, `ctaes`, `secp256k1`), never a port of it.** The owner refused a
  port of BearSSL's AES-GCM on 2026-10-10: a proven library is reviewed and
  measured, a port is a new thing to review.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D1
  (proposals).
- **BearSSL comes unmodified from webcpp's mirror `webcpporg/bearssl`; its
  notice ships as `LICENSE-BEARSSL.txt`, and webcpp's canary lives in the
  library's `src/`. The backend names its code itself: the CTR class of
  AES-NI, then POWER8, then `aes_ct64`, and GHASH by PCLMUL, then POWER8,
  then `ghash_ctmul64`; the test seam `WEBCPP_CRYPTO_DETAIL_BEARSSL_PORTABLE`
  keeps it on the portable pair.** On wasm32 BearSSL's own default would be
  its 32-bit code; the seam lets the agreement test compare both of BearSSL's
  code paths with OpenSSL's on x86-64.
  Source: `include/webcpp/crypto/backends/bearssl.hpp`,
  `test/agreement_gcm_portable_test.cpp` (libs/crypto).
- **OpenSSL is the superproject's source-built OpenSSL 3.5.9, static,
  through crypto's alias `/webcpp/crypto//openssl`, which on native, wasip2
  and wasip3 links `/webcpp/third_party//openssl` and defines
  `WEBCPP_CRYPTO_HAS_OPENSSL=1`, and on Emscripten stops the compile with a
  forced `#error` that names `/third_party//bearssl`; the header refuses an
  OpenSSL older than 3.0.** The alias follows asio's; webcpp builds no
  OpenSSL for Emscripten; version 3 is needed for `EVP_CIPHER_fetch`.
  Source: `build.jam`, `src/openssl_on_emscripten.hpp` (libs/crypto).
- **The source-built OpenSSL is compiled `no-asm` on MSVC, wasip2 and wasip3:
  table-based AES and 4-bit GHASH, neither constant time, and no AES-NI; the
  page says so and how a program chooses BearSSL there.** The provider's
  profile (chapter 5 rule 7); `OPENSSL_AES_CONST_TIME` would make only the AES
  core constant time.
  Source: `doc/jamfile.adoc`, `doc/backends.adoc` (libs/crypto); the owner's
  decision 2 of 2026-11-14 (proposals, `reference/plan.md`).
- **OpenSSL is given the key once, in `make`; each message re-initialises
  the context with a null key; lengths go in pieces of at most `INT_MAX`
  rounded down to a multiple of 16; `make` maps a null `EVP_CIPHER_CTX_new`
  to `not_enough_memory` and a failed fetch or init to `backend_failure`; and
  the thread's error queue is left as it was found.** EVP takes lengths as
  `int`; the error queue cannot tell a memory failure apart across versions;
  nothing webcpp raises may be left for Beast's TLS to misread.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 3.3 (proposals); `include/webcpp/crypto/backends/openssl.hpp`
  (libs/crypto).
- **ctaes is the copy Bitcoin Core v31.1 ships, `src/crypto/ctaes` of the
  shallow submodule `third_party/libs/bitcoin`, built from `ctaes.c` alone and
  exposed as the block cipher alone.** The owner named "the ctaes of Bitcoin
  Core"; `bitcoin-core/ctaes` is another copy, which adds CBC.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D12
  (proposals).
- **libsecp256k1 is built every module on, and its precomputed tables are the
  b2 feature `webcpp-secp256k1-tables` (`auto`, `small`, `large`), whose
  `auto` is small on Emscripten and large natively and on WASI.** Emscripten
  is the browser's target, where size counts most, and WASI the server's.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D11
  (proposals); `third_party/Jamfile` (webcpp).

**Default backend.**

- **Each family has one default backend per target, chosen by the target
  alone for a stated reason, whatever the program links; no define changes it,
  and a program names any other backend in the type.** AES-GCM's is OpenSSL
  natively, on MSVC too, and BearSSL on Emscripten, wasip2 and wasip3:
  OpenSSL's assembly uses the CPU's AES and carry-less multiplication
  instructions on x86-64 and ARMv8, and BearSSL has them on x86 only; on
  WebAssembly BearSSL is constant time where the `no-asm` OpenSSL is not. A
  program that uses a default it does not link stops where it calls it, with
  the Jamfile line and the type that names another backend; version 0.1's
  `WEBCPP_CRYPTO_DEFAULT_BACKEND_BEARSSL` and `_OPENSSL` stop the build with the
  type to write. Measurements are references and decide no default.
  Source: `doc/tables/crypto.json` and the generated
  `include/webcpp/crypto/detail/defaults.hpp` (libs/crypto); design D32 and the
  owner's answers Q1 to Q4 of 2026-11-17 (proposals, `foundation/design.md`,
  `reference/roadmap.md`).
- **The page warns that a native program that names BearSSL runs BearSSL's
  portable code on an ARM server, where the default, OpenSSL, uses ARMv8's AES;
  the examples use the default and link it on every target with
  `/webcpp/crypto//gcm-default`; it states no factor.** BearSSL has no ARMv8
  AES or PMULL code; the slowdown on the source-built OpenSSL is not measured.
  Source: `doc/aead.adoc` (libs/crypto).

**Randomness and memory.**

- **`random_device` is shaped as `std::random_device` and adds
  `fill(std::span<std::uint8_t>)`, returning `result<void>`; entropy comes
  from one source per platform and nothing else (`getentropy` on Linux, macOS
  and WASI, and through it `crypto.getRandomValues` on Emscripten;
  `BCryptGenRandom` on Windows), in pieces of at most 256 bytes, with no cache
  and no fallback.** The owner's decision of 2026-10-11: entropy always takes
  the safest path, in code simple enough to be checked by anyone. Open: on
  Emscripten, `getentropy` lets a JavaScript exception from a missing or
  throwing `crypto.getRandomValues` into WebAssembly, which trystero measured
  and avoided by calling it from a JavaScript block that catches (chapter 15,
  trystero); `random_device` needs the same guard.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D10
  (proposals); `include/webcpp/crypto/detail/entropy.hpp` (libs/crypto).
- **The backends draw from the same source: BearSSL is compiled with
  `BR_USE_GETENTROPY=1`, `BR_RDRAND=0` and `BR_USE_URANDOM=0`, its seeders
  off on Windows; libsecp256k1's context is randomized from `random_device`;
  webcpp never calls `RAND_bytes`.** No backend chooses its own entropy.
  Source: `third_party/Jamfile` (webcpp).
- **webcpp's code allocates only `keypair::make`'s context, in the resource
  the user gives; no seal, open, `encrypt`, `fill`, signature, `ecdh` or
  verification allocates on any backend; OpenSSL's `make` allocates its
  context through OpenSSL's own allocator, which its page states and
  `allocation_openssl` counts, unless the program takes OpenSSL's memory
  option (below), which sends every allocation of OpenSSL's to the program's
  resource, natively.** The owner's allocators decision, with OpenSSL's
  departure accepted on 2026-10-11; the option serves a program that wants
  OpenSSL's allocations in its own resource.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D17
  (proposals); `test/support/counting.hpp`, `test/openssl_memory/Jamfile`
  (libs/crypto).
- **Key schedules inside webcpp's objects are wiped on destruction and on
  move by stores through a `volatile` pointer followed by
  `std::atomic_signal_fence(std::memory_order_seq_cst)`.** The optimiser
  cannot drop these stores, where it can drop a `memset`.
  Source: `include/webcpp/crypto/detail/wipe.hpp` (libs/crypto).

**OpenSSL's memory option (built after 0.1.0; plan Tasks 15, 16 and 33).**

- **`<define>WEBCPP_CRYPTO_OPENSSL_MEMORY_RESOURCE` sends every allocation of
  OpenSSL in the process to a `std::pmr::memory_resource`; the program gives
  it with `<library>/webcpp/crypto//openssl` in its project's requirements,
  and `config.hpp` refuses it with an `#error` on every WebAssembly target,
  Emscripten, wasip2 and wasip3, and without OpenSSL linked.** The owner's
  decision of 2026-10-11 made `CRYPTO_set_mem_functions` an option of the
  config, so that a program that wants OpenSSL's allocations in its own
  allocator can say so; the library beside the define keeps every target that
  gets it linked with OpenSSL. The owner's decision of 2026-11-17 made it
  native only: on WebAssembly a program's default backend is BearSSL, which
  allocates nothing, and the option's tests are native designs.
  Source: `include/webcpp/crypto/config.hpp`, `doc/memory.adoc`
  (libs/crypto); `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 3.7 and `design.md` D16 (proposals).
- **Under the option the program defines
  `webcpp::crypto::openssl_memory_resource()` once, a `noexcept` function that
  returns a `std::pmr::memory_resource&`, and calls
  `backends::openssl::install_memory_functions()` as the first statement of
  `main`; webcpp never installs from a static initialiser.** OpenSSL's hook
  carries no user data, so any other form would keep the resource in a global
  variable of webcpp's, which the rulebook forbids; static initialisation
  order is unspecified and cannot return an error.
  Source: `include/webcpp/crypto/backends/openssl.hpp`,
  `example/openssl_memory.cpp` (libs/crypto).
- **The program's resource is never destroyed, is thread-safe wherever
  OpenSSL may run on two threads, and is reached without an exception; the
  example makes it with `new` and never deletes it.** OpenSSL frees through it
  after `main`.
  Source: `example/openssl_memory.cpp` (libs/crypto).
- **`install_memory_functions()` only reads OpenSSL's state until its guards
  pass: webcpp's adapter already in place is a success that changes nothing,
  functions other than OpenSSL's three defaults are
  `memory_functions_refused`, then the resource is constructed, then the
  adapter is installed, and OpenSSL's refusal is `memory_functions_refused`;
  every OpenSSL `make` under the option checks that the adapter is in place
  and otherwise returns `memory_functions_not_installed`.** Replacing another
  party's functions would make OpenSSL free that party's blocks through
  webcpp's adapter; a forgotten install gives an error, not an allocation
  outside the resource. The defaults are told by their three addresses alone,
  so a libcrypto DLL, which webcpp never builds, is refused (chapter 19).
  Source: `include/webcpp/crypto/backends/openssl.hpp` (libs/crypto).
- **The adapter is three `extern "C"`, `inline`, `noexcept` functions of
  external linkage, each block headed by its size and aligned to the larger
  of `alignof(std::max_align_t)` and `__STDCPP_DEFAULT_NEW_ALIGNMENT__`; with
  exceptions each call into the resource sits in a `try` whose `catch (...)`
  returns null.** OpenSSL calls them as C functions and frees without a size;
  no exception may cross OpenSSL.
  Source: `include/webcpp/crypto/backends/openssl.hpp` (libs/crypto).
- **On MSVC `backends/openssl.hpp` carries
  `#pragma detect_mismatch("webcpp_crypto_openssl_memory", ...)`, `"resource"`
  with the option and `"openssl"` without it.** Two files of one program
  compiled one with the option and one without then fail with LNK2038.
  Source: `include/webcpp/crypto/backends/openssl.hpp`,
  `test/msvc/memory_two_files` (libs/crypto).
- **Two allocations stay outside the resource, the C library's `FILE` while
  OpenSSL reads its configuration file and OpenSSL's secure heap; the
  resource must serve OpenSSL's initialisation: one that fails there leaves
  OpenSSL unusable for the rest of the process on an OpenSSL built without
  threads, and on one built with threads (MSVC's only build) the call never
  returns; on Windows a thread that used OpenSSL calls
  `OPENSSL_thread_stop()` before it ends, or its blocks stay in the resource;
  the program's code that uses the backend lives in one module; the page
  states each.** No hook of OpenSSL's reaches the first two; OpenSSL keeps a
  failed initialisation, and with threads reports the failure through an
  error queue that needs the initialisation running, which it re-enters; the
  static libcrypto on Windows is never told that a thread ends; a second
  module has its own copy of the adapter, whose address the guard does not
  recognise.
  Source: `doc/memory.adoc`, `example/openssl_memory.cpp`,
  `test/openssl_memory/fail_init_test.cpp` (libs/crypto).
- **The option's programs are native, in `test/openssl_memory`, each declared
  with exceptions and without by the rule `memory-run`: `adapter`;
  `everything`, `late`, `foreign`, `fresh_install`, `forgotten`, `replaced`,
  `second_install`, `fail_second`, `fail_init`, `fail_init_threads` (the
  same program on an OpenSSL built with threads) and `handshake`, which count
  every call of the C library's allocator through an interposer per system;
  and `neighbours`, beside Asio's TLS and libdatachannel; `header_alone` and
  the `windows_h` twins compile. The fixtures `memory_option`,
  `memory_missing_definition_install`, `memory_missing_definition_make`,
  `memory_two_files` and `openssl_memory_on_emscripten` build the user's
  Jamfiles, and `test/messages` and `test/msvc` check each `#error`.** The
  counter proves the whole process, Beast's TLS and libdatachannel's DTLS
  included; a forgotten definition fails the link, and the project's form the
  page shows is built and run.
  Source: `test/openssl_memory/Jamfile` (libs/crypto);
  `tools/test/fixtures/crypto_jamfiles/` (webcpp).

**Build.**

- **BearSSL, libsecp256k1 and ctaes are pinned submodules under
  `third_party/libs/`, built by `third_party/Jamfile` from their own sources,
  file by file, as static libraries, on every target, with `<warnings>off`
  and a section per function and datum (chapter 5).** Neither BearSSL nor
  libsecp256k1 compiles as C++; a program keeps only what it calls.
  Source: `third_party/Jamfile` (webcpp).
- **A program names `/webcpp/crypto//crypto`, a header-only alias, and each
  backend it uses, `/third_party//<name>` (OpenSSL: `/webcpp/crypto//openssl`);
  the Jamroot registers the third-party project as `/third_party` beside
  `/webcpp/third_party`.** The user's form is `/third_party//<name>`, as
  chapter 5 rule 5 writes it, and the existing consumers keep theirs.
  Source: `Jamroot`, `libs/crypto/build.jam` (webcpp).
- **A library named and not called adds no byte, which the rule
  `webcpp.same-program` proves on every target for each backend.** No rule
  built a pair and compared it before.
  Source: `tools/same_program/same_program.jam` (webcpp);
  `test/unused/Jamfile` (libs/crypto).
- **Three layers stop a wrong build, each naming what to add, for BearSSL,
  libsecp256k1 and ctaes: an `#error` or `static_assert` at compile time; a
  link-time canary, `webcpp_crypto_<name>_<commit7>_<configuration>`
  followed by `__add_third_party_<name>_to_your_link`, defined by
  `src/canary_<name>.c`; and on MSVC `#pragma detect_mismatch`, one key per
  backend and one for the default backend. OpenSSL has no canary: its layers
  are the `#error`s and the default backend's key.** A library missing, or of
  another commit or configuration, then fails to link with that name; the
  provider injects nothing into upstream (chapter 5 rule 7).
  Source: `include/webcpp/crypto/detail/canary.h`, `src/canary_*.c`
  (libs/crypto).
- **Every message has a test of its own, in a directory of its own, that
  checks its text: clang's with `webcpp.compile-diagnostic` under
  `test/messages/`, MSVC's as `webcpp.compile-fail` or `webcpp.link-fail`
  under `test/msvc/`, and the build's and the linker's as fixtures of
  `tools/test/crypto_jamfiles_test.py`.** b2 shares one object file between
  two programs that differ only by a free define or a library;
  `compile-diagnostic` is clang's, and skips Emscripten.
  Source: `test/messages/`, `test/msvc/` (libs/crypto).
- **The user's Jamfiles are the fixtures `tools/test/fixtures/crypto_jamfiles/<case>/`,
  each with its `<case>.outcome` (targets, build, what runs print, what each
  linker prints), built on a scratch superproject: `web`, `server`,
  `both_bearssl_named`, `gcm_default`, `block`, `encrypt_and_sign`,
  `openssl_linked`, `sign`, `sign_small`, and the stops (canaries, OpenSSL on Emscripten); a
  `same-as:` line keeps a copied program equal to its original, and the page
  includes each Jamfile and outcome by tag.** A user's Jamfile is what an
  agent copies, so each one shown is built and run as it is shown.
  Source: `tools/test/crypto_jamfiles_test.py` (webcpp).
- **One copy per program: trystero links `/third_party//secp256k1` and no
  other libsecp256k1, and asio and crypto name the one source-built
  OpenSSL.** libsecp256k1's tables are global symbols, and two libcrypto would
  be two error queues.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 4.5 (proposals).

**Targets and evidence.**

- **crypto targets native, wasip2, wasip3 and Emscripten: BearSSL, ctaes and
  libsecp256k1 on every target, OpenSSL on native, wasip2 and wasip3; on
  Windows `/webcpp/crypto//crypto` adds `bcrypt`.** webcpp builds no OpenSSL
  for Emscripten; MSVC has no `getentropy`.
  Source: `build.jam`, `test/Jamfile` (libs/crypto).
- **The vectors run on every backend that has the algorithm: the GCM
  specification's cases and Wycheproof's AES-GCM files, sealed whole and in
  pieces; FIPS 197 for the block cipher; BIP340's vectors, Wycheproof's
  Bitcoin ECDSA file and DER through `from_der`, and BIP341's wallet
  vectors through the tweak.** Every case runs because keys of 24 bytes and
  IVs of any size up to 128 are accepted.
  Source: `test/Jamfile` (libs/crypto); `third_party/libs/wycheproof`,
  `third_party/libs/bips` (webcpp).
- **BearSSL and OpenSSL are compared on AES-GCM, and ctaes and OpenSSL on the
  block cipher, on random inputs from a fixed seed and a drawn one, natively,
  on wasip2 and on wasip3; on x86-64 BearSSL runs once on AES-NI and PCLMUL
  and once on its portable code.** A failure prints its seed; on WASI OpenSSL
  runs its portable C code, another pair of implementations.
  Source: `test/support/agreement.hpp`, `test/agreement_gcm_test.cpp`
  (libs/crypto).
- **The test Jamfile's rule `crypto-run` declares every test program twice,
  the second with `<exception-handling>off`, and every test ends with
  `webcpp::test::exit_status(boost::report_errors())`.** No ordinary lane
  builds without exceptions.
  Source: `test/Jamfile` (libs/crypto).
- **The C libraries' own test programs run on webcpp's build in the own lane
  `c-suites`, on native, wasip2, wasip3 and Emscripten, on every push.**
  Chapter 5 rule 11; the CI has no nightly level (Task 25b, chapter 17).
  Source: `test/c_suites/Jamfile` (libs/crypto).
- **The page is generated where it states support: `doc/tables/generate.py`
  writes the comparison, backend, default, message and Jamfile tables and
  `llms.txt` from `doc/tables/crypto.json` and the tests, and the doc build
  fails when they are stale; size, throughput and measured constant time say
  "not measured yet".** Every table that states support, size or speed comes
  from what tests or measurements produce (the owner's documentation
  requirements of 2026-11-15).
  Source: `doc/tables/generate.py`, `doc/Jamfile` (libs/crypto).

### asio (Boost.Asio on native, Emscripten and WASIp2/P3; implemented for 0.1.0 in preparation)


**Owner-approved architecture update, 2026-11-06.** The coordinated Asio,
Cobalt and Beast migration supersedes the earlier derived-native-context and
consumer overlay choices in the historical design inventory below. Native
upstream-equivalent public types are the actual Boost types. Wasm implementations
are shipped under explicit WebCPP paths, selected by config, and shared by B2
and independent compiler/CMake consumers. Cobalt owns its compiled sources;
Asio's old Cobalt targets are compatibility aliases. Native Cobalt SSL alone uses
the separately corrected WebCPP type after reproduced state/cancellation defects
and explicit owner approval. The core and runner remain unchanged upstream.
On 2026-11-07 the owner reaffirmed that defects found in original Boost behavior
are documented and retained, with negative witnesses; this does not authorize
native fixes or compatibility shims, including for MSVC's no-exceptions
`co_main`. The previously approved native SSL exception remains in force, as do
the separately shipped Wasm adaptations and their correction provenance.

Distribution closure uses `sources.json` in Asio and Cobalt, with B2 lists
generated from the same inventories. Direct compiler and CMake consumers build
from an extracted, hashed source archive. Compiler dependencies must name only
that archive, explicit dependencies or the selected toolchain's declared paths.
Custom executor/PMR settings apply to every source; incompatible per-translation-
unit flags are not repaired by a general ABI guard. The consumer audit checks
the requested configuration instead. Consumer overlay recipes and the lint's
overlay preparation hook have been removed. Historical patch inputs remain only
for maintainer provenance and upstream comparison.

Verified maintainer-generated imports preserve upstream provenance and style;
owned adapters and generators remain linted. The shared integrity gate checks
all generated hashes before any documentation or lint classification. Guides
explain WebCPP additions and link the pinned upstream reference. The migration
plan and its local evidence, not the historical inventory below, determine
current closure. Dated application matrices and Release measurements passed locally
on 2026-11-07. Local lint and review are complete; coordinated remote CI and
publication remain separate gates.


webcpp::asio is a C++20 wrapper over Boost.Asio: natively it is
Boost.Asio itself, and on Emscripten its context derives from the shipped
Asio backend. Its run family suspends into the browser's event loop and yields
after every turn of `max_handlers_per_turn` handlers, with a bridge through
which browser events post, promises and DOM events as Asio operations, sockets and a
resolver that fail as values, and Boost.Cobalt's `co_main` on that loop. The
implementation, source-built OpenSSL, embedded CAs and Cobalt SSL are integrated
with the owner's authorization in superproject `2ba5116`. The published library
repository is `webcpporg/asio`. The original integration record is
[the local closeout](docs/superpowers/plans/2026-11-02-local-integration.md);
[the joint closure](docs/superpowers/plans/2026-11-03-asio-beast-closure.md) covers
tasks 22/23, the complete review and final CI. Version 0.1.0 is in preparation,
not a published release. Pending gates are not claimed complete here.

The source labels below retain the design inventory read on 2026-10-26:
`genesis/` means `libraries/asio/openspec/changes/genesis/` in proposals;
(asio) was `f5fd7a8`, (superproject branch) was `d159022`, and (main) was
`ddb6cb2`. Those historical sources were subsequently committed as Asio `6a7f3fe` and
superproject `c07c212`. Current contracts below include the owner's 2026-11-03
amendments; old dates and commits identify evidence, not the current Git status.
Baseline CI 41597577370 at root `55a72c0` does not validate the closure tree.
Asio's first library-main CI and the final joint candidate remain separate gates.

**Decided.**

**Interface and names.**

- **Native public types are aliases of Boost.Asio; Wasm public types select
  the shipped `webcpp::asio_backend` implementation.** On Emscripten the
  public context derives from that backend context and adds bounded turns.
  Portable applications use `webcpp::asio` headers and names for contexts,
  timers, `post`, `co_spawn`, completion tokens and executor bindings. Wasm
  objects do not interoperate with separately instantiated Boost.Asio types.
  The three portable libraries share the same selected implementation.
  Source: owner approval, 2026-11-06, and
  `docs/superpowers/specs/2026-11-06-portable-network-libraries.md`.
- **Each target links its explicit runtime source once:**
  `src/browser_src.cpp` supplies the browser bridge and JavaScript imports;
  `src/wasip2/pollable.cpp` and `src/wasip3/waitable.cpp` supply their WASI
  bridges. Cobalt owns its separately compiled core and runner. B2 and
  external builds consume these shipped sources without modifying Boost.
  Source: `doc/distribution.adoc` (asio) and the portable-library contract.
- **The convenience header `<webcpp/asio.hpp>` leaves out
  `<webcpp/asio/ssl.hpp>`.** Natively that header brings OpenSSL, which a user
  of the rest should not pay for.
  Source: `genesis/specs/asio/spec.md`, Library: Convenience header
  (proposals).
- **`<webcpp/asio/config.hpp>` includes `<webcpp/config.hpp>` first and
  derives `WEBCPP_ASIO_NO_EXCEPTIONS` from the collection's exception policy,
  preserving an explicit library override.** The public target and browser
  source target depend on `/webcpp/config//config`. `WEBCPP_NO_EXCEPTIONS`
  and compiler exception settings agree with the library macro; `config_all_off`
  exercises a real global-disable consumer. Public headers include config first,
  and public platform selections use the collection's target macros.
  The compiler-forced `src/openssl_on_webassembly.hpp` refusal intentionally
  tests the compiler macro before normal configuration headers are available.
  Throwing APIs stay guarded and raise through `boost::throw_exception`.
  Source: `genesis/specs/asio/spec.md`, Library: Configuration header
  (proposals).
- **On single-thread Emscripten the shipped backend disables threads in every
  translation unit, `browser-src` included; explicit pthread builds retain
  its POSIX thread configuration.** Both link embind,
  `browser-src`, the variant's link flags and the tag rule. The backend's inline
  namespace differs with and without threads, so every compiled dependency
  must use the consumer's profile. A silent switch from multi to single is
  forbidden. Browser runtime isolation remains a host requirement.
  Source: `genesis/specs/asio/spec.md`, Build (proposals).
- **The library uses Boost.Asio's native types and a checked, shipped backend
  derived from Boost 1.92 on Emscripten and WASIp2/P3; WASI supports guest TCP/UDP
  and optional source-built TLS.** A library
  may declare only the targets its actual APIs support. Beast's portable
  messages and WASI host HTTP do not require guest sockets. xactor's existing
  Asio driver stays native until separately adapted; Asio's port does not
  silently extend that driver's target set.
  Source: `genesis/design.md`, D16 (proposals).
- **A library built on webcpp::asio is given an executor and never calls
  `run`, `run_one` or `run_for`; a program's own call says why after
  `lint-run:`, and xactor's `asio_driver` keeps draining an `io_context{1}` of
  its own with `poll`.** The run family may suspend only where a program
  allows it, and a context without a reactor suspends nothing, so xactor is a
  user of asio, not a dependency.
  Source: `genesis/specs/asio/spec.md`, Run, and `genesis/proposal.md`
  (proposals).

- **Asio capabilities are read-only 0/1 macros in `config.hpp`; optional
  dependency selection is separate from target availability.** Explicit
  `WEBCPP_ASIO_REQUIRE_*` switches reject compiler-visible unsupported needs;
  feature headers diagnose wrong targets. Network grants, trust roots, actual
  browser isolation and blocking host imports remain runtime conditions.
  The owner approved implementation completion and external-boundary guards on
  2026-11-03. Do not reclassify missing WebCPP code as a platform limitation.
  Source: `docs/superpowers/specs/2026-11-03-asio-capability-completion-design.md`.

**The run family and the turn limit.**

- **On Emscripten the six members of the run family hide the backend's and compose
  `poll_one` and `run_one`: a turn of ready handlers, a return if stopped or
  expired, a yield if the turn reached the limit, else one `run_one` whose
  handler consumes the same turn budget.** The latter suspends in the reactor's
  `select`; natively the context and its operations are Boost's unchanged
  types. Boost's `run` is not virtual and cannot be told to
  yield: measured, a self-posting handler ran 300,000 times under it before a
  `setTimeout(0)` ran, because a zero-timeout `select` suspends only to a
  microtask. Code that calls `run` through a `webcpp::asio_backend::io_context&`
  gets the inherited backend run without the limit, as documented.
  Source: `genesis/design.md`, D2 (proposals).
- **The yield is the `EM_ASYNC_JS` import `webcpp_asio_yield`, which awaits a
  promise that a `MessageChannel` message resolves.** A macrotask lets the
  browser render, run its timers and deliver its events, and `MessageChannel`
  exists in node and in every browser; the guide calls the yield an
  opportunity for browser work, not a promise that a given timer or frame runs
  first.
  Source: `genesis/design.md`, D3 (proposals); `doc/run.adoc` (asio).
- **A timed run checks its deadline before each handler, a limit of 0 is taken
  as 1, and a `stop()` by the handler that reaches the limit returns at once,
  without a yield.** A passed deadline then runs nothing, a self-posting
  handler cannot outrun `run_for`, and the run family never yields forever
  without running anything.
  Source: `genesis/design.md`, D3, and `genesis/specs/asio/spec.md`, Run
  (proposals).
- **The default `max_handlers_per_turn` is 100, the build default
  `WEBCPP_ASIO_DEFAULT_MAX_HANDLERS_PER_TURN` of `config.hpp`, which a context
  overrides at construction or with `max_handlers_per_turn(n)`.** The owner
  selected 100 on 2026-10-15, after the Release yield benchmark, to favor the
  browser's responsiveness: about ten times as many yields as 1,000, at about
  44.0/54.5 ms of scheduling per million trivial handlers (JSPI/Asyncify)
  against 4.64/5.73 ms, a policy and not a measured optimum. The earlier 1,000
  was an initial policy, kept after task 13's Chrome check (turn p95 0.7 ms
  under JSPI, 1.6 ms under Asyncify).
  Source: `doc/yield-cost.adoc`, `AGENTS.md`, commit `24c1e2c` (asio).
- **The build default is a compiler definition that every translation unit of
  a program shares, Cobalt's separately compiled runner included, and a
  negative value stops the compile.** The owner asked for a build-time
  configuration; objects built with different definitions are never mixed in
  one program.
  Source: `include/webcpp/asio/config.hpp`, `doc/run.adoc` (asio);
  `genesis/reference/STATUS.md` (proposals).
- **The limit counts every handler completed by `poll_one` or `run_one` in
  the same turn, and is no time budget.** At most `max_handlers_per_turn`
  handlers run between explicit cooperative yields. Only that yield resets
  the budget: a wait can suspend only to microtasks, so resetting after each
  wait can starve browser events and worker proxy messages. A blocking wait
  may give the host an earlier opportunity to run, and a long handler is never
  interrupted. Stop, expiry and exhaustion of work still return before a yield.
  Source: `doc/run.adoc`, `test/turn_limit_test.cpp` (asio).
- **The browser lane stops the work for the owner's decision when a turn's
  95th percentile exceeds 8 ms in any of three runs, and its driver fails when
  no animation callback occurs.** The criterion leaves roughly half of a 60 Hz
  frame's 16.7 ms to the browser and is a heuristic, not a frame-rate
  guarantee; with 100, Chrome measured a turn p95 of 0.100 ms (JSPI) and 0.300
  ms (Asyncify) and about 60 callbacks a second.
  Source: `genesis/design.md`, D3, and `genesis/reference/STATUS.md`
  (proposals); `doc/yield-cost.adoc` (asio).
- **The turn limit's tests count the run family's yields
  (`webcpp::test::yield_counter`, every `MessagePort.postMessage`) for both
  self-posting handlers and timer-completion chains.** They pin the handler
  budget between explicit yields, but assert only where a `setTimeout(0)`
  runs, never after how many handlers that particular timer must run. When a
  `setTimeout(0)` runs is the host's: node delays it by 1 ms, a browser clamps
  a nested one to 4 ms and throttles a background tab's to 1 s or more.
  Source: `genesis/specs/asio/spec.md`, Testing (proposals).

**The reactor and who calls the run family.**

- **The io_context holds one unarmed `boost::asio::steady_timer` member,
  through public API, so that the reactor exists from construction.** With
  threads disabled, a `run` that has work and no reactor waits in
  `null_event::do_wait`'s `::pause()`, which nothing wakes (measured); with
  the reactor it suspends in `select`, which a post wakes.
  Source: `genesis/design.md`, D6 (proposals).
- **Handlers run only on the stack of a run family call: work and events that
  arrive before `run` wait for it, and after `main` returns, the runtime
  alive, nothing runs until an export listed for suspension calls the run
  family again.** The owner settled on 2026-10-10 that use without `run` is
  not supported, on every target, as natively.
  Source: `genesis/reference/spec.md`, sections 4.8 and 11 (proposals).
- **The run family is called on `main`'s stack or on an export the program
  lists for suspension (`-sJSPI_EXPORTS`, `ccall(..., {async: true})`), and
  nothing calls `run`, `poll` or `dispatch` from a JavaScript event.**
  Anywhere else its first suspension fails: a `SuspendError` under JSPI, an
  unwind that corrupts a suspended `main` under Asyncify.
  Source: `genesis/specs/asio/spec.md`, Run (proposals); `AGENTS.md` (asio).

**The bridge and the detection.**

- **Every browser event source is a JavaScript function made by
  `browser::bridge`, a service of the io_context made with its allocator,
  registered by a `std::uint64_t` key counted from 1 and never reused (a
  `BigInt` in JavaScript); a delivery looks the key up and only posts.** While
  `run` is suspended an event sees `running_in_this_thread()` true, so a
  `dispatch` would run its handler on the event's stack, and a run family call
  there fails at its first suspension; a key never reused lets a late event
  find nothing.
  Source: `genesis/design.md`, D7 (proposals).
- **The bridge's JavaScript functions keep the stack pointer, the count of
  deliveries in progress and the event's handle however a delivery ends; a C++
  exception is caught in C++, a trap goes on to the page, `ExitStatus` and
  `'unwind'` end the delivery unreported, and nothing enters WebAssembly after
  `ABORT`.** A JavaScript error passes every C++ `catch` and skips the frames'
  epilogues, and their destructors outside WebAssembly exceptions.
  Source: `genesis/design.md`, D7 (proposals).
- **`bridge::deliver` is private, with the export `webcpp_asio_deliver` as its
  only friend, and `delivering()` takes no value, both pinned by compile-fail
  tests.** An earlier public `unwound` let user code break the refusal of a
  run family call made from an event.
  Source: `genesis/design.md`, D7, and `genesis/reference/STATUS.md`
  (proposals).
- **Each of the six members admits its call once, first, by a flag
  (`BOOST_ASSERT_MSG`, else a return of 0 that runs nothing), then calls only
  private unchecked code; a `flag_scope` puts back the value it found, and the
  four calls it cannot detect are documented.** A public member that called
  another would be refused by its own flag, and an inner scope must never
  clear an outer one's; a C++ exception clears the flag on its way out of
  `run`.
  Source: `genesis/design.md`, D8 (proposals).
- **asio does not restore its flag after a JavaScript error escapes a handler:
  handlers catch JavaScript errors in JavaScript.** No boundary can restore
  Boost's own state (its work count, its call stack), and a recovered flag
  would trade a reported refusal for a `run` that never returns.
  Source: `genesis/design.md`, D8 (proposals).

**Suspension variants, artifacts and the loader.**

- **JSPI and Asyncify are build variants, the propagated composite feature
  `webcpp-suspend`: `jspi` by default, with WebAssembly exceptions, and
  `asyncify`, which composes `<exception-handling-method>js` and builds in a
  directory of its own.** The owner decided on 2026-10-10 that the variant is
  chosen at build time and the developer ships the artifact a page's loader
  picks; b2 takes only free features from usage requirements, and Asyncify
  traps at run time with WebAssembly exceptions.
  Source: `genesis/design.md`, D4 (proposals).
- **The variants link `-sJSPI` and `-sASYNCIFY` with no
  `ASYNCIFY_IGNORE_INDIRECT` and no list of suspending imports.** Emscripten
  finds `__syscall_poll` and the yield itself, and the path from `main` to
  `select` passes the virtual `scheduler_task::run`.
  Source: `genesis/specs/asio/spec.md`, Build (proposals).
- **Asyncify's stack is 8192 bytes unless a program raises it with the
  propagated feature `asyncify-stack-size` (powers of two up to 1048576, a
  smaller value stopping the compile), and `asyncify_stack` reads the bytes
  each unwind wrote from Asyncify's own data, in debug and release.** A
  suspension that does not fit traps with `RuntimeError: unreachable`. 8192
  was twice the smallest power of two every build passed with when b2 linked
  a release build without optimization (deepest 3,540 bytes, Cobalt's
  1,088); since release links at `-O3` (#18) debug is the deepest build
  (1,168 bytes, 388 in release; Cobalt's 1,036 and 384, measured on
  2026-11-15). The owner decided on 2026-11-15 that 8192 stays: programs
  ship release builds, where the deepest suspension of the libraries built
  on asio wrote 564 bytes (trystero's room test), and debug, for
  development and the tests, 2,344, within the half `asyncify_stack` asks;
  8192 is also the floor those libraries are tested against.
  Source: `genesis/design.md`, D5 (proposals); `AGENTS.md` (asio).
- **Artifacts are named Boost's way (`app-60-d-jspi.js`,
  `webcpp-suspend-asyncify/app-60-d-asyncify.js`), `webcpp.variants` builds a
  page program in both variants with `<name>.variants.json`, and
  `webcpp-asio-loader.mjs` (`supportsJspi`, `pick`, `load`) reads that
  manifest, never a pattern.** The owner decided on 2026-10-10 that build
  output and names follow Boost's own build exactly, and the manifest lets the
  page load the variant its browser runs; the loader resolves scripts against
  `response.url`, so that a redirect does not misdirect it.
  Source: `genesis/design.md`, D10, and `genesis/reference/STATUS.md`, task 12
  (proposals).
- **Published binary sizes are release builds, which the superproject links
  at `-O3` as it compiles them, and `webcpp.size-table` records every guide
  example in both variants.** b2 1.92's emscripten toolset passes no
  optimization level to the link, which the Jamroot's region
  `emscripten-link-optimization` adds (#18); in release Asyncify's program
  is about twice JSPI's (asio's timers, 988,047 bytes against 489,216 of
  `.wasm`), and 2.9 times in debug. The
  optimized JSPI link exports `emscripten_stack_get_current` and
  `_emscripten_stack_restore`, since Emscripten reads `EM_JS_DEPS` after
  native linking.
  Source: `genesis/reference/STATUS.md`, task 14 (proposals); `build.jam`
  (asio).

**Tests.**

- **A test under node ends as its `main` ends: `node-pre.js`, which every
  `webcpp.run`, `webcpp.run-fail` and `webcpp.example` links on Emscripten,
  fails a test whose `main` did not finish, keeps the first status
  `webcpp::test::exit_status` gives, and stops a test past its bound (120 s by
  default).** Under node a `main` that suspended and returns non-zero exits 0
  under Asyncify, and one that never finishes exits 0 on both variants, so
  every Asyncify lane would read green whatever it tested.
  Source: `genesis/design.md`, D9 (proposals); `AGENTS.md`, chapter 9
  (superproject branch).
- **Cobalt's exit statuses are checked by a driver, exactly 7 and 0, in lanes
  of their own (`cobalt`, `cobalt_asyncify`).** A `run-fail` test alone would
  also accept a trap or an unfinished `main`.
  Source: `genesis/reference/STATUS.md`, task 16 (proposals); `test/Jamfile`
  (asio).
- **Concurrent builds are not capped: a test that fails under load is flaky
  and is fixed.** The owner ruled on 2026-10-11 that a flaky test is never
  protected by running less at once.
  Source: `genesis/reference/plan.md`, Global Constraints (proposals).

**Exceptions.**

- **A handler's exception propagates out of `run` on both variants, after any
  number of suspensions, and each variant compiles with the exception model it
  can suspend through.** Handlers run on `main`'s stack inside the run family
  call, and Asyncify traps when it suspends inside a `catch` block of
  WebAssembly exceptions.
  Source: `genesis/specs/asio/spec.md`, Exceptions (proposals).
- **Every browser test is declared in four builds, JSPI and Asyncify each with
  exceptions on and off, the Asyncify ones in the own lane `asyncify`.** The
  owner asked on 2026-10-10 that every variant be tested; native runs without
  exceptions are departure 5.
  Source: `genesis/specs/asio/spec.md`, Exceptions (proposals).
- **`/webcpp/cobalt//core` follows the consumer's exception setting, and
  without exceptions b2 prints a non-fatal warning that names Cobalt's issue
  287.** The owner asked on 2026-10-14 to remove the blanket refusal; in Boost
  1.92 moving a pending task calls `std::make_exception_ptr`, which aborts
  with libc++ and `-fno-exceptions`, so the warning states a run-time risk and
  claims no safety.
  Source: `genesis/reference/STATUS.md` (proposals); `AGENTS.md`, chapter 1
  (superproject branch).
- **The shipped Wasm Cobalt promises supply `unhandled_exception` for main
  and thread when exceptions are disabled; native promises remain Boost's.**
  The Wasm hooks use `std::terminate` for the unreachable exception path,
  retaining strict diagnostics and worker/join tests. Boost 1.92 omits those
  hooks natively: MSVC rejects no-exceptions `co_main`, and a compile-failure
  witness is paired with an exceptions-enabled control and a missing-member
  witness. Other no-exceptions consumers remain enabled without a general
  safety guarantee.
  Source: `doc/differences.adoc`, `test/upstream_limits/main_no_exceptions.cpp`
  (cobalt); the historical `tools/boost/cobalt-common/boost-1.92.patch`
  records correction provenance only.

**Allocation.**

- **The io_context passes the user's allocator to Boost's constructor, an
  operation allocates through its handler's associated allocator, and the
  bridge's map through the context's.** Native Boost retains the IOCP thread
  allocation limitation described below; passing a context allocator does not
  establish zero global allocation on every platform. An allocator given to
  the context is not associated with handlers, which bind it with
  `bind_allocator`.
  Source: `genesis/specs/asio/spec.md`, Allocation (proposals);
  `doc/allocation.adoc` (asio).
- **The counting test counts every `operator new`, the C library's allocation
  functions and the aligned ones, with a control that sees an unbound handler,
  and names rather than tolerates what the runtime allocates itself:
  Emscripten's `select` poll array, Asyncify's unwind data and
  `basic_resolver_results`' entries.** Asio's default handler memory ends in
  `aligned_alloc` or Boost.Align, never in `operator new`, so counting
  `operator new` alone reads 0; native allocation tests compile with
  `-fno-builtin`, since optimized builtins elided or reordered the counted
  calls.
  Source: `genesis/specs/asio/spec.md`, Allocation, and
  `genesis/reference/STATUS.md` (proposals).

**Timers, promises and events.**

- **Timers use the selected Asio backend on every supported target, in the
  reactor's timer queue: Beast's timeouts fire.** On Emscripten an idle program
  holds the reactor's one `setTimeout`, of at most 300 s, and schedules nothing else.
  Its code resumes when the browser delivers an event, never by polling.
  Source: `genesis/specs/asio/spec.md`, Timers and Browser (proposals).
- **`async_await(executor, promise, token)` and
  `async_wait_event(executor, target, type, token)` initiate through
  `async_initiate` as bridge registrations: the settlement or the event posts
  the handler, a rejection completes with `browser::error::promise_rejected`
  (value 1 of `webcpp.asio`, never reused) and the reason, a cancellation
  completes at once with `operation_aborted` and drops the registration (and
  the listener), and a pending operation is outstanding work that destroying
  the io_context destroys uncalled.** Every completion token then works (a
  callback, `deferred`, `use_awaitable`, Cobalt's `use_op`), and a late
  settlement finds nothing.
  Source: `genesis/design.md`, D12 (proposals).
- **A promise or event operation allocates through its handler's associated
  allocator and keeps its handler's executor work while pending; an event wait
  listens with `once: true` and makes the event type a JavaScript string from
  the `std::string_view`, with no `std::string`.** The final review found the
  handler's executor work lost, fixed in `f5fd7a8`.
  Source: `genesis/specs/asio/spec.md`, Promise and Event, and
  `genesis/reference/STATUS.md` (proposals).

**Sockets, the resolver and TLS.**

- **On Emscripten `ip::tcp` and `ip::udp` are webcpp's protocol classes with
  Boost's members, and the sockets and the acceptor are class templates over
  `browser::transport<Protocol>`, whose primary completes every operation with
  `operation_not_supported`, synchronously or through a post; natively all are
  aliases of Boost's.** Boost's sockets compile on Emscripten but connect
  through SOCKFS, which opens a WebSocket, and `getaddrinfo` invents
  addresses; the owner decided on 2026-10-10 that what a browser cannot do
  compiles and fails as a value behind a point a relay can fill.
  Source: `genesis/design.md`, D13 (proposals).
- **A transport specialisation is visible in every translation unit before its
  first use, is enabled for a whole program by a b2 feature designed with the
  first relay library, supplies `close()`, and leaves a moved-from source with
  a usable executor.** The one definition rule; the final review found `close`
  not forwarded and moved-from transports unusable.
  Source: `genesis/design.md`, D13, and `genesis/reference/STATUS.md`
  (proposals).
- **The browser resolver resolves nothing (option A): one entry with the host and
  service names, an unspecified address and the service's port; reverse
  resolution, and a plain socket's connect on the entry, fail with
  `operation_not_supported`.** Only webcpp::beast's browser streams accept the
  entry, so Beast's layered client code runs unchanged; a resolver that failed
  like the sockets would change a line of every Beast client.
  Source: `genesis/design.md`, D14 (proposals).
- **`<webcpp/asio/ssl.hpp>` selects Boost's `ssl` natively and the shipped
  Asio backend's SSL types on WASI; on Emscripten it records TLS settings
  and a host name in `std::pmr` storage for webcpp::beast's browser streams.**
  Guest TLS explicitly names
  `/webcpp/asio//openssl` on native or WASI. Naming that source provider for
  Emscripten fails with an instruction; the browser owns TLS in its profile.
  WASI host HTTP continues to use the host's independent TLS implementation.
  Source: `genesis/design.md`, D15 (proposals); `include/webcpp/asio/ssl.hpp`
  (asio).

**Boost.Cobalt.**

- **Cobalt owns separate native and Wasm core and runner sources, selected
  by `/webcpp/cobalt//cobalt`; neither Asio nor the Jamroot declares an alias
  to a Cobalt target (the owner's decision of 2026-11-14).** Native
  `src/native/main.cpp` retains upstream behavior. Wasm
  `src/wasm/main.cpp` supplies `main_promise::run_main` and `final_suspend`
  over `webcpp::asio::io_context{WEBCPP_ASIO_BACKEND_CONCURRENCY_HINT_1}`,
  which adds bounded turns on Emscripten. `co_main` calls the separately
  compiled runner, so its settings must agree with the application. The core
  excludes the runner and optional SSL implementation; `sources.json` records
  all target-specific source selections.
  Source: `sources.json`, `src/Jamfile`, `doc/building.adoc` (cobalt);
  `genesis/design.md`, D11 (proposals), records the original runner design.
- **Under Asyncify `run_main` ends the program with `std::exit` once the
  context and the signal set are destroyed, and `EXIT_RUNTIME` stays 0.** A
  `main` that suspended loses its return value under Asyncify, so the
  `co_return` value would not be the exit status; a full runtime teardown is
  not promised.
  Source: `genesis/design.md`, D11, and `genesis/reference/STATUS.md`, task 16
  (proposals).
- **Cobalt's shipped `src/wasm/main.cpp` keeps the copyright notice of
  Boost.Cobalt's `main.cpp`, beside webcpp's.** The earlier adaptation at
  Asio's `src/cobalt_main.cpp` acquired that attribution during its original
  review; the generated source preserves it after the move.
  Source: `genesis/reference/STATUS.md`, task 16 (proposals).

**Documentation and release.**

- **The guide is one AsciiDoc page with a MrDocs reference, written by
  learning, doing, understanding and reference needs (Diataxis), with thirteen
  numbered guarantees and examples checked against their `.expected` output,
  the portable ones natively and in the browser.** The owner asked for
  Diataxis writing on 2026-10-14 and kept the superproject's documentation
  pipeline.
  Source: `genesis/reference/STATUS.md`, task 14 (proposals);
  `doc/guarantees.adoc` (asio).
- **The release record distinguishes repository integration, CI and a
  published release.** The repository and submodule exist, and the owner
  authorized the joint closure's pushes and merges on 2026-11-03. That does
  not authorize a release tag. Final review and CI must describe the exact
  candidate, with root workflow integration before library-main CI because
  those workflows consume `library.yml@main`. Baseline CI is not evidence for
  later edits. The AsciiDoc changelog and 0.1.0 New Libraries entry remain
  preparation metadata until a release is requested.
  Source: `docs/superpowers/plans/2026-11-03-asio-beast-closure.md` (superproject).

**Earlier approved departures and their current scope.** The owner approved
five bounded departures on 2026-10-11. The later source-provider decision
supersedes the temporary system-OpenSSL choice; it does not reopen every rule.

- The `asyncify` own lane runs on every push while nightly/release CI levels
  remain roadmap work. Declaring it does not establish that Asio main has run it.
- The Wasm context retains concurrency-hint constructors with and without an
  allocator, including Cobalt's `io_context{1}` use. Native constructors are
  Boost's unchanged constructors.
- Plain `/webcpp/cobalt//core` omits SSL; the explicit
  `/webcpp/cobalt//io_ssl` supplies the corrected native or WASI wrapper.
- The former shared system OpenSSL/native-only bridge is superseded by the
  pinned static source provider on native, WASIp2 single and WASIp3, without
  waiting for crypto.
  Chapter 5 rule 7 retains its Configure/Make and exact-archive canary exception.
- Dedicated no-exceptions programs and local complete suites run natively;
  the general CI-level expansion remains chapter 16 work. Do not mistake those
  programs for proof of every native compiler and profile.

**Compatibility and allocation boundaries.** The existing
`webcpp.asio.tls` category and `tls_context_error` values 1 to 3 remain public
identities alongside `webcpp.asio`. Preserving callers' comparisons is a bounded
compatibility departure from chapter 4's single-category naming convention;
merging or renumbering those errors is not an approved cleanup.
TLS category identity uses the fixed Boost.System ID `0x6173696f2e746c73`
(ASCII `asio.tls`), so codes compare equally across hidden native shared-library
boundaries. This does not make category virtual functions safe after a provider
library is unloaded; callers retain that library while using its error values.

The browser resolver owns host/service copies through the completion token's
associated allocator, captured when `async_resolve` creates the operation. It
still resolves inside initiation, so deferred tokens remain lazy and inputs
survive caller mutation. A deferred operation needs its allocator bound at
creation; binding only when starting it cannot retroactively select storage.
Boost resolver result entries have no allocator hook and remain a named boundary,
as do Emscripten's select poll storage and Asyncify unwind storage. OpenSSL's
process-global allocator is a separate boundary below, never installed by the
TLS context factory.

Allocation witnesses now execute on WASIp3 single with exceptions on/off and
cooperative with exceptions off. They distinguish supplied allocator storage,
global C++ allocation and wrapped C allocation. The narrowly attributed wasi-libc
pipe creation and writes to tracked pipe descriptors have positive controls;
the witness does not classify arbitrary Boost allocations as runtime storage.
This proves the exercised operations, not all possible library paths.
The `threads` own lane contains `cobalt_thread`, `wasi_core_threads` and the
threaded allocation witness on native/WASIp3. Real exception unwinding in the
single profile and standalone `ssl.hpp` are also tested on WASIp3.

**WASIp3 and TLS beyond the original proposal.** These increments were
implemented with local specs and plans under `docs/superpowers/` and integrated
on 2026-11-02 after the owner's instruction to finish the remaining integration.
The owner ratified these additions to the proposal on 2026-11-03. Its amended
D15/D16 now distinguish WASIp3 sockets and guest TLS from the browser adapters.
The closure record distinguishes the baseline CI from validation of later changes.

- **Asio runs on WASIp3 (`clang-wasip3`) through its shipped backend, derived
  from Boost 1.92's scheduler and select reactor with explicit platform
  adaptations.** The installed Boost tree remains untouched. Maintainer import
  generation checks the pinned inputs and records the generated hashes;
  consumers compile the shipped headers and runtime sources directly. The
  earlier private-header patching workflow is historical provenance only.
  Source: `upstream/README.md`, `sources.json`, `doc/distribution.adoc` (asio);
  `docs/superpowers/specs/2026-10-15-asio-wasip3.md` records the original port.
- **On WASIp3 the io_context uses the backend's run family, with no turn limit,
  bridge or yield.** Its system calls suspend through wasi-libc and the host's
  Component Model.
  Source: `doc/capabilities.adoc`, `include/webcpp/asio/io_context.hpp` (asio).
- **`threading=single` disables Asio's threads, with exceptions on or off;
  `threading=multi` selects wasi-sdk's experimental cooperative sysroot with
  `-pthread`, exceptions off, and a combination the SDK cannot supply stops
  the build.** A threaded build must never get the single-threaded
  implementation in silence, and wasi-sdk 34's cooperative sysroot has no C++
  exception runtime.
  Source: `docs/superpowers/specs/2026-10-15-asio-wasip3.md`,
  `tools/webcpp-wasi.jam` (superproject).
- **The WASIp2/P3 tests use the project-pinned Wasmtime 50.0.1 through the
  corresponding `tools/boost/asio-wasip2/run.sh` or `asio-wasip3/run.sh`
  launcher, which grants network and name lookup and defaults to 600 s per
  process.** These launchers serve the global lanes, including large finite
  parsing workloads that exceed a focused networking test's 60 s budget.
  `WEBCPP_WASIP2_TEST_TIMEOUT` and `WEBCPP_WASIP3_TEST_TIMEOUT` can select another
  positive finite bound for their target. Wasmtime 47.0.3 cannot load the
  cooperative component. These grants and limits are test-harness settings;
  they neither configure production capabilities nor enforce network isolation.
  Source: `tools/boost/asio-wasip3/README.md` (superproject).
- **WASI UDP sends gather several nonempty buffers into one datagram,
  connected or unconnected; receives scatter one datagram into the destination
  sequence.** Temporary storage uses the context allocator synchronously or
  the handler's allocator asynchronously and is released before completion.
  Truncation, empty datagrams and cancellation preserve datagram boundaries.
  The pinned libc lacks `sendmsg`/`recvmsg`; the shipped Asio backend contains
  this adaptation without changing the installed SDK.
  Source: `docs/superpowers/specs/2026-10-15-asio-wasip3.md` (superproject); `AGENTS.md` (asio).
- **What WASI lacks is explicit: Asio's `shut_down` error maps to `EPIPE`,
  interface-name scopes are refused, a missing socket option reports
  `operation_not_supported`, and reverse/canonical lookup policies remain
  unsupported.** Forward asynchronous resolution uses native P2 pollables or
  P3 async subtasks/waitables in both supported thread profiles. It never
  blocks initiation, starts a hidden worker or scans DNS with periodic timers.
  Private libc descriptor APIs require the checked SDK/revision/hash manifest.
  Source: `doc/capabilities.adoc` (asio).
- **The library's applicable test and example Jamfiles declare WASIp2/P3
  beside native and Emscripten; Cobalt and OpenSSL support WASIp2 S, and
  `doc/capabilities.adoc` with `doc/feature-matrix.adoc` is kept current for
  every feature, target and variant, telling unavailable from unverified.**
  The owner approved an AsciiDoc feature matrix that links its evidence.
  Source: `docs/superpowers/specs/2026-10-15-asio-wasip3.md` (superproject); `AGENTS.md` (asio).
- **`/webcpp/cobalt//cobalt` builds on WASIp2/P3 from its shipped Wasm headers
  and sources: signal, serial-port and seqpacket sources are left out,
  `src/wasm/thread.cpp` comes only with threads, and the archive and its
  consumers share the selected Asio backend and thread profile.** Unsupported
  local sockets, signals and serial ports must not break the IP APIs, and an archive
  and its program must agree about headers, threads and exceptions.
  Source: `sources.json`, `src/Jamfile` (cobalt);
  `docs/superpowers/plans/2026-10-16-cobalt-wasip3.md` records the original port.
- **On WASIp2/P3 `run_main` sets the promise's `signal_set` to null and includes
  no POSIX signal service, keeping the executor, the initial post, the status
  and Cobalt's internal cancellation.** WASI delivers no process signal; a
  host's graceful shutdown needs a protocol of the program's.
  Source: `src/wasm/main.cpp`, `AGENTS.md` (cobalt).
- **On WASIp3 the Cobalt status driver expects host exit status 1 for a
  nonzero `co_return`.** The component command reports failure to the host;
  the driver verifies that outcome rather than assuming a native integer exit
  status is preserved by the component interface.
  Source: `test/cobalt_status_driver.mjs` (cobalt).
- **OpenSSL 3.5.9 (`45e844f`) is a pinned, unmodified submodule at
  `third_party/libs/openssl`, built as static `libssl.a` and `libcrypto.a`
  with their generated headers by upstream Configure and `make build_libs`,
  driven by B2 as `/webcpp/third_party//openssl`, in a directory keyed by the
  effective compiler configuration.** Upstream compiles file by file from its
  own manifests, which B2 would otherwise duplicate, and the headers and
  archives of one configuration must stay paired.
  Source: `docs/superpowers/plans/2026-10-16-openssl-source-build.md`,
  `tools/webcpp-openssl.jam` (superproject).
- **The OpenSSL recipe covers native Clang and GCC on macOS and Linux and
  WASIp2 single, WASIp3 single/cooperative, and native MSVC using Configure/nmake;
  Emscripten stops the build, and a host OpenSSL is never a fallback.**
  Windows recipes preserve B2 runtime settings. Windows runtime results must
  be tied to their tested candidate, not inferred from recipe tests or older
  CI. A silent system fallback could link a second copy.
  Source: `docs/superpowers/plans/2026-10-16-openssl-source-build.md`
  (superproject).
- **On WASIp2/P3 OpenSSL uses the external Configure targets `webcpp-wasip2`
  and `webcpp-wasip3` (no
  assembly, no DSO, no QUIC, `getrandom` seeding) and fails closed when host
  entropy fails.** wasi-libc's `getentropy` reaches `wasi:random`; the tests
  show entropy is requested and that its failure stops key generation, not its
  quality.
  Source: `tools/openssl/wasip3.conf`, `tools/openssl/build.py` (superproject); `doc/building.adoc` (asio).
- **`/webcpp/asio//openssl` forwards `/webcpp/third_party//openssl` with
  `WEBCPP_ASIO_HAS_OPENSSL` natively and on WASIp2/P3, Emscripten keeps the
  forced-include refusal, and asio's tests that need OpenSSL fail rather than
  being left out.** A missing checkout is named
  (`git submodule update --init third_party/libs/openssl`), never skipped.
  Source: `build.jam`, `doc/building.adoc` (asio).
- **The OpenSSL build copies the unchanged sources to a temporary directory
  before Configure, and caches its configuration fingerprint per property
  set.** Configure canonicalizes source symlinks, which would bring a checkout
  path with spaces into the Makefiles, and an uncached fingerprint built two
  archives for one configuration, two OpenSSL copies in one program.
  Source: `docs/superpowers/plans/2026-10-16-openssl-source-build.md`,
  `docs/superpowers/plans/2026-10-16-cobalt-ssl.md` (superproject).
- **Each configuration of OpenSSL and libdatachannel is built once, in
  `bin/third_party/<name>/config-<hash>`, named by the bytes of its inputs
  (its scripts and its pin) and by its build command, and never again, `b2 -a`
  included: its outputs are `NOUPDATE`.** A directory that exists holds the
  build of exactly those inputs and that command, so consumers whose
  properties differ only in what the command leaves out, as
  `exception-handling` for OpenSSL's C, share it, and the CI restores a lane's
  directories from its cache (`tools/ci/actions/third-party`) and builds only
  those the cache lacks. A consumer depends on the selection of its
  configuration, `<name>-config-<hash>.selected` in its own variant directory,
  which is written when the configuration changes, to a new one or back to one
  built earlier, so the consumer is built again. Removing a configuration's
  directory builds it again. A checkout that differs from its pin stops b2
  before any build, by the library's own `check_checkout`.
  Source: `tools/webcpp-third-party.jam`, `tools/third_party_build.py`
  (superproject).
- **A dated curl export of Mozilla's root certificates (2026-09-25, 121 CAs)
  is checked in under `third_party/ca_certificates`, with a manifest of its
  URL, SHA-256 and DER fingerprints and its MPL-2.0 licence, verified and
  embedded as a generated header by `/webcpp/third_party//ca_certificates`,
  and changed only by `tools/ca_certificates/update.py`.** Its generated private
  header is `<webcpp/asio/detail/ca_certificates.hpp>` and its namespace is
  `webcpp::asio::detail::ca_certificates`, in build and installed consumers.
  It is a published
  data artifact, not implementation code, so a snapshot rather than a
  submodule; builds need no network, and an update is a reviewed trust-policy
  change that lists removals beside additions.
  Source: `docs/superpowers/plans/2026-10-16-ca-certificates.md`,
  `third_party/ca_certificates/README.md` (superproject).
- **`/webcpp/asio//tls` and `make_tls_client_context()` return a
  `boost::system::result<ssl::context>` that verifies peers, requires TLS 1.2
  or newer and trusts the embedded roots, never the system's; the
  `std::string_view` overload trusts only the PEM it is given, refusing an
  empty, malformed or partly invalid set, and Emscripten returns
  `unsupported_target`.** Replacing roots must remove public trust, not add to
  it, and the browser owns trust there; hostname verification and SNI stay the
  program's, per connection.
  Source: `include/webcpp/asio/tls_client_context.hpp` (asio);
  `docs/superpowers/plans/2026-10-16-ca-certificates.md` (superproject).
- **The TLS client context and its trust store allocate through OpenSSL, not
  through an Asio allocator.** OpenSSL's allocation hook is process-global and
  must be selected before its first allocation. Installing it from a context
  factory would mutate other users' policy and cannot honor independent
  per-operation allocators. The factory therefore states the allocation boundary;
  a future explicit process-wide crypto policy is separate work.
  Source: `docs/superpowers/plans/2026-10-16-ca-certificates.md`
  (superproject).
- **`/webcpp/cobalt//io_ssl` compiles the corrected, shipped SSL sources
  independently of the plain core, and `/webcpp/cobalt//cobalt_ssl` adds the
  runner and the shared `/webcpp/asio//tls` provider on native and WASIp2/P3.**
  Native SSL uses `src/native_ssl.cpp` and `src/native_ssl_transfer.cpp`;
  WASI uses `src/wasm/io/ssl.cpp`. Native SSL is the owner's explicit exception
  to Boost type identity; plain native coroutine and I/O types, core and runner
  remain upstream. The old root and Asio SSL target names are compatibility
  aliases, and plain Cobalt takes no OpenSSL. Against a real TLS server,
  Boost 1.92's wrapper finished a handshake with `secure` false and then
  wrote plaintext, and its verification callback's constraint named
  `ssl::context` for `ssl::verify_context`; the corrected wrapper fixes both
  and adds the borrowed `native_ssl_handle()` for SNI.
  Source: `sources.json`, `doc/differences.adoc` (cobalt);
  `docs/superpowers/plans/2026-10-16-cobalt-ssl.md` records the original correction.
- **Cobalt's SSL stream allows plaintext only before the first TLS attempt: a
  failed or cancelled handshake and a completed shutdown block application
  I/O, and the wrapper keeps the handler's associations.** A failed handshake
  must never fall back to plaintext, and an unbound lambda in their place
  would lose cancellation.
  Source: `docs/superpowers/plans/2026-10-16-cobalt-ssl.md` (superproject).
- **The shipped Wasm Cobalt composition promise connects its cancellation
  source to the handler's slot; native composition retains Boost's behavior.**
  Reproduced: a composed read's cancellation hung, because Boost 1.92's
  composition promise did not attach to the received handler's slot.
  The corrected Wasm sources also supply the
  required main/thread promise exception hooks in no-exceptions builds;
  worker/join tests and the native upstream-limitation probes keep those
  contracts distinct. Native SSL uses its separately corrected transfer path
  without changing the upstream native composition or coroutine types.
  Source: `doc/differences.adoc`, `src/native_ssl_transfer.cpp` (cobalt);
  `docs/superpowers/plans/2026-10-16-cobalt-ssl-cancellation.md` records the
  correction's historical overlay implementation.
- **TLS transfer cancellation is terminal: the connection is closed
  afterwards, with no promise of rollback or reuse, and the tests require a
  real `operation_aborted` from a Cobalt promise, one write per cancellable
  promise, and a fresh connection when a completion wins the race.** TCP
  backpressure does not exclude a queued successful SSL completion, which the
  review reproduced, and an abort manufactured from coroutine state would
  prove nothing.
  Source: `docs/superpowers/plans/2026-10-16-cobalt-ssl-cancellation.md`
  (superproject).
- **The superproject's README names Crossbind's OpenSSL recipe as an
  engineering reference for WASIp3 builds.** Its source-based recipes and WASI
  ports help to bring low-level libraries to the web; webcpp still validates
  the toolchain, the entropy and the features itself.
  Source: `README.md` (superproject).

Native Windows uses unmodified Boost.Asio, including IOCP worker and timer-thread
state that does not forward the context allocator. The earlier
`tools/boost/asio-windows` allocator overlay is historical provenance, not a
consumer build path. The Windows allocation scenario is a negative witness:
it requires observable global allocation, preserves the timer and posted-handler
checks, and prints `UPSTREAM-LIMITATION`. It establishes neither zero global
allocation nor an arbitrary allowance. A future upstream fix must fail this
witness and be reclassified. Other supported targets retain checks for zero
global allocation in the measured scenario, with its documented runtime boundaries.

The `tls-integration` own lane drives real TLS, embedded trust, Cobalt state and
cancellation fixtures on native and WASIp3 profiles. The native
`openssl-upstream` lane opts into `webcpp-openssl-tests=on`, which runs the full
upstream `alltests` suite against the exact archive configuration before linking
the consumer. The `openssl-upstream-msvc-14.3` and
`openssl-upstream-msvc-14.5` aliases select the matching Windows CI toolsets;
real execution on the final Windows candidate remains a validation gate.
OpenSSL's upstream harness is unavailable on WASIp3, and the integration
witnesses do not claim to replace it. Native combined-provider
coverage belongs to Trystero's `test/provider//provider-integration`, where its
secp256k1 dependency is `/third_party//secp256k1`. Final-candidate CI and remaining
coverage limitations are tracked in chapter 19.

### cobalt (Boost.Cobalt source integration; local candidate for 0.1.0)

The owner approved independent Cobalt ownership and the coordinated source contract
on 2026-11-06. `libs/cobalt` owns core, runner, optional SSL, tests, examples and
Diataxis/MrDocs documentation. Native coroutine/plain I/O types and core/runner
sources are Boost 1.92. Wasm uses checked-in sources over the same WebCPP Asio
backend as Beast. Consumer builds require no patches or replacement Boost headers.

The corrected native SSL stream is an explicit owner-approved identity exception,
after real upstream state/cancellation failures. Document the wrapper as fixing
those defects, including plaintext fallback after a failed or cancelled handshake,
with its regression evidence and supported target boundaries. The owner reaffirmed
this exception on 2026-11-07 and directed that other newly identified original
Boost defects be documented without local corrections. Plain Cobalt never links SSL.
Native upstream defects outside that wrapper remain named negative probes;
corrected Wasm behavior is not reported as native Boost behavior. The issue-287
no-EH caution remains informational, with versioned runtime evidence.

Default browser scheduling stays at Asio's 100 handlers. Config distinguishes
application requirements, read-only capabilities and build-wide executor/PMR
policies. A capability cannot grant runtime permissions. Arbitrary cross-unit ABI
mismatches remain caller errors; source consumers must rebuild all support units.
B2 lists and external builds consume the same source inventories.

GCC 15.2's default-argument `await_suspend` regression (GCC PR121643) prevents
unmodified native Cobalt `race` applications from compiling. The GCC 15 CI lane
therefore provisions GCC 15.3 from a pinned official image and validates an
independent compile/run coroutine probe, including after cache restoration.
The lane does not change the native core or omit those tests.
A local build probes the GCC 15 its user-config.jam configures the same way: the
Jamroot's `gcc-probe` compiles and runs that probe once per compiler and run of b2,
and a compiler that fails it stops the build with a message naming PR121643 and
GCC 15.3, before a lane would end in internal compiler errors. GCC 14's separate
known coroutine-allocation false positive (boostorg/cobalt#7) is scoped to the
affected test functions; the two immutable original application probes retain the
warning as nonfatal for GCC 14 alone. Consumers inherit no warning-suppression flags.

The 2026-11-07 report covers 12 original applications in 432 cells, keeping
counterparts, unavailable facilities and upstream defects separate. Shared Release
measurements cover 136 builds and 15,906 runtime observations, with immutable source
snapshots and distinct memory boundaries. The full source-archive, lint, review and
publication gates are recorded in the portable-network migration plan. Local
results do not claim a released library, GitHub repository creation or CI approval.

### beast (Boost.Beast portability facade)

The owner's expanded Beast genesis proposal in
`libraries/beast/openspec/changes/genesis` governs this implementation. The
library is the `webcpporg/beast` submodule at `libs/beast`. The proposal records
source compatibility, explicit environment counterparts and unavailable
facilities separately; a successful compile never proves runtime parity.

- The existing `webcpp.beast.wasi` category and its enum values remain public
  identities beside `webcpp.beast`. As with Asio's TLS category, preserving
  error comparisons is a bounded compatibility departure from chapter 4;
  it does not authorize renumbering or merging categories.
- Portable HTTP messages, parsers and serializers reuse Boost.Beast 1.92.
  `http.hpp` remains independent of a socket reactor. Byte-stream algorithms
  are explicit `http/read.hpp` and `http/write.hpp` includes.
- Native and WASIp2/P3 guest sockets use webcpp::asio. Guest TLS is optional and
  explicitly links the project's source-built OpenSSL through `//tls`.
  `set_server_name` sets SNI only; peer verification and hostname validation
  remain explicit. Native equivalent types are exactly Boost.Beast types.
  Wasm protocol sources are shipped explicitly and use Asio's selected backend,
  without replacement Boost include directories. WASI stream internals retain
  upstream Beast's allocation behavior; browser allocator extensions do not
  change the native type or constructor contract.
- The browser backend uses JavaScript WebSocket and fetch. Its TCP-shaped
  lowest layer records an authority rather than opening a raw socket, and its
  TLS-shaped layer records intent rather than running guest OpenSSL. The
  browser owns trust, handshake headers, framing, DNS and redirects.
- Browser stream state, retained metadata and payloads use the stream allocator;
  operation completions use their associated allocator and executor. The
  intrusive Asio bridge registration avoids an independent lookup allocation.
  Receive limits account for retained message records as well as payloads,
  including browser arrivals before the application drains its executor.
  Terminal registrations and queued events are scoped to one connection or
  request generation, so cancellation and reuse cannot deliver stale results.
- `browser::http_byte_stream` is an explicit synthetic HTTP/1.1 adapter for
  algorithms that require bytes. Fetch has already decoded the body. Its
  internal parser, fields and body use the stream resource; synthetic chunk
  sizes use fixed storage because upstream's helper has no allocator hook.
- The propagated B2 feature `webcpp-beast-unsupported=error|ignore` selects the
  unsupported-setting policy, defaulting to error. Translation units with
  different policies must fail to link. Ignoring a setting never enables an
  unavailable transport or conceals an operational network failure.
- WASI host HTTP is independent of guest sockets and OpenSSL. The `//wasi-http`
  target uses webcpp::wasi's independent host bindings on P2/P3, preserving
  full messages, trailers, cancellation and explicit host ownership. Supplied
  stdin/stdout streams are meaningful counterparts for local-socket examples;
  they do not supply Unix-domain addressing. Host HTTP does not provide a
  WebSocket upgrade or a guest TCP listener.
  Posted completions release their associated allocation before user code runs;
  a per-operation PMR resource may be destroyed inside that callback. Supplied
  HTTP reads respect the remaining DynamicBuffer maximum capacity and report
  `http::error::buffer_overflow` when an incomplete parser exhausts it.
- **A WebSocket client bounds the HTTP response its handshake reads with
  `websocket::bounded_handshake_stream`, a next layer between the stream and
  its transport: it parses the response's header with Beast's own parser
  under `response_limits` (by default 8 KiB of header and 1 KiB after a
  refusal's header), fails the handshake with `http::error::header_limit` or
  `body_limit` after reading at most both bounds, and lets a 101 pass
  through unchanged; the plain stream keeps upstream's limits.** The owner's
  decision of 2026-11-14: upstream's handshake reads with Beast's default
  parser limits, 8 KiB of header and 8 MiB of a refusal's body, outside the
  caller's allocator, and natively that is Boost.Beast's own code and on
  WASI the shipped copy, neither of which is corrected; a client that
  connects to servers it does not trust selects the layer, as
  webcpp::trystero's relays do. The layer starts its transport's operations
  through a pointer, so that misc-no-recursion sees no cycle through it in a
  consumer's lint, and the WASI facade passes an allocator-tagged
  construction on to a next layer that uses an allocator
  (`std::uses_allocator`), as Boost does natively. The browser's WebSocket
  reads its own response; on Emscripten the layer serves only the guest
  engine over a supplied channel.
  Source: `include/webcpp/beast/websocket/bounded_handshake_stream.hpp` and
  `doc/beast.adoc` (libs/beast).
- The immutable upstream application corpus contains all 53 executable
  definitions at its pinned commit. Inventory checks validate original hashes,
  Jamfiles, CMake definitions and entry points. All adaptations are generated
  by checked-in generators and inspectable patches; never edit their output.
  Preserve each application's algorithm where possible, and record every
  scheduling, resolver, transport or error-handling adaptation explicitly.
- Feature and application matrices in the guide keep compilation and execution
  separate for every target, exception mode and supported threading profile.
  Unavailable stackful Wasm coroutines, browser listeners and cooperative
  WASIp3 exceptions remain unavailable in SDK 34, never counted as passes.
  The 2026-11-07 application matrix includes WASIp2 guest sockets: across
  53 applications and 35 profiles it records 843 passed, 816 unavailable and
  196 blocked cells. Dated results identify their exact measured source
  snapshot; subsequent edits do not silently replace that evidence.
- Native upstream programs are the oracle. Browser validation runs in real
  Chrome with a disposable CA profile, independently of Node. WASI host HTTPS
  uses a pinned Wasmtime host fixture with normal trust and hostname checks;
  guest TLS evidence cannot substitute for it. Positive and negative trust
  controls accompany TLS application evidence. Documentation follows Diataxis
  in AsciiDoc with MrDocs API reference and executable examples.

### webrtc (WebRTC data channels in Asio's model; own; implementing, its three increments built)

webcpp::webrtc is a header-only C++20 library of webcpp's own (`kind: own`,
although it wraps libdatachannel natively) for peer connections and data
channels, shaped as the W3C WebRTC API in Asio's model, media out of scope.
The owner accepted its proposal on 2026-11-14 (webcpporg/proposals#12); its
`design.md` supersedes the specification of 2026-10-10 (`reference/spec.md`)
where they differ, and `reference/plan.md` holds three increments: the
interface, the runtime and the native implementation (built, in `libs/webrtc`,
from one import commit of `reference/source/`), the browser implementation
over webcpp::asio's bridge with its `browser` and `interop` lanes (built), and
trystero on it (built, trystero's branch `webrtc-backend`, in its
`refactor`).

- **A library of its own on webcpp::asio, not a part of webcpp::beast.** The
  owner's decision of 2026-11-14: beast is a source-compatible facade of
  Boost.Beast and WebRTC has no Boost counterpart; libdatachannel and its
  threads would burden every beast user; beast targets WASIp2/P3, where WebRTC
  has no stack; and beast's D6 already foresees a WebRTC channel's byte stream
  as an opt-in next layer, so beast would use webrtc, never the reverse.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D1 (proposals).
- **The interface carries the W3C names and shapes (`peer_connection`,
  `data_channel`, `session_description`, `ice_candidate`, the `RTC*`
  enumerations in snake case) in Asio's model: `async_*` operations with any
  completion token, the executor (default `webcpp::asio::any_io_executor`) and
  the allocator as template parameters, inputs as views and outputs owned.**
  The owner's decision of 2026-10-10, so that a program, trystero first, is
  written once and runs natively and in a browser; webcpp::asio's name is the
  type the browser implementation shares with the program's io_context.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D2 (proposals).
- **Its targets are native and Emscripten, and its configuration stops with an
  `#error` under WASI that names the reason.** libdatachannel has no WASI port
  (its threads, and libjuice's and usrsctp's, need preemptive threads, and its
  ICE and SCTP were never ported to WASI sockets), and no WASI host interface
  offers WebRTC. A WASI stub was rejected because it would let a program
  compile and fail at run time.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D3 (proposals).
- **The native backend calls libdatachannel's C API only, so the library works
  with exceptions on and off.** The owner's decision of 2026-11-14:
  libdatachannel throws and cannot be built without exceptions, but every
  function of its C API catches them and returns a negative code, so a
  program built with `-fno-exceptions` uses it: the native suite passes built
  with `exception-handling=off` against archives built with exceptions. The
  C++ API, which would leave a program without exceptions with no native
  backend, was rejected.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D4 (proposals).
- **Reading a message through the C API costs four allocations and four
  copies inside libdatachannel, and three to five times the time of the C++
  API's `receive()`, under 2% of the time the message takes to arrive.**
  Measured on 2026-11-14 (`bench/receive_bench.cpp`, macOS arm64, Apple clang
  21, release, 100,000 messages): 4.37 million messages of 1 KiB a second
  against 12.76 million, 131,000 of 64 KiB against 632,000, while the
  loopback delivered 71 and 124 MB/s. The backend calls `rtcReceiveMessage`
  twice, a size probe then the read, and each call copies the message twice
  (`peek`, then a by-value visit); the design's estimate of one copy and one
  allocation was low. The cost is libdatachannel's allocator's, not the
  user's.
  Source: `doc/native.adoc` (libs/webrtc).
- **Events are pending operations the caller re-arms
  (`async_wait_ice_candidate`, `async_wait_state_change`,
  `async_accept_data_channel`, `async_receive` and their kin), one wait of a
  kind at a time, with a stated policy for an event that arrives while none is
  pending.** This keeps every handler on the executor and every lifetime in
  the caller's hands, as an acceptor's `async_accept`; callbacks, and one wait
  returning a variant of events, were rejected.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D5 (proposals).
- **A `runtime` the program owns holds libdatachannel's process-wide state,
  one at a time natively as a stated precondition, made before any connection
  and destroyed after the last, and enforces `max_peer_connections` (default
  256) on both targets.** webcpp keeps no global or static mutable state, so a
  second runtime cannot be detected; 256 is half of Chromium's 500 per page.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D6 (proposals).
- **libdatachannel's callbacks copy and post through a weak pointer, and
  destruction calls `rtcDelete*`, which waits for the callbacks in flight.**
  libdatachannel documents that wait; nothing of the user's allocator is
  touched on its threads. The lifetime test runs 100 rounds of destruction
  while the peer floods, clean under ThreadSanitizer.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D7 (proposals).
- **In the browser it follows webcpp::beast's browser WebSocket as built:
  one intrusive registration of the bridge per object, arrivals staged and
  charged on arrival to the receive bound, one notification posted per batch,
  and JavaScript's exceptions caught in JavaScript and reported by
  DOMException name.** Those patterns are proved; where webrtc differs (a
  send refused before the browser sees it leaves the channel open; several
  event kinds; terminal cancellation only for the description operations,
  and in the browser for adding a candidate, whose promise cannot be called
  back) the design and the page say why. The page's census of
  `RTCPeerConnection`s, kept in JavaScript until a `FinalizationRegistry`
  sees each collected, is what `max_peer_connections` caps there.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D6, D8, D11
  and D12 (proposals); `doc/browser.adoc` (libs/webrtc).
- **What a target cannot honour fails with `operation_not_supported` by
  default, or is ignored under the propagated b2 feature
  `webcpp-webrtc-unsupported=ignore` where the platform does something
  equivalent of its own; on both targets the classes live in an inline
  namespace named after the policy, so translation units that disagree fail
  to link.** Natively the policy decides a data channel's
  `max_packet_life_time` of 0, which libdatachannel's C API takes as 0
  retransmissions, so that a browser peer would read it as `maxRetransmits`
  0 (ruled on 2026-11-15); in the browser, `configuration::bind_address`. A
  getter cannot fail: a native channel the peer announced with a lifetime of
  0 reads as `max_retransmits()` 0, whatever the policy. The design put the
  native classes outside the namespace, as honouring every setting (chapter
  19).
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D14
  (proposals); `doc/differences.adoc` and `doc/native.adoc` (libs/webrtc).
- **The tests run on both targets: natively, on emscripten under Node with a
  fake connection where a real one is not needed, in headless Chrome with two
  peers in one page (the `browser` lane), and native against Chrome through a
  local relay over webcpp::beast's WebSocket (the `interop` lane).** Chrome
  156 offers a page with no media permission only its default-route address,
  whatever `--allow-loopback-in-peer-connection` says, so the interop driver
  grants the page's origin the microphone, which starts no capture, to keep
  the exchange on 127.0.0.1; and Chrome 156 may drop messages sent just
  before a channel is closed, which the page states as a difference.
  Source: `doc/testing.adoc`, `test/interop/run.mjs` (libs/webrtc).
- **`async_receive` copies one whole message into the caller's dynamic
  buffer; natively unread messages wait in libdatachannel's own queue of
  1,024, a flow control that never fails, and in the browser in a queue
  bounded by `max_received_bytes`.** Measured on 2026-11-14 and pinned by
  `test/stall_test.cpp`: a native channel never read, once its queue is full,
  stalls its connection's other channels until it is read or destroyed; the
  page tells a program to read or close every channel, and closing or
  destroying a channel drains its queue.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D9 (proposals).
- **libdatachannel is the superproject's pinned, source-built copy, unmodified,
  justified in the documentation, with nothing of it in a public header; its
  MPL-2.0 is accepted for this library.** The owner's decision of 2026-11-14,
  as trystero already distributes it; no WebRTC exists in webcpp, Boost, the
  C++ Alliance or the standard library, and libdatachannel is the smallest
  complete implementation.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D16 (proposals).
- **webcpp::webrtc knows nothing of xactor: an actor that needs a peer holds a
  `peer_connection` made on the executor its driver runs on, and turns each
  completion into a message to itself.** The two meet at the executor.
  Source: `libraries/webrtc/openspec/changes/genesis/design.md` D17 (proposals).

## 16. Roadmap

What webcpp does not have yet, and the chapters that mention it:

- **Every variant tested, in three levels of CI.** The lint and the CI test
  every variant a library supports: with exceptions on and off (the whole
  suites, not only a compile, chapter 6) and each library's own
  configurations. The CI runs in three levels: fast on every push and pull
  request (the changed library and its dependents, one native compiler and
  wasip2 in the default variant, one native lane without exceptions, the
  lint, the docs); nightly on main (every target and compiler, the suites
  without exceptions natively, sanitizers, the heavy own lanes, the
  container lanes); and release, when the whole of webcpp is released (every
  target times every variant). `tools/ci/matrix.py` takes the level, and
  the fast set runs locally as one command (`AGENTS.md` chapter 4).
- **The review of the existing libraries.** Once the pending work is done,
  every library is brought to the rules of exceptions, variants,
  allocators, the order of what a library builds on, written for the web, the newest Boost
  library of a kind, wrapped outside libraries, and fixed-width types
  (chapter 4); the lint then checks the last (no plain `int`, `long`,
  `short` or `unsigned` in a public header where no interface asks for it).
- **Trystero on Asio and Beast.** Asio's executor integration and Beast's
  native/WASI/browser adapters are implemented for 0.1.0 in preparation. The
  owner reiterated on 2026-11-03 that they are foundations for Trystero's later
  migration. Their coexistence is required; dependency provenance must not be
  addressed by prohibiting a combined program. Actor-based libraries use
  xactor's scheduler through an application-owned loop.
- **webcpp::webrtc.** Its increment 1, the interface
  and the native implementation, is built (chapter 15); its increment 2 brings
  the browser implementation and the interop lane; its increment 3 has moved
  trystero's WebRTC onto it, both backends, with trystero's Asio named
  webcpp::asio (chapter 15's trystero entry). Authenticated encryption and
  randomness are webcpp::crypto's, and the relays' WebSockets Beast's.
  Trystero can then retain its protocol over those shared facilities.
- **crypto after 0.1** (chapter 17): constant time checked, sizes and
  throughput measured, the browser lane, the CI's nightly level, NIST CAVP's
  vectors, ChaCha20-Poly1305 and Botan.
- **The libraries web developers use most,** brought to C++: a JavaScript
  interpreter (QuickJS), libp2p, HTTP fetch.
- **The site, increments 2 to 8.** Increment 1 is done: the site's
  repository and `b2 site`, the landing, the list of libraries and the three
  doors (C++, JavaScript, AI), the libraries' pages and the report under the
  site's theme, `robots.txt`, `llms.txt` and `libraries.json`, published at
  https://webcpporg.github.io/, the preview, with the redirect from
  `/webcpp/` (`AGENTS.md` chapter 4). To come, in this order:

  2. xstate for emscripten (its machine layer), and the site's wasm running
     its own machines, the player's and the install's: the PWA;
  3. the bridge visualizer and the calculator example;
  4. trystero's JavaScript API and the collaborative cursors;
  5. the examples of a state machine, of C++ calling the browser, and of
     C++ on the server;
  6. file transfer and video chat, as trystero's roadmap delivers them;
  7. Google search, for webcpp.org: the Programmable Search engine and the
     Search Console property are made for the release site; the preview,
     the development version, gets neither and is never indexed;
  8. the release channel at https://webcpp.org/, at the first release, with
     the move of the domain's DNS.
- **Documentation for web developers and for AI developers,** beside the
  documentation for C++ developers every library has today, and webcpp's
  integrations with the AIs.
- **External libraries built from `third_party/`.** No library is externally
  provisioned: trystero links `/third_party//secp256k1`, and OpenSSL and
  native libdatachannel, including its required nested dependencies, build from
  pinned sources against one OpenSSL provider.
- **Every library on `<webcpp/config.hpp>`.** Each library's `config.hpp`
  includes it first: trystero (held with config's publication), and wasi with
  its redesign, which brings Boost into it.
- **Allocators.** The rule of chapter 4, shareable data structures with an
  `Allocator` template parameter and every other allocation through the
  user's allocator, applied first to xactor, xstate and wasi, whose response
  holds its body as a `std::string`; pratt is born with the rule, and
  trystero through `std::pmr` (chapter 4).
- **Compiled Boost libraries.** Boost.URL, Boost.Charconv and Boost.Locale are
  built from Boost's sources (`/webcpp//boost_url`, `/webcpp//boost_charconv`,
  `/webcpp//boost_locale`); Boost.Cobalt from the sources libs/cobalt ships
  (`/webcpp/cobalt//core`). Boost.Locale requires exceptions. Boost.Cobalt
  follows the consumer's exception setting with a non-fatal warning when
  disabled (AGENTS.md chapter 1). This is not a guarantee that all of Cobalt
  works without exceptions: in Boost 1.92, moving a pending task calls
  std::make_exception_ptr, which aborts with libc++ and -fno-exceptions, even
  when the application uses as_result. Eager promises and timer cancellation
  handled as values are covered by tools/test/boost_libraries_test.py.
  The compiled libraries are not yet measured on Windows. A
  Boost.Test suite still compiles the framework's header-only form (chapters
  2 and 9).
- **Bundled toolchains.** Each toolchain is installed by hand and configured
  in `user-config.jam` (`AGENTS.md` chapter 1), until webcpp bundles them.

## 17. Decided, not built

The proposals the owner accepted that are not in the superproject's `main`,
each with its decisions as decided. While a proposal is open, its own
`design.md` and specification hold it in full and rule over this summary; the
change that builds it moves its decisions into chapter 14 or 15. Their
conflicts with chapters 1 to 13 are in chapter 19.

### crypto, after 0.1 (genesis accepted 2026-10-11, foundation accepted 2026-11-14; the foundation's increment 1 built on its branch, not merged)

The genesis's plan (`reference/plan.md`, revised on 2026-11-14) built version
0.1 from its increments 1 and 2, and OpenSSL's memory option after it. The
foundation (`libraries/crypto/openspec/changes/foundation`) takes the work
on: twelve increments, version 0.2 onward, and the genesis's increments 4 and
5 (ChaCha20-Poly1305, Botan) with them; trystero's migration is dropped.
Its rules are webcpp::hash's: one default backend per family and target with
its reason stated, no profile and no per-family override (design D32), tables
of size and speed only from release builds, and primitives only (D24). What
is built is in chapter 15; what follows is decided and not built, except
increment 1, whose state is first.

**The foundation's increment 1 (plan Tasks 1 to 16).**

- **Built on the branch `crypto/foundation-1` of the library and the
  superproject, awaiting the owner's merge: libsodium's backend, the families
  on it, the capability table, the fixed defaults, the three own lanes and
  the page.** `backends::sodium` on `/third_party//sodium`, shared with
  webcpp::hash, with crypto's canary; `curves::ed25519` (strict verification
  over the twelve edge cases, Ed25519ph, the conversion, RFC 8410's formats and
  PEM), `curves::x25519` and `kx_keypair`, `ciphers::aead` with
  `chacha20_poly1305` (also on BearSSL and OpenSSL), its original form and
  `xchacha20_poly1305`, `ciphers::secretbox`, `hybrid::box` and `sealed_box`,
  and `secret<N>` with the errors 15 to 20. `supports_v` and
  `default_backend_t` read the capability table, which `doc/tables/generate.py`
  writes from `crypto.json` and the tests the Jamfiles declare (it replaced
  `capabilities.py` and `measure.py`); the own lanes are `c-suites` (the
  backends' own suites), `sizes` (at `variant=release`, on every target) and
  `constant-time`. Throughput is measured by hand and dated, and decides
  nothing.
  Source: `libraries/crypto/openspec/changes/foundation/reference/plan.md`
  Tasks 2 to 16 and its revision of 2026-11-17 (proposals);
  `libs/crypto/AGENTS.md`.
- **One finding is open: X25519's constant time on wasip2.** dudect measures
  `agree` under wasmtime above its threshold (|t| 13 to 32 against 10), where
  the native builds pass; no secret branch was found in the WebAssembly or in
  wasmtime's code and the cause is unknown. The page's constant-time table
  and `crypto.json` record it as an open finding, not a pass, and the lane
  prints its value without judging it. Valgrind, MemorySanitizer and dudect
  are not run on wasip3 or Emscripten, which the page says, as it says that
  OpenSSL's `open` is left out of memcheck.
  Source: `libs/crypto/doc/generated/constant-time.adoc`,
  `doc/tables/crypto.json` (libs/crypto).
- **What is not built is in the other increments: libsecp256k1's remaining
  modules (2), BearSSL's (3), the browser backend and the asynchronous family
  (4), libsodium completed (5), blst (6), Botan as a submodule (7), OpenSSL's
  remaining algorithms (8), KZG, BN254, Shamir and HPKE (9 to 12).** The
  merges, the CI's run and the proposals' status are the owner's.
  Source: `libraries/crypto/openspec/changes/foundation/reference/roadmap.md`
  (proposals).

**Constant time (increment 1, Task 14; built on the branch).**

- **Constant time is checked deterministically on Linux x86-64 and arm64
  (Valgrind memcheck and MemorySanitizer, each harness failing on a planted
  leak, and libsecp256k1's `ctime_tests`), and statistically by dudect's
  method natively and under wasmtime on wasip2, through the seam
  `WEBCPP_CRYPTO_DETAIL_DECLASSIFY`.** `equal` compiles in the user's
  translation unit, so it is checked at -O2 and -Os; under wasmtime the
  engine's compiler decides whether BearSSL's `bmul64` stays constant time.
  The page's per-target cells are generated from the lane's own entries, and
  a target the lane does not run says "not measured yet".
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  sections 3.2 and 8.3 (proposals); `test/constant_time/Jamfile` (libs/crypto).

**Sizes and throughput (increment 1, Task 11'; built on the branch).**

- **Sizes are measured at `variant=release` on every target by the own lane
  `sizes`, through `webcpp.size-table`; throughput by webcpp's own program
  (`bench/collect.py`, which refuses a build that is not a release) on the
  developer's machine, dated; neither decides a default.** b2 has no -O2 that
  reaches the libraries a program names, so the tables are dated references;
  the ubuntu-24.04, ubuntu-24.04-arm and macos-15 runs wait for the owner
  (`throughput` in `runners.yml` is not built). A moved pin updates no size
  table (chapter 19).
  Source: `libraries/crypto/openspec/changes/foundation/design.md` D32 and
  `reference/plan.md` Task 11' (proposals).

**The browser lane (plan Task 23).**

- **WebCrypto in node and in Chrome is an outside oracle for AES-GCM, random
  messages under 16-byte IVs included.** Those are the IVs trystero exchanges
  with Trystero's JavaScript peers; on Emscripten, where one AEAD backend
  exists, WebCrypto stands in for a second.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  sections 8.1 and 8.2 (proposals).

**The CI's nightly level (plan Task 25b).**

- **The heavy own lanes (`constant-time`, `browser`, `throughput`) run at a
  nightly level the plan builds, `sizes` on every push.** In 0.1 the CI has no levels, and
  every own lane, `c-suites` included, runs on every push (gate O2).
  Source: `libraries/crypto/openspec/changes/genesis/design.md` Risks
  (proposals).

**NIST CAVP (gate O3).**

- **NIST CAVP's GCM cases with 128-bit tags and AESAVS run on every backend
  that has the algorithm; the archives are pinned by URL and SHA-256 and
  fetched into `.local/nist-cavp`, never tracked.** NIST publishes them as zip
  files on csrc.nist.gov only, and the rulebook's mirror is for C libraries,
  not test data.
  Source: `libraries/crypto/openspec/changes/genesis/reference/plan.md` C11
  (proposals).

**ChaCha20-Poly1305 (built in increment 1, Task 8b, on the branch; the genesis's increment 4).**

- **`ciphers::chacha20_poly1305` on BearSSL and OpenSSL is one shot only,
  with an IV of exactly 12 bytes, refuses a message over 2^38 - 64 bytes with
  `message_too_long`, and where BearSSL leaves the tag check to its caller the
  backend compares with `equal` and zeroes `data` on a mismatch; it is a
  family of the one-shot template `ciphers::aead<Family, Backend>`, not
  new traits.** BearSSL's
  ChaCha20-Poly1305 is one function over the whole message; 12 bytes and the
  limit are RFC 8439's.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 2.5 (proposals).
- **The BearSSL backend takes `br_chacha20_sse2_get()` else
  `br_chacha20_ct_run`, and `br_poly1305_ctmulq_get()` else
  `br_poly1305_ctmul_run`; Wycheproof's ChaCha20-Poly1305 file and RFC 8439
  are its vectors.** BearSSL's own default on wasm32 is its 32-bit code.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  sections 3.2 and 8.1 (proposals).

**Botan (increment 5).**

- **Botan 3 is found by `webcpp.external` (`-sBOTAN_ROOT`, then
  `.local/botan`, then the system), never built, native only and only with
  exceptions: `backends/botan.hpp` declares nothing under
  `WEBCPP_CRYPTO_NO_EXCEPTIONS`, a program built without exceptions that names
  it gets an `#error`, a user's program that names a missing one stops the
  build with three ways out, and a WebAssembly build that names it stops
  before compiling.** Botan 3.13.0 has no OS definition for wasip2 or wasip3,
  and reports every error by throwing; a program that names a backend has
  asked for it. `webcpp.external` comes back for it.
  Source: `libraries/crypto/openspec/changes/genesis/design.md` D19 and
  `reference/spec.md` section 4.4 (proposals).
- **Botan's backend calls Botan inside one `try` and maps what it throws
  (`Invalid_Authentication_Tag`, `Invalid_IV_Length`, `Invalid_Key_Length`,
  `std::bad_alloc`, anything else), calls `set_associated_data` before every
  `start`, and finishes a message on a scratch `secure_vector` reserved in
  `make`; its `make` allocates through Botan's own allocator, which the page
  states; it joins the block cipher and the AEADs' default order after OpenSSL
  and BearSSL.** No exception may leave a webcpp function; Botan keeps the
  additional data between messages; Botan 3.13.0 has no allocation hook.
  Source: `libraries/crypto/openspec/changes/genesis/reference/spec.md`
  section 3.6, and `design.md` D9 and D17 (proposals).

**Open questions for the owner.**

- Gate O2: the nightly level, built by Task 25b.
- Gate O3: NIST CAVP's archives pinned by URL and SHA-256 (recommended), or a
  mirror repository.
- Item O5: the departures C14, C16 and C17, and `brew install botan` on the
  development machine.
- Whether webcpp::webrtc and webcpp::beast use this library, and how.
- A later increment: an incremental `open` with the plaintext withheld until
  the tag verifies, an incremental ChaCha20-Poly1305, and a Botan WebAssembly
  build.

Source: `libraries/crypto/openspec/changes/genesis/design.md` Open Questions
(proposals).

### wasi redesign (accepted 2026-10-09, not built)

The owner reviewed wasi 0.1.0 on 2026-10-08 and approved this redesign on
2026-10-09; a spike measured it with wasi-sdk 34, wasmtime 47.0.3 and
wit-bindgen 0.62.0, and nothing of it exists in code. Where the spike and the
owner's design differ, the design wins.

**Purpose.**

- **wasi exists to hide the `wasi:http` bindings, resource handles with a
  different API on each version, behind a function that returns a plain
  `response`, keeping every guarantee of its page.** wasi-libc gives wasip2
  and wasip3 the same POSIX part (files, sockets, clocks, stdio) and nothing
  for `wasi:http`; the owner confirmed this purpose.
  Source: `libraries/wasi/openspec/changes/redesign/reference/design.md`
  (proposals).
- **The redesign changes no verdict of 0.1.0's handler (the status range,
  the content type, the chunks, the trailers), and every served test keeps
  its `.requests` and `.expected`.** Every guarantee of the page is kept, and
  the 0.1.0 transcripts prove it on the new layout.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).

**Dependencies.**

- **wasi depends on Boost and webcpp::config like every webcpp library: its
  `config.hpp` includes `<webcpp/config.hpp>` first, the target `wasi` brings
  `/webcpp/config//config`, and the by-hand build names the include paths of
  Boost and config.** The claim "wasi needs no Boost" was inherited from the
  README of the project wasi was written for, and is removed.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **`WEBCPP_WASI_NO_EXCEPTIONS` follows `WEBCPP_HAS_EXCEPTIONS` by
  webcpp::config's two lines, and wasi no longer reads the compiler's macros
  itself.** `<webcpp/config.hpp>`, included first, says whether webcpp has
  exceptions.
  Source:
  `libraries/wasi/openspec/changes/redesign/specs/wasi/spec.md`
  (proposals).

**Versions and targets.**

- **Each version of WASI has a namespace, `webcpp::wasi::p2` and
  `webcpp::wasi::p3`, in `wasi/p2/` and `wasi/p3/`, and the configured one is
  `inline`, as Boost.Process's `v1` and `v2`.** `webcpp::wasi::http::...`
  then names the configured target's, and the two versions read apart.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **A version holds only the feature namespaces it provides, today `http`
  alone; there is no `filesystem`, `sockets`, `clocks` or `environment`
  namespace.** As Boost.Asio's `posix` and `windows` exist only where the
  platform has them; files, sockets, clocks and the environment go through
  the same wasi-libc on both versions (measured).
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **What both versions share (`response`, `request`, the common internals)
  lives in `webcpp::wasi::detail` and appears in each version's `http` by
  `using`; a WASI build has no `webcpp::wasi::http` outside the versions.** A
  public `wasi::http` beside the inline version's would make every lookup of
  it ambiguous.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **Each version's handler is in a header of its own,
  `<webcpp/wasi/p2/http.hpp>` and `<webcpp/wasi/p3/http.hpp>`, with no `#if`
  in its logic; the one choice between them is made in
  `<webcpp/wasi/http.hpp>`.** 0.1.0's `entrypoint.hpp` interleaved the two
  handlers with `#if` in about 500 lines, and could not be read a version at
  a time.
  Source: `libraries/wasi/openspec/changes/redesign/proposal.md`
  (proposals).
- **The compiler chooses the version: `config.hpp` defines
  `WEBCPP_WASI_TARGET_P2` or `_P3` from `__wasip2__` or `__wasip3__`, and the
  build defines nothing.** The compiler already knows the target, and a
  program compiled by hand gets the version b2 would give it.
  Source:
  `libraries/wasi/openspec/changes/redesign/specs/wasi/spec.md`
  (proposals).
- **`WEBCPP_WASI_TARGET`, `p2` or `p3`, overrides the compiler's choice, as
  `BOOST_PROCESS_VERSION` does, and any other value stops with the one error
  `WEBCPP_WASI_TARGET is p2 or p3`.** The spike measured a p3 handler on the
  wasip2 libc and a p2 handler on the wasip3 libc both serving, so the
  override is a real choice.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **wasip1 and every other WebAssembly target stop at webcpp::config's error
  `unsupported target`, before wasi's own block is read.** (reason not
  recorded)
  Source:
  `libraries/wasi/openspec/changes/redesign/specs/wasi/spec.md`
  (proposals).

**Interface.**

- **A program writes an ordinary function, `response fn(request const&)`,
  and names it once, at global scope, with
  `WEBCPP_WASI_HTTP_ENTRY_POINT(fn)`; `WEBCPP_WASI_HTTP_MAIN_BEGIN`, `_END`,
  `WEBCPP_WASI_HTTP_EXPORTS` and `http_main` are removed.** The function has
  no ABI in its type, so it compiles natively and a native test calls it;
  0.1.0's main, defined inside macros that need the component ABI, ran only
  in a served component.
  Source: `libraries/wasi/openspec/changes/redesign/proposal.md`
  (proposals).
- **The function has no name the library fixes, may live in any namespace
  and may be defined in another translation unit than the macro.** The
  macro takes the function's qualified name, so the body is no longer inside
  a namespace of wasi's.
  Source:
  `libraries/wasi/openspec/changes/redesign/specs/wasi/spec.md`
  (proposals).
- **`WEBCPP_WASI_P2_HTTP_ENTRY_POINT(fn)` and
  `WEBCPP_WASI_P3_HTTP_ENTRY_POINT(fn)` define each version's export, and
  `WEBCPP_WASI_HTTP_ENTRY_POINT(fn)` only forwards to the configured one.**
  A program can name a version whatever the configuration says, and the
  macros' names mirror the namespace path, as Boost's do, since the
  preprocessor has no namespaces.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **`request` is an aggregate of `std::string_view method` and
  `std::string_view target`, views valid during the call.** It carries what
  0.1.0's main received; headers and a body are a later extension.
  Source: `libraries/wasi/openspec/changes/redesign/reference/design.md`
  (proposals).
- **One source is built once per target into one component per target, each
  exporting one version's handler; a component with both exports is not
  built.** Measured: wasmtime always answers through the p3 export, a host
  without p3 cannot load the component, Spin 4.2.2 refuses two handlers, it
  grows 24% (16.5 KB stripped), and one module linked against both libcs
  fails in wasm-ld.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **One world per target keeps wit-bindgen's plain names and the two
  standard worlds of 0.1.0; no interface is renamed with `--rename`.**
  `--rename` served only the dual world, which is rejected.
  Source: `libraries/wasi/openspec/changes/redesign/reference/STATUS.md`
  (proposals).
- **Derived by the proposal, to be confirmed (O1): on a build with no WASI
  version, `<webcpp/wasi/http.hpp>` declares `webcpp::wasi::http` with
  `response` and `request` alone and defines the entry-point macro as
  nothing.** The program's function then compiles and runs natively.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **Derived by the proposal, to be confirmed (O2): the ABI-free `response`
  and `request` are the public headers `<webcpp/wasi/detail/response.hpp>`
  and `<webcpp/wasi/detail/request.hpp>`.** The alternative,
  `<webcpp/wasi/http/response.hpp>`, suggests a public `wasi::http` outside
  the versions, which the design refuses.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **The handler keeps no state, as 0.1.0's did.** A wasip3 instance and its
  globals outlive one request: wasmtime reuses it 128 times by default.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).

**Capabilities.**

- **`config.hpp` defines capability macros from the compiler's own macros,
  as Boost.Asio's `BOOST_ASIO_HAS_*`: they say what compiles, and what runs
  is the host's grant, which the page tables (`--dir`, `-S inherit-network`,
  `allow-ip-name-lookup`, `--env`).** A program can ask what the target
  offers; a grant belongs to the command that runs the program, not to a
  macro.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **`WEBCPP_WASI_HAS_SOCKETS` is `__wasip2__ || __wasip3__`.** wasip1 has no
  `<netdb.h>`, and sockets compile and run on both versions behind
  `-S inherit-network` (measured).
  Source: `libraries/wasi/openspec/changes/redesign/reference/spike.md`
  (proposals).
- **`WEBCPP_WASI_HAS_THREADS` is `__wasi_cooperative_threads__`, never
  `__STDCPP_THREADS__`.** No thread runs on either version: wasip3
  predefines `__STDCPP_THREADS__` and links `std::thread`, which fails at run
  time with ENOTSUP (measured).
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **`WEBCPP_WASI_HAS_EXCEPTIONS` is `__wasm_exception_handling__`, never
  `__cpp_exceptions`.** wasm defines `__cpp_exceptions` without
  `-fwasm-exceptions`, a build that then fails to link.
  Source: `libraries/wasi/openspec/changes/redesign/reference/spike.md`
  (proposals).
- **Three capability macros are kept; the spike's
  `WEBCPP_WASI_HAS_FILESYSTEM` and `WEBCPP_WASI_HAS_PROCESS_CLOCKS` are
  not.** Files, clocks, random, the environment and stdio are on every WASI
  target; why the process clocks get no macro is not recorded.
  Source: `libraries/wasi/openspec/changes/redesign/reference/spike.md`
  (proposals).

**Run scripts.**

- **b2 writes a POSIX `sh` script, `<program>.sh`, beside every `.wasm` it
  builds for wasip2 or wasip3, by a rule of the build system that every
  library's programs get.** 0.1.0's programs ran through a wasmtime command
  line that the test harness composed and nobody else could copy, its flags
  differing by kind, target and exception setting.
  Source: `libraries/wasi/openspec/changes/redesign/proposal.md`
  (proposals).
- **The script finds wasmtime in `$WASMTIME` or on `PATH` (exit 127 and a
  message otherwise), adds `$WASMTIME_FLAGS`, finds the `.wasm` beside
  itself and `exec`s wasmtime.** The pair can be copied anywhere together,
  and a signal sent to the script reaches wasmtime, which the harness's
  keeper relies on.
  Source: `libraries/wasi/openspec/changes/redesign/reference/spike.md`
  (proposals).
- **The script states the explicit flags of the artifact
  (`-W exceptions=y`, `-S p3 -W component-model-async`), not the minimal ones
  of wasmtime 47.** The line then runs on the oldest wasmtime that can run
  the artifact: wasmtime 37 to 46 need `-W exceptions=y`, and WASI 0.3 needs
  46 or later.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **A served component's script takes an optional first argument that does
  not start with `-` as the address, `127.0.0.1:8080` by default, and passes
  the rest to `wasmtime serve`.** (reason not recorded) The spike measured
  that an option first keeps the default address.
  Source:
  `libraries/wasi/openspec/changes/redesign/specs/wasi/spec.md`
  (proposals).
- **`serve.py` and `run_example.py` run the programs through their scripts;
  b2's `webcpp.run` tests may keep `testing.launcher=wasmtime`.** The CI then
  tests the scripts, and the minimal line of a `run` test is the same on
  wasmtime 47.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).
- **The rule lives in `tools/component/component.jam`, where it replaces
  `.wasmtime-flags.p2` and `.p3` as the one place that knows wasmtime's
  flags, and declares a script for the WASI toolsets alone (`<build>no`
  elsewhere, read from the toolset and its version).** A native build
  declares no script and looks for no wasmtime.
  Source: `libraries/wasi/openspec/changes/redesign/reference/spike.md`
  (proposals).
- **The generator quotes `"on"`, builds each line as a list of words, and
  writes the script's `$(` through a variable.** Three b2 facts the
  prototype hit: `on` is a jam keyword, a string that holds an empty list
  vanishes whole, and `$(` in a string is b2's.
  Source: `libraries/wasi/openspec/changes/redesign/reference/spike.md`
  (proposals).
- **No `.cmd` script is written until a Windows WASI lane exists.** No WASI
  lane runs on Windows, and a script is for the machine that built it.
  Source: `libraries/wasi/openspec/changes/redesign/reference/spike.md`
  (proposals).

**Evidence.**

- **New tests hold the new layout: `target_namespace`,
  `target_override_p2`, `target_override_p3`, `target_refused`,
  `capabilities`, `request`, `function_native` and the served
  `http_explicit`; `target_refused` replaces the two refusals of 0.1.0.** The
  version no longer comes from a macro the build defines, so the refusals of
  neither and both are false.
  Source:
  `libraries/wasi/openspec/changes/redesign/specs/wasi/spec.md`
  (proposals).
- **A check of the run scripts proves them generated, clean under
  `shellcheck -s sh`, run by `dash` and from a path with a space, and exiting
  127 without wasmtime; shellcheck and dash are looked for by this check
  alone.** (reason not recorded) The spike ran each of these on its
  prototype.
  Source:
  `libraries/wasi/openspec/changes/redesign/specs/wasi/spec.md`
  (proposals).

**Process.**

- **The redesign is a breaking change made before webcpp's first release,
  after webcpp::config exists, with a mechanical migration listed in the
  changelog.** The breaking change then costs no user, and wasi needs
  `<webcpp/config.hpp>`.
  Source: `libraries/wasi/openspec/changes/redesign/proposal.md`
  (proposals).
- **The run-script rule is code of the superproject's tools, specified in
  wasi's specification for now.** The design places it in the redesign and
  wasi's tests exercise it; where it belongs is O4.
  Source: `libraries/wasi/openspec/changes/redesign/design.md` (proposals).

**Open questions for the owner.**

- **O1.** What does `<webcpp/wasi/http.hpp>` do on a build with no WASI
  version (native, Emscripten)? Recommended and specified: it declares
  `webcpp::wasi::http::response` and `request` and defines
  `WEBCPP_WASI_HTTP_ENTRY_POINT` as nothing, so the function compiles and a
  native test calls it.
- **O2.** Are the shared types public headers under `detail/`
  (`<webcpp/wasi/detail/response.hpp>`)? Recommended: yes, since they are
  the ABI-free headers; the alternative is `<webcpp/wasi/http/response.hpp>`,
  which suggests a public `wasi::http` outside the versions that the design
  refuses.
- **O3.** Host grants as a feature of the build (`<wasi-grant>filesystem`,
  `network`, `environment`), and `install` listing both the `.wasm` and its
  `.sh`, as the spike outlines? Recommended: later; the design asks for the
  flags of the kind and target, and wasi's tests need no grant.
  `WASMTIME_FLAGS` serves meanwhile.
- **O4.** Where is the run-script rule specified? It is code of the
  superproject's tools, shared by every library; this change specifies its
  behaviour in wasi's specification because the design places it in the
  redesign and wasi's tests exercise it. Recommended: the organization's
  specification records the rule, and wasi's refers to it.

### The site, increments 4 and 5 (accepted 2026-10-10, not built)

The open change `site-increments-4-5`: trystero's JavaScript package and the
collaborative cursors (increment 4), then the state machine, on the server,
and C++ calls the browser (increment 5). None of its plan's Tasks 20 to 35 is
built. While it is open, its `design.md` holds it in full and rules over this
summary.

**The package.**

- **trystero's JavaScript face is the package `@webcpp/trystero`, in
  `libs/trystero/js/` and built by a trystero target; the site serves it
  unbundled at `packages/trystero/`, and an example page reaches it through an
  import map.** The page then runs the very bytes a JavaScript developer gets;
  a copy built into the site was rejected, since it would not be a library
  artifact.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).
- **The package's surface is Trystero 0.26.0's, and every member of Trystero's
  configuration and options it does not implement throws a `TypeError` naming
  it.** None is accepted in silence: a relay-only ICE policy ignored would
  expose the address it asks to hide.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).
- **Every event is copied out of the wasm memory and delivered on a microtask,
  and `observe`, webcpp's one addition to the surface, hands the site's
  visualizer copies of each crossing.** As in Trystero, a handler may then
  leave its room or send at once.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).
- **The package is built on trystero's shared connection, `app`, alone: one
  `selfId`, and one connection per peer across the rooms of an app.** Trystero
  does so, and webcpp::trystero does so only through `app`.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).
- **trystero gains `raw_payload`, an action type that hands a message's format
  and bytes undecoded.** Without it a JSON message would be parsed in C++ and
  serialized again, which can change its text (`1.0` becomes `1`).
  Source:
  `organization/openspec/changes/site-increments-4-5/specs/site/spec.md`
  (proposals).
- **The package is `@webcpp/trystero` 0.1.0, `"private": true` until the owner
  publishes it on npm; until then b2 builds it, the site serves it and no page
  shows `npm install`.** The name and the version are gate G5, decided on
  2026-10-11; publication is gate G6, still open.
  Source:
  `organization/openspec/changes/site-increments-4-5/specs/site/spec.md`
  (proposals).

**The examples.**

- **The collaborative cursors run Trystero's own 24-line sketch byte for byte
  but its import line, with its provenance archived and its SHA-256 held by a
  test, and the three helpers the sketch leaves to the application are the
  site's.** trystero.dev publishes the sketch in no repository and its page
  states no licence, so a wrong copy must be detectable, and the copy relies
  on the owner's ruling that everything of Trystero is MIT; the helpers treat
  a peer's messages as hostile.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).
- **No page connects anywhere on load: an example reaches the public Nostr
  relays and STUN servers only on the reader's Join, under a notice, and no
  build or test reaches the public network.** The relays and STUN servers see
  the reader's address, as peers do; in tests Chrome resolves no host but
  127.0.0.1, a canary proves it, and the relay is the interop lane's.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).
- **A live example's surface is a page of its own, a `Frame`, shown in an
  `<iframe>` of the example page, `noindex` on both channels and without a
  card.** The visualizer then sits beside it and plays the crossings the
  package reports.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).
- **The state-machine example runs the site's own machines on webcpp::xstate,
  and XState's JavaScript is the oracle of the tests alone.** The site's state
  machines run on webcpp::xstate, not on XState's JavaScript (the owner's
  decision 10), so "the browser's own state" is the state React holds from the
  snapshot the C++ machine returned.
  Source:
  `organization/openspec/changes/site-increments-4-5/reference/plan.md`
  (proposals).
- **On the server, one handler, `answer(method, target)`, is called by two
  mains, a WASI component and a native host of the example's own on
  Boost.Beast, and both answer one committed transcript in the site's own lane
  `http` on native, wasip2 and wasip3.** webcpp::wasi has no native host (one
  comes with webcpp::beast), and `b2 site` has neither wasi-sdk nor wasmtime,
  so the page's terminal sessions are built from the committed transcript,
  never typed.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).
- **C++ calls the browser is a program on webcpp::asio, scheduled last, with
  no version on `emscripten::val` alone.** The owner's decision makes
  webcpp::asio the way the browser's promises and events reach C++, so the
  example waits for the asio track's publication.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).

**The site's build.**

- **Every `b2 site` measures each port of a JavaScript original beside the
  original, raw, gzip and brotli, into `bin/site/sizes.json`, never committed,
  and a check holds every size a page shows to that measurement.** A committed
  size file would couple the site's repository to every measured library and
  to the build machine: any byte a library's wasm moves would turn `main` red
  until the site regenerated it. It is the recommendation for gate O5.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).
- **A Jamfile under `site/examples` may declare own lanes, which the CI runs
  as a library's, and the site's programs never reach `b2 declared-targets`.**
  No ordinary lane is then planned for them.
  Source: `organization/openspec/changes/site-increments-4-5/design.md`
  (proposals).
- **The site's JavaScript path keeps working with npm alone: a test or type
  check that needs the package skips without b2, saying why and how to get it,
  and fails under b2, which requires it.** The owner's decision of 2026-10-10,
  two ways into the site's repository, keeps npm alone a way in, and a check
  that needs the package never passes in silence.
  Source:
  `organization/openspec/changes/site-increments-4-5/reference/plan.md`
  (proposals).

**Preconditions.**

- **The site's increments 2 and 3, Tasks 12 to 18 of the earlier site plan,
  are in the site's `main`, and Task 19 has reviewed and published them.** Not
  met: Tasks 12 to 15 (xstate on emscripten, the site's wasm, the PWA, the
  trace) exist only as unpublished patches under the change's `reference/`,
  and Tasks 16 to 19 (the visualizer, the calculator, the browser lane, the
  review) are not built. Tasks 26 to 30 and 32 wait on them.
  Source: `organization/openspec/changes/site-increments-4-5/tasks.md`
  (proposals).
- **trystero's shared connection, `app`, is in trystero's `main`, and the
  superproject's `main` points to it.** The change's `tasks.md` and
  `STATUS.md` record it as missing, but the superproject's `main` now records
  trystero at `77fed8f`, whose history holds the shared connection
  (`2e2dcd4`): it appears met, for Task 20 to confirm. Tasks 22 to 26 and 28
  wait on it.
  Source: `organization/openspec/changes/site-increments-4-5/tasks.md`
  (proposals); `libs/trystero` (webcpp).
- **webcpp::asio's Tasks 2 and 3 (`/webcpp//node-test`, `webcpp.variants`) are
  in the superproject's `main`, and for Task 33 `libs/asio` is published as a
  submodule.** Not met: `main` has neither rule and no `libs/asio` submodule.
  Task 23's Steps 1 and 2, Task 31 and Task 33 wait on them.
  Source: `organization/openspec/changes/site-increments-4-5/tasks.md`
  (proposals).
- **`/webcpp//boost_url` is in the superproject's `main`.** Met: the
  on-the-server example links it rather than compile Boost.URL's sources
  itself.
  Source: `organization/openspec/changes/site-increments-4-5/tasks.md`
  (proposals).

**The owner's gates.**

- **G4: trystero's JavaScript API is approved, naming `observe`, the refusal
  list and the delivery on a microtask.** Open; Tasks 22 to 25 wait on it.
  Source:
  `organization/openspec/changes/site-increments-4-5/specs/site/spec.md`
  (proposals);
  `organization/openspec/changes/site-increments-4-5/reference/STATUS.md`
  (proposals).
- **G7: the public network from the site, (a) Trystero's app id and room, (b)
  a webcpp app id, or (c) no live Join, only a recorded trace.** Open, with
  (a) recommended; the push that publishes the cursors page carries the option
  the owner chose, never (a) by default.
  Source:
  `organization/openspec/changes/site-increments-4-5/specs/site/spec.md`
  (proposals).
- **O5: the sizes measured by every build, or a committed file.** Open, with
  the measurement by every build recommended; Task 27's `--check` and its
  Steps 4 to 6 wait on it.
  Source:
  `organization/openspec/changes/site-increments-4-5/specs/site/spec.md`
  (proposals);
  `organization/openspec/changes/site-increments-4-5/reference/plan.md`
  (proposals).
- **G6: the publication of `@webcpp/trystero` on npm.** Open; the
  recommendation is from the CI alone, with npm provenance, under an
  organisation enforcing two-factor authentication, after one review cycle on
  the preview.
  Source:
  `organization/openspec/changes/site-increments-4-5/specs/site/spec.md`
  (proposals).
- **G2: the push of trystero, the site and the superproject after each
  increment's review.** The owner's act, as every outward act is.
  Source:
  `organization/openspec/changes/site-increments-4-5/specs/site/spec.md`
  (proposals).

### hash (hashing and key derivation over Boost.Hash2 and C backends; wrapper; accepted 2026-11-14, increments 1, 2, 3, 4, 5 and 7 built, not merged)

webcpp::hash is one entry point for hashing and key derivation in a C++20
program on every target webcpp has, a wrapper (`"port-of": null`). Increment 1
is built on the library's branch (`libs/hash`, to become `webcpporg/hash`):
Boost.Hash2's algorithms and `hmac` re-exported by alias (`algorithms.hpp`,
`hmac.hpp`); Keccak-256 with the original padding over XKCP's permutation
(`keccak.hpp`) and BLAKE3 over its official C implementation (`blake3.hpp`),
both in Hash2's HashAlgorithm form; HKDF (RFC 5869, `hkdf.hpp`) and PBKDF2 (RFC
8018, `pbkdf2.hpp`) on the backends `hash2`, `sodium`, `bearssl` and `openssl`
(`backends/`); Argon2id (RFC 9106, parallelism 1, `argon2.hpp`) and scrypt (RFC
7914, `scrypt.hpp`) from libsodium; the default backend (`config.hpp`), the
capability table (`doc/capabilities.json`), and the measured table
(`doc/measurements*.json`), a dated reference of 2026-11-16 that decides
nothing. The families `digest_of`, `hasher`, `mac` and `argon2` take the tags of
`digests`, `macs` and `kdfs`; increment 2 gives them libsodium's whole surface:
BLAKE2b with its key, salt, personalisation and length, SipHash-2-4 and
SipHash-2-4x, BLAKE2b subkeys (`blake2b_subkey.hpp`), SHA-2, SHA-3, SHAKE,
TurboSHAKE, HMAC, and Argon2i and Argon2id with one lane; increment 3 gives them
XKCP's surface: Keccak-224 to Keccak-512, SHA-3, SHAKE, SP 800-185's cSHAKE,
KMAC, TupleHash and ParallelHash, and RFC 9861's KangarooTwelve and TurboSHAKE;
increment 4 gives them OpenSSL's surface, each reached only by naming
`backends::openssl` (native, wasip2 and wasip3): MD5, SHA-1, SHA-2, SHA-3,
SHAKE, Keccak-224 to Keccak-512, BLAKE2, RIPEMD-160, TLS 1.0's MD5-SHA1 and
SM3; HMAC, KMAC, keyed BLAKE2 and SipHash; scrypt, and Argon2d, Argon2i and
Argon2id with every parameter of RFC 9106; and the key derivations of
standards (`kdf_standards.hpp`), SP 800-108's KBKDF, SP 800-56C's one-step KDF
and ANSI X9.63's KDF, which have no default backend; increment 5 gives them
BearSSL's MD5, SHA-1, SHA-2, TLS 1.0's MD5-SHA1, SHAKE and HMAC, each reached
only by naming `backends::bearssl`. The C libraries are built by
`third_party/Jamfile` (`xkcp`, `blake3`, `sodium`, `bearssl`, each with a
canary), their own suites by the `c-suites` lane (`test/c_suites`), the
examples are in `example/` and the documentation in `doc/`. Every function
reports failure as a `boost::system::result`, takes its data as `std::span` and
allocates nothing in webcpp's own code; increment 7 adds an asynchronous family
in `async.hpp` over webcpp::asio (any completion token, Cobalt's `use_op`
included): the password hashes and PBKDF2 on a thread pool where the build has
threads, the digests, HMAC and HKDF through a post, and `backends::webcrypto`,
the browser's WebCrypto on Emscripten, which only that family takes. Its
repository, `webcpporg/hash`, is still to be created by the owner (gates G1, G2
and G4); the proposal, with the specification, the design and the plan, is in
`libraries/hash/openspec/changes/genesis/` (proposals).

- **Two constructions of webcpp's own, over an audited primitive each, and no
  primitive.** HKDF and PBKDF2 over Boost.Hash2's `hmac<H>` on every target,
  the RFC's text step by step in under 150 lines with every intermediate value
  wiped; and Keccak-256's sponge (absorbing, the `0x01 ... 0x80` padding and
  squeezing) over XKCP's Keccak-p[1600], line for line as Boost.Hash2's
  `detail::keccak_base<0x01, 512, 256>`, which is its oracle, until Boost
  publishes a `keccak_256`. This departs from chapter 4's rule that webcpp
  writes no cryptography of its own, as the owner recorded on 2026-11-14.
  Source: `libraries/hash/openspec/changes/genesis/reference/spec.md` section
  1.3 (proposals).
- **The key derivation functions and the families have backends, as
  webcpp::crypto's algorithms do, and a backend that lacks a function or a tag
  refuses at compile time.** `backends::hash2`, `xkcp`, `blake3`, `sodium`,
  `bearssl` and `openssl`, and `webcrypto` for the asynchronous family alone;
  the default is one stated rule, the same on every target and fixed (designs
  D33 and D34): the first of `hash2`, `xkcp`, `blake3` and `sodium` that has the
  algorithm whole, else the first of them with a partial cell, else none (the
  call names its backend); `bearssl`, `openssl`, `botan` and `webcrypto` are
  never a default. No measurement decides it.
  Source: `libraries/hash/openspec/changes/genesis/reference/spec.md` section
  1.4 (proposals).
- **The C libraries of hash (`xkcp`, `blake3`, `sodium`) are built file by
  file by `third_party/Jamfile`, with a link-time canary each.** The shared
  block of that Jamfile (`HASH`, `.hash-c-library`, `hash-checked-out`) is
  the one every C library of hash uses; `.hash-c-library` and crypto's
  `.c-library` share the C libraries' properties (`.c-sections`) and the
  link's (`.gc`), each defined once.
  Source: `libraries/hash/openspec/changes/genesis/reference/spec.md` section
  5 (proposals).
- **Seven increments, each usable alone.** The first, built, is Hash2 by alias,
  `keccak_256`, `blake3`, HKDF, PBKDF2, Argon2id, scrypt, the default backend
  and the measured table; the second, built, is the families and libsodium's
  whole surface; the third, built, is XKCP's whole surface through the families;
  the fourth, built, is OpenSSL's whole surface through the families and the key
  derivations of standards, each reached only by naming `backends::openssl`;
  the fifth, built, is BearSSL's MD5, SHA-1, SHA-2, TLS 1.0's MD5-SHA1 and SHAKE
  through `digest_of` and `hasher`, and its HMAC through `mac`, each reached
  only by naming `backends::bearssl`; the seventh, built, adds the browser
  backend over WebCrypto through a parallel asynchronous family, whose cells
  `doc/capabilities.json` marks asynchronous only; the sixth widens Botan's
  surface. Across the built increments every tag that two backends or more
  have is checked to give the same bytes on each pair of them, on random cases.
  Source: `libraries/hash/openspec/changes/genesis/reference/spec.md` section
  1.5 (proposals).

## 18. Proposed, not decided

The proposals not yet decided, each briefly, with the questions they leave
for the owner. Neither a draft nor a proposal under discussion decides
anything: each is here so that a contributor sees what is coming, and its
proposal holds it in full. A draft that a built change superseded stays,
marked so, with what superseded it, until its proposal is archived with its
status (chapter 14), so that its reasons stay readable.

### json_schema (draft, not decided)

webcpp::json_schema would be a header-only C++20 JSON Schema validator of
webcpp's own for drafts 4, 6, 7, 2019-09 and 2020-12 and OpenAPI 3.0's Schema
Object, on native, wasip2, wasip3 and Emscripten, proven by the official
JSON-Schema-Test-Suite, whose IR, loader, emitter and validator webcpp::zod
would later reuse. Its design and specification were approved by the owner on
2026-10-08 and 2026-10-09 and its plan has 58 tasks (`reference/plan.md`);
tasks E1.1 to E1.9 were built on an unpublished local branch, kept as
`reference/source/`, E1.10 is written and uncommitted
(`reference/source-wip/`), E1.4 (the regex policy) must be redone, and this
draft revives a library the owner shelved on 2026-10-12.

- **Every dialect is an empty policy tag (`draft2020_12`, `draft2019_09`,
  `draft7`, `draft6`, `draft4`, `openapi3_0`) whose machinery lives in
  `detail`, and `basic_validator<Traits, Dialects...>` carries the set a
  program chooses.** A program that needs one dialect does not carry the
  others' tables, and adding v1 later touches no existing dialect.
  Source: `libraries/json_schema/openspec/changes/genesis/design.md` D2
  (proposals).
- **Errors and annotations render as 2020-12's four output formats as
  `boost::json` values; messages are built lazily from one table of English
  templates, which a hook in the validate options replaces; Boost.Locale is
  reached only through one optional header, refused without exceptions, and
  the `.pot` catalogue is printed from the same table.** The official formats
  are what other implementations and Bowtie compare; a hook keeps localisation
  out of the core and out of global state; Boost.Locale is compiled and
  throws, so only one optional header needs it and json_schema stays
  header-only.
  Source: `libraries/json_schema/openspec/changes/genesis/design.md` D4
  (proposals).
- **`pattern` and `patternProperties` run on Boost.Regex 1.92, header-only,
  through webcpp::lexical's ECMA-262 translator behind json_schema's unchanged
  regex policy, with a step budget that turns a runaway search into an error,
  and the appended `errc::unsupported_regex = 21` for a pattern the engine
  cannot run as ECMA-262 does.** The owner abandoned SRELL and webcpp::regex
  on 2026-10-12; the translator passes 881 of 881 regex-dependent suite tests
  on all five lanes and gave no wrong answer against V8 on 87,028 fuzz
  queries, and it already ships in lexical for `format: regex`, so json_schema
  shares one engine with it.
  Source: `libraries/json_schema/openspec/changes/genesis/design.md` D5
  (proposals).
- **A schema is compiled once into an immutable flat plan of instructions
  whose operands are indices into constant tables, run by a small iterative VM
  on an explicit stack, with no separate tree-walking interpreter; `is_valid`
  and `validate` share the engine through a template sink.** One engine cannot
  drift from another, a flat plan of indices is relocatable, copyable and
  later serializable, and no input depth reaches the C++ stack.
  Source: `libraries/json_schema/openspec/changes/genesis/design.md` D9
  (proposals).
- **`load`, `compile`, `validate`, `emit` and `to_json` return
  `boost::system::result<T, diagnostic>`, whose `diagnostic` holds a code and
  two 256-byte `static_string`s, where and what, and the policies are grouped
  in one `traits` type.** So a refusal under an exhausted allocator still
  names its place; `std::error_code` alone names no place, exceptions on the
  main path fail webcpp's rule, and a template parameter per policy makes
  signatures unwieldy.
  Source: `libraries/json_schema/openspec/changes/genesis/design.md` D11
  (proposals).
- **Numbers are exact: `traits::number_type` is `boost::decimal::decimal64_t`
  by default, schema numbers are read from their lexeme, an instance double is
  compared as the exact decimal its shortest text denotes, and `multipleOf`
  works on coefficients and exponents in 128 bits, never with `fmod`.**
  Required suite tests fail otherwise: rounding to `decimal64_t` accepts 2^64
  under `maximum: 18446744073709551615`, a double's binary value makes `1.1`
  exceed `exclusiveMinimum: 1.1`, and Boost.Decimal's `fmod` fails a required
  test.
  Source: `libraries/json_schema/openspec/changes/genesis/design.md` D13
  (proposals).
- **Nothing recurses on input depth, and allocation goes through two
  allocators the program gives, the schema's and the validation's (pmr by
  default), with `is_valid` allocating nothing on the common path; the stated
  exceptions are the user's callbacks, Boost.Locale, and Boost.Regex's
  compiled programs and backtracking stack.** No input depth may reach the C++
  stack, so a 100,000-level hostile instance is a depth error, not a stack
  overflow; Boost.Regex allocates through the global `operator new`, so the
  full guarantee holds for schemas without patterns, which the allocation test
  measures.
  Source: `libraries/json_schema/openspec/changes/genesis/design.md` D20 and
  D5 (proposals).
- **The official suite, read at run time from the superproject's submodule,
  runs on every target through one runner per dialect that runs `is_valid` and
  `validate` on every test and requires them to agree, against known-failure
  lists that fail on an unlisted failure, on a listed test that passes and on
  a listed test it cannot find.** So the lists never lie; the suite is MIT
  test data, never copied.
  Source: `libraries/json_schema/openspec/changes/genesis/design.md` D21
  (proposals).

**Open questions for the owner.**

- The owner's go to revive the library, and where its canonical local
  repository lives now.
- lexical's public matching interface (lexical's change `strategies`, group
  3): its names, and whether its compiled pattern keeps the resource it was
  given (task E1.4).
- `errc::unsupported_regex = 21`, appended by this change, and the allocation
  exception for Boost.Regex: the owner confirms both.
- Amendment A1 (numbers, the exact decimal of the shortest text), which E1.2
  implements, and A2 (`format_entry::check_in`), which E5.5 needs.
- The licence of the bundled meta-schemas and of the OpenAPI schema inside a
  BSL-1.0 repository (recommended: commit them with `LICENSE-JSON-SCHEMA.txt`
  and `LICENSE-OPENAPI.txt`).
- jsonschema-benchmark's missing licence, the benchmark's pins (its commit,
  Blaze, ajv) and Bowtie's pin.

Source: `libraries/json_schema/openspec/changes/genesis/design.md` Open
Questions (proposals).

### lexical: strategies (draft, not decided)

The change `strategies` is the design the owner asked for on 2026-10-13,
reviewing lexical 0.1.0's interface: one entry point whose behaviour a
developer chooses, Boost.Regex as an optional strategy, and the matching
interface webcpp::json_schema needs. Nothing of it is built, and its open
questions O1 to O6 await the owner. A source is given relative to
`libraries/lexical/openspec/changes/strategies/` in proposals.

- **One entry point for every format, `is<Format>(std::string_view s, Strategy
  const& strategy = Format::default_strategy{})`, constrained by
  `strategy_for`: any callable `bool(std::string_view)` is a strategy, and one
  that declares `using format` is a strategy for that format alone.** 0.1.0's
  functions have four shapes, so a table of formats needs a wrapper per
  format; with one signature, templates and tables handle every format, and
  `is` adds nothing to the strategy's answer. The model is Boost.Geometry's
  strategies (a default per type, others passed in).
  Source: `design.md`, D1; `reference/design.md`, sections 1 to 3 and 13
  (proposals).
- **Each format becomes a tag type in `webcpp::lexical` that nests its
  strategies, each an aggregate named after its standard (`time::rfc3339`,
  `iri::rfc3987`, `regex::ecma262`), and the configuration moves into them
  (`.leap`, `.manipulation`, `.resource`, `.max_length`, `.max_nesting`).** A
  developer chooses webcpp's implementation or another, or writes their own;
  the default strategy of each format gives, for every string, the answer
  0.1.0 gives, since no default verdict is to change.
  Source: `design.md`, D1 and Goals; `reference/design.md`, section 4
  (proposals).
- **Each strategy webcpp ships gives its configured grammar rule through
  `rule()`, and `is<F>(s, S{c})` equals `parse(s, S{c}.rule()).has_value()`,
  which replaces 0.1.0's invariant that a validator and its rule agree; `is`
  is `constexpr`, and its `noexcept` is the strategy's.** A Boost.URL rule
  carries its configuration, as a strategy does; a developer's own strategy
  carries no guarantee; a constexpr strategy stays so, and the IRI strategies
  may throw `std::bad_alloc`.
  Source: `design.md`, D1; `reference/design.md`, sections 3 and 4.1
  (proposals).
- **`date_time::rfc3339` gains `leap`, a `leap_seconds` defaulting to
  `allowed`.** A `date-time` holds a `time`, and 0.1.0's `date_time_rule_t`
  always allows second 60, so JSON Schema v1's `date-time` cannot refuse it;
  the default changes no answer.
  Source: `design.md`, D2; `reference/design.md`, section 4 (proposals).
- **Boost.Regex becomes an optional strategy, `regex::via_boost_regex<Judge>`:
  it refuses a pattern over its length bound or not ECMA-262 without calling
  the judge, translates the pattern into Boost's Perl syntax over code points,
  and hands the judge a `boost_regex_pattern` (the translation, its flags, the
  source); `boost_regex_compiles` is the ready judge, `ecma262_traits` the
  traits of ECMA-262's classes, and `<webcpp/lexical/regex/boost_regex.hpp>`
  alone includes Boost.Regex.** A developer who runs the patterns with
  Boost.Regex wants to refuse, when validating, a valid pattern Boost.Regex
  cannot run and to compile with the syntax and flags the engine will use; the
  translator is the feasibility prototype's, identical to V8 on 20,130 fuzzed
  patterns, rewritten to webcpp's rules.
  Source: `design.md`, D3; `reference/design.md`, section 6; `proposal.md`,
  Impact (proposals).
- **`via_boost_regex` is never `noexcept` and writes its translation through
  the memory resource it is given, and a pattern the translator marks
  `unsupported` goes to the judge, which `boost_regex_compiles` answers
  `false`, from a committed list.** The translation allocates; only the
  judge's engine knows what it can run, and the list makes each difference
  from V8 known.
  Source: `design.md`, Risks; `reference/design.md`, sections 6.3, 6.4 and 10
  (proposals).
- **The same header offers the matching interface json_schema's regex policy
  needs: an ECMA-262 pattern compiled into `boost::basic_regex<char32_t,
  ecma262_traits>` as a value that says why it failed (`syntax` or
  `unsupported`), and a search over UTF-8 text with a step budget (10,000,000
  steps plus 64 per byte) that answers `found`, `not_found` or `limit`,
  allocating through the caller's resource or allocator.** json_schema
  compiles a schema's `pattern` once and searches instances with a bounded
  number of steps; its task 1.4 waits for this group.
  Source: `design.md`, D4; `proposal.md`, Impact (proposals).
- **The move from 0.1.0 is mechanical and done in one version, each `is_x`
  call mapped to `is<F>` with its changelog lines, and while both exist
  0.1.0's functions are the oracle of the new entry point's tests;
  composition, a strategy taking its parts' strategies, is staged for later.**
  The tests prove that every default strategy answers as 0.1.0 did over every
  string of the unit tests and the suite; nothing in the first step prevents
  adding part strategies as members with defaults.
  Source: `design.md`, Migration Plan and Risks; `reference/design.md`,
  sections 7, 8 and 10 (proposals).

Open questions for the owner:

- **O1.** Keep the `is_x` functions as one-line forms of `is<F>`, or remove
  them? Recommended: remove them in the version that adds `is<F>`.
- **O2.** Composition (a strategy taking the strategies of its parts, `email`
  its `hostname`'s) in the same version, or later? Recommended: later.
- **O3.** Boost.Regex as an optional dependency of one header needs a recorded
  decision.
- **O4.** Format tags in `webcpp::lexical` directly, or in a namespace of
  their own; strategies named by their standard (`rfc3339`, `ecma262`)?
- **O5.** `ecma262_traits` shipped by lexical (recommended), or left to the
  developer?
- **O6.** The matching interface (D4) in lexical, as json_schema's proposal
  assumes, or in json_schema itself?

### trystero: bounded JSON parse (draft, superseded)

**Superseded** by trystero's JSON on webcpp::document (trystero `a0cfac5`,
then on its `webcpp::document::pmr::document`, `2af7906`; chapter 15's
trystero entry). document's objects are ordered indices, not
hashed, so the quadratic parse this draft answers is gone, and with it the
bound of 18 members, its `static_assert`, the colliding keys' generator
(question 7) and `parse_payload`; the draft's byte bound for each caller is
adopted as `parse_options::max_bytes`, with an image bound of twice that
bound and 64 KiB. Of its questions, 1 is moot, since no numbered guarantee is
added; 2 no longer matters, since no object's size is bounded; 3 is
answered, the page's differences listing the bounds; 4 is answered, the
platform backend reading a remote candidate, at most 16 KiB of it, on both
targets; 5 and 6 are moot, the allocation test showing that no text a room
reads allocates outside its resource. Its proposal is still marked `draft`
(`.openspec.yaml`, proposals); archiving it as withdrawn is the owner's
(chapter 14). The draft's record follows as it was.

A relay or a peer can stall a room with a text well under the 1 MiB bound:
keys that collide in Boost.JSON's object hash, seeded with the object's
address, make a parse quadratic (4 MB in 9.2 s against 4 ms for random keys;
256 keys of 128 bytes, a text of 35 KB, cost 32,640 comparisons). The change
`bounded-json-parse` is uncommitted work on `d2563a6` (branch
`fix/json-flood`) that the owner has not decided.

- **Every object of a text the room parses for the protocol holds at most
  `protocol::json::max_object_members` (18) members, tied to Boost.JSON's
  `detail::small_object_size_` by a `static_assert`.** Below that threshold
  Boost.JSON hashes no object, whatever the seed, the key length or the word
  size, and the protocol's largest object has 7 members; the assertion fails
  the build if a Boost moves the threshold.
  Source: `libraries/trystero/openspec/changes/bounded-json-parse/design.md`
  (proposals).
- **The parse is a `boost::json::basic_parser` over a handler of trystero's
  whose `max_object_size` is 18: it stops at the 19th member, before reading
  its key, with `boost::json::error::object_too_large`, and builds no
  object.** What follows is never read, and the handler's `value_stack` over
  the room's storage keeps the parse in the room's resource, as before.
  Source: `libraries/trystero/openspec/changes/bounded-json-parse/design.md`
  (proposals).
- **`protocol::json::parse(text, max_bytes, storage, ec)` refuses a longer
  text with `errc::message_size` before reading it, each caller naming its
  bound, with no default: 68,608 bytes for a relay's text, 66,560 for a
  signal, 1,024 for a handshake message, 16 KiB for a native candidate.** The
  bounds come from the fields' own bounds (the signal's is a sealed
  description of 64 KiB with the longest ids and 1 KiB to spare), not from the
  measures (762 bytes for the longest signal, 1,244 for the longest relay
  text), and `static_assert`s tie them to those fields and keep the relay
  bound under 1 MiB. Having no default makes a new caller choose.
  Source: `libraries/trystero/openspec/changes/bounded-json-parse/design.md`
  (proposals).
- **A relay's text or a signal the parse refuses is logged and dropped, and
  the relay's connection stays open; a handshake message over its bound fails
  the handshake as one of the wrong shape does.** A text of the wrong shape
  was already ignored without closing; only a text over 1 MiB closes the
  connection, as in 0.1.0.
  Source: `libraries/trystero/openspec/changes/bounded-json-parse/design.md`
  (proposals).
- **An application's JSON payload keeps the unbounded parse, as
  `protocol::json::parse_payload`.** It is any JSON by design, as Trystero's
  `JSON.parse` reads it, and the cost of its objects is the application's,
  which asked for a `boost::json::value`.
  Source: `libraries/trystero/openspec/changes/bounded-json-parse/design.md`
  (proposals).
- **The page gains a guarantee: no text of a relay costs a room more than its
  length to read.** It is the change's goal; the diff numbers it 9, which
  `shared-connection` also numbers, so whichever change is archived second
  takes the next free number, anchors being permanent.
  Source: `libraries/trystero/openspec/changes/bounded-json-parse/design.md`
  (proposals).
- **The tests build the attack: `json_bounds` checks the bounds to the member
  and to the byte, and `hostile_relay_texts_are_refused_and_the_room_goes_on`
  sends 256 keys of 128 bytes sharing one Boost.JSON digest under three seeds
  through a memory relay, in an event and in a signal.** A sample of random
  keys would prove nothing about colliding ones; the key generator, written
  for 64-bit and 32-bit words, does not terminate as it stands.
  Source: `libraries/trystero/openspec/changes/bounded-json-parse/design.md`
  (proposals).
- **Nesting depth, array length and Boost.JSON's seed are left alone, and the
  wire does not change.** Boost.JSON's parser already bounds depth, arrays are
  not hashed, the seed is Boost.JSON's, and the oracle lane stays
  byte-identical.
  Source: `libraries/trystero/openspec/changes/bounded-json-parse/design.md`
  (proposals).

**Open questions for the owner.**

1. **Numbering with `shared-connection`.** Which change takes guarantee 9? The
   diff writes 9 and `shared-connection` 9 to 11; whichever is archived second
   renumbers, and the two modified requirements are merged by hand.
2. **Public relays.** Does any public Nostr relay send events with more than
   18 members? The `interop` lane's `--public` mode would show it; it was not
   run.
3. **The difference from Trystero JS.** The page's "Differences from Trystero"
   should list the bound: a relay's text over 67 KiB and an object over 18
   members are dropped.
4. **Candidates.** The native bound for a candidate is
   `max_sealed_candidate_bytes`, since an opened candidate is shorter than its
   sealed form; the browser backend's `add_ice_candidate` hands the text to
   the page's `JSON.parse`, untouched by the diff, and whether it needs a
   bound is not addressed.
5. **The allocation bound for a signal.** The room test asserts that the room
   handed out less than 8,192 bytes while reading the signal of 256 colliding
   members; with a stand-in key set the signal read 137,946 bytes, the event
   that carries it holding some 40 KB, so the assertion needs another bound or
   another measure.
6. **Instrumentation.** The sizes cited (1,244 and 762 bytes) were measured
   with an instrumented relay in an earlier copy of the work, which the change
   does not include.
7. **The key generator does not terminate.** The partner of a printable word
   differs from it by a constant that makes its top byte non-printable, for
   8-byte and 4-byte words alike, so the hostile case cannot reach its
   assertions; it needs another way to build colliding keys that are valid
   JSON strings, or another test of the claim.

Source: `libraries/trystero/openspec/changes/bounded-json-parse/design.md`
(proposals), "Open Questions".

## 19. Conflicts and open questions

This chapter records unresolved rule conflicts, design discrepancies and
validation gates. The original inventory was read on 2026-10-26 at superproject
`ddb6cb2` and the then-current library/proposal snapshots. The Asio/Beast portion
was reconciled against the owner's 2026-11-03 decisions and current code;
unrelated entries below retain their dated scope. A recommendation in an audit
is not an approval. Fixed discrepancies leave the active inventory; a bounded
compatibility departure belongs with its rationale in chapter 15.

### Asio/Beast closure: remaining gates and limits

Chapter 15 now records the implemented configuration, allocator and private-header
corrections, native/Emscripten/WASIp2/P3 target contract, default turn limit 100,
Diataxis guide, source-built OpenSSL, shipped Wasm backends and recurring thread
and TLS lanes. Chapter 4's executor contract and compiled-unit exceptions and
chapter 6's SDK-limited exception profiles reflect the existing approvals.
Public `webcpp.asio.tls` and `webcpp.beast.wasi` identities remain compatible.
The proposed resolver eager-evaluation workaround, category renumbering,
Asio/Beast/Trystero combination ban and new OpenSSL canary requirement were not
adopted. Chapter 5 rule 7's existing exact-archive exception stays in force.

- **Final candidate and main CI.** Root `55a72c0` / baseline CI 41597577370
  predates closure edits. Local passes and lane registration do not prove the
  final candidate or Asio's first library-main CI. The whole-branch review,
  proposal gates and integration sequence remain explicit in
  `docs/superpowers/plans/2026-11-03-asio-beast-closure.md`. Keep 0.1.0 in
  preparation until a separately authorized release.
- **Upstream dependency test coverage.** Native `openssl-upstream` runs
  upstream's full suite when `webcpp-openssl-tests=on`. WASIp3 cannot execute
  that upstream harness; real TLS/entropy integration is narrower evidence.
  This is an explicit remaining limit against chapter 5 rule 11, not a claim
  that the rule has been satisfied on WASI or an approved general exemption.
  Libdatachannel's source recipe currently disables its upstream tests;
  OpenSSL and combined-consumer witnesses do not prove that C++ library's own
  suite or every nested C dependency's suite. Keep that distinction in closure
  and CI reports without broadening this change to unrelated library work.
- **Upstream corrections follow-up.** Checked input/output hashes, version refusal
  and runtime witnesses bound the Asio/Cobalt corrections. They do not prove
  that every patch has an upstream issue or has been accepted there. Preserve
  existing issue references and verify provenance when rebasing; do not invent
  an upstream acceptance claim. Cobalt's pending-task no-exceptions limitation
  remains the separately documented warning for issue 287.
- **Historical subjects.** Earlier commits use conventional subjects rather
  than chapter 2's part convention. Retain history; the current work follows
  the convention for new commits. This observation does not justify rewriting
  already published commits or changing the general rule.

The global WASIp2/P3 launchers grant network/name lookup and default to 600 seconds
for tests; it establishes no production capability policy. Native Trystero
requires multiple threads and uses the same source-built OpenSSL through pinned
libdatachannel, which webcpp::webrtc now wraps for it, and names its Asio
webcpp::asio. Its relays now run on webcpp::beast's facade, natively Boost.Beast
over that same OpenSSL (trystero's branch `refactor`), and coexistence is
required.

### The libraries against the rules

Each library below does not keep a rule of chapters 3 to 12 at the commit
0.1.0 pins. The roadmap (chapter 16) already brings some of them to it, as
it says.

- **Allocation (chapter 4).** xactor takes no allocator and has no counting
  test (`include/webcpp/xactor/scheduler.hpp`); xstate's machine has no
  `Allocator` parameter and holds `std::shared_ptr` and `std::function`
  (`machine.hpp:1322-1328`, `implementations.hpp:81-145`); wasi's response
  holds its body as a `std::string`; these three are on the roadmap. The
  pages of pratt and idna do not say which of their types are shareable
  (each library's `doc/allocation.adoc`).
- **Types of a fixed meaning (chapter 4).** Plain `int` or `unsigned` where no
  interface asks for it: pratt's binding powers and `max_depth`
  (`parser.hpp:54,175,199,309`, `calculator.hpp:988-1017`), wasi's
  `response.hpp:45` and `entrypoint.hpp:101,122,200,234` (with unqualified
  `uintN_t`), idna's `detail/nfc.hpp:229,233`, lexical's
  `date_time.hpp:54-144`, `detail/regex_validator.hpp:71` and
  `detail/regex_unicode.hpp:35`, and document's sizes as `std::uint64_t`. The
  roadmap's review covers it.
- **What a library builds on (chapter 4).** document hashes with an FNV-1a of
  its own rather than Boost.Hash2's; lexical has a UTF-8 decoder of its own in
  `detail`, the third in webcpp.
- **xactor's browser target.** xactor still declares no Emscripten target
  (`test/Jamfile:11`), with no reason recorded. Executor-based Trystero and
  document adapters are no longer conflicts merely because they use Asio:
  chapter 4 now distinguishes executors from libraries that contain actors.
- **Errors as values (chapter 4).** lexical has no error category of its own.
- **Text (chapter 4).** lexical passes text as `boost::core::string_view`,
  where the rule asks for `std::string_view`.
- **Bringing a C library (chapter 5).** trystero links
  `/third_party//secp256k1`, which follows the source-target `HAS`/canary
  contract. Libdatachannel is a pinned C++ source target with nested
  dependencies; its remaining upstream-test limit is recorded above.
- **crypto against chapter 5's rules 11 and 12.**
  - MSVC's messages: each case of `test/msvc` fails on the `msvc-14.3` and
    `msvc-14.5` lanes on every push (`webcpp.compile-fail`,
    `webcpp.link-fail`), and its exact text (`C1189`, `C2338`, `LNK2001`,
    `LNK2038`) is checked on no CI. The text is checked on clang, GNU ld and
    wasm-ld by the tools job, and ld64's on a developer's macOS, recorded in
    the ledger; the tools job has no macOS or Windows leg.
  - crypto has no measured size until its sizes lane (chapter 17), so a pin's
    move (rule 12) updates the submodule, the canary's commit and the tests
    on every target, and no table.
  - The c-suites lane runs BearSSL's and libsecp256k1's own suites on one
    native toolset per target, so they never run on the MSVC build, whose
    BearSSL configuration (no seeder, `BR_USE_WIN32_RAND=0`) differs most from
    the others; only webcpp's own tests exercise it.
  - The source-built OpenSSL is compiled `no-asm` on MSVC, wasip2 and wasip3:
    table-based AES and 4-bit GHASH, no AES-NI, not constant time
    (`OPENSSL_AES_CONST_TIME` would make only the AES core constant time).
    On MSVC crypto's default backend is still OpenSSL when it is linked (on
    wasip2 and wasip3 it is BearSSL), and the page says how to choose
    BearSSL.
- **Exceptions (chapter 6).** lexical's throwing IRI functions
  (`uri.hpp:281-325`) and document's throwing conveniences are not behind
  their library's `NO_EXCEPTIONS` macro; xstate's `machine.hpp:1213,1233`
  and `node_set.hpp:121` call `.at()`, which throws `std::out_of_range` on a
  precondition violation, beside guarantee 15, "xstate throws no exception
  of its own". wasi's `config.hpp:38-48` reads `WEBCPP_NO_EXCEPTIONS` itself,
  as chapter 6 records until its redesign.
- **Fidelity and evidence (chapters 11 and 12).** Sixteen entries of xstate's
  appendix "Differences" have no `diff_` program (names, src, targets,
  undefined, system, time, deadlines, timers, tick, stop, gone, core-clock
  among them); document has no twins, and its Node is not pinned.

### The text of the rules

These are errors of the rules' own text, moved here unchanged (the proposal
`coding-guidelines`, design D3), to be corrected each by a change of its own.

- `AGENTS.md` chapter 1's table of libraries gives lexical's path as
  `libs/formats`; it is `libs/lexical`.
- Chapter 9's table leaves out the lint's rule "Doc Comment code spans"
  (`tools/lint/lint.sh`, rule 17), and the organization's specification counts
  twenty-one rules where the lint runs twenty-two (`octal escapes` added).
- Chapter 16 says trystero's `config.hpp` is not yet on
  `<webcpp/config.hpp>`; it includes it
  (`libs/trystero/include/webcpp/trystero/config.hpp:14`).
- Chapter 8 lets a program exclude a target with `#ifndef __wasi__`, while
  config's design chose `WEBCPP_TARGET_*` so that no library reads the
  compiler's macros (config's genesis `design.md`); xactor's `drivers.hpp`
  tests `__wasi__`.
- Chapter 6 asks every library for `WEBCPP_<NAME>_NO_EXCEPTIONS` and
  `test/config_test.cpp`; config has neither, and chapter 3 exempts only its
  names and its namespace.
- Chapter 3 says nothing of the error enumeration's name: pratt's is `error`,
  xactor's and xstate's `errc`.
- Chapter 10's "every file BSL-1.0" has no exception for the Unicode-licensed
  data idna generates into `detail/tables.hpp`, and the owner's confirmation
  is not recorded (idna's genesis `reference/STATUS.md`).
- Chapter 2 limits "one import commit" to code moved from elsewhere;
  `CONTRIBUTING.md` and the organization's specification say every webcpp
  repository starts from one.
- `AGENTS.md` chapter 4 shows xactor's `test/Jamfile` "whole" without its
  `config_*`, `errors` and `sequence_and_log` tests, and names trystero's
  `interop` as the one Chrome lane, where `tools/ci/matrix.py` also gives
  document's `js` one.
- `AGENTS.md` chapter 5 and `tools/release/release.py` bundle `site` and
  `third_party` in `dist`, where the organization's specification says `dist`
  refuses a submodule that is not a library.
- `CONTRIBUTING.md` states as present the testing of every variant, which
  chapter 16 holds as a roadmap item, and, with the site's community page,
  says a library is proposed by an issue, where the proposals'
  `CONTRIBUTING.md` says by a proposal. `README.md`'s table of libraries
  leaves out config.
- `.gitmodules` gives `site` an absolute SSH URL, against chapter 10's
  relative URLs; whether a `git clone --recursive` over HTTPS then needs SSH
  access is not tested.

### Design documents and specifications against their trees

Each library's specification and design are in
[webcpporg/proposals](https://github.com/webcpporg/proposals), under
`libraries/<name>/openspec/`. Where one disagrees with its tree, chapter 15
says what the tree does.

- **Every library of 0.1.0.** The specifications of config, xactor, xstate,
  pratt, wasi, idna and lexical still put their changelog's entries under
  "Unreleased", which 0.1.0 froze under "webcpp 0.1.0". wasi's and idna's
  `.openspec.yaml` link implementations (`6e3c529`, `e2452e5`) older than the
  commits 0.1.0 pins (`b936324`, `f298a3e`).
- **config.** `README.md`, `doc/testing.adoc` and the specification still
  give the site as `webcpporg.github.io/webcpp/`; the genesis `design.md`
  gives the lint the check of reserved names that `tools/doc/libraries.py`
  makes.
- **xactor.** Its `AGENTS.md` and `doc/quick-start.adoc` say the target adds
  only its include directory and Boost; `build.jam` also adds config. The
  specification counts four test programs; the tree has six.
- **xstate.** The genesis says every failure has the category
  `webcpp.xstate`; the actor layer refuses a call with xactor's
  `invalid_argument`. `test/CONVERSION.md` counts 23 public headers; there are
  24. Its `AGENTS.md` and `<webcpp/xstate.hpp>` say it depends on Boost.JSON
  alone, leaving out config.
- **pratt.** `reference/design-source.md` says "without exceptions on wasip2
  only", which D11 and the tree superseded; `doc/pratt.adoc` and the
  specification leave Emscripten out of its targets.
- **wasi.** The genesis says an allocator is not planned; chapter 16 plans
  one, wasi's among the first. The redesign (chapter 17) says it lands before
  webcpp's first release, which 0.1.0 prepares with the current interface;
  its specification credits `serve.py` with flags that
  `tools/component/component.jam` composes, requires a refusal on wasip1 that
  an earlier requirement makes unreachable, and puts public types in
  `detail`, against chapter 3.
- **idna.** The specification's include boundary, allocation test and
  changelog differ from `meta/include-boundaries.json`,
  `test/allocation_test.cpp` and `doc/changelog.adoc`, and it leaves out the
  generator's rule for MSVC's warning C4125.
- **lexical.** Its `AGENTS.md` names `max_regex_alternatives`, which no longer
  exists, and the stack at the nesting bound was not measured again;
  `doc/regex.adoc` lists the old generator's checks; the comment of
  `tools/generate_patterns.py` says three kinds and lists four; the brief of
  `detail/regex_validator.hpp` is wrong and its `flags::i` is set and never
  read; the specification's counting resource differs from
  `test/counting_resource.hpp`; the genesis lists four guards where the tree
  has five, and its reference's section 5.8, step 5, is not built; the
  introduction and `json_pointer.hpp` cite only draft handrews-01;
  `test/Jamfile` calls `/bigobj` "not measured" while MSVC's CI is green.
  Its draft strategies (chapter 18) cites a decision D10 that does not exist,
  refuses leap seconds in v1 where the suite's `date-time.json` accepts them,
  counts 22 functions where there are 21, names `uuid::rfc4122` where RFC
  9562 replaced it, and leaves its O6 out of its reference.
- **document.** The tree accepts `float`, which the specification refuses;
  the genesis's D5 puts the text `stringify` returns, a missing member's key
  and the parser's frames on the process heap, whose `std::bad_alloc` is
  "the one failure that is not a value", where the tree keeps all but
  `stringify`'s text in the document's allocator and, with exceptions, makes
  a failure there `errc::capacity`; the genesis keeps O5 open though it is
  resolved and counts 20 examples where there are 22; `doc/testing.adoc` and
  `doc/exceptions.adoc` are incomplete.
- **trystero.** The genesis ties 0.1.0 to `160f431`, while 0.1.0 also holds
  the change `shared-connection` (trystero `e9326e9`). The specification gives
  the interop driver's timeout as 900 where `test/oracle/Jamfile` gives 2400;
  the shared connection's delta has the roadmap list shared relay sockets,
  which `doc/roadmap.adoc` leaves out; `test/oracle/interop/js.html:149`
  still cites Trystero's source with a private shorthand, `C/`, where every
  other comment writes `dist/`.
- **webrtc.** The genesis `design.md` D14 puts the native classes outside the
  unsupported policy's inline namespace, since they honoured every setting;
  the tree puts them inside it, since natively the policy decides a data
  channel's `max_packet_life_time` of 0 (webrtc `871a4ef`).
- **crypto.** The genesis specification's section 3.7 and its plan's Task
  15 give OpenSSL's memory option a Windows branch that tells a libcrypto
  DLL's default functions by `GetModuleHandleExW` and `GetProcAddress`, and
  Task 16 measures the MSVC shared link. The tree compares the three
  addresses alone: webcpp builds OpenSSL static only, so the branch could
  never run in a test, and a libcrypto DLL (a program built without b2) is
  refused with `memory_functions_refused`, which the page says. Serving such
  a program takes the plan's branch back, never measured.
- **asio.** The 2026-11-03 amendment reconciles default turn limit 100,
  supported targets, source-built TLS, private configuration/allocation fixes
  and guide order. Proposal source snapshots must name the final committed
  library/root trees, and archive/status gates must wait for their actual
  integration and CI evidence. Historical snapshot commits remain provenance,
  never substitutes for validation of the current candidate.
- **The site.** The site's specification names `.htmlvalidate*.json`, which
  the site's `d113e38` renamed, and that commit broke the wrapping of
  `site/Jamfile`'s comments. The proposal of increments 4 and 5 (chapter 17)
  says the shared connection is missing, which `main` has, keeps the old fixed
  commit identity in its `STATUS.md` and plan, and is `decided` a day before
  it was `created`.
- **The organization.** Its specification's requirement on the compilers the
  CI tests predates the rule that makes them a subset of the lanes
  (`AGENTS.md` chapter 5), and its roadmap requirement repeats chapter 16's
  sentence on trystero's configuration.

### trystero's refactor: open items

trystero's refactor onto webcpp's libraries and Boost (trystero's branch
`refactor`, at `459b08c` on 2026-11-15), with its one platform backend, its
`std::chrono` clocks, its examples' twins, its JSON on webcpp::document's
`pmr::document` and its relays' bounded handshake, leaves these to their
owners.

- **asio.** `libs/asio/include/webcpp/asio/browser/src.hpp:189` cites a
  measurement made "in trystero's browser_event_loop_test.cpp", which the
  browser's move onto webcpp::asio's run model removed; the citation names a
  file that no longer exists. `libs/asio/doc/building.adoc:415` names
  `/webcpp/trystero//native`, which is now `/webcpp/trystero//platform`, and
  says such a program selects exceptions for Trystero's worker-thread
  backend, which needs none since webcpp::webrtc's move.
- **Chapter 16.** Its "webcpp::webrtc and webcpp::crypto" says webrtc's
  increment 2 "brings" the browser implementation, built since, and still
  leaves the relays' WebSockets to Beast; its "Trystero on Asio and Beast"
  calls Asio and Beast foundations for Trystero's later migration, which the
  refactor made (chapter 15's trystero entry).
- **trystero, its examples.** trystero's quick start is native alone, its
  browser counterpart the chat page: a program with an `.expected` cannot
  also be a `webcpp.link` page program, which doc-check refuses; a quick
  start on both targets would need doc-check to accept a linked source whose
  output another declaration compares.
- **trystero, deferred.** Reaching a relay whose host is an international
  name, through webcpp::idna, or one written with a WHATWG IPv4 shorthand,
  both failing closed today; and natively, a deadline on the resolution of a
  relay's name, which has none (the system's resolver on Asio's resolver
  thread).
- **trystero, document's cost.** As WP7 measured it, natively at `-O2` and
  before document took an allocator, document reads a relay's event in
  about 12 us, where Boost.JSON took 1.6 us, and the chat's debug
  WebAssembly grew from 29.2 MB to 33.7 MB; neither is measured since, nor
  the release size, and neither figure is recorded in trystero's tree.

### webrtc: open questions

- **Whether a later version synthesises `negotiationneeded` natively** (the
  design's O1), and **whether a later change adds a byte stream over a data
  channel**, for webcpp::beast's D6 (O2).
- **Whether natively a channel keeps its own queue bounded in bytes,** so that
  a channel never read cannot stall its connection's others, at the price of
  the flow control that slows the peer (O3).
- **Whether the native receive drops its size probe,** reading into the
  caller's buffer with the last message's size as a guess and asking for the
  size only when a message does not fit, which would halve the four
  allocations and copies a message costs (chapter 15). As `src/capi.cpp`
  reads, libdatachannel reports the size of a message too large for the
  buffer given as 0, since it moves the message out before it reads its size,
  so the probe would stay for that case.
- **A received message past the local maximum message size,** natively, is
  truncated by libdatachannel to that size (`src/impl/sctptransport.cpp`),
  silently, since webrtc installs no logger for it, and delivered; the page
  states it as a difference. A peer that keeps to the size announced in the description never
  sends one; whether the backend should detect the truncation and fail the
  receive with `message_too_large`, as the browser implementation will, is
  open.
