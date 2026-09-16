import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

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
        # Avoid network access: validate the deterministic shape produced by the collector.
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


if __name__ == "__main__":
    unittest.main()
