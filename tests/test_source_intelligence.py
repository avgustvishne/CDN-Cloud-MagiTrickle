import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "source_intelligence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("source_intelligence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SourceIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_module()

    def test_parse_time_handles_zulu_and_invalid(self):
        self.assertIsNotNone(self.engine.parse_time("2026-09-16T12:00:00Z"))
        self.assertIsNone(self.engine.parse_time("not-a-date"))

    def test_source_status_is_observational(self):
        rows = self.engine.source_status(
            {"example": {"role": "cross-check", "refresh": "daily"}},
            {"sources": {"example": {"providers_checked": 2}}},
        )
        self.assertEqual(rows[0]["audit_providers_checked"], 2)
        self.assertFalse(rows[0]["live_fetch_enabled"])

    def test_consensus_summary_ignores_invalid_json(self):
        old = self.engine.DATA
        try:
            with tempfile.TemporaryDirectory() as td:
                self.engine.DATA = Path(td)
                (self.engine.DATA / "broken-consensus.json").write_text("{", encoding="utf-8")
                self.assertEqual(self.engine.consensus_summary(), {})
        finally:
            self.engine.DATA = old

    def test_prefix_intelligence_counts_sources(self):
        old = self.engine.DATA
        try:
            with tempfile.TemporaryDirectory() as td:
                self.engine.DATA = Path(td)
                (self.engine.DATA / "example-consensus.json").write_text(
                    json.dumps({"records": [
                        {"cidr": "1.2.3.0/24", "sources": ["official", "IPVerse"]},
                        {"cidr": "1.2.4.0/24", "sources": ["IPVerse"]},
                    ]}),
                    encoding="utf-8",
                )
                rows = self.engine.prefix_intelligence()
                self.assertEqual(rows[0]["total_prefixes"], 2)
                self.assertEqual(rows[0]["independent_source_types"], 2)
        finally:
            self.engine.DATA = old


if __name__ == "__main__":
    unittest.main()
