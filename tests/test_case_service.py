import os
import tempfile
import unittest

from onboardops.auth import Actor, AuthorizationError
from onboardops.case_service import CaseService
from onboardops.cases import CaseStore, CaseStoreError


class CaseServiceAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = CaseStore(os.path.join(self.temp.name, "cases.sqlite3"))
        self.alice = Actor("alice", frozenset({"onboardops-requester"}), "trusted_proxy")
        self.bob = Actor("bob", frozenset({"onboardops-requester"}), "trusted_proxy")
        self.approver = Actor("reviewer", frozenset({"onboardops-approver"}), "trusted_proxy")
        self.alice_service = CaseService(self.store, self.alice)
        self.bob_service = CaseService(self.store, self.bob)
        self.approver_service = CaseService(self.store, self.approver)
        self.alice_service.create_case(case_id="CASE-ALICE", lifecycle="onboarding", summary="Alice request")
        self.bob_service.create_case(case_id="CASE-BOB", lifecycle="onboarding", summary="Bob request")
        self.store.transition(case_id="CASE-BOB", target="pending_approval", actor_id="bob")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_requester_listing_and_direct_read_are_scoped(self):
        self.assertEqual([c["case_id"] for c in self.alice_service.list_cases()], ["CASE-ALICE"])
        with self.assertRaisesRegex(CaseStoreError, "not found or access denied"):
            self.alice_service.get_case("CASE-BOB")
        with self.assertRaisesRegex(CaseStoreError, "not found or access denied"):
            self.alice_service.list_events("CASE-BOB")

    def test_requester_cannot_mutate_case_through_service(self):
        alice_case = self.alice_service.get_case("CASE-ALICE")
        with self.assertRaises(AuthorizationError):
            self.alice_service.transition(case_id="CASE-ALICE", target="pending_approval",
                                          expected_version=alice_case["version"])

    def test_approver_sees_pending_cases_and_can_review_them(self):
        self.assertEqual([c["case_id"] for c in self.approver_service.list_cases()], ["CASE-BOB"])
        pending = self.approver_service.get_case("CASE-BOB")
        approved = self.approver_service.approve_case(
            case_id="CASE-BOB", expected_version=pending["version"],
        )
        self.assertEqual(approved["status"], "approved")
        with self.assertRaisesRegex(CaseStoreError, "not found or access denied"):
            self.approver_service.get_case("CASE-ALICE")

    def test_unknown_role_cannot_read_or_create_cases(self):
        visitor = CaseService(
            self.store, Actor("visitor", frozenset({"unknown"}), "trusted_proxy"),
        )
        with self.assertRaises(AuthorizationError):
            visitor.list_cases()
        with self.assertRaises(AuthorizationError):
            visitor.create_case(case_id="CASE-VISITOR", lifecycle="onboarding",
                                summary="Not allowed")


if __name__ == "__main__":
    unittest.main()
