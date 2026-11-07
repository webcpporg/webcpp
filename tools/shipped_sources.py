#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Verify shipped imports before treating their original style as third-party text."""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def checked_file(base: Path, name: str) -> Path:
    """Resolve one inventory entry without following a source symlink."""
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe shipped-source path: {name}")
    path = base
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"unsafe shipped-source path: {name}")
    if not path.resolve().is_relative_to(base.resolve()):
        raise ValueError(f"shipped-source path escapes library: {name}")
    if not path.is_file():
        raise ValueError(f"missing shipped-source file: {path}")
    return path.resolve()


@functools.lru_cache(maxsize=None)
def verified(library: Path) -> frozenset[Path]:
    """Return verified generated paths; an absent manifest grants no exemption."""
    library = library.resolve()
    manifest = library / "upstream/generated.json"
    if not manifest.is_file():
        return frozenset()
    entries = json.loads(manifest.read_text())
    if not isinstance(entries, dict) or not entries:
        raise ValueError(f"empty or invalid shipped-source manifest: {manifest}")
    result = set()
    for name, expected in entries.items():
        path = checked_file(library, name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"shipped source differs from maintainer output: {path}")
        result.add(path)
    return frozenset(result)


def check_generator(script: Path, *arguments: str) -> None:
    """Check maintainer output without writing files or granting directory exemptions."""
    try:
        result = subprocess.run(
            [sys.executable, str(script), *arguments], capture_output=True, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60, check=False)
    except subprocess.TimeoutExpired as error:
        raise ValueError(f"shipped-source check timed out: {script}") from error
    if result.returncode != 0:
        raise ValueError(f"shipped-source check failed: {script}\n"
                         + (result.stdout + result.stderr).strip())


@functools.lru_cache(maxsize=None)
def lint_sources(library: Path) -> frozenset[Path]:
    """Return exact imported lint inputs; public header discovery uses verified alone.

    Cobalt's original corpus and mechanical namespace migration retain upstream
    style. Functional network/Python adaptations and adjacent owned files do not.
    """
    library = library.resolve()
    paths = set(verified(library))
    applications = library / "test/applications"
    manifest = applications / "manifest.json"
    if library.name != "cobalt" or not manifest.is_file():
        return frozenset(paths)
    check_generator(applications / "inventory.py")
    inventory = json.loads(manifest.read_text())
    originals = inventory["applications"] + inventory["benchmarks"]
    for entry in originals + inventory["supporting_files"]:
        paths.add(checked_file(applications, "upstream/" + entry["path"]))
    if (applications / "migrated").is_dir():
        check_generator(applications / "prepare.py", "--check")
        for entry in originals:
            paths.add(checked_file(applications, "migrated/" + entry["path"]))
    extraction = applications / "spsc/extract.py"
    if extraction.is_file():
        check_generator(extraction, "--check")
        paths.add(checked_file(applications, "spsc/original_queue.hpp"))
    return frozenset(paths)


def header_filter(paths: list[str], root: Path | None = None) -> str:
    """Match exact verified files with a compact POSIX extended regex.

    Sharing literal prefixes avoids repeated directory alternatives. With a
    checkout root, a subtree is compacted only when every C++ file in it belongs
    to the verified set. Adding an owned neighbor restores exact-file matching.
    """
    def alternatives(values: list[str]) -> str:
        if len(values) == 1:
            return re.escape(values[0])
        prefix = os.path.commonprefix(values)
        if prefix:
            return re.escape(prefix) + alternatives([v[len(prefix):] for v in values])
        groups: dict[str, list[str]] = {}
        for value in values:
            groups.setdefault(value[:1], []).append(value[1:])
        choices = [re.escape(key) + alternatives(tails) for key, tails in groups.items()]
        return "(" + "|".join(choices) + ")"

    remaining = set(paths)
    directories: list[str] = []
    if root is not None:
        # Choose only complete import subtrees. A name outside
        # the manifest is not an import, even when placed beside imported code.
        cpp_suffixes = {".h", ".hpp", ".ipp", ".cpp"}
        parents = {Path(name).parent.as_posix() for name in remaining}
        candidates = {parent.as_posix() for name in parents
                      for parent in (Path(name), *Path(name).parents)
                      if parent.as_posix() not in (".", "libs")}
        for name in sorted(candidates, key=lambda value: (value.count("/"), value)):
            prefix = name + "/"
            imported = {path for path in remaining if path.startswith(prefix)}
            if not imported:
                continue
            entries = list((root / name).rglob("*"))
            if any(path.is_symlink() for path in entries):
                continue
            actual = {path.relative_to(root).as_posix() for path in entries
                      if path.is_file() and path.suffix in cpp_suffixes}
            if actual == imported:
                directories.append(re.escape(prefix) + r".*\.(h|hpp|ipp|cpp)")
                remaining.difference_update(imported)
    choices = directories + ([alternatives(sorted(remaining))] if remaining else [])
    return "(^|/)(" + "|".join(choices) + ")$" if choices else "^$"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--list", action="store_true",
                        help="Print exact verified imported lint files, NUL-separated")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        paths = set()
        for library in sorted((root / "libs").iterdir()):
            if library.is_dir():
                paths.update(lint_sources(library))
        for path in sorted(paths):
            if args.list:
                print(path.relative_to(root).as_posix(), end="\0")
        if not args.list:
            print(f"Verified {len(paths)} imported lint inputs")
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
