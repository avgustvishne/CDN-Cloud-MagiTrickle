import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "external_intelligence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("external_intelligence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExternalIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_module()

    def test_parse_cidrs_normalizes_and_deduplicates(self):
        data = b"10.0.0.1/32\n10.0.0.0/24 # comment\n10.0.0.0/24\nnot-cidr\n2001:db8::1/128\n"
        values = self.engine.parse_cidrs(data)
        self.assertEqual(values, ["10.0.0.0/24", "10.0.0.1/32", "2001:db8::1/128"])

    def test_parse_domains_accepts_raw_and_common_rule_forms(self):
        data = b"Example.COM\n*.cdn.example.com\nDOMAIN-SUFFIX,foo.example\n# comment\ninvalid_domain\n"
        self.assertEqual(
            self.engine.parse_domains(data),
            ["cdn.example.com", "example.com", "foo.example"],
        )

    def test_coverage_uses_exact_union(self):
        values = ["192.0.2.0/25", "192.0.2.64/26", "192.0.2.128/25"]
        self.assertEqual(self.engine.coverage(values, 4), 256)

    def test_intersection_uses_exact_union(self):
        left = ["192.0.2.0/24", "192.0.2.0/25"]
        right = ["192.0.2.128/25"]
        self.assertEqual(self.engine.intersection_coverage(left, right, 4), 128)

    def test_ip_metrics_separates_families_and_profiles(self):
        profiles = {
            "full": {"ipv4": ["192.0.2.0/24"], "ipv6": ["2001:db8::/32"]},
            "performance": {"ipv4": ["198.51.100.0/24"], "ipv6": []},
        }
        metrics = self.engine.ip_metrics(
            ["192.0.2.0/25", "2001:db8:1::/48", "198.51.100.0/25"],
            profiles,
        )
        self.assertEqual(metrics["4"]["coverage_ips"], 256)
        self.assertEqual(metrics["4"]["overlap_full_ips"], 128)
        self.assertEqual(metrics["4"]["overlap_performance_ips"], 128)
        self.assertEqual(metrics["6"]["coverage_ips"], 2**80)
        self.assertEqual(metrics["6"]["overlap_full_ips"], 2**80)

    def test_registry_declares_eight_evidence_only_feeds(self):
        registry = json.loads((ROOT / "config/source_registry.json").read_text(encoding="utf-8"))
        block = registry["external-intelligence"]
        self.assertEqual(len(block["feeds"]), 8)
        self.assertEqual(block["policy"], "evidence-only; never mutates provider subscriptions")
        self.assertEqual({item["type"] for item in block["feeds"].values()}, {"ip", "domain"})

    def test_generated_profile_missing_files_is_safe(self):
        old = self.engine.DATA
        try:
            with tempfile.TemporaryDirectory() as td:
                self.engine.DATA = Path(td)
                profile = self.engine.generated_profile("full")
                self.assertEqual(profile, {"ipv4": [], "ipv6": []})
        finally:
            self.engine.DATA = old


if __name__ == "__main__":
    unittest.main()
