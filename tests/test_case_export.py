import json
import unittest
from datetime import datetime, timezone

from onboardops.case_export import build_case_export, render_case_export_json


class CaseExportTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            "case_id": "CASE-DEMO-1", "lifecycle": "onboarding", "status": "in_progress",
            "priority": "high", "assigned_to": "tech@example.invalid",
            "requester_id": "requester", "summary": "Synthetic onboarding",
            "created_at": "2026-10-20T10:00:00+00:00",
            "updated_at": "2026-10-21T10:00:00+00:00", "version": 3,
            "request_data": {"employee_id": "DEMO-1", "api_token": "[REDACTED]"},
            "internal_connection": "must not export",
        }
        self.events = [
            {"event_type": "case.created", "actor_id": "requester",
             "from_status": None, "to_status": "draft", "occurred_at": "2026-10-20T10:00:00Z",
             "metadata": {"raw_payload": "private-payload"}},
            {"event_type": "case.triage_updated", "actor_id": "dispatcher",
             "from_status": None, "to_status": None, "occurred_at": "2026-10-21T10:00:00Z",
             "metadata": {"priority_from": "normal", "priority_to": "high",
                          "secret_token": "must not export"}},
        ]

    def test_export_has_versioned_case_packet_and_newest_first_history(self):
        packet = build_case_export(
            self.case, self.events,
            exported_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
        self.assertEqual(packet["schema_version"], 1)
        self.assertEqual(packet["case"]["case_id"], "CASE-DEMO-1")
        self.assertEqual(packet["history"][0]["event"], "Priority / assignment updated")
        self.assertEqual(packet["exported_at"], "2026-10-24T00:00:00+00:00")
        self.assertNotIn("internal_connection", packet["case"])

    def test_export_does_not_include_raw_event_metadata(self):
        rendered = render_case_export_json(build_case_export(self.case, self.events))
        self.assertNotIn("private-payload", rendered)
        self.assertNotIn("must not export", rendered)
        self.assertIn("DEMO-1", rendered)
        self.assertEqual(json.loads(rendered)["schema_version"], 1)

    def test_render_is_deterministic_for_a_fixed_packet(self):
        packet = build_case_export(
            self.case, self.events,
            exported_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
        self.assertEqual(render_case_export_json(packet), render_case_export_json(packet))



    def test_export_redacts_sensitive_fields_from_legacy_request_data(self):
        legacy_case = dict(self.case)
        legacy_case["request_data"] = {
            "employee_id": "DEMO-1",
            "api_token": "legacy-live-token",
            "nested": [{"client_secret": "legacy-secret", "department": "IT"}],
        }
        rendered = render_case_export_json(build_case_export(legacy_case, self.events))
        self.assertNotIn("legacy-live-token", rendered)
        self.assertNotIn("legacy-secret", rendered)
        packet = json.loads(rendered)
        self.assertEqual(packet["case"]["request_data"]["api_token"], "[REDACTED]")
        self.assertEqual(packet["case"]["request_data"]["nested"][0]["client_secret"], "[REDACTED]")
        self.assertEqual(packet["case"]["request_data"]["nested"][0]["department"], "IT")

if __name__ == "__main__":
    unittest.main()
