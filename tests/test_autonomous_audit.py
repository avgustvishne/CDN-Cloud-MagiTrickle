import importlib.util
import unittest

spec = importlib.util.spec_from_file_location("autonomous_audit", "scripts/autonomous_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AutonomousAuditTests(unittest.TestCase):
    def test_required_gates_are_present(self):
        self.assertFalse([x for x, token in audit.REQUIRED.items() if token not in audit.TEXT])

    def test_forbidden_destructive_operations_are_absent(self):
        self.assertFalse([x for x, token in audit.FORBIDDEN.items() if token in audit.TEXT])


if __name__ == "__main__":
    unittest.main()
