import unittest
from datetime import datetime, timezone

from onboardops.reporting import build_operations_report


class OperationsReportTests(unittest.TestCase):
    def test_report_counts_and_aging_are_deterministic(self):
        now = datetime(2026, 10, 24, tzinfo=timezone.utc)
        cases = [
            {"case_id": "CASE-1", "status": "in_progress", "lifecycle": "onboarding",
             "priority": "urgent", "assigned_to": None, "created_at": "2026-10-10T00:00:00Z",
             "request_data": {"employee_id": "DEMO-1"}},
            {"case_id": "CASE-2", "status": "completed", "lifecycle": "offboarding",
             "priority": "low", "assigned_to": "tech", "created_at": "2026-10-01T00:00:00Z"},
            {"case_id": "CASE-3", "status": "blocked", "lifecycle": "transfer",
             "created_at": "invalid"},
        ]
        report = build_operations_report(cases, now=now)
        self.assertEqual((report["total"], report["active"], report["closed"]), (3, 2, 1))
        self.assertEqual(report["unassigned_active"], 2)
        self.assertEqual(report["high_priority_active"], 1)
        self.assertEqual(report["status_counts"]["blocked"], 1)
        self.assertEqual(report["priority_counts"]["normal"], 1)
        self.assertEqual([c["case_id"] for c in report["aging_cases"]], ["CASE-1"])
        self.assertEqual(report["aging_cases"][0]["age_days"], 14.0)
        self.assertNotIn("request_data", report["aging_cases"][0])

    def test_empty_report_has_stable_priority_keys(self):
        report = build_operations_report([], now=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["priority_counts"], {"urgent": 0, "high": 0, "normal": 0, "low": 0})
        self.assertEqual(report["aging_cases"], [])


if __name__ == "__main__":
    unittest.main()
