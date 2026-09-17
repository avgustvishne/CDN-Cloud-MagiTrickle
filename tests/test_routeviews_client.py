import concurrent.futures
import json
import unittest
from unittest.mock import patch

from scripts import routeviews_client


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(["1.2.3.0/24", "2001:db8::/32"]).encode()


class RouteViewsClientTests(unittest.TestCase):
    def setUp(self):
        routeviews_client.clear_cache()
        routeviews_client._last_request_at = 0.0

    def test_fetches_both_families_with_one_request_per_asn(self):
        with patch.object(routeviews_client.urllib.request, "urlopen", return_value=FakeResponse()) as mocked:
            first = routeviews_client.routeviews_prefixes("13335")
            second = routeviews_client.routeviews_prefixes("13335")

        self.assertEqual(first, ["1.2.3.0/24", "2001:db8::/32"])
        self.assertEqual(second, first)
        mocked.assert_called_once()
        self.assertIn("/asn/13335", mocked.call_args.args[0].full_url)
        self.assertNotIn("?af=", mocked.call_args.args[0].full_url)

    def test_concurrent_same_asn_is_fetched_once(self):
        with patch.object(routeviews_client.urllib.request, "urlopen", return_value=FakeResponse()) as mocked:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(routeviews_client.routeviews_prefixes, ["13335"] * 8))

        self.assertTrue(all(result == results[0] for result in results))
        mocked.assert_called_once()


if __name__ == "__main__":
    unittest.main()
