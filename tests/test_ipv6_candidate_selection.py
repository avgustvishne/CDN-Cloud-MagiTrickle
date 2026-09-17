import importlib.util
import ipaddress
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_generator():
    path = ROOT / "scripts" / "update_cdn_lists.py"
    spec = importlib.util.spec_from_file_location("update_cdn_lists", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CandidateSelectionTests(unittest.TestCase):
    def test_balances_ipv4_and_ipv6(self):
        module = load_generator()
        v4 = [f"198.51.{i}.0/24" for i in range(160)]
        v6 = [f"2001:db8:{i:x}::/48" for i in range(160)]
        selected = module.select_ripe_candidates(v4 + v6, limit=128)
        self.assertEqual(len(selected), 128)
        self.assertEqual(sum(ipaddress.ip_network(p).version == 4 for p in selected), 64)
        self.assertEqual(sum(ipaddress.ip_network(p).version == 6 for p in selected), 64)

    def test_skewed_input_keeps_rare_ipv6(self):
        module = load_generator()
        v4 = [f"203.0.{i}.0/24" for i in range(500)]
        v6 = [f"2001:db8:{i:x}::/48" for i in range(3)]
        first = module.select_ripe_candidates(v4 + v6, limit=128)
        second = module.select_ripe_candidates(list(reversed(v4 + v6)), limit=128)
        self.assertEqual(first, second)
        self.assertEqual(sum(ipaddress.ip_network(p).version == 6 for p in first), 3)
        self.assertEqual(sum(ipaddress.ip_network(p).version == 4 for p in first), 125)

    def test_small_input_preserves_all(self):
        module = load_generator()
        values = ["192.0.2.0/24", "2001:db8::/32"]
        self.assertEqual(set(module.select_ripe_candidates(values)), set(values))

    def test_invalid_prefixes_are_ignored(self):
        module = load_generator()
        values = ["not-a-cidr", "192.0.2.0/24", "2001:db8::/32"]
        selected = module.select_ripe_candidates(values)
        self.assertEqual(set(selected), {"192.0.2.0/24", "2001:db8::/32"})


if __name__ == "__main__":
    unittest.main()
