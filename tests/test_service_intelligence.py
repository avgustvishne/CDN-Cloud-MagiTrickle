import json
import tempfile
import unittest
from pathlib import Path

from scripts.service_intelligence import build_report, load_registry, write_outputs


REGISTRY = {
    "schema_version": 1,
    "policy": {
        "source_of_truth": "official-service-documentation",
        "external_lists_are_evidence_only": True,
        "resolved_ips_are_evidence_only": True,
        "shared_infrastructure_requires_review": True,
    },
    "services": {
        "alpha": {
            "category": "test",
            "domains": ["a.example", "b.example"],
            "ports": [443],
            "official_sources": ["https://example.test/alpha"],
        },
        "beta": {
            "category": "test",
            "domains": ["c.example"],
            "ports": [443],
            "official_sources": ["https://example.test/beta"],
        },
    },
}


class ServiceIntelligenceTests(unittest.TestCase):
    def resolver(self, domain, family):
        values = {
            ("a.example", 4): ["192.0.2.1"],
            ("a.example", 6): ["2001:db8::1"],
            ("b.example", 4): ["192.0.2.2"],
            ("b.example", 6): [],
            ("c.example", 4): ["192.0.2.1"],
            ("c.example", 6): [],
        }
        return values[(domain, family)]

    def test_build_report_is_deterministic_and_detects_shared_ip(self):
        first = build_report(REGISTRY, self.resolver)
        second = build_report(REGISTRY, self.resolver)
        self.assertEqual(first, second)
        self.assertEqual(first["shared_ips"], {"192.0.2.1": ["alpha", "beta"]})
        self.assertTrue(first["services"]["alpha"]["routing"]["domain_ready"])
        self.assertFalse(first["services"]["alpha"]["routing"]["ip_ready"])
        self.assertEqual(first["services"]["alpha"]["confidence"], 100.0)

    def test_write_outputs_contains_domain_subscriptions(self):
        report = build_report(REGISTRY, self.resolver)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_outputs(report, output)
            self.assertEqual(
                (output / "services" / "alpha-domains.txt").read_text(),
                "a.example\nb.example\n",
            )
            saved = json.loads((output / "service-intelligence.json").read_text())
            self.assertEqual(saved["schema_version"], 1)
            self.assertEqual(sorted(saved["services"]), ["alpha", "beta"])

    def test_registry_rejects_duplicate_domains(self):
        invalid = json.loads(json.dumps(REGISTRY))
        invalid["services"]["alpha"]["domains"].append("a.example")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "services.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_registry(path)


if __name__ == "__main__":
    unittest.main()
