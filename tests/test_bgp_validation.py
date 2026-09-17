import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bgpstream_validate.py"
spec = importlib.util.spec_from_file_location("bgp_validation", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Item:
    def __init__(self, collector_id, ts_end, url):
        self.collector_id = collector_id
        self.ts_end = ts_end
        self.url = url


class BgpValidationTests(unittest.TestCase):
    def test_select_update_files_deduplicates_collectors_and_prefers_latest(self):
        items = [
            Item("rrc00", "2026-09-17T05:00:00Z", "old-rrc00"),
            Item("rrc00", "2026-09-17T05:05:00Z", "new-rrc00"),
            Item("route-views2", "2026-09-17T05:04:00Z", "rv2"),
            Item("route-views3", "2026-09-17T05:03:00Z", "rv3"),
        ]
        selected = module.select_update_files(items, 3)
        self.assertEqual(
            [(x.collector_id, x.url) for x in selected],
            [
                ("rrc00", "new-rrc00"),
                ("route-views2", "rv2"),
                ("route-views3", "rv3"),
            ],
        )

    def test_select_update_files_is_bounded(self):
        items = [Item(f"collector-{i}", f"2026-09-17T05:{i:02d}:00Z", str(i)) for i in range(20)]
        selected = module.select_update_files(items, 5)
        self.assertEqual(len(selected), 5)
        self.assertEqual(len({x.collector_id for x in selected}), 5)

    def test_load_asns_deduplicates_provider_asns(self):
        pairs = module.load_asns(64)
        asns = [asn for _, asn in pairs]
        self.assertEqual(len(asns), len(set(asns)))
        self.assertTrue(pairs)


if __name__ == "__main__":
    unittest.main()
