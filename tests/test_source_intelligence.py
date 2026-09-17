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

    def test_consensus_summary_calculates_exact_family_coverage(self):
        old = self.engine.DATA
        try:
            with tempfile.TemporaryDirectory() as td:
                self.engine.DATA = Path(td)
                (self.engine.DATA / "example-consensus.json").write_text(
                    json.dumps({"records": [
                        {"cidr": "1.2.3.0/25", "sources": ["official"]},
                        {"cidr": "1.2.3.128/25", "sources": ["IPVerse"]},
                        {"cidr": "2001:db8::/33", "sources": ["official"]},
                    ]}),
                    encoding="utf-8",
                )
                row = self.engine.consensus_summary()["example"]
                self.assertEqual(row["coverage"]["ipv4"], 256)
                self.assertEqual(row["coverage"]["ipv6"], 2**95)
        finally:
            self.engine.DATA = old

    def test_reliability_score_is_bounded(self):
        score = self.engine.reliability_score({
            "authority": "official",
            "audit_providers_checked": 2,
            "new_coverage_ipv4": 10,
            "new_coverage_ipv6": 0,
        })
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_confirmation_requires_two_independent_sources(self):
        current = {"providers": {"cloudflare": {
            "records": 40, "sources": {"official": 40, "IPVerse": 40}
        }}}
        previous = {"providers": {"cloudflare": {"records": 100}}}
        rows = self.engine.provider_anomalies(current, previous)
        self.assertEqual(rows[0]["action"], "confirmed_observation")
        self.assertTrue(rows[0]["confirmation"]["confirmed"])

    def test_unconfirmed_change_stays_observation_only(self):
        current = {"providers": {"cloudflare": {
            "records": 40, "sources": {"official": 40}
        }}}
        previous = {"providers": {"cloudflare": {"records": 100}}}
        rows = self.engine.provider_anomalies(current, previous)
        self.assertEqual(rows[0]["action"], "observe_only")
        self.assertFalse(rows[0]["confirmation"]["confirmed"])

    def test_large_provider_change_is_observation_only(self):
        current = {"providers": {"cloudflare": {"records": 40}}}
        previous = {"providers": {"cloudflare": {"records": 100}}}
        rows = self.engine.provider_anomalies(current, previous)
        self.assertEqual(rows[0]["action"], "observe_only")
        self.assertEqual(rows[0]["previous_records"], 100)

    def test_coverage_change_triggers_anomaly_even_when_count_is_stable(self):
        current = {"providers": {"cloudflare": {
            "records": 100,
            "coverage": {"ipv4": 50, "ipv6": 100},
            "sources": {"official": 100, "IPVerse": 100},
        }}}
        previous = {"providers": {"cloudflare": {
            "records": 100,
            "coverage": {"ipv4": 100, "ipv6": 100},
        }}}
        rows = self.engine.provider_anomalies(current, previous)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["trigger"], "coverage")
        self.assertEqual(rows[0]["coverage_changes"]["ipv4"]["drop_percent"], 50.0)
        self.assertEqual(rows[0]["action"], "confirmed_observation")

    def test_small_provider_change_is_not_anomaly(self):
        current = {"providers": {"cloudflare": {"records": 95}}}
        previous = {"providers": {"cloudflare": {"records": 100}}}
        self.assertEqual(self.engine.provider_anomalies(current, previous), [])

    def test_prefix_evidence_normalizes_and_confirms_prefix(self):
        old = self.engine.DATA
        try:
            with tempfile.TemporaryDirectory() as td:
                self.engine.DATA = Path(td)
                (self.engine.DATA / "example-consensus.json").write_text(
                    json.dumps({"records": [
                        {"cidr": "1.2.3.0/24", "sources": ["official", "IPVerse"]},
                        {"cidr": "2001:db8::/32", "sources": ["official"]},
                    ]}),
                    encoding="utf-8",
                )
                rows = self.engine.prefix_evidence()
                self.assertEqual(rows[0]["prefix"], "1.2.3.0/24")
                self.assertEqual(rows[0]["status"], "confirmed")
                self.assertEqual(rows[1]["version"], 6)
                self.assertEqual(rows[1]["status"], "single_source")
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
