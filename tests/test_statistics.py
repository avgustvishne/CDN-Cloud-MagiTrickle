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

if __name__ == "__main__":
    unittest.main()