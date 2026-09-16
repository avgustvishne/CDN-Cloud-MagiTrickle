import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_statistics.py"

def load_stats():
    spec = importlib.util.spec_from_file_location("generate_statistics", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class StatisticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stats = load_stats()

    def test_file_stats_counts_ipv4_ipv6_and_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.txt"
            path.write_text("192.0.2.0/24\n2001:db8::/32\n192.0.2.0/24\n", encoding="utf-8")
            result = self.stats.file_stats(path)
        self.assertEqual(result["cidr_count"], 3)
        self.assertEqual(result["ipv4_count"], 2)
        self.assertEqual(result["ipv6_count"], 1)
        self.assertEqual(result["ipv4_coverage"], 512)
        self.assertEqual(result["ipv6_coverage"], 2**96)

    def test_human_count_uses_space_separator(self):
        self.assertEqual(self.stats.human_count(12478), "12 478")

    def test_readme_pattern_compiles_and_matches_raw_links(self):
        import re
        pattern = re.compile(
            r"(\*\*)[0-9][0-9 ]*(?: CIDR)(\*\*\s*·\s*\[(?:IPv4|IPv6)\]\()"
            r"(https://raw\.githubusercontent\.com/avgustvishne/CDN-Cloud-MagiTrickle/main/(?:data/)?(?:presets/)?([^/)]+\.txt))"
        )
        match = pattern.search(
            "**12 594 CIDR** · [IPv4](https://raw.githubusercontent.com/"
            "avgustvishne/CDN-Cloud-MagiTrickle/main/data/asn-all-v4.txt)"
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(4), "asn-all-v4.txt")

if __name__ == "__main__":
    unittest.main()