# Boost guidance for WebCPP

Adapted from [Writing Documentation for Boost](https://www.boost.org/doc/libs/latest/more/writingdoc/),
reviewed on 2026-10-15, including its Introduction, Documentation Structure,
HTML Design, and nine linked templates. This is a selective application, not a
copy of the guide or its HTML scaffolding.

Boost presents these as optional guidance and does not expect library authors
to write a full standardization proposal. Use their precision within WebCPP's
Diataxis organization, AsciiDoc source, and MrDocs reference. Existing project
rules and the user's scope remain controlling.
[Source: Introduction](https://www.boost.org/doc/libs/latest/more/writingdoc/introduction.html).

## C++ contracts and entry context

For direct symbol links, make the library, namespace, header, and routes to
examples and tutorials discoverable. Check MrDocs output; WebCPP does not publish
file-level comments.

Define generic requirements using valid expressions and semantics, without
imposing member functions. Name shared requirements and tabulate expressions when
helpful. Describe template constraints and invariants; omit preconditions already
enforced by C++.

State each fact once. Separate guarantees from notes and examples. Equivalence
code need not prescribe implementation. Promise complexity only as a justified
bound; omit irrelevant fields. A currently linear implementation or a timing
sample does not establish a portable complexity contract.
[Source: Documentation Structure](https://www.boost.org/doc/libs/latest/more/writingdoc/structure.html).

The following mapping is WebCPP's adaptation of Boost's
[header template](https://www.boost.org/doc/libs/latest/more/writingdoc/template/header.html)
to the tags allowed by the root `AGENTS.md`:

| Contract element | Content | MrDocs representation |
| --- | --- | --- |
| Requires | Predicates the caller must satisfy | `@pre` |
| Effects | Actions not already specified elsewhere | Detail prose or `@par Effects` |
| Postconditions | Observable state after successful completion | `@post` |
| Returns | Meaning of the result, not just its declared type | `@return` |
| Throws | Exception type and the circumstances that can trigger it | `@throws` |
| Complexity | Supported time/space bound, when promised | `@par Complexity` |
| Rationale | Design reason and alternatives | Explanation section linked with `@see` |

Keep parameter and template-parameter documentation required by WebCPP. Link
shared requirement definitions instead of repeating them. Do not invent tags
named after these headings. MrDocs owns signatures and reference organization;
do not duplicate its output or change its ordering merely to match the template.
For error-code or exception-disabled configurations, describe the actual failure
channel and resulting state; never infer those from the exception-enabled path.

## Configuration and surrounding content

Distinguish application-defined controls, public library-defined detection macros,
and internal implementation macros. Only the first group is user configuration;
do not invite applications to override the others.
[Source: Configuration template](https://www.boost.org/doc/libs/latest/more/writingdoc/template/configuration.html).

For WebCPP, verify each public control's default, accepted values, definition
timing, compiler-define/header interaction, and target restrictions against its
code and tests. Put exact macro details in reference and configuration steps in
how-to guides; keep internal switches out of the public configuration contract.

Use the overview to establish purpose and unfamiliar concepts. Put terminology
in a glossary or local definitions, design reasons in explanation, and answers
to recurring user problems in the relevant how-to or FAQ. Credit external
sources and contributions. These can be sections, not additional pages.

Use semantic lists: numbered steps for sequences, bullets for unordered items,
and description lists for terms. Distinguish identifiers from prose. Keep
navigation and headings useful, links meaningful, and images lightweight.
[Source: HTML Design](https://www.boost.org/doc/libs/latest/more/writingdoc/design.html).

WebCPP implements these presentation goals through its shared AsciiDoc renderer
and styles. Do not import the historical Boost logo/CSS, raw HTML templates,
timestamp scripts, or an empty FAQ. Keep project licensing and generated history
as configured. Use AsciiDoc footnotes when needed and structural markup instead
of spacing tricks. Add a diagram only when it improves understanding, and check
its legibility and loading cost in the rendered page.

## Focused review

For substantive documentation changes, review the rendered entry point and one
direct API link: can a reader locate the required include, understand the
contract, reach a working example, and distinguish configurable behavior from
implementation details? Check that tutorial advice agrees with reference and
that every claimed guarantee has supporting evidence. Apply only the checks
relevant to the requested change; a typo fix does not require a new chapter.
