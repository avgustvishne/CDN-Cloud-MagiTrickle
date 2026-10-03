import importlib.util
import unittest

spec = importlib.util.spec_from_file_location("asn_discovery", "scripts/asn_discovery.py")
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


class ASNDiscoveryTests(unittest.TestCase):
    def test_load_config_maps_asns_to_providers(self):
        original = discovery.CONFIG
        try:
            import tempfile
            from pathlib import Path
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "providers.json"
                path.write_text('{"providers":{"aws":["16509"],"cloudflare":["13335"]}}', encoding="utf-8")
                discovery.CONFIG = path
                result = discovery.load_config()
                self.assertEqual(result[16509], {"aws"})
                self.assertEqual(result[13335], {"cloudflare"})
        finally:
            discovery.CONFIG = original

    def test_aggregate_requires_signal_and_never_returns_known_asn(self):
        known = {16509: {"aws"}, 13335: {"cloudflare"}}
        observations = [
            {
                "asn": 16509,
                "status": "OK",
                "neighbours": [
                    {"asn": 64500, "type": "right", "power": 4, "v4_peers": 20, "v6_peers": 10},
                    {"asn": 64501, "type": "right", "power": 1, "v4_peers": 1, "v6_peers": 0},
                    {"asn": 13335, "type": "right", "power": 50},
                ],
            },
            {
                "asn": 13335,
                "status": "OK",
                "neighbours": [
                    {"asn": 64500, "type": "left", "power": 3, "v4_peers": 10, "v6_peers": 0},
                ],
            },
        ]
        result = discovery.aggregate(observations, known)
        self.assertEqual([row["asn"] for row in result], ["AS64500"])
        self.assertEqual(result[0]["known_provider_connections"], 2)
        self.assertEqual(result[0]["status"], "candidate")
        self.assertEqual(result[0]["policy"], "human_review_required")

    def test_errors_are_ignored_without_affecting_candidates(self):
        known = {16509: {"aws"}}
        observations = [
            {"asn": 16509, "status": "ERROR", "error": "temporary"},
            {"asn": 16509, "status": "OK", "neighbours": []},
        ]
        self.assertEqual(discovery.aggregate(observations, known), [])


if __name__ == "__main__":
    unittest.main()
