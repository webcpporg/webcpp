#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Imported text retains its provenance without exempting hand-written wrappers."""
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import shipped_sources

sys.path.insert(0, str(Path(__file__).parent / "lint"))
import compile_commands


class ShippedSourcesTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="verified import ")
        self.root = Path(self.temporary.name)
        self.library = self.root / "libs/demo"
        self.imported = self.library / "include/webcpp/demo/detail/backend.hpp"
        self.imported.parent.mkdir(parents=True)
        self.imported.write_text("// upstream implementation\n")
        self.owned = self.library / "include/webcpp/demo/config.hpp"
        self.owned.write_text("// documented WebCPP configuration\n")
        (self.library / "upstream").mkdir()
        self.manifest = self.library / "upstream/generated.json"
        self.manifest.write_text(json.dumps({
            self.imported.relative_to(self.library).as_posix():
                hashlib.sha256(self.imported.read_bytes()).hexdigest()}))

    def tearDown(self):
        shipped_sources.verified.cache_clear()
        self.temporary.cleanup()

    def test_public_aggregate_keeps_owned_headers(self):
        self.assertEqual(compile_commands.public_headers(str(self.root), "demo"),
                         ["webcpp/demo/config.hpp"])

    def test_tampered_import_fails_before_exemption(self):
        self.imported.write_text("// different implementation\n")
        with self.assertRaisesRegex(ValueError, "differs"):
            compile_commands.public_headers(str(self.root), "demo")

    def test_header_filter_matches_only_exact_paths(self):
        paths = [f"libs/demo/include/webcpp/demo/backend/dir{i}/file{j}.ipp"
                 for i in range(8) for j in range(40)]
        paths += ["libs/demo/include/webcpp/demo/a.hpp", "libs/demo/include/webcpp/demo/a+.hpp"]
        pattern = shipped_sources.header_filter(paths)
        matcher = re.compile(pattern)
        self.assertLess(len(pattern), sum(map(len, paths)) // 2)
        for path in paths:
            self.assertIsNotNone(matcher.search(path))
            self.assertIsNotNone(matcher.search("/tmp/tree/" + path))
            self.assertIsNone(matcher.search(path + ".other"))
            self.assertIsNone(matcher.search("x" + path))
        self.assertIsNone(matcher.search("libs/demo/include/webcpp/demo/backend/owned.ipp"))
        self.assertIsNone(re.search(shipped_sources.header_filter([]), "anything.hpp"))

    def test_complete_import_subtree_is_compact_but_owned_neighbors_stay_visible(self):
        paths = [self.imported.relative_to(self.root).as_posix()]
        compact = shipped_sources.header_filter(paths, self.root)
        self.assertIn(".*", compact)
        self.assertIsNotNone(re.search(compact, paths[0]))
        neighbor = self.imported.with_name("owned.ipp")
        neighbor.write_text("// maintained WebCPP source\n")
        exact = shipped_sources.header_filter(paths, self.root)
        self.assertNotIn(".*", exact)
        self.assertIsNotNone(re.search(exact, paths[0]))
        self.assertIsNone(re.search(exact, neighbor.relative_to(self.root).as_posix()))
        self.assertIsNone(re.search(exact, self.owned.relative_to(self.root).as_posix()))

    def test_compact_filter_does_not_exempt_other_header_extensions(self):
        paths = [self.imported.relative_to(self.root).as_posix()]
        for extension in (".inc", ".inl", ".hxx", ".tpp", ""):
            neighbor = self.imported.with_name("owned" + extension)
            neighbor.write_text("// maintained header\n")
            pattern = shipped_sources.header_filter(paths, self.root)
            self.assertIsNone(re.search(pattern, neighbor.relative_to(self.root).as_posix()))
        self.assertIsNotNone(re.search(pattern, paths[0]))

    def test_symlink_neighbor_prevents_subtree_compaction(self):
        (self.imported.parent / "linked").symlink_to(self.owned.parent,
                                                   target_is_directory=True)
        paths = [self.imported.relative_to(self.root).as_posix()]
        pattern = shipped_sources.header_filter(paths, self.root)
        self.assertNotIn(".*", pattern)
        self.assertIsNotNone(re.search(pattern, paths[0]))

    def test_no_manifest_exempts_nothing(self):
        self.manifest.unlink()
        self.assertEqual(len(compile_commands.public_headers(str(self.root), "demo")), 2)

    def test_manifest_cannot_escape_its_library(self):
        self.manifest.write_text(json.dumps({"../foreign.hpp": ""}))
        with self.assertRaisesRegex(ValueError, "unsafe"):
            shipped_sources.verified(self.library)

    def test_symlink_is_not_imported_source(self):
        self.imported.unlink()
        self.imported.symlink_to(self.owned)
        with self.assertRaisesRegex(ValueError, "unsafe"):
            shipped_sources.verified(self.library)


class CobaltLintSourcesTest(unittest.TestCase):
    """Only checked upstream text and mechanical outputs leave lint's owned set."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cobalt lint sources ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.checkout = Path(__file__).resolve().parents[1]
        self.applications = self.root / "libs/cobalt/test/applications"
        original = self.checkout / "libs/cobalt/test/applications"
        self.applications.mkdir(parents=True)
        for name in ("upstream", "migrated"):
            shutil.copytree(original / name, self.applications / name)
        for name in ("manifest.json", "inventory.py", "prepare.py"):
            shutil.copyfile(original / name, self.applications / name)
        (self.applications / "spsc").mkdir()
        for name in ("extract.py", "original_queue.hpp"):
            shutil.copyfile(original / "spsc" / name, self.applications / "spsc" / name)
        shutil.copyfile(self.checkout / ".clang-format", self.root / ".clang-format")
        formatter = self.root / ".local/wasi-sdk/bin/clang-format"
        formatter.parent.mkdir(parents=True)
        formatter.symlink_to(self.checkout / ".local/wasi-sdk/bin/clang-format")

    def classify(self):
        return subprocess.run(
            [sys.executable, str(self.checkout / "tools/shipped_sources.py"),
             str(self.root), "--list"], capture_output=True, text=True, check=False)

    def test_exact_corpus_paths_include_non_cpp_but_not_owned_neighbors(self):
        neighbors = [self.applications / "migrated/example/owned.hpp",
                     self.applications / "network/port/http.cpp",
                     self.applications / "python/binding.cpp",
                     self.applications / "spsc/owned.hpp"]
        for path in neighbors:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("// maintained implementation\n")
        result = self.classify()
        self.assertEqual(result.returncode, 0, result.stderr)
        paths = set(result.stdout.split("\0"))
        for suffix in ("upstream/example/http.cpp", "upstream/example/python.py",
                       "upstream/example/Jamfile", "migrated/example/http.cpp",
                       "spsc/original_queue.hpp"):
            self.assertIn("libs/cobalt/test/applications/" + suffix, paths)
        for path in neighbors:
            self.assertNotIn(path.relative_to(self.root).as_posix(), paths)

    def test_changed_original_is_rejected_before_classification(self):
        source = self.applications / "upstream/example/http.cpp"
        source.write_text(source.read_text() + "// changed upstream body\n")
        result = self.classify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source hash mismatch", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_changed_migration_and_updated_hash_still_fail_generator_check(self):
        source = self.applications / "migrated/example/http.cpp"
        source.write_text(source.read_text() + "// changed generated body\n")
        mapping = self.applications / "migrated/mapping.json"
        entries = json.loads(mapping.read_text())
        for entry in entries["files"]:
            if entry["source"] == "example/http.cpp":
                entry["migrated_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        mapping.write_text(json.dumps(entries))
        result = self.classify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale namespace migration", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_changed_extraction_is_rejected_without_rewriting_it(self):
        source = self.applications / "spsc/original_queue.hpp"
        changed = source.read_text() + "// changed queue body\n"
        source.write_text(changed)
        result = self.classify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stale", result.stderr)
        self.assertEqual(source.read_text(), changed)
        self.assertEqual(result.stdout, "")

    def test_corpus_symlink_does_not_exempt_an_owned_file(self):
        source = self.applications / "upstream/example/http.cpp"
        owned = self.root / "owned.cpp"
        owned.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(owned)
        result = self.classify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
