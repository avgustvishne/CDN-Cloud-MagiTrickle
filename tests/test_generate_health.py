import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"generate_health.py"

def load_module():
    spec=importlib.util.spec_from_file_location("generate_health",SCRIPT); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class GenerateHealthTests(unittest.TestCase):
    def setUp(self): self.mod=load_module()
    def test_all_ok_sources_render_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"source-health.json"; out=Path(tmp)/"HEALTH.md"
            source.write_text(json.dumps({"checked_at":"2026-01-01 00:00:00 UTC","sources":{"AWS":{"ok":True,"bytes":2048},"RIPEstat":{"ok":True,"bytes":512}}}),encoding="utf-8")
            with patch.object(self.mod,"SOURCE",source),patch.object(self.mod,"OUT",out): self.mod.main()
            content=out.read_text(encoding="utf-8")
        self.assertIn("2/2 источников отвечают",content); self.assertIn("AWS",content); self.assertIn("✅",content); self.assertNotIn("❌",content)
    def test_failed_source_shown_with_dash_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"source-health.json"; out=Path(tmp)/"HEALTH.md"
            source.write_text(json.dumps({"checked_at":"2026-01-01 00:00:00 UTC","sources":{"Broken":{"ok":False,"error":"timeout"}}}),encoding="utf-8")
            with patch.object(self.mod,"SOURCE",source),patch.object(self.mod,"OUT",out): self.mod.main()
            content=out.read_text(encoding="utf-8")
        self.assertIn("0/1 источников отвечают",content); self.assertIn("❌",content); self.assertIn("| Broken | ❌ | — |",content)
    def test_missing_source_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"does-not-exist.json"; out=Path(tmp)/"HEALTH.md"
            with patch.object(self.mod,"SOURCE",source),patch.object(self.mod,"OUT",out): result=self.mod.main()
        self.assertEqual(result,0); self.assertFalse(out.exists())
    def test_fmt_bytes_scales_units(self): self.assertEqual(self.mod.fmt_bytes(500),"500 B"); self.assertEqual(self.mod.fmt_bytes(2048),"2.0 KB"); self.assertEqual(self.mod.fmt_bytes(5*1024*1024),"5.0 MB")

if __name__=="__main__": unittest.main()
