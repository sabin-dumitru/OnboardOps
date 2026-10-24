import unittest

from onboardops.auth import Actor
from onboardops.case_access import can_read_case, visible_cases


class CaseVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.cases = [
            {"case_id": "CASE-OWN", "requester_id": "alice", "status": "draft"},
            {"case_id": "CASE-OTHER", "requester_id": "bob", "status": "in_progress"},
            {"case_id": "CASE-PENDING", "requester_id": "bob", "status": "pending_approval"},
        ]

    def actor(self, subject, *roles, mode="trusted_proxy"):
        return Actor(subject, frozenset(roles), mode)

    def test_requester_only_sees_cases_they_requested(self):
        actor = self.actor("alice", "onboardops-requester")
        self.assertEqual([c["case_id"] for c in visible_cases(actor, self.cases)], ["CASE-OWN"])
        self.assertFalse(can_read_case(actor, self.cases[1]))

    def test_approver_only_sees_pending_cases(self):
        actor = self.actor("reviewer", "onboardops-approver")
        self.assertEqual([c["case_id"] for c in visible_cases(actor, self.cases)], ["CASE-PENDING"])

    def test_operator_and_admin_can_review_all_cases(self):
        for role in ("onboardops-operator", "onboardops-admin"):
            with self.subTest(role=role):
                actor = self.actor("ops", role)
                self.assertEqual(len(visible_cases(actor, self.cases)), 3)

    def test_demo_scope_is_explicitly_for_synthetic_local_work(self):
        actor = self.actor("local-demo", "onboardops-demo", mode="demo")
        self.assertEqual(len(visible_cases(actor, self.cases)), 3)

    def test_unknown_role_is_denied_by_default(self):
        actor = self.actor("visitor", "unknown")
        self.assertEqual(visible_cases(actor, self.cases), [])


if __name__ == "__main__":
    unittest.main()
