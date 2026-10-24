import os
import tempfile
import unittest
import requests
from unittest.mock import Mock
from onboardops.auth import Actor, AuthorizationError
from onboardops.cases import CaseStore, CaseStoreError
from onboardops.provider_workflow import approve_github_issue, create_github_followup
from onboardops.workflow import ActionLedger, DuplicateActionError, WorkflowError, action_fingerprint
from onboardops.integrations.github import GitHubClient
from onboardops.integrations.base import IntegrationError

class GitHubWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=CaseStore(os.path.join(self.temp.name,"cases.sqlite3"))
        self.requester=Actor("operator@example.invalid",frozenset({"onboardops-operator"}),"trusted_proxy")
        self.approver=Actor("approver@example.invalid",frozenset({"onboardops-approver"}),"trusted_proxy")
        self.ledger=ActionLedger()
        self.session=Mock()
        response=Mock(status_code=201,content=b'{"number":17,"html_url":"https://github.com/example/demo/issues/17"}')
        response.iter_content.return_value = [response.content]
        response.json.return_value={"number":17,"html_url":"https://github.com/example/demo/issues/17"}
        self.session.request.return_value=response
        self.client=GitHubClient("fake-token",session=self.session)
        self.store.create_case(case_id="CASE-201",lifecycle="onboarding",requester_id=self.requester.subject,summary="Synthetic onboarding")
    def tearDown(self):
        self.ledger.close()
        self.store.close()
        self.temp.cleanup()
    def _approval(self,title="Follow up CASE-201",body="Synthetic test"):
        return approve_github_issue(store=self.store,case_id="CASE-201",requester_id=self.requester.subject,
            approver=self.approver,repository="example/demo",title=title,body=body)
    def test_persisted_approval_runs_through_mocked_http_and_ledger(self):
        approval=self._approval()
        result=create_github_followup(store=self.store,approval_id=approval["approval_id"],actor=self.requester,
            client=self.client,ledger=self.ledger,case_id="CASE-201",repository="example/demo",
            title="Follow up CASE-201",body="Synthetic test")
        self.assertEqual(result["number"],17)
        self.session.request.assert_called_once()
        args=self.session.request.call_args
        self.assertEqual(args.args[0],"POST")
        self.assertEqual(args.args[1],"https://api.github.com/repos/example/demo/issues")
        self.assertEqual(args.kwargs["json"],{"title":"Follow up CASE-201","body":"Synthetic test"})
        action=self.ledger.connection.execute("SELECT status,external_id FROM actions").fetchone()
        self.assertEqual((action["status"],action["external_id"]),("succeeded","17"))
        self.assertEqual(self.store.get_provider_approval(approval["approval_id"])["status"],"consumed")
        self.assertTrue(self.ledger.verify_audit_chain())
    def test_modified_payload_is_rejected_before_http(self):
        approval=self._approval(title="Original")
        with self.assertRaises(WorkflowError):
            create_github_followup(store=self.store,approval_id=approval["approval_id"],actor=self.requester,
                client=self.client,ledger=self.ledger,case_id="CASE-201",repository="example/demo",
                title="Changed",body="Synthetic test")
        self.session.request.assert_not_called()
    def test_demo_identity_cannot_make_provider_write(self):
        demo=Actor("local-demo",frozenset({"onboardops-demo"}),"demo")
        approval=self._approval()
        with self.assertRaises(AuthorizationError):
            create_github_followup(store=self.store,approval_id=approval["approval_id"],actor=demo,
                client=self.client,ledger=self.ledger,case_id="CASE-201",repository="example/demo",
                title="Follow up CASE-201",body="Synthetic test")
        self.session.request.assert_not_called()
    def test_requester_cannot_approve_own_action(self):
        with self.assertRaises(WorkflowError):
            approve_github_issue(store=self.store,case_id="CASE-201",requester_id=self.approver.subject,
                approver=self.approver,repository="example/demo",title="Test",body="Synthetic")
    def test_persisted_approval_cannot_be_consumed_twice(self):
        approval=self._approval()
        create_github_followup(store=self.store,approval_id=approval["approval_id"],actor=self.requester,
            client=self.client,ledger=self.ledger,case_id="CASE-201",repository="example/demo",
            title="Follow up CASE-201",body="Synthetic test")
        with self.assertRaises(DuplicateActionError):
            create_github_followup(store=self.store,approval_id=approval["approval_id"],actor=self.requester,
                client=self.client,ledger=self.ledger,case_id="CASE-201",repository="example/demo",
                title="Follow up CASE-201",body="Synthetic test")
        self.assertEqual(self.session.request.call_count,1)

    def test_timeout_consumes_approval_and_marks_outcome_unknown(self):
        approval=self._approval()
        self.session.request.side_effect=requests.Timeout("synthetic timeout")
        with self.assertRaises(IntegrationError) as caught:
            create_github_followup(store=self.store,approval_id=approval["approval_id"],actor=self.requester,
                client=self.client,ledger=self.ledger,case_id="CASE-201",repository="example/demo",
                title="Follow up CASE-201",body="Synthetic test")
        self.assertIn("timed out",str(caught.exception).lower())
        action=self.ledger.connection.execute("SELECT status FROM actions").fetchone()
        self.assertEqual(action["status"],"unknown")
        self.assertEqual(self.store.get_provider_approval(approval["approval_id"])["status"],"consumed")
        self.assertEqual(self.session.request.call_count,1)

    def test_provider_server_error_marks_outcome_unknown_without_leaking_body(self):
        approval=self._approval()
        response=Mock(status_code=500,content=b"private upstream details")
        response.json.return_value={"message":"private upstream details"}
        self.session.request.return_value=response
        with self.assertRaises(Exception) as caught:
            create_github_followup(store=self.store,approval_id=approval["approval_id"],actor=self.requester,
                client=self.client,ledger=self.ledger,case_id="CASE-201",repository="example/demo",
                title="Follow up CASE-201",body="Synthetic test")
        self.assertNotIn("private upstream details",str(caught.exception))
        action=self.ledger.connection.execute("SELECT status FROM actions").fetchone()
        self.assertEqual(action["status"],"unknown")
        self.assertEqual(self.store.get_provider_approval(approval["approval_id"])["status"],"consumed")
        self.session.request.assert_called_once()

    def test_approval_cannot_be_used_for_another_case(self):
        approval=self._approval()
        with self.assertRaises(WorkflowError):
            create_github_followup(store=self.store,approval_id=approval["approval_id"],actor=self.requester,
                client=self.client,ledger=self.ledger,case_id="CASE-OTHER",repository="example/demo",
                title="Follow up CASE-201",body="Synthetic test")
        self.session.request.assert_not_called()

    def test_approval_cannot_be_used_by_a_different_requester(self):
        approval=self._approval()
        other=Actor("other-operator@example.invalid",frozenset({"onboardops-operator"}),"trusted_proxy")
        with self.assertRaises(WorkflowError):
            create_github_followup(store=self.store,approval_id=approval["approval_id"],actor=other,
                client=self.client,ledger=self.ledger,case_id="CASE-201",repository="example/demo",
                title="Follow up CASE-201",body="Synthetic test")
        self.session.request.assert_not_called()

    def test_expired_approval_is_failed_before_any_provider_request(self):
        approval = self._approval()
        self.store.connection.execute(
            "UPDATE provider_approvals SET expires_at=? WHERE approval_id=?",
            ("2000-01-01T00:00:00+00:00", approval["approval_id"]),
        )
        self.store.connection.commit()
        with self.assertRaisesRegex(CaseStoreError, "expired"):
            create_github_followup(
                store=self.store, approval_id=approval["approval_id"], actor=self.requester,
                client=self.client, ledger=self.ledger, case_id="CASE-201",
                repository="example/demo", title="Follow up CASE-201", body="Synthetic test",
            )
        action = self.ledger.connection.execute("SELECT status FROM actions").fetchone()
        self.assertEqual(action["status"], "failed")
        self.session.request.assert_not_called()

    def test_provider_4xx_rejection_is_failed_not_unknown(self):
        approval = self._approval()
        response = Mock(status_code=403, content=b"private rejection details")
        response.json.return_value = {"message": "private rejection details"}
        self.session.request.return_value = response
        with self.assertRaises(IntegrationError) as caught:
            create_github_followup(
                store=self.store, approval_id=approval["approval_id"], actor=self.requester,
                client=self.client, ledger=self.ledger, case_id="CASE-201",
                repository="example/demo", title="Follow up CASE-201", body="Synthetic test",
            )
        self.assertEqual(caught.exception.code, "provider_rejected_request")
        action = self.ledger.connection.execute("SELECT status FROM actions").fetchone()
        self.assertEqual(action["status"], "failed")
        self.assertNotIn("private rejection details", str(caught.exception))
        self.session.request.assert_called_once()

    def test_local_payload_validation_failure_is_failed_not_unknown(self):
        payload = {"repository": "invalid-repository", "title": "Follow up", "body": "Synthetic"}
        approval = self.store.record_provider_approval(
            case_id="CASE-201", requester_id=self.requester.subject,
            approver_id=self.approver.subject, provider="github", operation="create_issue",
            payload=payload, fingerprint=action_fingerprint("github", "create_issue", payload),
        )
        with self.assertRaisesRegex(ValueError, "owner/repository"):
            create_github_followup(
                store=self.store, approval_id=approval["approval_id"], actor=self.requester,
                client=self.client, ledger=self.ledger, case_id="CASE-201",
                repository="invalid-repository", title="Follow up", body="Synthetic",
            )
        action = self.ledger.connection.execute("SELECT status FROM actions").fetchone()
        self.assertEqual(action["status"], "failed")
        self.session.request.assert_not_called()

if __name__ == "__main__":
    unittest.main()
