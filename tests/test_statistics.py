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
            path.write_text(
                "192.0.2.0/24\n2001:db8::/32\n192.0.2.0/24\n",
                encoding="utf-8",
            )
            result = self.stats.file_stats(path)
        self.assertEqual(result["cidr_count"], 3)
        self.assertEqual(result["ipv4_count"], 2)
        self.assertEqual(result["ipv6_count"], 1)
        self.assertEqual(result["ipv4_coverage"], 512)
        self.assertEqual(result["ipv6_coverage"], 2**96)

    def test_human_count_uses_space_separator(self):
        self.assertEqual(self.stats.human_count(12478), "12 478")

    def test_update_readme_refreshes_all_profile_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            readme = root / "README.md"
            readme.write_text(
                "intro\n\n<!-- AUTO-STATS:START -->\nold\n<!-- AUTO-STATS:END -->\n",
                encoding="utf-8",
            )
            original = self.stats.README
            self.stats.README = readme
            try:
                stats = {
                    "generated_at": "2026-09-21T00:00:00Z",
                    "profiles": {
                        "full-v4": {"cidr_count": 17512},
                        "full-v6": {"cidr_count": 5292},
                        "balanced-v4": {"cidr_count": 9204},
                        "balanced-v6": {"cidr_count": 3085},
                        "minimal-v4": {"cidr_count": 1852},
                        "minimal-v6": {"cidr_count": 674},
                        "stable-v4": {"cidr_count": 17512},
                        "stable-v6": {"cidr_count": 5292},
                        "messaging-v4": {"cidr_count": 19},
                        "messaging-v6": {"cidr_count": 8},
                    },
                    "datasets": {
                        "asn_all": {"ipv4": 100, "ipv6": 200},
                        "all_cloud": {"ipv4": 300, "ipv6": 400},
                    },
                }
                changed = self.stats.update_readme(stats)
                text = readme.read_text(encoding="utf-8")
            finally:
                self.stats.README = original

        self.assertEqual(changed, 1)
        self.assertIn("**FULL** | **17 512 CIDR** | **5 292 CIDR**", text)
        self.assertIn("**STABLE** | **17 512 CIDR** | **5 292 CIDR**", text)
        self.assertIn("**MESSAGING** | **19 CIDR** | **8 CIDR**", text)
        self.assertIn("**ASN ALL** | **100 CIDR** | **200 CIDR**", text)
        self.assertIn("2026-09-21T00:00:00Z", text)
        self.assertNotIn("old", text)

    def test_update_readme_publishes_messaging_row_when_files_exist(self):
        with tempfile.TemporaryDirectory() as td:
            readme = Path(td) / "README.md"
            readme.write_text(
                "| Тот же набор, что FULL, но обновляется раз в неделю | **STABLE** | stable4 | stable6 |\n"
                "> **MESSAGING (Telegram + Twitter/X)** временно убран из этой таблицы: old note\n",
                encoding="utf-8",
            )
            original = self.stats.README
            self.stats.README = readme
            try:
                stats = {
                    "generated_at": "2026-09-21T00:00:00Z",
                    "files": {
                        "data/presets/messaging-v4.txt": {"cidr_count": 19},
                        "data/presets/messaging-v6.txt": {"cidr_count": 8},
                    },
                    "profiles": {},
                    "datasets": {
                        "asn_all": {"ipv4": 1, "ipv6": 2},
                        "all_cloud": {"ipv4": 3, "ipv6": 4},
                    },
                }
                self.stats.update_readme(stats)
                text = readme.read_text(encoding="utf-8")
            finally:
                self.stats.README = original

        self.assertIn("| Telegram + Twitter/X | **MESSAGING** |", text)
        self.assertIn("messaging-v4.txt", text)
        self.assertNotIn("old note", text)


    def test_update_readme_adds_block_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            readme = Path(td) / "README.md"
            readme.write_text("## 🔄 Обновление\n\ntext\n", encoding="utf-8")
            original = self.stats.README
            self.stats.README = readme
            try:
                stats = {
                    "generated_at": "2026-09-21T00:00:00Z",
                    "profiles": {},
                    "datasets": {
                        "asn_all": {"ipv4": 1, "ipv6": 2},
                        "all_cloud": {"ipv4": 3, "ipv6": 4},
                    },
                }
                self.stats.update_readme(stats)
                text = readme.read_text(encoding="utf-8")
            finally:
                self.stats.README = original

        self.assertIn("<!-- AUTO-STATS:START -->", text)
        self.assertIn("<!-- AUTO-STATS:END -->", text)
        self.assertIn("**ALL-CLOUD** | **3 CIDR** | **4 CIDR**", text)

    def test_readme_block_omits_missing_profiles(self):
        with tempfile.TemporaryDirectory() as td:
            readme = Path(td) / "README.md"
            readme.write_text("<!-- AUTO-STATS:START -->old<!-- AUTO-STATS:END -->", encoding="utf-8")
            original = self.stats.README
            self.stats.README = readme
            try:
                stats = {
                    "generated_at": "2026-09-21T00:00:00Z",
                    "profiles": {"full-v4": {"cidr_count": 10}, "full-v6": {"cidr_count": 20}},
                    "datasets": {"asn_all": {"ipv4": 1, "ipv6": 2}, "all_cloud": {"ipv4": 3, "ipv6": 4}},
                }
                self.stats.update_readme(stats)
                text = readme.read_text(encoding="utf-8")
            finally:
                self.stats.README = original

        self.assertIn("**FULL** | **10 CIDR** | **20 CIDR**", text)
        self.assertNotIn("**MESSAGING**", text)


if __name__ == "__main__":
    unittest.main()
