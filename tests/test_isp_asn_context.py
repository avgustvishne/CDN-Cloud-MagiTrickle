import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class IspAsnContextTests(unittest.TestCase):
    def test_rostelecom_asn_is_configured_as_network_context(self):
        config = json.loads(
            (ROOT / "config" / "isp_profiles.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["schema_version"], 1)
        self.assertTrue(config["enabled"])
        self.assertIn(
            {"asn": 12389, "name": "Rostelecom", "country": "RU"},
            config["asns"],
        )

    def test_isp_context_does_not_become_a_cloud_provider(self):
        import importlib.util

        path = ROOT / "scripts" / "import_dpi_results.py"
        spec = importlib.util.spec_from_file_location("import_dpi_results", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertIsNone(module.provider_for({"AS": "AS12389", "Org": "PJSC Rostelecom"}))
        context = module.load_isp_context()
        self.assertTrue(context["enabled"])
        self.assertEqual(context["asns"][0]["asn"], 12389)


if __name__ == "__main__":
    unittest.main()
