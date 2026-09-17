import unittest

from scripts.rollback_guard import VALIDATION_ONLY, address_coverage, dataset_metrics


class RollbackCoverageTests(unittest.TestCase):
    def test_coverage_uses_union_not_prefix_count(self):
        text = "10.0.0.0/25\n10.0.0.128/25\n"
        self.assertEqual(address_coverage(text, 4), 256)

    def test_validation_samples_are_excluded_from_guard(self):
        self.assertEqual(
            VALIDATION_ONLY,
            {"asn-confirmed-v4.txt", "asn-confirmed-v6.txt"},
        )

    def test_reaggregation_does_not_trigger_coverage_drop(self):
        previous = "10.0.0.0/25\n10.0.0.128/25\n"
        current = "10.0.0.0/24\n"
        metrics = dataset_metrics(previous, current)
        self.assertEqual(metrics["previous"], 2)
        self.assertEqual(metrics["current"], 1)
        self.assertEqual(metrics["coverage"]["4"]["previous"], 256)
        self.assertEqual(metrics["coverage"]["4"]["current"], 256)
        self.assertEqual(metrics["coverage"]["4"]["drop_percent"], 0)

    def test_real_address_space_loss_is_detected(self):
        previous = "10.0.0.0/24\n"
        current = "10.0.0.0/25\n"
        metrics = dataset_metrics(previous, current)
        self.assertEqual(metrics["coverage"]["4"]["drop_percent"], 50.0)
        self.assertEqual(metrics["coverage"]["4"]["ratio"], 0.5)

    def test_ipv4_and_ipv6_are_measured_separately(self):
        previous = "10.0.0.0/24\n2001:db8::/32\n"
        current = "10.0.0.0/24\n2001:db8::/33\n"
        metrics = dataset_metrics(previous, current)
        self.assertEqual(metrics["coverage"]["4"]["drop_percent"], 0)
        self.assertEqual(metrics["coverage"]["6"]["drop_percent"], 50.0)

    def test_invalid_lines_do_not_break_metric_calculation(self):
        previous = "10.0.0.0/24\nnot-a-cidr\n"
        current = "10.0.0.0/24\n"
        metrics = dataset_metrics(previous, current)
        self.assertEqual(metrics["coverage"]["4"]["drop_percent"], 0)


if __name__ == "__main__":
    unittest.main()
