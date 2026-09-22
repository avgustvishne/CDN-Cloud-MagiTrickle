import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_service_packs as generator


class ServicePackTests(unittest.TestCase):
    def test_pack_domains_are_deduplicated_and_sorted(self):
        services = {
            "a": {"domains": ["z.example", "shared.example"]},
            "b": {"domains": ["a.example", "shared.example"]},
        }
        self.assertEqual(
            generator.build_domains({"services": ["a", "b"]}, services),
            ["a.example", "shared.example", "z.example"],
        )

    def test_yaml_contains_valid_classical_rules(self):
        text = generator.render_classical_yaml(["api.example.com", "example.org"])
        self.assertIn("payload:", text)
        self.assertIn("DOMAIN-SUFFIX,api.example.com", text)
        self.assertIn("DOMAIN-SUFFIX,example.org", text)

    def test_generation_creates_all_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            services_path = Path(tmp) / "services.json"
            packs_path = Path(tmp) / "packs.json"
            output = Path(tmp) / "out"
            services_path.write_text(json.dumps({
                "schema_version": 1,
                "services": {
                    "one": {"domains": ["one.example"]},
                    "two": {"domains": ["two.example"]},
                },
            }), encoding="utf-8")
            packs_path.write_text(json.dumps({
                "schema_version": 1,
                "packs": {
                    "both": {"services": ["one", "two"]}
                },
            }), encoding="utf-8")
            generator.SERVICES = services_path
            config = generator.load_config(packs_path)
            files = generator.generate(config, output)
            self.assertEqual(len(files), 3)
            self.assertEqual(
                (output / "both-domains.txt").read_text(encoding="utf-8"),
                "one.example\ntwo.example\n",
            )
            self.assertTrue((output / "both-mihomo.yaml").exists())
            self.assertTrue((output / "both-rule-provider.yaml").exists())


if __name__ == "__main__":
    unittest.main()
