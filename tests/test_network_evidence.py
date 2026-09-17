import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "network_evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("network_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NetworkEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_module()

    def test_prefix_normalization(self):
        self.assertEqual(self.engine.validate_prefix("1.2.3.4/24"), "1.2.3.0/24")
        self.assertEqual(self.engine.validate_prefix("2001:db8::/32"), "2001:db8::/32")
        self.assertIsNone(self.engine.validate_prefix("not-a-prefix"))

    def test_policy_never_deletes_on_negative_evidence(self):
        old = self.engine.OUTPUT
        try:
            with tempfile.TemporaryDirectory() as td:
                self.engine.OUTPUT = Path(td) / "network-evidence.json"
                payload = {
                    "schema_version": 1,
                    "policy": {
                        "rpki_invalid_deletes_prefix": False,
                        "bgp_absence_deletes_prefix": False,
                        "irr_absence_deletes_prefix": False,
                    },
                }
                self.engine.OUTPUT.write_text(json.dumps(payload), encoding="utf-8")
                data = json.loads(self.engine.OUTPUT.read_text(encoding="utf-8"))
                self.assertFalse(data["policy"]["rpki_invalid_deletes_prefix"])
                self.assertFalse(data["policy"]["bgp_absence_deletes_prefix"])
                self.assertFalse(data["policy"]["irr_absence_deletes_prefix"])
        finally:
            self.engine.OUTPUT = old

    def test_evidence_result_has_separate_network_dimensions(self):
        row = {
            "provider": "example",
            "prefix": "1.2.3.0/24",
        }
        prefix = self.engine.validate_prefix(row["prefix"])
        self.assertEqual(prefix, "1.2.3.0/24")
        result = {
            "provider": "example",
            "prefix": prefix,
            "bgp": {"announced": None, "origins": [], "visibility": None},
            "irr": {"present": None, "sources": []},
            "rpki": {"checked": False, "statuses": []},
        }
        self.assertIn("bgp", result)
        self.assertIn("irr", result)
        self.assertIn("rpki", result)

    def test_candidate_selection_keeps_ipv6_coverage(self):
        rows = [
            {"provider": "v4", "prefix": f"1.0.{i}.0/24"} for i in range(200)
        ] + [
            {"provider": "v6", "prefix": f"2001:db8:{i}::/48"} for i in range(200)
        ]
        selected = self.engine.select_evidence_candidates(rows, 20)
        self.assertEqual(len(selected), 20)
        self.assertTrue(any(":" in row["prefix"] for row in selected))
        self.assertTrue(any(":" not in row["prefix"] for row in selected))

    def test_rpki_call_includes_prefix_and_asn(self):
        calls = []

        def fake_api(endpoint, resource, extra=None):
            calls.append((endpoint, resource, extra))
            if endpoint == "prefix-routing-consistency":
                return {"in_bgp": True, "in_whois": True, "irr_sources": [], "origins": [13335]}
            return {"status": "valid"}

        with patch.object(self.engine, "api", side_effect=fake_api):
            result = self.engine.evidence_for({"provider": "cloudflare", "prefix": "1.2.3.0/24"})

        self.assertEqual(result["rpki"]["statuses"], [{"asn": "AS13335", "status": "valid"}])
        self.assertEqual(
            calls[1],
            ("rpki-validation", 13335, {"prefix": "1.2.3.0/24"}),
        )


if __name__ == "__main__":
    unittest.main()
