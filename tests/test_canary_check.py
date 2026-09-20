import importlib.util
import ipaddress
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"canary_check.py"

def load_module():
    spec=importlib.util.spec_from_file_location("canary_check",SCRIPT); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class IpInNetworksTests(unittest.TestCase):
    def setUp(self): self.mod=load_module()
    def test_matching_ipv4_is_found(self): self.assertTrue(self.mod.ip_in_networks("149.154.167.99",{4:[ipaddress.ip_network("149.154.160.0/20")],6:[]}))
    def test_non_matching_ipv4_is_not_found(self): self.assertFalse(self.mod.ip_in_networks("8.8.8.8",{4:[ipaddress.ip_network("149.154.160.0/20")],6:[]}))
    def test_ipv6_checked_against_ipv6_list_only(self):
        n={4:[ipaddress.ip_network("1.2.3.0/24")],6:[ipaddress.ip_network("2606:4700::/32")]}; self.assertTrue(self.mod.ip_in_networks("2606:4700::1",n)); self.assertFalse(self.mod.ip_in_networks("2001:4860::1",n))

class LoadNetworksTests(unittest.TestCase):
    def setUp(self): self.mod=load_module()
    def test_loads_both_families_and_skips_bad_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp)/"data"; data.mkdir(); (data/"acme-v4.txt").write_text("1.2.3.0/24\nnot-a-cidr\n"); (data/"acme-v6.txt").write_text("2606:4700::/32\n")
            with patch.object(self.mod,"DATA",data): networks=self.mod.load_networks("acme")
        self.assertEqual(networks[4],[ipaddress.ip_network("1.2.3.0/24")]); self.assertEqual(networks[6],[ipaddress.ip_network("2606:4700::/32")])
    def test_missing_provider_files_return_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp)/"data"; data.mkdir()
            with patch.object(self.mod,"DATA",data): networks=self.mod.load_networks("nonexistent")
        self.assertEqual(networks,{4:[],6:[]})

class MainAdvisoryBehaviorTests(unittest.TestCase):
    def setUp(self): self.mod=load_module()
    def test_main_never_fails_even_when_every_canary_misses(self):
        with patch.object(self.mod,"resolve_ips",return_value=(["203.0.113.1"],None)),patch.object(self.mod,"load_networks",return_value={4:[],6:[]}): self.assertEqual(self.mod.main(),0)
    def test_main_handles_dns_failure_gracefully(self):
        with patch.object(self.mod,"resolve_ips",return_value=(None,"Name or service not known")): self.assertEqual(self.mod.main(),0)

if __name__=="__main__": unittest.main()
