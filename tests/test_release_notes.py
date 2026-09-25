import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release_notes.py"


def load_module():
    spec = importlib.util.spec_from_file_location("release_notes", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrependChangelogTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()

    def test_header_is_not_duplicated_into_entries_on_repeated_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            with patch.object(self.mod, "CHANGELOG", changelog):
                self.mod.prepend_changelog("# Subscription update — v1\n\nfirst entry")
                self.mod.prepend_changelog("# Subscription update — v2\n\nsecond entry")
                self.mod.prepend_changelog("# Subscription update — v3\n\nthird entry")
            text = changelog.read_text(encoding="utf-8")
        needle = "Automated log of provider CIDR changes"
        self.assertEqual(text.count(needle), 1)
        self.assertIn("third entry", text)
        self.assertIn("second entry", text)
        self.assertIn("first entry", text)
        self.assertLess(text.index("third entry"), text.index("second entry"))
        self.assertLess(text.index("second entry"), text.index("first entry"))

    def test_max_entries_cap_is_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            with patch.object(self.mod, "CHANGELOG", changelog):
                for i in range(5):
                    self.mod.prepend_changelog(f"entry {i}", max_entries=3)
            text = changelog.read_text(encoding="utf-8")
        self.assertIn("entry 4", text)
        self.assertIn("entry 2", text)
        self.assertNotIn("entry 1", text)
        self.assertNotIn("entry 0", text)


    def test_legacy_duplicate_descriptions_are_removed_without_losing_entries(self):
        description = self.mod.CHANGELOG_HEADER.split("\\n\\n", 1)[1]
        legacy = (
            "# Changelog\\n\\n"
            + description
            + "\\n\\nentry old-1"
            + self.mod.CHANGELOG_SEPARATOR
            + description
            + "\\n\\nentry old-2"
        )
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(legacy, encoding="utf-8")
            with patch.object(self.mod, "CHANGELOG", changelog):
                self.mod.prepend_changelog("entry new")
            text = changelog.read_text(encoding="utf-8")
        self.assertEqual(text.count(description), 1)
        self.assertIn("entry old-1", text)
        self.assertIn("entry old-2", text)
        self.assertLess(text.index("entry new"), text.index("entry old-1"))
        self.assertLess(text.index("entry old-1"), text.index("entry old-2"))

    def test_unrecognized_existing_file_falls_back_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text("# Some other title\n\nsome prior content", encoding="utf-8")
            with patch.object(self.mod, "CHANGELOG", changelog):
                self.mod.prepend_changelog("new entry")
            text = changelog.read_text(encoding="utf-8")
        self.assertIn("new entry", text)
        self.assertIn("some prior content", text)


if __name__ == "__main__":
    unittest.main()
