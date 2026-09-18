import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_domain_subscriptions as generator


class DomainConsensusTests(unittest.TestCase):
    def test_parse_domains_normalizes_and_rejects_invalid(self):
        data = b"""
        # comment
        DOMAIN-SUFFIX,Example.COM
        *.cdn.example.com
        valid.example.org.
        invalid
        localhost
        """
        self.assertEqual(
            generator.parse_domains(data),
            {"example.com", "cdn.example.com", "valid.example.org"},
        )

    def test_consensus_requires_two_sources(self):
        feeds = {
            "a": {"one.example", "two.example"},
            "b": {"two.example", "three.example"},
            "c": {"two.example"},
        }
        self.assertEqual(
            generator.build_consensus(feeds, minimum_sources=2),
            ["two.example"],
        )

    def test_registry_contains_multiple_domain_feeds(self):
        registry = json.loads(
            (ROOT / "config" / "source_registry.json").read_text(encoding="utf-8")
        )
        feeds = generator.domain_feeds(registry)
        self.assertGreaterEqual(len(feeds), 4)

    def test_atomic_writer_preserves_deterministic_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "domains.txt"
            generator.write_atomic(path, ["a.example", "z.example"])
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "a.example\nz.example\n",
            )


if __name__ == "__main__":
    unittest.main()
