import unittest
from unittest.mock import Mock
from onboardops.auth import Actor, AuthorizationError
from onboardops.provider_workflow import approve_github_issue, create_github_followup
from onboardops.workflow import ActionLedger, WorkflowError
from onboardops.integrations.github import GitHubClient

class GitHubWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.requester=Actor("operator@example.invalid",frozenset({"onboardops-operator"}),"trusted_proxy")
        self.approver=Actor("approver@example.invalid",frozenset({"onboardops-approver"}),"trusted_proxy")
        self.ledger=ActionLedger()
        self.session=Mock()
        response=Mock(status_code=201,content=b'{"number":17,"html_url":"https://github.com/example/demo/issues/17"}')
        response.json.return_value={"number":17,"html_url":"https://github.com/example/demo/issues/17"}
        self.session.request.return_value=response
        self.client=GitHubClient("fake-token",session=self.session)
    def tearDown(self):
        self.ledger.close()
    def test_approved_issue_runs_end_to_end_through_mocked_http_and_ledger(self):
        approval=approve_github_issue(requester_id=self.requester.subject,approver=self.approver,
            repository="example/demo",title="Follow up CASE-1",body="Synthetic test")
        result=create_github_followup(actor=self.requester,approver_id=self.approver.subject,approval=approval,
            client=self.client,ledger=self.ledger,case_id="CASE-1",repository="example/demo",
            title="Follow up CASE-1",body="Synthetic test")
        self.assertEqual(result["number"],17)
        self.session.request.assert_called_once()
        args=self.session.request.call_args
        self.assertEqual(args.args[0],"POST")
        self.assertEqual(args.args[1],"https://api.github.com/repos/example/demo/issues")
        self.assertEqual(args.kwargs["json"],{"title":"Follow up CASE-1","body":"Synthetic test"})
        action=self.ledger.connection.execute("SELECT status,external_id FROM actions").fetchone()
        self.assertEqual((action["status"],action["external_id"]),("succeeded","17"))
        self.assertTrue(self.ledger.verify_audit_chain())
    def test_modified_payload_is_rejected_before_http(self):
        approval=approve_github_issue(requester_id=self.requester.subject,approver=self.approver,
            repository="example/demo",title="Original",body="Synthetic")
        with self.assertRaises(WorkflowError):
            create_github_followup(actor=self.requester,approver_id=self.approver.subject,approval=approval,
                client=self.client,ledger=self.ledger,case_id="CASE-2",repository="example/demo",
                title="Changed",body="Synthetic")
        self.session.request.assert_not_called()
    def test_demo_identity_cannot_make_provider_write(self):
        demo=Actor("local-demo",frozenset({"onboardops-demo"}),"demo")
        approval=approve_github_issue(requester_id="local-demo",approver=self.approver,
            repository="example/demo",title="Test",body="Synthetic")
        with self.assertRaises(AuthorizationError):
            create_github_followup(actor=demo,approver_id=self.approver.subject,approval=approval,
                client=self.client,ledger=self.ledger,case_id="CASE-3",repository="example/demo",
                title="Test",body="Synthetic")
        self.session.request.assert_not_called()
    def test_requester_cannot_approve_own_action(self):
        with self.assertRaises(WorkflowError):
            approve_github_issue(requester_id=self.approver.subject,approver=self.approver,
                repository="example/demo",title="Test",body="Synthetic")

if __name__ == "__main__":
    unittest.main()
