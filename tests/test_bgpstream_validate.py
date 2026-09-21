import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bgpstream_validate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("bgpstream_validate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BgpstreamValidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_query_uses_only_supported_broker_arguments(self):
        calls = []

        class FakeBroker:
            def query(self, **kwargs):
                calls.append(kwargs)
                return []

        self.mod.query_update_files(
            FakeBroker(),
            "2026-09-21T00:00:00Z",
            "2026-09-21T00:30:00Z",
            "routeviews",
        )

        self.assertEqual(
            calls,
            [{
                "ts_start": "2026-09-21T00:00:00Z",
                "ts_end": "2026-09-21T00:30:00Z",
                "project": "routeviews",
                "data_type": "updates",
            }],
        )

    def test_select_update_files_keeps_latest_file_per_collector(self):
        class Item:
            def __init__(self, collector_id, ts_end, url):
                self.collector_id = collector_id
                self.ts_end = ts_end
                self.url = url

        items = [
            Item("c1", "2026-09-21T00:01:00Z", "https://example/c1-old"),
            Item("c1", "2026-09-21T00:02:00Z", "https://example/c1-new"),
            Item("c2", "2026-09-21T00:03:00Z", "https://example/c2"),
        ]
        selected = self.mod.select_update_files(items, 2)
        self.assertEqual([x.url for x in selected], [
            "https://example/c2",
            "https://example/c1-new",
        ])


if __name__ == "__main__":
    unittest.main()
