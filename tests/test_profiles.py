import importlib.util
import json
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

    def test_profiles_have_intended_scope(self):
        expected = {
            "minimal": {
                "cloudflare",
                "akamai",
                "fastly",
                "cdn77",
                "gcore",
            },
            "performance": {
                "cloudflare",
                "akamai",
                "fastly",
                "cdn77",
                "gcore",
                "digitalocean",
                "scaleway",
            },
            "balanced": {
                "cloudflare",
                "akamai",
                "fastly",
                "cdn77",
                "gcore",
                "digitalocean",
                "hetzner",
                "ovh",
                "vultr",
                "scaleway",
            },
        }
        for profile, providers in expected.items():
            self.assertEqual(set(self.engine.PROFILES[profile]), providers)

        self.assertTrue(
            set(self.engine.PROFILES["minimal"])
            < set(self.engine.PROFILES["performance"])
            < set(self.engine.PROFILES["balanced"])
        )
        for profile in ("minimal", "performance", "balanced"):
            selected = set(self.engine.PROFILES[profile])
            self.assertNotIn("aws", selected)
            self.assertNotIn("microsoft", selected)
            self.assertNotIn("oracle", selected)
            self.assertNotIn("alibaba", selected)

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

    def test_intersection_and_subset_are_exact(self):
        left = ["8.8.8.0/24"]
        right = ["8.8.8.0/25", "1.1.1.0/24"]
        self.assertEqual(
            self.engine.intersection_coverage(left, right, 4),
            128,
        )
        self.assertTrue(self.engine.is_coverage_subset(right[:1], left, 4))
        self.assertFalse(self.engine.is_coverage_subset(right, left, 4))

    def test_profile_metrics_report_incremental_coverage(self):
        previous = ["8.8.8.0/24"]
        current = ["8.8.8.0/23"]
        metrics = self.engine.profile_metrics(current, previous, 4)
        self.assertEqual(metrics["prefixes"], 1)
        self.assertEqual(metrics["coverage_ips"], 512)
        self.assertEqual(metrics["overlap_ips"], 256)
        self.assertEqual(metrics["new_coverage_ips"], 256)
        self.assertTrue(metrics["is_superset"])

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
            report = json.loads((data / "profile-intelligence.json").read_text(encoding="utf-8"))
            self.assertEqual(report["schema_version"], 1)
            self.assertEqual(report["policy_version"], self.engine.PROFILE_POLICY_VERSION)
            self.assertEqual(report["anomalies"], [])
            for family in (4, 6):
                for name in self.engine.PROFILE_ORDER:
                    self.assertTrue(report["profiles"][f"{name}-v{family}"]["is_superset"] if name != "minimal" else True)

    def test_anomaly_gate_detects_large_unexpected_change(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td)
            previous = {
                "schema_version": 1,
                "policy_version": self.engine.PROFILE_POLICY_VERSION,
                "profiles": {
                    f"{name}-v4": {"prefixes": 100, "coverage_ips": 1000}
                    for name in self.engine.PROFILE_ORDER
                },
            }
            (data / "profile-intelligence.json").write_text(
                json.dumps(previous),
                encoding="utf-8",
            )
            profile_data = {
                name: {
                    4: [f"8.8.{index}.0/24" for index in range(10)],
                    6: ["2001:4860:4801::/48"],
                }
                for name in self.engine.PROFILE_ORDER
            }
            with self.assertRaises(RuntimeError):
                self.engine.build_profile_intelligence(
                    profile_data,
                    {name: list(self.engine.PROFILES[name]) for name in self.engine.PROFILE_ORDER},
                    data,
                )


if __name__ == "__main__":
    unittest.main()
