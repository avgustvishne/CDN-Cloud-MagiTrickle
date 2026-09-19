import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression_gate.py"


class RegressionGateTests(unittest.TestCase):
    def run_gate(self, old_root, new_root):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(old_root), str(new_root)],
            capture_output=True,
            text=True,
            check=False,
        )

    def write(self, root, relative, text):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_stale_published_profile_uses_source_backed_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old"
            new = root / "new"

            self.write(old, "cloudflare-v4.txt", "10.0.0.0/8\n")
            self.write(
                old,
                "presets/balanced-v4.txt",
                "10.0.0.0/8\n192.0.2.0/24\n",
            )
            self.write(new, "cloudflare-v4.txt", "10.0.0.0/8\n")
            self.write(new, "presets/balanced-v4.txt", "10.0.0.0/8\n")

            result = self.run_gate(old, new)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("stale published baseline detected", result.stdout)

    def test_source_backed_regression_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old"
            new = root / "new"

            self.write(old, "cloudflare-v4.txt", "10.0.0.0/8\n")
            self.write(old, "presets/balanced-v4.txt", "10.0.0.0/8\n")
            self.write(new, "cloudflare-v4.txt", "192.0.2.0/24\n")
            self.write(new, "presets/balanced-v4.txt", "192.0.2.0/24\n")

            result = self.run_gate(old, new)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("coverage 16777216 -> 256", result.stdout)


if __name__ == "__main__":
    unittest.main()
