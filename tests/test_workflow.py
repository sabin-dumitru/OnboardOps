import unittest
from onboardops.workflow import (ActionLedger, DuplicateActionError, WorkflowCase, WorkflowError,
                                 action_fingerprint, approve_action, verify_approval)


class WorkflowTests(unittest.TestCase):
    def test_valid_lifecycle_and_terminal_state(self):
        case = WorkflowCase("CASE-1", "onboarding", requester_id="requester")
        for target in ("pending_approval", "approved", "in_progress", "completed"):
            case = case.transition(target)
        with self.assertRaises(WorkflowError): case.transition("draft")

    def test_invalid_transition_is_rejected(self):
        with self.assertRaises(WorkflowError): WorkflowCase("CASE-2", "offboarding").transition("completed")

    def test_approval_is_bound_to_exact_payload(self):
        payload = {"project": "DEMO", "summary": "Synthetic onboarding"}
        approval = approve_action(requester_id="alice", approver_id="bob", provider="jira",
                                  operation="create_issue", payload=payload)
        verify_approval(approval, provider="jira", operation="create_issue", payload=payload)
        with self.assertRaisesRegex(WorkflowError, "stale"):
            verify_approval(approval, provider="jira", operation="create_issue",
                            payload={"project": "PROD", "summary": "Synthetic onboarding"})

    def test_self_approval_is_rejected_case_insensitively(self):
        with self.assertRaisesRegex(WorkflowError, "cannot approve"):
            approve_action(requester_id="Alice", approver_id="alice", provider="x", operation="write", payload={})

    def test_fingerprint_is_stable_for_key_order(self):
        self.assertEqual(action_fingerprint("p", "op", {"a": 1, "b": 2}),
                         action_fingerprint("p", "op", {"b": 2, "a": 1}))

    def test_ledger_blocks_duplicate_and_unknown_replay(self):
        ledger = ActionLedger()
        try:
            ledger.begin_action(idempotency_key="CASE-1:ticket", provider="servicenow", operation="create")
            ledger.finish_action("CASE-1:ticket", status="unknown")
            with self.assertRaises(DuplicateActionError):
                ledger.begin_action(idempotency_key="CASE-1:ticket", provider="servicenow", operation="create")
        finally: ledger.close()

    def test_audit_redacts_secret_keys_and_verifies_chain(self):
        ledger = ActionLedger()
        try:
            ledger.append_audit(event_type="case.created", case_id="CASE-1", actor_id="demo",
                                metadata={"api_token": "do-not-log", "apiKey": "camel-case-secret",
                                          "privateKey": "private-key-secret", "nested": {"status": "ok"}})
            self.assertTrue(ledger.verify_audit_chain())
            row = ledger.connection.execute("SELECT metadata_json FROM audit_events").fetchone()
            self.assertNotIn("do-not-log", row["metadata_json"])
            self.assertNotIn("camel-case-secret", row["metadata_json"])
            self.assertNotIn("private-key-secret", row["metadata_json"])
            self.assertIn("[REDACTED]", row["metadata_json"])
        finally: ledger.close()

    def test_audit_chain_detects_tampering(self):
        ledger = ActionLedger()
        try:
            ledger.append_audit(event_type="case.created", case_id="CASE-1", actor_id="demo")
            ledger.connection.execute("UPDATE audit_events SET actor_id='tampered' WHERE sequence=1")
            self.assertFalse(ledger.verify_audit_chain())
        finally: ledger.close()


if __name__ == "__main__": unittest.main()
