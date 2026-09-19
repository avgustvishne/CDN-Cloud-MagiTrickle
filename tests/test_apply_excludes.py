import importlib.util
import ipaddress
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_excludes.py"

def load_module():
    spec = importlib.util.spec_from_file_location("apply_excludes", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class SubtractTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
    def net(self, s):
        return ipaddress.ip_network(s, strict=False)
    def test_disjoint_networks_are_kept(self):
        self.assertEqual(self.mod.subtract([self.net("10.0.0.0/24")], [self.net("192.168.0.0/24")]), [self.net("10.0.0.0/24")])
    def test_exact_match_is_fully_removed(self):
        self.assertEqual(self.mod.subtract([self.net("10.0.0.0/24")], [self.net("10.0.0.0/24")]), [])
    def test_exclude_bigger_than_entry_removes_entry(self):
        self.assertEqual(self.mod.subtract([self.net("10.0.0.0/24")], [self.net("10.0.0.0/16")]), [])
    def test_exclude_inside_entry_splits_it(self):
        result=self.mod.subtract([self.net("10.0.0.0/24")],[self.net("10.0.0.128/25")])
        self.assertEqual(sum(n.num_addresses for n in result),128)
    def test_multiple_excludes(self):
        result=self.mod.subtract([self.net("10.0.0.0/24")],[self.net("10.0.0.0/26"),self.net("10.0.0.192/26")])
        self.assertEqual(sum(n.num_addresses for n in result),128)
    def test_ipv6_and_ipv4_do_not_interfere(self):
        self.assertEqual(self.mod.subtract([self.net("10.0.0.0/24"),self.net("2001:db8::/32")],[self.net("10.0.0.0/24")]),[self.net("2001:db8::/32")])

class ProcessFileTests(unittest.TestCase):
    def setUp(self):
        self.mod=load_module()
    def test_process_file_rewrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"example-v4.txt"
            path.write_text("10.0.0.0/24\n192.168.1.0/24\n",encoding="utf-8")
            removed=self.mod.process_file(path,{4:[ipaddress.ip_network("10.0.0.0/24")],6:[]})
            self.assertEqual(removed,1)
            self.assertEqual(path.read_text(encoding="utf-8").splitlines(),["192.168.1.0/24"])
    def test_noop_without_excludes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"example-v4.txt"; original="10.0.0.0/24\n192.168.1.0/24\n"; path.write_text(original,encoding="utf-8")
            self.assertEqual(self.mod.process_file(path,{4:[],6:[]}),0)
            self.assertEqual(path.read_text(encoding="utf-8"),original)
    def test_load_excludes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"custom-exclude.txt"; path.write_text("# c\n\n10.0.0.0/24 # note\n2001:db8::/32\n",encoding="utf-8")
            result=self.mod.load_excludes(path)
            self.assertEqual(result[4],[self.net("10.0.0.0/24")]); self.assertEqual(result[6],[self.net("2001:db8::/32")])
    def test_invalid_cidr(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"custom-exclude.txt"; path.write_text("not-a-cidr\n",encoding="utf-8")
            with self.assertRaises(SystemExit): self.mod.load_excludes(path)

if __name__=="__main__":
    unittest.main()
