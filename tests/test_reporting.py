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

    def test_approval_queue_is_oldest_first_and_excludes_request_payloads(self):
        now = datetime(2026, 10, 24, tzinfo=timezone.utc)
        cases = [
            {"case_id": "CASE-NEW", "status": "pending_approval", "lifecycle": "onboarding",
             "priority": "normal", "assigned_to": None, "created_at": "2026-10-23T12:00:00Z",
             "request_data": {"employee_id": "DEMO-SECRET"}},
            {"case_id": "CASE-OLD", "status": "pending_approval", "lifecycle": "offboarding",
             "priority": "urgent", "assigned_to": "tech", "created_at": "2026-10-20T00:00:00Z"},
            {"case_id": "CASE-DONE", "status": "completed", "lifecycle": "transfer",
             "created_at": "2026-10-01T00:00:00Z"},
            {"case_id": "CASE-BAD-TIME", "status": "pending_approval", "created_at": "invalid"},
        ]
        report = build_operations_report(cases, now=now)
        queue = report["approval_queue"]
        self.assertEqual([case["case_id"] for case in queue], ["CASE-OLD", "CASE-NEW"])
        self.assertEqual(queue[0]["age_hours"], 96.0)
        self.assertEqual(queue[1]["age_hours"], 12.0)
        self.assertEqual(queue[0]["priority"], "urgent")
        self.assertNotIn("request_data", queue[0])
        self.assertNotIn("DEMO-SECRET", str(queue))

    def test_empty_report_has_stable_priority_keys(self):
        report = build_operations_report([], now=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["priority_counts"], {"urgent": 0, "high": 0, "normal": 0, "low": 0})
        self.assertEqual(report["aging_cases"], [])
        self.assertEqual(report["approval_queue"], [])


if __name__ == "__main__":
    unittest.main()
