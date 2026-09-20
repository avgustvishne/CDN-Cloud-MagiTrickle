import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_config.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_config", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidateProvidersTests(unittest.TestCase):
    def setUp(self): self.mod = load_module()
    def write(self, tmp, name, obj):
        path = Path(tmp) / name; path.write_text(json.dumps(obj), encoding="utf-8"); return path
    def test_real_repo_config_passes(self): self.assertEqual(self.mod.validate_providers(ROOT / "config" / "providers.json"), [])
    def test_valid_minimal_config_passes(self):
        with tempfile.TemporaryDirectory() as tmp: self.assertEqual(self.mod.validate_providers(self.write(tmp, "providers.json", {"providers": {"aws": ["16509"], "backblaze": []}})), [])
    def test_missing_providers_key_fails(self):
        with tempfile.TemporaryDirectory() as tmp: self.assertEqual(len(self.mod.validate_providers(self.write(tmp, "providers.json", {"not_providers": {}}))), 1)
    def test_empty_providers_object_fails(self):
        with tempfile.TemporaryDirectory() as tmp: self.assertEqual(len(self.mod.validate_providers(self.write(tmp, "providers.json", {"providers": {}}))), 1)
    def test_uppercase_provider_name_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors=self.mod.validate_providers(self.write(tmp,"providers.json",{"providers":{"AWS":["16509"]}})); self.assertEqual(len(errors),1); self.assertIn("AWS",errors[0])
    def test_non_numeric_asn_fails(self):
        with tempfile.TemporaryDirectory() as tmp: self.assertEqual(len(self.mod.validate_providers(self.write(tmp,"providers.json",{"providers":{"aws":["AS16509"]}}))),1)
    def test_duplicate_asn_in_same_provider_fails(self):
        with tempfile.TemporaryDirectory() as tmp: self.assertEqual(len(self.mod.validate_providers(self.write(tmp,"providers.json",{"providers":{"aws":["16509","16509"]}}))),1)
    def test_malformed_json_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"providers.json"; path.write_text("{not valid json",encoding="utf-8"); self.assertEqual(len(self.mod.validate_providers(path)),1)

class ValidatePolicyTests(unittest.TestCase):
    def setUp(self): self.mod=load_module()
    def write(self,tmp,name,obj):
        path=Path(tmp)/name; path.write_text(json.dumps(obj),encoding="utf-8"); return path
    def test_real_repo_policy_passes(self): self.assertEqual(self.mod.validate_policy(ROOT/"config"/"policy.json"),[])
    def test_missing_policy_file_is_not_an_error(self): self.assertEqual(self.mod.validate_policy(Path("/nonexistent/policy.json")),[])
    def test_valid_policy_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=self.write(tmp,"policy.json",{"enabled":True,"providers":{"aws":{"exclude":["10.0.0.0/24"],"include":[]}},"global":{"exclude":[],"include":["1.2.3.0/24"]}}); self.assertEqual(self.mod.validate_policy(path),[])
    def test_missing_enabled_flag_fails(self):
        with tempfile.TemporaryDirectory() as tmp: self.assertEqual(len(self.mod.validate_policy(self.write(tmp,"policy.json",{"providers":{},"global":{}}))),1)
    def test_invalid_cidr_in_exclude_fails(self):
        with tempfile.TemporaryDirectory() as tmp: self.assertEqual(len(self.mod.validate_policy(self.write(tmp,"policy.json",{"enabled":True,"providers":{},"global":{"exclude":["not-a-cidr"],"include":[]}}))),1)

if __name__ == "__main__": unittest.main()
