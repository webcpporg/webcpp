---
name: webcpp-documentation
description: Use when authoring or reviewing documentation for any WebCPP library, including Diataxis guides, AsciiDoc examples, Boost-style C++ contracts, MrDocs API comments, and documented test or benchmark results.
---

# WebCPP documentation

Organize documentation by the reader's need using Diataxis. Preserve WebCPP's
AsciiDoc toolchain and generate API reference from C++ Doc Comments with MrDocs.

When writing or reviewing API contracts, configuration, or guide coverage, read
[Boost guidance for WebCPP](references/boost-guidance.md). It adapts Boost's
documentation recommendations to this workflow, including precise C++ semantics
and context for readers entering through a deep link. These are recommendations,
not Boost submission requirements or a replacement for the project's toolchain.

## Establish the scope

Locate the superproject by `Jamroot` and `tools/doc/`, then identify the library
repository under `libs/<name>`. Read the superproject `AGENTS.md`, especially
chapters 2 and 3, `CODING-GUIDELINES.md` chapter 7, and the library's
own instructions. Inspect its `doc/Jamfile`,
guide, public headers, examples, and relevant tests. Those files determine the
pinned tools, supported targets, contracts, and validation commands. Do not
assume another library supports Asio's browser or coroutine configurations.

Keep the requested scope: a small correction does not require reorganizing a
guide. Respect session restrictions on builds and CI. Documentation work does
not authorize publishing, pushing, merging, or starting CI. Write files in
English; preserve the repository's licence notices and text conventions.

## Choose the reader's path

| Reader's need | Form | Include |
| --- | --- | --- |
| Learn through a first successful experience | Tutorial | Prerequisites, ordered steps, runnable commands, expected observations, a clear finish |
| Complete a particular task | How-to | A concrete goal, necessary steps, relevant variations and failure handling |
| Look up exact behavior | Reference | Generated API details; precise configuration and contract tables where appropriate |
| Understand the design | Explanation | Mechanisms, reasons, tradeoffs, limitations, and evidence |

Link between these forms instead of mixing every concern into the tutorial.
They can be sections of the existing single-page guide; do not require four
directories or invent empty sections. Retain guarantees, testing guidance,
differences, and appendix ordering required by the repository.

Preserve library-prefixed anchors and numbered guarantee identifiers. When a
heading changes, update incoming links and Doc Comments that cite its title.
Separate behavior established by tests from assumptions and unsupported cases.

## Keep one source for code and API details

Use `doc/<name>.adoc` and its included sections. Reuse the shared `webcpp.doc`
and `webcpp.reference` rules; keep their target-specific parsing requirements.
Do not replace the toolchain or weaken MrDocs warnings to make a build pass.

Document public symbols in `/** ... */` comments with a one-sentence brief,
parameters, template parameters, and return values where applicable. State
lifetime, errors, allocation, execution, and platform constraints when relevant.
Use only the tags allowed by the current root rulebook. Link symbols with
`@ref` and guide headings with `@see "Exact heading", in the guide.` Avoid
handwritten duplicates of generated API entries and unstable overload hashes.
Keep human-written contracts and explanations alongside the generated reference:

```asciidoc
[#reference]
== Reference

include::{reference}[leveloffset=+1]
```

Every C++ listing must include actual compiled source. For example, Asio's
registered Promise example provides both the tagged program and expected output:

```asciidoc
[source,cpp]
----
include::{examples}/asio_promise.cpp[tag=program,indent=0]
----

[listing]
----
include::{examples}/asio_promise.expected[]
----
```

Adapt filenames and tags to the selected library. Register new examples in its
Jamfile and verify their output. Use `[source,bash]` for commands and `[listing]`
for output or Jam syntax. Reuse build-provided attributes and dynamic counts.
Never hand-edit `CHANGELOG.md` or files marked as generated, including generated
reference and measurements. Follow repository rules for maintained AsciiDoc
release notes within the authorized scope.

## Verify locally

Resolve executable targets from the actual Jamfile. An example's `.output`
target runs and checks it; merely building its executable does not. From the
superproject root, with the toolchain configured and `CPATH`,
`CPLUS_INCLUDE_PATH`, and `C_INCLUDE_PATH` unset, Asio examples include:

```bash
b2 -a toolset=emscripten libs/asio/example//asio_promise.output
b2 -a toolset=emscripten webcpp-suspend=asyncify libs/asio/example//asio_promise.output
b2 -a libs/asio/doc
```

These are local commands, not CI. Adapt them to declared targets and the requested
scope. Use fresh builds as final evidence. Run documentation builds sequentially;
they share outputs. Inspect diagnostics and rendered
`libs/<name>/doc/html/index.html` for links, included code, output, reference
navigation, and narrow-screen tables.
Run applicable comment/lint checks when changing headers. Report unavailable
tools or unverified configurations instead of claiming validation.

## Document measurements when requested

Publish optimized Release results. Record effective compiler **and linker**
flags, tool versions, platform, source revision, and exact commands. Inspect
existing measurement rules before invoking them; do not infer their matrix from
a target name. Compare the same program and artifact boundary across supported
optimization, exception, and suspension configurations. Separate raw Wasm,
required JavaScript, totals, and any compressed sizes; do not substitute a test
harness binary for the application.

For timing, identify clocks, warmup, sample counts, and summary statistics.
Separate compilation time, runtime, callback work, and yield latency. State
measurement limits and preserve reproducible inputs. Never invent results or
generalize one machine's measurements into a platform guarantee.

Finish with changed paths, actual commands and results, and remaining validation
limits. Do not advance a later task merely because documentation was requested.

## Background

- [Diataxis: the four documentation needs](https://diataxis.fr/start-here/)
- [MrDocs AsciiDoc generator](https://www.mrdocs.com/docs/mrdocs/generators/adoc.html)
- The checked-out superproject `AGENTS.md` is authoritative for WebCPP-specific
  syntax, configuration, and tool versions.
