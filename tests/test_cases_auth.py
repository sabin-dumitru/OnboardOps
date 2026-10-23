import os
import tempfile
import unittest
from onboardops.auth import AuthorizationError, require_permission, resolve_actor
from onboardops.cases import CaseStore, CaseStoreError
from onboardops.workflow import WorkflowError

class AuthTests(unittest.TestCase):
    def test_demo_cannot_authorise_production_write(self):
        actor = resolve_actor(environ={"ONBOARDOPS_AUTH_MODE":"demo"})
        require_permission(actor, "cases:create")
        with self.assertRaises(AuthorizationError):
            require_permission(actor, "provider:write", production_only=True)

    def test_unknown_mode_fails_closed(self):
        with self.assertRaises(AuthorizationError):
            resolve_actor(environ={"ONBOARDOPS_AUTH_MODE":"unexpected"})

    def test_proxy_identity_requires_explicit_trust_and_role(self):
        headers={"X-Auth-Request-User":"alice@example.invalid","X-Auth-Request-Groups":"onboardops-requester"}
        with self.assertRaises(AuthorizationError):
            resolve_actor(headers, environ={"ONBOARDOPS_AUTH_MODE":"trusted_proxy"})
        actor=resolve_actor(headers,environ={"ONBOARDOPS_AUTH_MODE":"trusted_proxy","ONBOARDOPS_TRUSTED_AUTH_PROXY":"true"})
        require_permission(actor,"cases:create")
        with self.assertRaises(AuthorizationError):
            require_permission(actor,"provider:write")

    def test_missing_identity_is_denied(self):
        with self.assertRaises(AuthorizationError):
            resolve_actor({},environ={"ONBOARDOPS_AUTH_MODE":"trusted_proxy","ONBOARDOPS_TRUSTED_AUTH_PROXY":"true"})

class CaseStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=os.path.join(self.temp.name,"cases.sqlite3")
        self.store=CaseStore(self.path)
    def tearDown(self):
        self.store.close()
        self.temp.cleanup()
    def test_case_persists_and_history_is_recorded(self):
        self.store.create_case(case_id="CASE-100",lifecycle="onboarding",requester_id="alice",summary="Synthetic onboarding",request_data={"employee_id":"DEMO-100"})
        self.store.transition(case_id="CASE-100",target="pending_approval",actor_id="alice",expected_version=1)
        self.store.close()
        self.store=CaseStore(self.path)
        self.assertEqual(self.store.get_case("CASE-100")["status"],"pending_approval")
        self.assertEqual([e["event_type"] for e in self.store.list_events("CASE-100")],["case.created","case.status_changed"])
    def test_duplicate_case_is_rejected(self):
        args=dict(case_id="CASE-101",lifecycle="onboarding",requester_id="alice",summary="Demo")
        self.store.create_case(**args)
        with self.assertRaises(CaseStoreError): self.store.create_case(**args)
    def test_bad_transition_and_stale_version_are_rejected(self):
        self.store.create_case(case_id="CASE-102",lifecycle="onboarding",requester_id="alice",summary="Demo")
        with self.assertRaises(WorkflowError): self.store.transition(case_id="CASE-102",target="completed",actor_id="alice")
        self.store.transition(case_id="CASE-102",target="pending_approval",actor_id="alice",expected_version=1)
        with self.assertRaises(CaseStoreError): self.store.transition(case_id="CASE-102",target="approved",actor_id="bob",expected_version=1)
    def test_case_approval_requires_a_different_actor_and_cannot_be_bypassed(self):
        self.store.create_case(case_id="CASE-104",lifecycle="onboarding",requester_id="alice",summary="Demo")
        self.store.transition(case_id="CASE-104",target="pending_approval",actor_id="alice",expected_version=1)
        with self.assertRaises(WorkflowError):
            self.store.approve_case(case_id="CASE-104",approver_id="alice",expected_version=2)
        with self.assertRaises(WorkflowError):
            self.store.transition(case_id="CASE-104",target="approved",actor_id="bob",expected_version=2)
        approved=self.store.approve_case(case_id="CASE-104",approver_id="bob",expected_version=2)
        self.assertEqual(approved["status"],"approved")
        self.assertEqual(self.store.list_events("CASE-104")[-1]["actor_id"],"bob")

    def test_provider_approval_is_persisted_and_secret_payload_is_redacted(self):
        self.store.create_case(case_id="CASE-105",lifecycle="onboarding",requester_id="alice",summary="Demo")
        record=self.store.record_provider_approval(case_id="CASE-105",requester_id="alice",approver_id="bob",
            provider="github",operation="create_issue",payload={"title":"Demo","api_token":"secret"},
            fingerprint="fingerprint-demo")
        self.store.close()
        self.store=CaseStore(self.path)
        restored=self.store.get_provider_approval(record["approval_id"])
        self.assertEqual(restored["status"],"approved")
        self.assertEqual(restored["payload"]["api_token"],"[REDACTED]")
        self.assertEqual(restored["approver_id"],"bob")

    def test_provider_approval_must_belong_to_case_requester(self):
        self.store.create_case(case_id="CASE-106",lifecycle="onboarding",requester_id="alice",summary="Demo")
        with self.assertRaises(WorkflowError):
            self.store.record_provider_approval(case_id="CASE-106",requester_id="mallory",approver_id="bob",
                provider="github",operation="create_issue",payload={"title":"Demo"},fingerprint="fp")

    def test_secret_values_are_redacted_from_stored_request(self):
        case=self.store.create_case(case_id="CASE-103",lifecycle="onboarding",requester_id="alice",summary="Demo",request_data={"api_token":"must-not-persist","team":"IT"})
        self.assertEqual(case["request_data"]["api_token"],"[REDACTED]")
        self.assertEqual(case["request_data"]["team"],"IT")

if __name__ == "__main__":
    unittest.main()
