import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dpi_classifier.py"

def load_module():
    spec = importlib.util.spec_from_file_location("dpi_classifier", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class DPIClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_module()

    def test_exact_statuses(self):
        c = self.engine.classify_message
        self.assertEqual(c("tcp 16-20: not detected"), "safe")
        self.assertEqual(c("tcp 16-20: unlikely"), "unlikely")
        self.assertEqual(c("tcp 16-20: possible detected"), "possible")
        self.assertEqual(c("tcp 16-20: detected, method: 1"), "detected")
        self.assertEqual(c("alived: no"), "dead")
        self.assertEqual(c("alived: yes"), "alive")
        self.assertEqual(c("alived: unknown"), "unknown")

    def test_confirmed_detection_wins_over_other_observations(self):
        lines = [
            "[12:00] DPI checking(#US.TEST-01)/INFO: alived: yes",
            "[12:01] DPI checking(#US.TEST-01)/INFO: tcp 16-20: possible detected",
            "[12:02] DPI checking(#US.TEST-01)/INFO: tcp 16-20: detected, method: 2",
        ]
        report = self.engine.parse(lines)
        node = report["nodes"]["US.TEST-01"]
        self.assertEqual(node["status"], "detected")
        self.assertEqual(node["methods"], ["2"])

    def test_possible_is_not_confirmed(self):
        lines = [
            "[12:00] DPI checking(#US.TEST-02)/INFO: alived: yes",
            "[12:01] DPI checking(#US.TEST-02)/INFO: tcp 16-20: possible detected",
        ]
        report = self.engine.parse(lines)
        self.assertEqual(report["nodes"]["US.TEST-02"]["status"], "possible")
        self.assertNotEqual(report["nodes"]["US.TEST-02"]["status"], "detected")

    def test_duplicate_observations_are_merged(self):
        lines = [
            "[12:00] DPI checking(#US.TEST-03)/INFO: alived: yes",
            "[12:01] DPI checking(#US.TEST-03)/INFO: alived: yes",
            "[12:02] DPI checking(#US.TEST-03)/INFO: tcp 16-20: not detected",
        ]
        report = self.engine.parse(lines)
        self.assertEqual(report["nodes"]["US.TEST-03"]["status"], "safe")
        self.assertEqual(report["nodes"]["US.TEST-03"]["observations"], 3)
        self.assertEqual(report["counts"]["safe"], 1)

if __name__ == "__main__":
    unittest.main()
