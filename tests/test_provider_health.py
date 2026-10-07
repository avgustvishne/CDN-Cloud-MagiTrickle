import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_provider_health.py"
spec = importlib.util.spec_from_file_location("generate_provider_health", SCRIPT)
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class ProviderHealthTests(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(health.classify("OK", True), "healthy")
        self.assertEqual(health.classify("PARTIAL", True), "warning")
        self.assertEqual(health.classify("FILTERED", True), "warning")
        self.assertEqual(health.classify("KEEP_OLD_PARTIAL", True), "protected")
        self.assertEqual(health.classify("OK", False), "missing")

    def test_freshness_distinguishes_update_and_unchanged(self):
        unchanged = {
            "added": {"ipv4": 0, "ipv6": 0},
            "removed": {"ipv4": 0, "ipv6": 0},
        }
        changed = {
            "added": {"ipv4": 2, "ipv6": 0},
            "removed": {"ipv4": 1, "ipv6": 0},
        }
        self.assertEqual(health.freshness(unchanged, "OK", True), "unchanged")
        self.assertEqual(health.freshness(changed, "OK", True), "updated")
        self.assertEqual(health.freshness(changed, "KEEP_OLD", True), "protected")
        self.assertEqual(health.freshness(changed, "OK", False), "missing")

    def test_build_reports_real_file_hashes_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            diff = data / "diff"
            config = root / "config"
            data.mkdir()
            diff.mkdir()
            config.mkdir()

            (config / "providers.json").write_text(
                json.dumps({"providers": {"example": ["64500"]}}),
                encoding="utf-8",
            )
            (data / "audit.csv").write_text(
                "Provider,IPv4,IPv6,PreviousIPv4,PreviousIPv6,IPv4Change%,IPv6Change%,Status,Source,Errors\n"
                "example,2,1,1,1,100,0,OK,test,0\n",
                encoding="utf-8",
            )
            (data / "example-v4.txt").write_text("1.1.1.0/24\n2.2.2.0/24\n", encoding="utf-8")
            (data / "example-v6.txt").write_text("2001:db8::/32\n", encoding="utf-8")
            (diff / "example.json").write_text(
                json.dumps({
                    "provider": "example",
                    "added": {"ipv4": 1, "ipv6": 0},
                    "removed": {"ipv4": 0, "ipv6": 0},
                }),
                encoding="utf-8",
            )
            original = (health.ROOT, health.DATA, health.CONFIG, health.AUDIT)
            try:
                health.ROOT = root
                health.DATA = data
                health.CONFIG = config / "providers.json"
                health.AUDIT = data / "audit.csv"
                report = health.build()
            finally:
                health.ROOT, health.DATA, health.CONFIG, health.AUDIT = original

            provider = report["providers"][0]
            self.assertEqual(provider["health"], "healthy")
            self.assertEqual(provider["freshness"], "updated")
            self.assertEqual(provider["ipv4"], 2)
            self.assertEqual(provider["ipv6"], 1)
            self.assertEqual(len(provider["files"]["ipv4"]["sha256"]), 64)
            self.assertEqual(report["summary"]["updated"], 1)


if __name__ == "__main__":
    unittest.main()
