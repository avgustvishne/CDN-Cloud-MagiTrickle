import ipaddress
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_cdn_v3 as generator


class CdnV3Tests(unittest.TestCase):
    def test_policy_has_core_and_new_cdn_sources(self):
        config = json.loads((ROOT / "config" / "cdn_v3.json").read_text(encoding="utf-8"))
        names = {row["id"] for row in config["providers"]}
        self.assertTrue(generator.CORE.issubset(names))
        self.assertIn("bunny", names)
        self.assertIn("cachefly", names)
        self.assertFalse(config["policy"]["include_general_cloud"])
        self.assertFalse(config["policy"]["include_vps_only"])

    def test_normalize_is_global_deduplicated_and_collapsed(self):
        values = {
            "23.235.32.0/20",
            "23.235.32.0/21",
            "10.0.0.0/8",
            "2400:52e0:1::/48",
        }
        result = generator.normalize(values)
        self.assertEqual(
            [str(n) for n in result],
            ["23.235.32.0/20", "23.235.32.0/21", "2400:52e0:1::/48"],
        )

    def test_coverage_is_preserved(self):
        source = [
            ipaddress.ip_network("23.235.32.0/21"),
            ipaddress.ip_network("23.235.40.0/21"),
        ]
        collapsed = generator.normalize([str(n) for n in source])
        self.assertEqual(generator.coverage(source), generator.coverage(collapsed))

    def test_cachefly_parser_accepts_plain_cidr_lines(self):
        self.assertEqual(
            generator.parse_cidrs(b"# comment\n23.235.32.0/20\ninvalid\n"),
            {"23.235.32.0/20"},
        )


if __name__ == "__main__":
    unittest.main()
