import importlib.util
import ipaddress
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update_cdn_lists.py"


def load_engine():
    spec = importlib.util.spec_from_file_location("update_cdn_lists", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GeneratorUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_engine()

    def test_select_ripe_candidates_is_bounded_and_deterministic(self):
        values = [f"192.0.{i}.0/24" for i in range(200)]
        values += ["192.0.1.0/24", "192.0.2.0/24"]
        first = self.engine.select_ripe_candidates(values, limit=32)
        second = self.engine.select_ripe_candidates(list(reversed(values)), limit=32)
        self.assertEqual(len(first), 32)
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(set(first)))

    def test_select_ripe_candidates_prefers_less_specific_prefixes(self):
        values = ["192.0.2.0/28", "192.0.0.0/8", "192.0.2.0/24", "2001:db8::/32"]
        result = self.engine.select_ripe_candidates(values, limit=2)
        self.assertEqual(result[0], "192.0.0.0/8")
        self.assertEqual(result[1], "192.0.2.0/24")

    def test_load_ripe_cache_prunes_old_and_invalid_entries(self):
        now = 2_000_000_000
        payload = {
            "192.0.2.0/24": {"ts": now - 3600, "confirmed": True},
            "192.0.3.0/24": {"ts": now - 8 * 86400, "confirmed": True},
            "192.0.4.0/24": {"ts": now - 3600, "confirmed": False},
            "broken": "invalid",
        }
        with tempfile.TemporaryDirectory() as td:
            cache_file = Path(td) / "ripe-prefix-cache.json"
            cache_file.write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(self.engine, "RIPE_CACHE_FILE", cache_file),                  patch.object(self.engine.time, "time", return_value=now):
                cache = self.engine.load_ripe_cache()
        self.assertEqual(set(cache), {"192.0.2.0/24", "192.0.4.0/24"})
        self.assertTrue(cache["192.0.2.0/24"]["confirmed"])
        self.assertFalse(cache["192.0.4.0/24"]["confirmed"])

    def test_confirm_uses_cache_without_network_request(self):
        cache = {"192.0.2.0/24": {"ts": 2_000_000_000 - 3600, "confirmed": True}}
        with patch.object(self.engine.time, "time", return_value=2_000_000_000),              patch.object(self.engine, "ripe_prefix_overview") as lookup:
            self.assertTrue(self.engine.validate_prefix_with_ripe("192.0.2.0/24", cache))
            lookup.assert_not_called()

    def test_confirm_accepts_announced_prefix(self):
        with patch.object(self.engine, "ripe_prefix_overview", return_value={"announced": True, "asns": [13335]}):
            self.assertTrue(self.engine.validate_prefix_with_ripe("192.0.2.0/24", {}))

    def test_confirm_rejects_empty_ripe_response(self):
        with patch.object(self.engine, "ripe_prefix_overview", return_value={}):
            self.assertFalse(self.engine.validate_prefix_with_ripe("192.0.2.0/24", {}))

    def test_generated_cidrs_are_parseable(self):
        data = ROOT / "data"
        for path in (data / "all-cloud-v4.txt", data / "all-cloud-v6.txt",
                     data / "asn-all-v4.txt", data / "asn-all-v6.txt"):
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    ipaddress.ip_network(line.strip())

if __name__ == "__main__":
    unittest.main()
