import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.status_report as status_report


class StatusReportTests(unittest.TestCase):
    def test_source_summary_handles_current_mapping_schema(self):
        payload = {
            "sources": {
                "AWS": {"ok": True},
                "Broken": {"ok": False},
                "Cloudflare": {"ok": True},
            },
            "checked_at": "2026-09-17 00:00:00 UTC",
        }
        with mock.patch.object(status_report, "load_json", return_value=payload):
            result = status_report.source_summary()
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["healthy"], 2)
        self.assertEqual(result["failed"], 1)

    def test_rendered_status_contains_core_sections(self):
        args = mock.Mock(publication="validated", failed_run="")
        with mock.patch.object(status_report, "source_summary", return_value={"total": 2, "healthy": 2, "failed": 0, "audited_providers": 2}), \
             mock.patch.object(status_report, "network_summary", return_value={"queried": 4, "confirmed": 4, "statuses": {"ok": 4}}), \
             mock.patch.object(status_report, "provider_summary", return_value=[{"provider": "AWS", "ipv4": 2, "ipv6": 1, "total": 3}]), \
             mock.patch.object(status_report, "load_json", side_effect=[{"aggregate": {"ipv4": 2, "ipv6": 1}, "engine": "test"}, {"datasets": {"all-cloud-v4": {"added": 1}}}, {}]), \
             mock.patch.object(status_report, "git_sha", return_value="abc123"), \
             mock.patch.object(status_report, "read_timestamp", return_value="2026-09-17 00:00:00 UTC"):
            result = status_report.build_status(args)
        text = status_report.render_markdown(result)
        self.assertIn("# CDN-Cloud-MagiTrickle — Status", text)
        self.assertIn("## 🟢 HEALTHY", text)
        self.assertIn("## Данные", text)
        self.assertIn("## Проверки", text)
        self.assertIn("data/status.json", text)

    def test_output_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = mock.Mock(publication="dry-run", failed_run="")
            with mock.patch.object(status_report, "ROOT", root), \
                 mock.patch.object(status_report, "DATA", root / "data"), \
                 mock.patch.object(status_report, "source_summary", return_value={"total": 0, "healthy": 0, "failed": 0, "audited_providers": 0}), \
                 mock.patch.object(status_report, "network_summary", return_value={"queried": 0, "confirmed": 0, "statuses": {}}), \
                 mock.patch.object(status_report, "provider_summary", return_value=[]), \
                 mock.patch.object(status_report, "load_json", side_effect=[{"aggregate": {}, "engine": "test"}, {}, {}]), \
                 mock.patch.object(status_report, "git_sha", return_value="test"), \
                 mock.patch.object(status_report, "read_timestamp", return_value="unknown"):
                (root / "data").mkdir()
                status_report.main.__globals__["ROOT"] = root
                status_report.main.__globals__["DATA"] = root / "data"
                with mock.patch("sys.argv", ["status_report.py", "--output-json", "data/status.json", "--output-md", "STATUS.md"]):
                    status_report.main()
            parsed = json.loads((root / "data/status.json").read_text(encoding="utf-8"))
            self.assertEqual(parsed["schema_version"], 1)
            self.assertTrue((root / "STATUS.md").exists())


if __name__ == "__main__":
    unittest.main()
