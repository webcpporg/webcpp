---
name: webcpp-docs-site-release
description: "Write a library's page and Doc Comments, build the site, or prepare a release of webcpp."
---

# Docs, site and releases

The rules of a Doc Comment are in `CODING-GUIDELINES.md`, chapter 7; the rest is in `AGENTS.md`:
chapter 2 (The API reference), chapter 3 (Documentation), chapter 4 ("The site", "CI") and
chapter 5 ("The changelog", "Releases"). The site's own rules are `site/AGENTS.md`, and its
specification is the organization's `site` capability in webcpporg/proposals.

## A library's page
1. Doc Comments for every public symbol, with the commands `CODING-GUIDELINES.md` chapter 7 allows.
2. The page's sections as `AGENTS.md` chapter 3 lists them; C++ only by include of an example or a tagged region.
3. Counts by the build's attributes (`{n-tests}` ...), never typed.
4. `b2 -a libs/<name>/doc` passes doc-check and MrDocs strict.

## The site
`b2 site` (preview) or `b2 site -sWEBCPP_SITE=release -sWEBCPP_SITE_VERSION=<version>`, then
`b2 site-serve`. The superproject's CI builds and publishes the preview; nothing is published by hand.

## A release
Only when the owner asks, following `AGENTS.md` chapter 5's numbered steps: `b2 check-release`,
`b2 whats-new` (the owner approves the highlights), `b2 -a dist`; the tag and the GitHub Release
are the owner's.
