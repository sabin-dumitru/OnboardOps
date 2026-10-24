import unittest
from onboardops.audit_view import describe_event


class AuditViewTests(unittest.TestCase):
    def test_triage_event_has_human_readable_changes(self):
        event = describe_event({
            "event_type": "case.triage_updated", "actor_id": "dispatcher",
            "from_status": None, "to_status": None, "occurred_at": "2026-10-24T00:00:00Z",
            "metadata": {"priority_from": "normal", "priority_to": "urgent",
                         "assigned_to_from": None, "assigned_to_to": "tech@example.invalid",
                         "unapproved_secret": "must not be shown"},
        })
        self.assertEqual(event["event"], "Priority / assignment updated")
        self.assertIn("Priority: normal → urgent", event["details"])
        self.assertIn("Assignment: Unassigned → tech@example.invalid", event["details"])
        self.assertNotIn("must not be shown", str(event))

    def test_unknown_event_metadata_is_not_rendered(self):
        event = describe_event({"event_type": "unexpected.event", "actor_id": "operator",
                                "metadata": {"token": "private-value", "raw_payload": "private-payload"}})
        self.assertEqual(event["event"], "Other event")
        self.assertEqual(event["details"], "No additional display details")
        self.assertNotIn("private-value", str(event))
        self.assertNotIn("private-payload", str(event))

    def test_status_transition_is_explained(self):
        event = describe_event({"event_type": "case.status_changed", "actor_id": "alice",
                                "from_status": "draft", "to_status": "pending_approval", "metadata": {}})
        self.assertEqual(event["details"], "Status: draft → pending_approval")



    def test_provider_approval_events_have_human_readable_labels_without_payloads(self):
        approved = describe_event({
            "event_type": "provider_action.approved", "actor_id": "approver",
            "metadata": {"approval_id": 12, "provider": "github", "operation": "create_issue",
                         "fingerprint": "hash-value", "token": "must-not-render"},
        })
        consumed = describe_event({
            "event_type": "provider_action.approval_consumed", "actor_id": "operator",
            "metadata": {"approval_id": 12, "payload": {"title": "private payload"}},
        })
        self.assertEqual(approved["event"], "Provider action approved")
        self.assertEqual(consumed["event"], "Provider approval consumed")
        self.assertEqual(approved["details"], "Provider action metadata is available in the approval ledger")
        self.assertNotIn("must-not-render", str(approved))
        self.assertNotIn("private payload", str(consumed))

if __name__ == "__main__":
    unittest.main()
