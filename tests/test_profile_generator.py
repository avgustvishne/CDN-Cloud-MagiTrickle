import ipaddress
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from profile_generator import collapse, covered, minimalize

class ProfileGeneratorTests(unittest.TestCase):
    def test_collapse_removes_redundant_prefixes(self):
        nets=[ipaddress.ip_network("192.0.2.0/25"),ipaddress.ip_network("192.0.2.128/25")]
        self.assertEqual(collapse(nets),[ipaddress.ip_network("192.0.2.0/24")])

    def test_minimal_never_expands_coverage(self):
        nets=[ipaddress.ip_network("192.0.2.0/26"),ipaddress.ip_network("192.0.2.64/26")]
        result=minimalize(nets)
        self.assertTrue(all(covered(n,nets) for n in result))

if __name__=="__main__":
    unittest.main()
