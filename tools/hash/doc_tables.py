#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""The tables of webcpp::hash's guide, generated from its data (owner's documentation
requirements).

    python3 tools/hash/doc_tables.py --write [--library libs/hash]
    python3 tools/hash/doc_tables.py --check [--library libs/hash]

Reads, in the library's doc/: capabilities.json (which backend implements each public name, on
which targets, over which hmacs, with its constant time, and each function's default backend:
Task 14), guide.json (what the guide says of each name that no test produces: its use, its
security and where the world uses it, each with a source, and the rows of "Choose by use case"),
and, when it is there, measurements.json (each program's size per target and its throughput, a
reference measured once, on 2026-11-16, that decides nothing: the default backend is fixed, spec
4.1). A function row is keyed by its name and its form: a row with "form" (HKDF's "pieces") is
another form of the function its name names, rendered as "`hkdf_extract` over pieces", and shares
that function's facts of guide.json. It writes, in doc/:

- generated/compare-<chapter>.adoc: the comparison that opens each chapter, two tables with a
  row per public name: what it is (output, security, standard, status, the browser's
  WebCrypto), and how to choose it (from measurements.json, its throughput natively and its
  smallest program on Emscripten, then where it is used, each with its source, and when to
  choose it);
- generated/backends-<algorithm>.adoc: the backends of each algorithm, from the capability
  table (backend, the Jamfile line, targets, hmacs, constant time), and each function's default,
  with the template argument a call names another backend as, read from the header that declares
  the template (the library's include/);
- generated/choose.adoc: the decision table "Choose by use case", whose backend column is the
  capability table's;
- generated/measured.adoc: the includes of the data chapters, backends.adoc and
  measurements.adoc (this tool), performance.adoc (bench/collect.py) and allocation.adoc
  (bench/allocation_collect.py), each one that is there;
- backends.adoc: the capability table as the guide's data chapter shows it, with which functions
  set DIT around their calls and which do not (design D1 to D6 of the change
  data-independent-timing), from the table's chapters and kinds;
- measurements.adoc: measurements.json's tables, labelled as the dated reference they are;
- llms.txt: the guide's index for language models, installed beside the page.

--check renders the same files from the same data and fails, naming
`python3 tools/hash/doc_tables.py --write`, when one differs from what is committed, is
missing, or is left over; the doc build runs it (doc/Jamfile). It also fails when guide.json
lacks a public name of the capability table, names one it does not have, or a use case names
an example that example/ does not hold; when a row's form is not "pieces", is on a row whose
function the table does not have without a form, or two rows share a name and a form; when a
function of the capability table names a default that is not among its backends or outside the
order hash2, xkcp, blake3, sodium (design D33), or none (null) though a backend of that order has
it; when a family's tag (kind
digest, mac or kdf) names a default outside that order (design D34; null for a tag with none)
or one without its cell; when any default is a backend that only the asynchronous family takes,
a type has a default, or a row has an unknown kind; when a tag of digests or macs sits outside
its namespace's chapter; when the header a row names declares no template of it (or of its
family) with a Backend parameter; and when measurements.json's digest does not match its
content (a hand edit of the reference).
Nothing in the output depends on the time or the machine, so the files change only with their
data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
WRITE = 'python3 tools/hash/doc_tables.py --write'
LICENCE = ('// Copyright (c) 2026 WebCpp.org\n'
           '//\n'
           '// Distributed under the Boost Software License, Version 1.0. (See\n'
           '// accompanying file LICENSE_1_0.txt or copy at\n'
           '// https://www.boost.org/LICENSE_1_0.txt)\n')
# The chapters of the measured data, in the order the guide shows them, and what writes each:
# this tool writes the first two, from doc/capabilities.json and doc/measurements.json.
MEASURED_CHAPTERS = (
    ('backends.adoc', 'this tool, from doc/capabilities.json'),
    ('measurements.adoc', 'this tool, from doc/measurements.json'),
    ('performance.adoc', 'bench/collect.py'),
    ('allocation.adoc', 'bench/allocation_collect.py'),
)
OWN_CHAPTERS = ('backends.adoc', 'measurements.adoc')
TARGETS = ('native', 'wasip2', 'wasip3', 'emscripten')
# The chapters whose throughput is a rate over 1 MiB (the measured table's workloads).
RATE_CHAPTERS = ('digests', 'macs', 'non-cryptographic')
# The kinds of a family's tag (spec 2.15), and the backends that may be its default, in their order
# (design D34): the first that has the tag; never bearssl, openssl, botan or webcrypto. A
# function's default is of the same order (design D33).
FAMILY_KINDS = ('digest', 'mac', 'kdf')
FAMILY_DEFAULTS = ('hash2', 'xkcp', 'blake3', 'sodium')
# The chapters whose functions compute on a key, a password or a secret input, and so set DIT
# around each call: every row of them but a type, which is Boost.Hash2's by alias (the change
# data-independent-timing, design D1 and D3). The coverage tests read the same rule from the table.
KEYED_CHAPTERS = {'macs': 'MACs', 'kdfs': 'Key derivation', 'password_hashing': 'Password hashing'}
# How a call names a row of each kind: a tag through its family's template, a function by its
# name.
CALLED_AS = {'mac': 'mac<{}>', 'kdf': 'argon2<{}>', 'digest': 'digest_of<{}>'}
# The functions a keyed row's cell also holds, which the table lists under that row: bcrypt's
# verification, always keyed, listed after bcrypt.
ALSO_KEYED = {'bcrypt': 'bcrypt_verify'}
# The keyed calls of a row the keyed chapters do not hold, each with the row it is a call of: the
# keyed modes of a digest (design D1), keyed by their arguments (D4).
KEYED_CALLS = (
    ('digests::blake2b', '`digest_of<digests::blake2b>` and `hasher<digests::blake2b>` (`make`, '
     '`update`, `finish`) when the options carry a key'),
    ('blake3', 'the `blake3` class in its keyed, key-derivation and seeded keyed modes (a '
     'non-empty byte seed, a non-zero integer seed: BLAKE3\'s keyed hash): `keyed`, `derive_key`, '
     'those constructors, and `update`, `result`, `squeeze` and `reset` of such an object'),
)
APPLE_DIT = ('https://developer.apple.com/documentation/xcode/'
             'writing-arm64-code-for-apple-platforms'
             '#Enable-DIT-for-constant-time-cryptographic-operations')
# The chapter each namespace's tags belong in: a tag of macs is listed with the MACs.
NAMESPACE_CHAPTERS = {'digests::': 'digests', 'macs::': 'macs'}
# The templates a family's tag is the first template argument of, by its kind, each declared in
# the tag's header: the position of their Backend is read there.
FAMILY_TEMPLATES = {'digest': ('digest_of', 'hasher'), 'mac': ('mac',), 'kdf': ('argon2',)}
ORDINALS = ('first', 'second', 'third', 'fourth')
# How the guide spells each target in prose.
TARGET_NAMES = {'native': 'native', 'wasip2': 'wasip2', 'wasip3': 'wasip3',
                'emscripten': 'Emscripten'}


class Failure(Exception):
    """A fault of the data, which --write and --check both report."""


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise Failure(f'{path}: {error}') from error


def generated_header(sources: str) -> str:
    return f'{LICENCE}\n// Generated by tools/hash/doc_tables.py from {sources}: do not edit.\n'


def cell(text: str) -> str:
    """A table cell's text: a | would end the cell."""
    return text.replace('|', '{vbar}')


def link(text: str, url: str) -> str:
    return f'link:{url}[{text.replace("]", "&#93;")}]'


# The forms a function row may have besides its own: HKDF's overloads over byte_pieces.
FORMS = ('pieces',)

# A function row's key: its name and its form (None for the function's own row).
Key = tuple[str, Optional[str]]


def row_key(function: dict) -> Key:
    return function['name'], function.get('form')


def label(function: dict) -> str:
    """A row as prose names it without markup: `hkdf_extract`, or `hkdf_extract over pieces`."""
    name, form = row_key(function)
    return name if form is None else f'{name} over {form}'


def shown(function: dict, called: str | None = None) -> str:
    """A row as the guide names it in code: `` `hkdf_extract` ``, or `` `hkdf_extract` over
    pieces ``; `called` replaces the name inside the backticks (a tag through its family)."""
    name, form = row_key(function)
    text = f'`{called or name}`'
    return text if form is None else f'{text} over {form}'


class Data:
    """The capability table, the guide's facts and the measurements, joined."""

    def __init__(self, library: Path) -> None:
        self.library = library
        doc = library / 'doc'
        self.capabilities = load(doc / 'capabilities.json')
        self.guide = load(doc / 'guide.json')
        measured = doc / 'measurements.json'
        self.measurements = load(measured) if measured.is_file() else None
        self.backends = {b['name']: b for b in self.capabilities['backends']}
        self.functions: dict[Key, tuple[dict, dict]] = {}
        repeated = []
        for algorithm in self.capabilities['algorithms']:
            for function in algorithm['functions']:
                if row_key(function) in self.functions:
                    repeated.append(f'doc/capabilities.json has two rows {label(function)}')
                self.functions[row_key(function)] = (algorithm, function)
        if repeated:
            raise Failure('\n'.join(repeated))
        self.names = {name for name, _ in self.functions}
        self.check_forms()
        self.check_guide()
        self.check_defaults()
        self.check_chapters()
        self.check_digest()
        # The template argument each function's and each tag's call names its backend as.
        self.arguments = {key: self.backend_argument(function)
                          for key, (_, function) in self.functions.items()
                          if function['kind'] == 'function' or function['kind'] in FAMILY_KINDS}
        # The parameters a form's overload takes as byte_pieces, read from its header.
        self.form_parameters = {key: self.pieces_parameters(function)
                                for key, (_, function) in self.functions.items()
                                if 'form' in function}

    def pieces_parameters(self, function: dict) -> list[str]:
        """The names of the byte_pieces parameters of the function's overload over pieces, as
        input_key_material, read from the declarations in its header."""
        path = self.library / 'include' / function['header']
        try:
            text = path.read_text(encoding='utf-8')
        except OSError as error:
            raise Failure(f'{path}: {error}') from error
        code = re.sub(r'//[^\n]*|/\*.*?\*/', ' ', text, flags=re.DOTALL)
        found: list[str] = []
        for match in re.finditer(rf'(?<![\w:]){re.escape(function["name"])}\s*\(([^)]*)\)', code):
            names = re.findall(r'\bbyte_pieces\s+(\w+)', match.group(1))
            if names:
                found = names
                break
        if not found:
            raise Failure(f'{function["header"]} declares no {function["name"]} with a '
                          f'byte_pieces parameter (doc/capabilities.json, {label(function)})')
        return found

    def backend_argument(self, function: dict) -> str:
        """The words "as its <position> template argument", where a call names the backend,
        read from the header that declares the template (the function's own, or its family's
        templates), so that no sentence states a position the signature does not have."""
        names = FAMILY_TEMPLATES.get(function['kind'], (function['name'],))
        header = function['header']
        path = self.library / 'include' / header
        try:
            text = path.read_text(encoding='utf-8')
        except OSError as error:
            raise Failure(f'{path}: {error}') from error
        # (position, number of parameters) of the Backend in each declaration of each template.
        found = set()
        for name in names:
            places = {(i, len(parameters)) for parameters in template_parameters(text, name)
                      for i, parameter in enumerate(parameters)
                      if re.match(r'(?:class|typename)\s+Backend\b', parameter)}
            if not places:
                raise Failure(f'{header} declares no template {name} with a Backend parameter '
                              f'(doc/capabilities.json, {label(function)})')
            found |= places
        indices = {i for i, _ in found}
        if len(indices) != 1:
            raise Failure(f'{header}: {listed(list(names))} take the Backend at different '
                          f'positions (doc/capabilities.json, {label(function)})')
        (index,) = indices
        position = 'only' if all(count == 1 for _, count in found) else ORDINALS[index]
        return f'as its {position} template argument'

    def check_defaults(self) -> None:
        """A function (a template with a Backend parameter) names its default, a backend that
        has it, of the order hash2, xkcp, blake3, sodium (designs D33 and D34: never bearssl,
        openssl or botan), or none (null) exactly when no backend of the order has it (as kbkdf
        and bcrypt); a family's tag names one of the order that has its cell,
        or none (null): every default has its engine (ruling R84); no default is a backend only
        the asynchronous family takes (design D35); a type has none."""
        faults = []
        for _, function in self.functions.values():
            name = label(function)
            default = function.get('default')
            kind = function['kind']
            ordered = [b for b in FAMILY_DEFAULTS if b in function['backends']]
            if kind not in FAMILY_KINDS + ('function', 'type'):
                faults.append(f'doc/capabilities.json: {name} has the unknown kind {kind}')
            elif kind == 'type' and default is not None:
                faults.append(f'doc/capabilities.json: the type {name} has a default, {default}')
            elif default is not None and default in self.backends and \
                    self.backends[default].get('asynchronous_only'):
                faults.append(f'doc/capabilities.json: the {kind} {name} has the default '
                              f'{default}, which only the asynchronous family takes')
            elif kind == 'function' and default is None and ordered:
                faults.append(f'doc/capabilities.json: the function {name} has no default, '
                              f'though {ordered[0]}, a backend of the order, has it')
            elif kind == 'function' and default is not None and default not in FAMILY_DEFAULTS:
                faults.append(f'doc/capabilities.json: the function {name} has the default '
                              f'{default}, which is not one of {", ".join(FAMILY_DEFAULTS)}')
            elif kind == 'function' and default is not None and \
                    default not in function['backends']:
                faults.append(f'doc/capabilities.json: the function {name} has no default '
                              f'among its backends ({default})')
            elif kind in FAMILY_KINDS and default is not None and default not in FAMILY_DEFAULTS:
                faults.append(f'doc/capabilities.json: the tag {name} has the default {default}, '
                              f'which is not one of {", ".join(FAMILY_DEFAULTS)}')
            elif kind in FAMILY_KINDS and default is not None and \
                    default not in function['backends']:
                faults.append(f'doc/capabilities.json: the tag {name} has the default {default}, '
                              'which has no cell of it')
        if faults:
            raise Failure('\n'.join(faults))

    def check_chapters(self) -> None:
        """A tag of digests sits in the digests chapter, a tag of macs in the macs chapter, so
        that each chapter's table and llms.txt's section list every tag of its namespace."""
        faults = []
        for (name, _), (algorithm, _) in self.functions.items():
            for prefix, chapter in NAMESPACE_CHAPTERS.items():
                if name.startswith(prefix) and algorithm['chapter'] != chapter:
                    faults.append(f'doc/capabilities.json: the tag {name} is in the chapter '
                                  f'{algorithm["chapter"]}, not {chapter}')
        if faults:
            raise Failure('\n'.join(faults))

    def check_digest(self) -> None:
        """measurements.json's digest, the SHA-256 of its content without it: the reference is
        never edited by hand."""
        if self.measurements is None:
            return
        body = {k: v for k, v in self.measurements.items() if k != 'digest'}
        digest = 'sha256:' + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        if self.measurements.get('digest') != digest:
            raise Failure('doc/measurements.json: its digest does not match its content, which '
                          'was edited by hand; the reference measured on 2026-11-16 is kept as '
                          'measured')

    def check_forms(self) -> None:
        """A row's form is one of FORMS, on a function the table also has without a form."""
        faults = []
        for (name, form), _ in self.functions.items():
            if form is None:
                continue
            if form not in FORMS:
                faults.append(f'doc/capabilities.json: {name} has the unknown form {form}')
            elif (name, None) not in self.functions:
                faults.append(f'doc/capabilities.json: {name} over {form} is a form of no row '
                              f'{name}')
        if faults:
            raise Failure('\n'.join(faults))

    def check_guide(self) -> None:
        facts = self.guide['functions']
        missing = [name for name in sorted(self.names) if name not in facts]
        extra = [name for name in facts if name not in self.names]
        faults = [f'doc/guide.json has no entry for {name}, a function of '
                  f'doc/capabilities.json' for name in missing]
        faults += [f'doc/guide.json describes {name}, which doc/capabilities.json does not '
                   f'have' for name in extra]
        chapters = {a['chapter'] for a in self.capabilities['algorithms']}
        chapter_names = [c['chapter'] for c in self.guide['chapters']]
        faults += [f'doc/guide.json has no chapter {c} of doc/capabilities.json'
                   for c in sorted(chapters - set(chapter_names))]
        for case in self.guide['use_cases']:
            if (case['function'], None) not in self.functions:
                faults.append(f'doc/guide.json: the use case "{case["need"]}" names '
                              f'{case["function"]}, which doc/capabilities.json does not have')
            if not (self.library / 'example' / case['example']).is_file():
                faults.append(f'doc/guide.json: the use case "{case["need"]}" names '
                              f'example/{case["example"]}, which is not there')
        if faults:
            raise Failure('\n'.join(faults))

    def records(self, operation: str) -> list[dict]:
        if self.measurements is None:
            return []
        return [r for r in self.measurements['records'] if r['operation'] == operation]


def rate(ns: float) -> str:
    return f'{1e9 / ns:,.0f} MiB/s'


def duration(ns: float) -> str:
    if ns >= 1e6:
        return f'{ns / 1e6:.1f} ms'
    if ns >= 1e3:
        return f'{ns / 1e3:.2f} µs'
    return f'{ns:.0f} ns'


def fastest_native(data: Data, name: str, chapter: str) -> str:
    """The best native median of the function's records, over hmac_sha2_256 for a KDF, with
    its backend."""
    found = [r for r in data.records(name)
             if r['target'] == 'native' and r['throughput']
             and r['hmac'] in (None, 'hmac_sha2_256')]
    if not found:
        return '-'
    best = min(found, key=lambda r: r['throughput']['median_ns'])
    ns = best['throughput']['median_ns']
    value = rate(ns) if chapter in RATE_CHAPTERS else duration(ns)
    return f'{value} ({best["backend"]})'


def smallest_emscripten(data: Data, name: str) -> str:
    found = [r for r in data.records(name)
             if r['target'] == 'emscripten' and r['size_bytes']
             and r['hmac'] in (None, 'hmac_sha2_256')]
    if not found:
        return '-'
    best = min(found, key=lambda r: r['size_bytes'])
    return f'{best["size_bytes"]:,} bytes ({best["backend"]})'


def compare_table(data: Data, chapter: dict) -> str:
    key = chapter['chapter']
    m = data.measurements
    measured = m is not None
    out = [generated_header('doc/capabilities.json, doc/guide.json and doc/measurements.json'),
           '']
    # Two tables, what each function is and how to choose it, each led by the name: one of all
    # their columns would be a matrix (tools/doc/postprocess.mjs), which scrolls in its box.
    facts_columns = ['Name', 'Output', 'Security', 'Standard', 'Status',
                     'In the browser (WebCrypto)']
    choice_columns = ['Name'] + (['Fastest natively', 'Smallest on Emscripten'] if measured
                                 else []) + ['Where it is used', 'Choose it when']
    facts_rows: list[list[str]] = []
    choice_rows: list[list[str]] = []
    for algorithm in data.capabilities['algorithms']:
        if algorithm['chapter'] != key:
            continue
        for function in algorithm['functions']:
            if 'form' in function:
                continue  # one row per public name: its forms share its facts
            name = function['name']
            facts = data.guide['functions'][name]
            uses = '; '.join(link(cell(u['text']), u['source']) for u in facts['uses'])
            named = f'<<{facts["anchor"]},`{name}`>>'
            facts_rows.append([named, facts['output'], facts['security'],
                               facts.get('standard', algorithm['standard']), facts['status'],
                               facts['webcrypto'] or 'no'])
            choice_rows.append([named] + ([fastest_native(data, name, key),
                                           smallest_emscripten(data, name)] if measured
                                          else []) + [uses, facts['choose']])
    tables = ((f'[#{chapter["anchor"]}-compare]', f'What each of "{chapter["title"]}" is',
               ['2', '1', '3', '2', '1', '2'], facts_columns, facts_rows),
              (f'[#{chapter["anchor"]}-choose]', f'How to choose among "{chapter["title"]}"',
               ['2'] + (['2', '2'] if measured else []) + ['4', '4'], choice_columns,
               choice_rows))
    for anchor, title, widths, columns, rows in tables:
        out.append(anchor)
        out.append(f'.{title}')
        out.append(f'[cols="{",".join(widths)}",options="header"]')
        out.append('|===')
        out.append(' '.join(f'| {c}' for c in columns))
        for row in rows:
            out.append('')
            out.extend(f'| {cell(value)}' if not value.startswith('link:') and '<<' not in value
                       else f'| {value}' for value in row)
        out.append('|===')
        out.append('')
    if m is not None:
        out.append(f'The measured columns are doc/measurements.json\'s, a reference measured '
                   f'on {m["date"]} on {m["machine"]["cpu"]} that decides nothing: the native '
                   'throughput over 1 MiB, or the time of one derivation over `hmac_sha2_256`, '
                   'of the fastest backend, and the smallest Emscripten program that calls the '
                   'function; <<hash-measurements>> has every backend on every target.' +
                   (' The data was measured on a loaded, shared machine, so close figures may '
                    'swap at the next measurement.' if m.get('loaded') else ''))
    else:
        out.append('The measured columns, throughput natively and the size of a program on '
                   'Emscripten, come from doc/measurements.json, which this build of the guide '
                   'does not have yet.')
    out.append('')
    return '\n'.join(out)


def backend_targets(data: Data, backend: str) -> str:
    return ', '.join(data.backends[backend]['targets'])


def template_parameters(text: str, name: str) -> list[list[str]]:
    """The template parameter lists of each declaration of the template `name` (a function or a
    class) in a header's text, its comments removed: each list split at its top-level commas."""
    code = re.sub(r'//[^\n]*|/\*.*?\*/', ' ', text, flags=re.DOTALL)
    found = []
    for match in re.finditer(r'\btemplate\s*<', code):
        depth, end = 1, match.end()
        while depth and end < len(code):
            depth += {'<': 1, '>': -1}.get(code[end], 0)
            end += 1
        head = re.match(r'[^;{(]*', code[end:])
        if head is None or not re.search(rf'(?<![\w:]){re.escape(name)}\s*$', head.group(0)):
            continue
        parameters, depth, start = [], 0, match.end()
        for i in range(match.end(), end - 1):
            depth += {'<': 1, '(': 1, '>': -1, ')': -1}.get(code[i], 0)
            if code[i] == ',' and depth == 0:
                parameters.append(code[start:i].strip())
                start = i + 1
        parameters.append(code[start:end - 1].strip())
        found.append(parameters)
    return found


def listed(names: list[str]) -> str:
    """Names as prose lists them: a, b and c."""
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + f' and {names[-1]}'


def spelled_targets(data: Data, backend: str) -> str:
    """A backend's targets as the guide's prose spells them, as "native and Emscripten"."""
    return listed([TARGET_NAMES[t] if t in TARGET_NAMES else t
                   for t in data.backends[backend]['targets']])


def source_bullets(lead: str, sources: list[str]) -> list[str]:
    """One bullet led by `lead`: its one source after it, or its sources under it."""
    if len(sources) == 1:
        return [f'* {lead} {sources[0]}']
    return [f'* {lead}'] + [f'** {source}' for source in sources]


ASYNCHRONOUS_ONLY = 'asynchronous family only'


def asynchronous_only(data: Data, backend: str) -> bool:
    """Whether only the asynchronous family takes the backend (backends::webcrypto)."""
    return bool(data.backends[backend].get('asynchronous_only'))


EXCEPTIONS_ONLY = 'with exceptions only'


def exceptions_only(data: Data, backend: str) -> bool:
    """Whether a build without exceptions cannot have the backend (backends::botan)."""
    return bool(data.backends[backend].get('exceptions_only'))


def backend_notes(data: Data, backend: str) -> list[str]:
    """What a backend's name is followed by: that only the asynchronous family takes it, that only
    a build with exceptions has it."""
    notes = []
    if asynchronous_only(data, backend):
        notes.append(ASYNCHRONOUS_ONLY)
    if exceptions_only(data, backend):
        notes.append(EXCEPTIONS_ONLY)
    return notes


def llms_note(data: Data, backend: str) -> str:
    """backend_note in llms.txt's form, after a comma."""
    return ''.join(f', {note}' for note in backend_notes(data, backend))


def backend_note(data: Data, backend: str) -> str:
    """What follows a backend's name in a table: that only the asynchronous family takes it, or
    that only a build with exceptions has it."""
    return ''.join(f' ({note})' for note in backend_notes(data, backend))


def partial_text(held: dict) -> str:
    """What a partial cell refuses, after its backend's name; nothing for a whole cell."""
    partial = held.get('partial')
    return f' (partial: {cell(partial)})' if partial else ''


def backend_text(data: Data, backend: str, held: dict) -> str:
    """A cell's backend, with what it refuses when it is partial, and whether only the
    asynchronous family takes it."""
    return f'`{backend}`{backend_note(data, backend)}{partial_text(held)}'


def hmacs_text(hmacs: list[str] | None) -> str:
    if hmacs is None:
        return '-'
    return ', '.join('any other Hash2 hash (`hmac<H>`)' if h == 'other' else f'`{h}`'
                     for h in hmacs)


def backends_table(data: Data, algorithm: dict) -> str:
    out = [generated_header('doc/capabilities.json'), '']
    out.append(f'[#hash-backends-of-{algorithm["name"].replace("_", "-")}]')
    names = list(dict.fromkeys(f['name'] for f in algorithm['functions']))
    title = ', '.join(f'`{n}`' for n in names) if len(names) <= 3 else \
        f'`{names[0]}` to `{names[-1]}`, {len(names)} names'
    out.append(f'.Who implements {title} ({algorithm["standard"]})')
    out.append('[cols="2,1,2,2,3,1",options="header"]')
    out.append('|===')
    out.append('| Function | Backend | The program\'s Jamfile names | Targets | Hmacs '
               '| Constant time')
    for function in algorithm['functions']:
        for backend, held in function['backends'].items():
            out.append('')
            out.append(f'| {shown(function)}')
            out.append(f'| {backend_text(data, backend, held)}')
            out.append(f'| `{data.backends[backend]["jamfile"]}`')
            out.append(f'| {backend_targets(data, backend)}')
            out.append(f'| {hmacs_text(held["hmacs"])}')
            out.append(f'| {held["constant_time"]["value"]}')
    out.append('|===')
    out.append('')
    sources: dict[str, list[str]] = {}
    for function in algorithm['functions']:
        for backend, held in function['backends'].items():
            known = sources.setdefault(backend, [])
            if held['constant_time']['source'] not in known:
                known.append(held['constant_time']['source'])
    out.append('What each backend states on constant time, as the capability table read it:')
    out.append('')
    for backend in sorted(sources):
        out.extend(source_bullets(f'`{backend}`:', [cell(s) for s in sorted(sources[backend])]))
    out.append('')
    defaults = [(row_key(f), f['default']) for f in algorithm['functions'] if f['default']]
    # A family's tag, and a function without a default (design D34), each say how its default
    # stands.
    families = [f for f in algorithm['functions']
                if f['kind'] in FAMILY_KINDS or (f['kind'] == 'function' and f['default'] is None)]
    for function in families:
        if function['default'] is None:
            out.append(f'{shown(function)} has no default backend: the call names one of its '
                       f'backends, {data.arguments[row_key(function)]} '
                       '(<<hash-default-backend>>).')
            out.append('')
    if not defaults:
        # Types alone take no backend; a family's tag without a default has said so above.
        if not families:
            names = sorted({b for f in algorithm['functions'] for b in f['backends']})
            out.append(f'One backend, {", ".join(f"`{n}`" for n in names)}: the types take no '
                       'backend.')
            out.append('')
        return '\n'.join(out)
    # One sentence per default and set of other backends, so that each names, as the backends a
    # call may name instead, those of its own functions alone.
    by_backend: dict[tuple[str, tuple[str, ...], str], list[str]] = {}
    for key, default in defaults:
        # The backends a call may name instead: those of this function, not of the algorithm's
        # others, and never one only the asynchronous family takes.
        function = data.functions[key][1]
        others = tuple(sorted(b for b in set(function['backends']) - {default}
                              if not asynchronous_only(data, b)))
        by_backend.setdefault((default, others, data.arguments[key]), []).append(shown(function))
    used = {b for f in algorithm['functions'] for b in f['backends']}
    for (default, others, argument), names in by_backend.items():
        named = names[0] if len(names) == 1 else \
            ', '.join(names[:-1]) + f' and {names[-1]}'
        tail = (f'; {", ".join(f"`{b}`" for b in others)} only where the call names it, '
                f'{argument}') if others else ''
        out.append(f'The default of {named}: `{default}` on every target, whatever the program '
                   f'links{tail} (<<hash-default-backend>>).')
        out.append('')
    for backend in sorted(b for b in used if asynchronous_only(data, b)):
        out.append(f'`{backend}` serves the asynchronous family alone, on '
                   f'{spelled_targets(data, backend)}, where the type of its asynchronous call '
                   'names it (<<hash-async-webcrypto>>).')
        out.append('')
    return '\n'.join(out)


def choose_table(data: Data) -> str:
    out = [generated_header('doc/guide.json and doc/capabilities.json'), '']
    out.append('[#hash-choose-table]')
    out.append('[cols="3,3,2,2,2",options="header"]')
    out.append('|===')
    out.append('| I need to ... | Use | Its backends: the Jamfile names | Backend '
               '| Example')
    for case in data.guide['use_cases']:
        _, function = data.functions[(case['function'], None)]
        jamfiles = ', '.join(f'`{b}`{backend_note(data, b)}: `{data.backends[b]["jamfile"]}`'
                             for b in function['backends'])
        out.append('')
        out.append(f'| {cell(case["need"])}')
        out.append(f'| <<{case["anchor"]},{cell(case["use"])}>>')
        out.append(f'| {jamfiles}')
        out.append(f'| {cell(case["backend"])}')
        out.append(f'| `example/{case["example"]}`')
    out.append('|===')
    out.append('')
    return '\n'.join(out)


def rendered_chapters(data: Data) -> set[str]:
    """The data chapters this tool renders: backends.adoc always, measurements.adoc with its
    data."""
    return {'backends.adoc'} | ({'measurements.adoc'} if data.measurements is not None else set())


def measured_includes(data: Data) -> str:
    out = [generated_header('the data chapters present in doc/'), '']
    missing = []
    for name, tool in MEASURED_CHAPTERS:
        if name in rendered_chapters(data) or (name not in OWN_CHAPTERS and
                                               (data.library / 'doc' / name).is_file()):
            out.append(f'include::../{name}[]')
            out.append('')
        else:
            missing.append(f'`doc/{name}` ({tool})')
    if missing:
        out.append('[NOTE]')
        out.append('====')
        out.append('This build of the guide does not have ' + ', '.join(missing) +
                   ' yet: the matrices they hold join the guide here once their data is '
                   'committed.')
        out.append('====')
        out.append('')
    return '\n'.join(out)


def function_defaults(data: Data) -> str:
    """The defaults of the functions with a Backend parameter, as the capability table names
    them: one clause per default, per backend a call may name instead (none, one, or several,
    never one only the asynchronous family takes) and per template argument the call names it as
    (the header's), and one for the functions without a default."""
    clauses: dict[tuple[str | None, str, str], list[str]] = {}
    for key, (_, function) in data.functions.items():
        if function['kind'] != 'function':
            continue
        default = function['default']
        others = sorted(b for b in function['backends']
                        if b != default and not asynchronous_only(data, b))
        if default is None:
            instead = (f'backends::{others[0]}' if len(others) == 1
                       else 'one of its backends')
        elif not others:
            instead = ''
        elif len(others) == 1:
            instead = f'backends::{others[0]}'
        else:
            instead = 'another of its backends'
        clauses.setdefault((default, instead, data.arguments[key] if instead else ''),
                           []).append(label(function))
    sentences = []
    for (default, instead, argument), names in clauses.items():
        many = len(names) > 1
        if default is None:
            sentences.append(f'{listed(names)} {"have" if many else "has"} no default backend, '
                             f'and the call names {instead} {argument}')
        elif not instead:
            sentences.append(f'{listed(names)} {"run" if many else "runs"} on '
                             f'backends::{default} alone')
        else:
            sentences.append(f'{listed(names)} {"run" if many else "runs"} on '
                             f'backends::{default} unless the call names {instead} '
                             f'{argument}')
    return f'By default, {"; ".join(sentences)}.' if sentences else ''


def llms_txt(data: Data) -> str:
    page = data.guide['page']
    lines = ['# webcpp::hash', '',
             '> Hashing and key derivation for C++20 on every target webcpp has (native, '
             'wasip2, wasip3, Emscripten): Boost.Hash2\'s digests and HMAC, Keccak-256, BLAKE3, '
             'HKDF, PBKDF2, Argon2id, scrypt and the KDFs of NIST SP 800-108, SP 800-56C and '
             'ANSI X9.63 over C backends. Every synchronous function returns '
             'boost::system::result and allocates nothing in webcpp\'s own code; async.hpp gives '
             'the slow ones and the ones WebCrypto has an asynchronous form over webcpp::asio, '
             'and backends::webcrypto, the '
             'browser\'s WebCrypto, serves that form alone. A program links /webcpp/hash//hash '
             'and the library of each backend it uses. ' + function_defaults(data) +
             ' The families digest_of, hasher, mac and argon2 take a tag of digests, macs or '
             'kdfs and a backend, by default the first of ' +
             listed([f'backends::{b}' for b in FAMILY_DEFAULTS]) + ' that has the tag.', '',
             'Primitives only: protocol steps (BIP39, hash160, EIP-55, Nostr ids, NIP-44) '
             'are what a domain library builds from these functions; the guide shows them as '
             'examples, never as this library\'s API.', '',
             'Timing: every MAC, key derivation and password hash, and BLAKE2b\'s and BLAKE3\'s '
             'keyed modes, set DIT (data-independent timing) around each call on 64-bit ARM under '
             'Apple\'s systems and Linux where the CPU has FEAT_DIT, on every synchronous backend, '
             'and leave the thread\'s DIT as they found it; '
             'unkeyed digests and Boost.Hash2\'s hmac<H> by alias do not, so an HMAC with DIT is '
             f'mac<macs::hmac<D>>. [Section]({page}#hash-backends-dit)', '',
             f'- [The guide]({page}): every chapter, example and table',
             f'- [Choose by use case]({page}#hash-choose): a decision table, need to '
             'function, backend and example', '']
    for chapter in data.guide['chapters']:
        lines.append(f'## {chapter["title"]}')
        lines.append('')
        lines.append(f'{chapter["summary"]} [{chapter["title"]}]({page}#{chapter["anchor"]})')
        lines.append('')
        for algorithm in data.capabilities['algorithms']:
            if algorithm['chapter'] != chapter['chapter']:
                continue
            for function in algorithm['functions']:
                facts = data.guide['functions'][function['name']]
                backends = ', '.join(f'{b}{llms_note(data, b)} ({data.backends[b]["jamfile"]}; '
                                     f'{backend_targets(data, b)})'
                                     for b in function['backends'])
                standard = facts.get('standard', algorithm['standard'])
                if 'form' in function:
                    # A form shares its function's facts: say only what differs.
                    pieces = listed(data.form_parameters[row_key(function)])
                    lines.append(f'- webcpp::hash::{label(function)} '
                                 f'(<{function["header"]}>, {standard}): '
                                 f'{function["name"]} with its {pieces} as byte_pieces, read '
                                 'one after another as if concatenated, with no cap. '
                                 f'Backends: {backends}. [Section]({page}#{facts["anchor"]})')
                    continue
                lines.append(f'- webcpp::hash::{function["name"]} '
                             f'(<{function["header"]}>, {standard}): '
                             f'{facts["summary"]} Status: {facts["status"]}. '
                             f'Choose it: {facts["choose"]} Backends: {backends}. '
                             f'[Section]({page}#{facts["anchor"]})')
        lines.append('')
    lines.append('## Choose by use case')
    lines.append('')
    for case in data.guide['use_cases']:
        lines.append(f'- I need to {case["need"]}: {case["use"]}; backend: {case["backend"]}; '
                     f'example libs/hash/example/{case["example"]}. '
                     f'[Section]({page}#{case["anchor"]})')
    lines.append('')
    lines.append('## Data')
    lines.append('')
    lines.append('- doc/capabilities.json: which backend implements each function, on which '
                 'targets, over which hmacs, and its constant time')
    lines.append('- doc/capabilities.json also names each function\'s default backend')
    lines.append('- doc/measurements.json: each backend\'s program size per target and its '
                 'throughput, a reference measured on 2026-11-16 that decides nothing')
    lines.append('')
    return '\n'.join(lines)


def keyed_rows(data: Data) -> tuple[dict[str, list[str]], list[str]]:
    """The rows that set DIT, by chapter, each as a call names it (a tag through its family), in
    code (`` `mac<macs::kmac_128>` ``, `` `hkdf` over pieces ``), and the names of the types of the
    keyed chapters that do not (the aliases), in the table's order."""
    keyed: dict[str, list[str]] = {}
    aliases: list[str] = []
    for algorithm in data.capabilities['algorithms']:
        if algorithm['chapter'] not in KEYED_CHAPTERS:
            continue
        for function in algorithm['functions']:
            if function['kind'] == 'type':
                aliases.append(function['name'])
            else:
                called = CALLED_AS.get(function['kind'], '{}').format(function['name'])
                keyed.setdefault(algorithm['chapter'], []).append(shown(function, called))
                if function['name'] in ALSO_KEYED and 'form' not in function:
                    keyed[algorithm['chapter']].append(f'`{ALSO_KEYED[function["name"]]}`')
    return keyed, aliases


def dit_section(data: Data) -> list[str]:
    """Which functions set DIT around their calls and which do not, and why: the keyed chapters'
    rows from the table, the keyed calls of other rows, and the rest."""
    keyed, aliases = keyed_rows(data)
    lines = [
        '[#hash-backends-dit]', '=== Data-independent timing (DIT)', '',
        '64-bit ARM\'s DIT (data-independent timing) bit, PSTATE.DIT, makes the instructions Arm '
        'lists take a time independent of their data, and Apple requires it of constant-time code '
        f'({link("Apple, enable DIT for constant-time cryptographic operations", APPLE_DIT)}). '
        'None of the libraries hash calls sets it, so hash does: every function that computes '
        'on a key, a password or a key derivation\'s secret input runs its whole body inside '
        '`detail::timing_guard`, on every synchronous backend, which on 64-bit ARM under '
        'macOS, iOS, Linux and Android, where the CPU has FEAT_DIT (`hw.optional.arm.FEAT_DIT` '
        'on Apple\'s systems, `HWCAP_DIT` on Linux), sets DIT for the call and returns with '
        'the thread\'s DIT as it found it: clear when it was clear, set when the program set '
        'it itself (Apple\'s `timingsafe_enable_if_supported`) or an outer call did. An error '
        'and an exception leave it as found too, and DIT is a thread\'s own state, so a call '
        'never changes another thread\'s. A program does nothing. Elsewhere the guard executes '
        'no instruction: on x86 the counterpart, DOITM, is a register only the kernel writes; '
        'on WebAssembly the engine decides; on Windows on ARM64 no documented way to ask '
        'whether the CPU has FEAT_DIT was found, and DIT\'s instructions trap on a CPU without '
        'it.', '',
        'The functions that set DIT, on every synchronous backend of their cells:', '']
    for chapter, names in keyed.items():
        lines.append(f'* {KEYED_CHAPTERS[chapter]}: {listed(names)}.')
    calls = [text for row, text in KEYED_CALLS if row in data.names]
    if calls:
        lines.append('* Keyed by their arguments: ' + '; '.join(calls) + '. Called without a '
                     'key, they hold a disengaged guard, which reads its flag and does nothing '
                     'else.')
    lines += [
        '', 'The functions that do not:', '',
        '* Unkeyed digests and extendable-output functions, through `digest_of`, `hasher` and '
        'the types of Boost.Hash2\'s form (`keccak_256`, `blake3` in its plain mode): their input '
        'is not a secret by their contract (a program that derives from a secret uses a MAC or a '
        'key derivation, which set DIT); they are the streaming case, where a guard per `update` '
        'of every checksum would cost a real fraction of a short chunk for no secret; and the '
        'same algorithm is also Boost.Hash2\'s own type by alias, which hash cannot guard, so '
        'that guarding one spelling would make the protection depend on the spelling.']
    if aliases:
        lines.append(
            '* Boost.Hash2\'s types by alias, ' + listed([f'`{name}`' for name in aliases]) +
            ': they are Boost.Hash2\'s own classes, and a guard inside them would need a type of '
            'hash\'s in place of the alias. An HMAC with DIT is `mac<macs::hmac<D>>`, which runs '
            'the same Boost.Hash2 code on `backends::hash2` inside its guard, and a SipHash with '
            'DIT is `mac<macs::siphash_2_4>`; a program that calls `hmac<H>` or `siphash_64` '
            'directly sets DIT itself. HKDF and PBKDF2 on `backends::hash2` run '
            'Boost.Hash2\'s `hmac` inside their own guard.')
    lines += [
        '* The initiating functions of `async.hpp`: they check sizes and post, and the '
        'synchronous function they call sets DIT on the thread that computes, a thread of the '
        'work executor\'s pool for a heavy function, the caller\'s for a cheap one '
        '(<<hash-async>>). On `backends::webcrypto` the browser\'s JavaScript engine computes, '
        'and nothing is added.', '',
        'A coverage test per backend (`test/timing_coverage_<backend>_test.cpp`) reads this '
        'table and fails when a keyed cell of its backend has no call, when a call enters no '
        'guard, when the first guard it enters is not its own function\'s, or when it leaves DIT '
        'otherwise than it found it, from a thread with DIT clear and from one that set it; it '
        'checks that the unkeyed functions enter none. `test/timing_during_test.cpp` reads DIT '
        'while HKDF, PBKDF2 and `mac` compute, through a hash that records it at each update, '
        'on the calling thread and on an `async_pbkdf2` pool\'s. The guard '
        'is hash\'s own copy of '
        'webcpp::crypto\'s, which depends on hash: a change to one is a change to the other, and '
        'crypto\'s test `timing_hash_interop_test` runs both nested, in either order.', '']
    if (data.library / 'doc' / 'performance.adoc').is_file():
        lines += ['What the guard adds to a call, measured from a release build, is in '
                  '<<hash-performance-timing>>.', '']
    return lines


def chapter_header(title: str, anchor: str, sources: str) -> list[str]:
    return [generated_header(sources), f'[#{anchor}]', f'== {title}', '']


def backends_chapter(data: Data) -> str:
    """The capability table as the guide's data chapter shows it: the backends; per chapter,
    each function on each backend, its hmacs, its constant time and its targets; each
    function's default; and what each upstream states on constant time."""
    table = data.capabilities
    names = [b['name'] for b in table['backends']]
    lines = chapter_header('Backends', 'hash-backends', 'doc/capabilities.json')
    lines += ['Which backend implements each function, over which hmacs, on which targets, and '
              'what upstream', 'states about its constant time. The backends:', '',
              '[cols="1,3,1,2,2,2",options="header"]', '|===',
              '| Backend | Library | Licence | Jamfile | Targets | Called by']
    for b in table['backends']:
        called = (f'{ASYNCHRONOUS_ONLY} (async.hpp)' if b.get('asynchronous_only')
                  else 'every function of its cells')
        if b.get('exceptions_only'):
            called += f', {EXCEPTIONS_ONLY}'
        lines += ['', f'| {b["name"]}', f'| {b["library"]}', f'| {b["licence"]}',
                  f'| `{b["jamfile"]}`', f'| {", ".join(b["targets"])}', f'| {called}']
    lines += ['|===', '']
    chapters: dict[str, list[dict]] = {}
    for algorithm in table['algorithms']:
        chapters.setdefault(algorithm['chapter'], []).append(algorithm)
    for chapter, algorithms in chapters.items():
        lines += [f'=== {chapter.replace("_", " ").capitalize()}', '',
                  '[cols="2,1,3,1,4",options="header"]', '|===',
                  '| Function | Backend | Hmacs | Constant time | Targets']
        for algorithm in algorithms:
            for function in algorithm['functions']:
                for name in names:
                    c = function['backends'].get(name)
                    if c is None:
                        continue
                    hmacs = ', '.join(c['hmacs']) if c['hmacs'] else '-'
                    targets = ', '.join(data.backends[name]['targets'])
                    lines += ['', f'| {label(function)}',
                              f'| {name}{backend_note(data, name)}{partial_text(c)}',
                              f'| {hmacs}',
                              f'| {c["constant_time"]["value"]}', f'| {targets}']
        lines += ['|===', '']
    lines += dit_section(data)
    lines += ['=== The default backends', '',
              'The backend a call that names none uses, on every target, whatever the program '
              'links (<<hash-default-backend>>):', '',
              '[cols="2,1",options="header"]', '|===', '| Function | Default']
    for _, function in data.functions.values():
        if function['default'] is not None:
            lines += ['', f'| {label(function)}', f'| {function["default"]}']
        elif function['kind'] in FAMILY_KINDS:
            lines += ['', f'| {label(function)}', '| none: the call names its backend']
    lines += ['|===', '', '=== Constant time', '',
              'What each backend\'s upstream states, and where:', '']
    # One bullet per backend and value, in the capability table's order of backends, with each
    # distinct source of it once.
    seen: dict[tuple[str, str], list[str]] = {}
    for _, function in data.functions.values():
        for name, c in function['backends'].items():
            known = seen.setdefault((name, c['constant_time']['value']), [])
            if c['constant_time']['source'] not in known:
                known.append(c['constant_time']['source'])
    order = list(data.backends)
    for (name, value), sources in sorted(seen.items(), key=lambda item: order.index(item[0][0])):
        lines.extend(source_bullets(f'{name}: {value}.', sources))
    return '\n'.join(lines) + '\n'


def measured_time(ns: float) -> str:
    if ns >= 1e6:
        return f'{ns / 1e6:.2f} ms'
    if ns >= 1e3:
        return f'{ns / 1e3:.2f} µs'
    return f'{ns:.0f} ns'


def measured_speed(data: Data, operation: str, t: dict) -> str:
    algorithm, _ = data.functions[(operation, None)]
    if algorithm['chapter'] in RATE_CHAPTERS:
        def per_second(ns: float) -> str:
            return f'{1e9 / ns:.0f}'
        return (f'{per_second(t["median_ns"])} MiB/s ({per_second(t["max_ns"])} to '
                f'{per_second(t["min_ns"])})')
    return (f'{measured_time(t["median_ns"])} ({measured_time(t["min_ns"])} to '
            f'{measured_time(t["max_ns"])})')


def measurements_chapter(data: Data) -> str:
    """measurements.json's tables, the size and the throughput of each cell on each target,
    under the label of the dated reference they are."""
    m = data.measurements
    assert m is not None
    machine = m['machine']
    lines = chapter_header('Measured size and throughput', 'hash-measurements',
                           'doc/measurements.json')
    lines += [f'A reference measured once, on {m["date"]}, that decides nothing: what each '
              'backend cost a program on each',
              'target, in bytes and in time, when webcpp measured it. Every key derivation\'s '
              'default is',
              '`backends::hash2`, Argon2id\'s and scrypt\'s `backends::sodium`, whatever these '
              'tables say',
              '(<<hash-default-backend>>): `hash2` is the only backend that covers every hmac, '
              'operation and',
              'target; it is header-only, so a program carries only what it calls and shares the '
              'SHA code it',
              'already uses; and the differences measured here for HKDF are nanoseconds natively '
              'and a few KB',
              'of an isolated program on WebAssembly. No lane measures these figures again, and '
              'a move of a',
              'C library\'s pin leaves them as they were.', '',
              f'Measured on {m["date"]} on {machine["cpu"]}, {machine["cores"]} cores, '
              f'{machine["memory_gib"]} GiB, {machine["os"]};',
              f'WebAssembly under {m["runtimes"]["wasip2"]} (wasip2, wasip3) and '
              f'{m["runtimes"]["emscripten"]} (Emscripten).',
              'Compilers: ' + '; '.join(f'{t}: {c}' for t, c in m['toolchains'].items())
              + '.', '']
    native = m.get('native_toolchain') or {}
    if native:
        lines += [f'The native rows hold for {native["compiler"]} on {native["os"]} '
                  f'{native["processor"]}, stripped with {Path(native["strip"]).name}; another',
                  'native toolchain gives other native sizes and times.', '']
    if m['loaded']:
        load = m['load_average_before_after']
        lines += ['WARNING: the machine was shared and loaded while this was measured (many '
                  'builds ran at once;',
                  '1, 5 and 15 minute load averages '
                  + '/'.join(f'{x:.0f}' for x in load[0]) + ' before and '
                  + '/'.join(f'{x:.0f}' for x in load[1]) + f' after, on {machine["cores"]} '
                  'cores).',
                  'Every time is a median with its spread; read the spread, not a single '
                  'figure. Sizes do not',
                  'depend on the load.', '']
    lines += [f'Sizes: {m["rules"]["size"]}. Throughput: {m["rules"]["throughput"]}.', '']
    by_cell: dict[tuple, dict[str, dict]] = {}
    for r in m['records']:
        by_cell.setdefault((r['operation'], r['hmac'], r['backend']), {})[r['target']] = r
    lines += ['=== Size of a program, in bytes', '',
              '[cols="3,2,1,1,1,1,1",options="header"]', '|===',
              '| Function | Hmac | Backend | native | wasip2 | wasip3 | emscripten']
    for (operation, hmac, backend), targets in by_cell.items():
        lines += ['', f'| {operation}', f'| {hmac or "-"}', f'| {backend}']
        lines += [f'| {targets[t]["size_bytes"]}' if t in targets else '| -' for t in TARGETS]
    lines += ['|===', '', '=== Throughput', '',
              'A hash or MAC in MiB per second over 1 MiB, a key derivation in time per '
              'derivation: the median, then',
              'the range of its runs, the lower figure first. Per function, the workload:', '']
    lines += [f'* {f}: {w}.' for f, w in m['workloads'].items()]
    lines += ['', '[cols="3,2,1,3,3,3,3",options="header"]', '|===',
              '| Function | Hmac | Backend | native | wasip2 | wasip3 | emscripten']
    for (operation, hmac, backend), targets in by_cell.items():
        lines += ['', f'| {operation}', f'| {hmac or "-"}', f'| {backend}']
        for t in TARGETS:
            r = targets.get(t)
            if r is None:
                lines.append('| -')
            elif r['throughput'] is None:
                lines.append(f'| not measured: {r["throughput_absent"]}')
            else:
                lines.append(f'| {measured_speed(data, operation, r["throughput"])}')
    lines += ['|===', '']
    return '\n'.join(lines)


def render(data: Data) -> dict[str, str]:
    """Every generated file, by its path relative to the library's doc/."""
    files: dict[str, str] = {}
    for chapter in data.guide['chapters']:
        files[f'generated/compare-{chapter["chapter"].replace("_", "-")}.adoc'] = \
            compare_table(data, chapter)
    for algorithm in data.capabilities['algorithms']:
        files[f'generated/backends-{algorithm["name"].replace("_", "-")}.adoc'] = \
            backends_table(data, algorithm)
    files['generated/choose.adoc'] = choose_table(data)
    files['generated/measured.adoc'] = measured_includes(data)
    files['backends.adoc'] = backends_chapter(data)
    if data.measurements is not None:
        files['measurements.adoc'] = measurements_chapter(data)
    files['llms.txt'] = llms_txt(data)
    return files


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    parser.add_argument('--library', default=str(ROOT / 'libs' / 'hash'))
    arguments = parser.parse_args(argv)
    library = Path(arguments.library)
    doc = library / 'doc'
    try:
        files = render(Data(library))
    except Failure as failure:
        print(f'doc_tables.py: {failure}', file=sys.stderr)
        return 1
    present = {str(p.relative_to(doc)) for p in (doc / 'generated').glob('*.adoc')}
    present |= {name for name in OWN_CHAPTERS if (doc / name).is_file()}
    if arguments.write:
        (doc / 'generated').mkdir(exist_ok=True)
        for name in present - set(files):
            (doc / name).unlink()
        for name, text in files.items():
            (doc / name).write_text(text, encoding='utf-8')
        return 0
    faults = []
    for name, text in files.items():
        path = doc / name
        if not path.is_file():
            faults.append(f'doc/{name} is missing')
        elif path.read_text(encoding='utf-8') != text:
            faults.append(f'doc/{name} differs from what its data renders')
    faults += [f'doc/{name} is left over: no data renders it'
               for name in sorted(present - set(files))]
    for fault in faults:
        print(f'doc_tables.py: {fault}; run `{WRITE}`', file=sys.stderr)
    return 1 if faults else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
