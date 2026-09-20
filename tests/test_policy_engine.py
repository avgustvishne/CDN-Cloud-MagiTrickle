import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "policy_engine.py"

def load_module():
    spec = importlib.util.spec_from_file_location("policy_engine", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class PolicyEngineTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()

    def write_policy(self, tmp, policy):
        path = Path(tmp) / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        return path

    def test_disabled_policy_passes_everything_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_policy(tmp, {"enabled": False, "providers": {}, "global": {}})
            with patch.object(self.mod, "CONFIG", path):
                result, explain = self.mod.apply("aws", ["10.0.0.0/24"])
        self.assertEqual(result, ["10.0.0.0/24"])
        self.assertEqual(explain[0]["reason"], "policy disabled")

    def test_global_exclude_removes_matching_cidr(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_policy(tmp, {"enabled": True, "providers": {}, "global": {"exclude": ["10.0.0.0/24"], "include": []}})
            with patch.object(self.mod, "CONFIG", path):
                result, _ = self.mod.apply("aws", ["10.0.0.0/24", "192.168.1.0/24"])
        self.assertEqual(result, ["192.168.1.0/24"])

    def test_collect_explain_false_still_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_policy(tmp, {"enabled": True, "providers": {}, "global": {"exclude": ["10.0.0.0/24"], "include": []}})
            with patch.object(self.mod, "CONFIG", path):
                result, explain = self.mod.apply("aws", ["10.0.0.0/24", "192.168.1.0/24"], collect_explain=False)
        self.assertEqual(result, ["192.168.1.0/24"])
        self.assertEqual(explain, [])

    def test_mixed_ipv4_ipv6_policy_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_policy(tmp, {"enabled": True, "providers": {}, "global": {"exclude": ["10.0.0.0/24", "2606:4700::/32"], "include": []}})
            with patch.object(self.mod, "CONFIG", path):
                v4, _ = self.mod.apply("aws", ["10.0.0.0/24", "192.168.1.0/24"])
                v6, _ = self.mod.apply("aws", ["2606:4700::/32", "2a00:1450::/32"])
        self.assertEqual(v4, ["192.168.1.0/24"])
        self.assertEqual(v6, ["2a00:1450::/32"])

    def test_include_restricts_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_policy(tmp, {"enabled": True, "providers": {}, "global": {"exclude": [], "include": ["10.0.0.0/8"]}})
            with patch.object(self.mod, "CONFIG", path):
                result, _ = self.mod.apply("aws", ["10.1.2.0/24", "192.168.1.0/24"])
        self.assertEqual(result, ["10.1.2.0/24"])

if __name__ == "__main__":
    unittest.main()
