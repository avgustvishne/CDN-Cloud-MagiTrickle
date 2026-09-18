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

            # Give every configured provider a distinct prefix. The stale
            # ALL-CLOUD fixture deliberately contains a different prefix so
            # FULL cannot accidentally depend on that aggregate.
            for index, provider in enumerate(self.engine.PROVIDERS, start=1):
                (data / f"{provider}-v4.txt").write_text(
                    f"1.1.{index}.0/24\n1.1.{index}.0/24\n", encoding="utf-8"
                )
                (data / f"{provider}-v6.txt").write_text(
                    f"2606:4700:{index:x}::/48\n2606:4700:{index:x}::/48\n",
                    encoding="utf-8",
                )
            (data / "all-cloud-v4.txt").write_text("9.9.9.0/24\n", encoding="utf-8")
            (data / "all-cloud-v6.txt").write_text(
                "2606:4700:ffff::/48\n", encoding="utf-8"
            )

            counts = self.engine.generate_profiles(output_dir=out, data_dir=data)
            # Adjacent prefixes may be legitimately re-aggregated, so assert
            # exact address-space coverage rather than raw prefix count.
            self.assertEqual(counts["full-v4"], len(self.engine.collapse(
                [f"1.1.{index}.0/24" for index in range(1, len(self.engine.PROVIDERS) + 1)], 4
            )))
            self.assertEqual(counts["full-v6"], len(self.engine.collapse(
                [f"2606:4700:{index:x}::/48" for index in range(1, len(self.engine.PROVIDERS) + 1)], 6
            )))
            self.assertEqual(counts["stable-v4"], counts["full-v4"])
            self.assertEqual(counts["stable-v6"], counts["full-v6"])
            self.assertEqual(
                self.engine.address_space_coverage(
                    (out / "full-v4.txt").read_text(encoding="utf-8").splitlines(), 4
                ),
                len(self.engine.PROVIDERS) * 256,
            )
            self.assertEqual(
                self.engine.address_space_coverage(
                    (out / "full-v6.txt").read_text(encoding="utf-8").splitlines(), 6
                ),
                len(self.engine.PROVIDERS) * 2**80,
            )
            full_v4 = (out / "full-v4.txt").read_text(encoding="utf-8")
            full_v6 = (out / "full-v6.txt").read_text(encoding="utf-8")
            self.assertNotIn("9.9.9.0/24", full_v4)
            self.assertNotIn("2001:4860:ffff::/48", full_v6)
            report = json.loads((data / "profile-intelligence.json").read_text(encoding="utf-8"))
            self.assertEqual(report["schema_version"], 1)
            self.assertEqual(report["policy_version"], self.engine.PROFILE_POLICY_VERSION)
            self.assertEqual(report["anomalies"], [])
            for family in (4, 6):
                for name in self.engine.PROFILE_ORDER:
                    self.assertTrue(
                        report["profiles"][f"{name}-v{family}"]["is_superset"]
                        if name != "minimal"
                        else True
                    )

    def test_stable_profile_keeps_only_previous_full_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td) / "data"
            out = data / "presets"
            data.mkdir()

            for provider in self.engine.PROVIDERS:
                (data / f"{provider}-v4.txt").write_text(
                    "8.8.8.0/24\n", encoding="utf-8"
                )
                (data / f"{provider}-v6.txt").write_text(
                    "2001:4860:4860::/48\n", encoding="utf-8"
                )

            out.mkdir()
            (out / "full-v4.txt").write_text(
                "8.8.8.0/24\n9.9.9.0/24\n", encoding="utf-8"
            )
            (out / "full-v6.txt").write_text(
                "2001:4860:4860::/48\n2606:4700::/48\n", encoding="utf-8"
            )

            counts = self.engine.generate_profiles(output_dir=out, data_dir=data)
            stable4 = (out / "stable-v4.txt").read_text(encoding="utf-8")
            stable6 = (out / "stable-v6.txt").read_text(encoding="utf-8")
            self.assertEqual(stable4, "8.8.8.0/24\n")
            self.assertEqual(stable6, "2001:4860:4860::/48\n")
            self.assertEqual(counts["stable-v4"], 1)
            self.assertEqual(counts["stable-v6"], 1)

            report = json.loads((data / "profile-intelligence.json").read_text(encoding="utf-8"))
            self.assertFalse(report["stability_profile"]["profiles"]["stable-v4"]["bootstrap"])
            self.assertEqual(
                report["stability_profile"]["profiles"]["stable-v4"]["retention_coverage_ratio"],
                0.5,
            )

    def test_dpi_qualified_candidates_are_promoted_only_with_fresh_evidence(self):
        from datetime import datetime, timezone

        with tempfile.TemporaryDirectory() as td:
            data = Path(td) / "data"
            out = data / "presets"
            data.mkdir()

            base = {
                "cloudflare": "1.1.1.0/24",
                "akamai": "1.1.2.0/24",
                "fastly": "1.1.3.0/24",
                "cdn77": "1.1.4.0/24",
                "gcore": "1.1.5.0/24",
                "digitalocean": "1.1.6.0/24",
                "scaleway": "1.1.7.0/24",
                "hetzner": "2.2.2.0/24",
                "ovh": "3.3.3.0/24",
                "melbicom": "4.4.4.0/24",
                "buyvm": "5.5.5.0/24",
                "contabo": "6.6.6.0/24",
                "vultr": "7.7.7.0/24",
            }
            for provider in self.engine.PROVIDERS:
                value = base.get(provider, "9.9.9.0/24")
                (data / f"{provider}-v4.txt").write_text(value + "\n", encoding="utf-8")
                (data / f"{provider}-v6.txt").write_text(
                    "2001:4860:4801::/48\n", encoding="utf-8"
                )

            all_v4 = "\n".join(sorted(set(base.values()) | {"9.9.9.0/24"})) + "\n"
            (data / "all-cloud-v4.txt").write_text(all_v4, encoding="utf-8")
            (data / "all-cloud-v6.txt").write_text("2001:4860:4801::/48\n", encoding="utf-8")

            now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            report = {
                "schema_version": 1,
                "status": "ready",
                "checked_at": now,
                "qualified_prefixes": {
                    "hetzner": {"ipv4": ["2.2.2.0/24"]},
                    "ovh": {"ipv4": ["3.3.3.0/24"]},
                    "melbicom": {"ipv4": ["4.4.4.0/24"]},
                    "buyvm": {"ipv4": ["5.5.5.0/24"]},
                    "contabo": {"ipv4": ["6.6.6.0/24"]},
                },
            }
            (data / "dpi-intelligence.json").write_text(
                json.dumps(report), encoding="utf-8"
            )

            self.engine.generate_profiles(output_dir=out, data_dir=data)

            performance = (out / "performance-v4.txt").read_text(encoding="utf-8")
            balanced = (out / "balanced-v4.txt").read_text(encoding="utf-8")
            minimal = (out / "minimal-v4.txt").read_text(encoding="utf-8")
            self.assertIn("2.2.2.0/24", performance)
            self.assertIn("3.3.3.0/24", performance)
            self.assertIn("4.4.4.0/24", balanced)
            self.assertIn("5.5.5.0/24", balanced)
            self.assertIn("6.6.6.0/24", balanced)
            self.assertNotIn("2.2.2.0/24", minimal)
            self.assertNotIn("4.4.4.0/24", minimal)

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
