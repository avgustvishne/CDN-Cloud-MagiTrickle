import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_profiles.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_profiles", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_generator()

    def test_performance_uses_intended_focused_provider_set(self):
        selected = set(self.engine.PROFILES["performance"])
        self.assertEqual(
            selected,
            {
                "cloudflare",
                "akamai",
                "fastly",
                "cdn77",
                "gcore",
                "digitalocean",
                "hetzner",
                "ovh",
            },
        )
        for excluded in ("aws", "microsoft", "oracle", "alibaba"):
            self.assertNotIn(excluded, selected)

    def test_profile_provider_names_are_valid(self):
        known = set(self.engine.PROVIDERS)
        for selected in self.engine.PROFILES.values():
            self.assertTrue(set(selected) <= known)

    def test_coverage_is_exact_after_aggregation(self):
        cases = {
            4: [
                "8.8.8.0/24",
                "8.8.8.0/25",
                "1.1.1.0/24",
                "not-a-cidr",
            ],
            6: [
                "2001:4860:4860::/48",
                "2001:4860:4860::/64",
                "2606:4700::/32",
                "not-an-ipv6-prefix",
            ],
        }
        for version, values in cases.items():
            result = self.engine.collapse(values, version)
            expected = self.engine.address_space_coverage(values, version)
            self.assertGreater(expected, 0)
            self.assertEqual(
                expected,
                self.engine.address_space_coverage(result, version),
            )
            self.assertEqual(
                expected,
                self.engine.validate_coverage_preserved(values, result, version),
            )

    def test_profile_generation_keeps_ipv4_ipv6_separate_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td) / "data"
            out = data / "presets"
            data.mkdir()
            for provider in self.engine.PROVIDERS:
                (data / f"{provider}-v4.txt").write_text(
                    "1.1.1.0/24\n1.1.1.0/24\n", encoding="utf-8"
                )
                (data / f"{provider}-v6.txt").write_text(
                    "2001:4860:4801::/48\n2001:4860:4801::/48\n", encoding="utf-8"
                )
            (data / "all-cloud-v4.txt").write_text("1.1.1.0/24\n", encoding="utf-8")
            (data / "all-cloud-v6.txt").write_text("2001:4860:4801::/48\n", encoding="utf-8")
            counts = self.engine.generate_profiles(output_dir=out, data_dir=data)
            self.assertEqual(counts["full-v4"], 1)
            self.assertEqual(counts["full-v6"], 1)
            self.assertEqual(
                (out / "performance-v4.txt").read_text(encoding="utf-8"),
                "1.1.1.0/24\n",
            )
            self.assertEqual(
                (out / "performance-v6.txt").read_text(encoding="utf-8"),
                "2001:4860:4801::/48\n",
            )


if __name__ == "__main__":
    unittest.main()
