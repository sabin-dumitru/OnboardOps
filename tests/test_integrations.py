"""Offline adapter contract tests. These tests never call provider services."""
import json
import unittest
from unittest.mock import Mock
import requests
from onboardops.integrations.base import IntegrationError, JsonApiClient, require_approval, validate_base_url
from onboardops.integrations.github import GitHubClient
from onboardops.integrations.jira import JiraClient
from onboardops.integrations.servicenow import ServiceNowClient
from onboardops.integrations.snipeit import SnipeITClient
from onboardops.integrations.workday import WorkdayClient
from onboardops.workflow import approve_action


class IntegrationBaseTests(unittest.TestCase):
    def test_rejects_http_and_embedded_credentials(self):
        with self.assertRaises(ValueError): validate_base_url("http://example.com")
        with self.assertRaises(ValueError): validate_base_url("https://user:pass@example.com")

    def test_local_http_requires_explicit_opt_in(self):
        self.assertEqual(validate_base_url("http://localhost:8000", allow_local_http=True), "http://localhost:8000")

    def test_rejects_absolute_and_parent_paths(self):
        api = JsonApiClient("https://example.com", token="secret")
        with self.assertRaises(ValueError): api.request("GET", "https://evil.example/path")
        with self.assertRaises(ValueError): api.request("GET", "/../admin")

    def test_redirect_is_not_followed(self):
        session = Mock()
        session.request.return_value = Mock(status_code=302, content=b"", headers={"Location": "https://evil.example"})
        with self.assertRaises(IntegrationError) as ctx:
            JsonApiClient("https://example.com", token="secret", session=session).request("GET", "/api")
        self.assertEqual(ctx.exception.code, "redirect_rejected")
        self.assertFalse(session.request.call_args.kwargs["allow_redirects"])

    def test_error_does_not_echo_response_body_or_token(self):
        session = Mock()
        session.request.return_value = Mock(status_code=401, content=b"token=never-print-this")
        with self.assertRaises(IntegrationError) as ctx:
            JsonApiClient("https://example.com", token="never-print-this", session=session).request("GET", "/api")
        self.assertNotIn("never-print-this", str(ctx.exception))

    def test_timeout_is_retryable_but_outcome_is_ambiguous(self):
        session = Mock()
        session.request.side_effect = requests.Timeout("sensitive detail")
        with self.assertRaises(IntegrationError) as ctx:
            JsonApiClient("https://example.com", session=session).request("POST", "/api")
        self.assertTrue(ctx.exception.retryable)
        self.assertNotIn("sensitive detail", str(ctx.exception))

    def test_write_gate_requires_payload_bound_approval(self):
        self.assertEqual(require_approval(action="demo.write", dry_run=True, approval=None, payload={})["mode"], "dry_run")
        with self.assertRaises(IntegrationError):
            require_approval(action="demo.write", dry_run=False, approval=None, payload={})
        approval = approve_action(requester_id="requester", approver_id="approver",
                                  provider="demo", operation="write", payload={})
        self.assertIsNone(require_approval(action="demo.write", dry_run=False, approval=approval, payload={}))
        stale = approve_action(requester_id="requester", approver_id="approver",
                               provider="demo", operation="write", payload={"target":"A"})
        with self.assertRaises(IntegrationError):
            require_approval(action="demo.write", dry_run=False, approval=stale, payload={"target":"B"})


class ProviderPayloadTests(unittest.TestCase):
    def test_servicenow_payload_uses_correlation_id(self):
        result = ServiceNowClient("https://instance.service-now.com", "fake").create_incident(
            short_description="Synthetic onboarding", description="Demo only", correlation_id="CASE-1")
        self.assertEqual(result["payload"]["correlation_id"], "CASE-1")

    def test_jira_payload_uses_adf_and_case_label(self):
        result = JiraClient("https://example.atlassian.net", "demo@example.invalid", "fake").create_issue(
            project_key="DEMO", summary="Synthetic onboarding", description="Demo", case_id="CASE-1")
        fields = result["payload"]["fields"]
        self.assertEqual(fields["description"]["type"], "doc")
        self.assertIn("onboardops-case-1", fields["labels"])

    def test_github_issue_payload_is_previewed(self):
        result = GitHubClient("fake").create_issue(repository="owner/repo", title="Demo", body="Synthetic")
        self.assertEqual(result["mode"], "dry_run")

    def test_snipeit_checkout_payload_is_previewed(self):
        result = SnipeITClient("https://assets.example.invalid/api/v1", "fake").checkout_to_user(
            asset_id=4, user_id=12, note="CASE-1")
        self.assertEqual(result["payload"]["assigned_user"], 12)

    def test_workday_post_is_previewed(self):
        result = WorkdayClient("https://wd.example.invalid/ccx/api/v1/demo", "fake").submit_configured_business_process(
            endpoint_path="/workers", payload={"demo": True})
        self.assertEqual(result["mode"], "dry_run")


    def test_provider_timeout_must_be_finite_and_bounded(self):
        for timeout in (0, -1, float("inf"), float("nan"), 121, True, "10"):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    JsonApiClient("https://example.com", timeout_seconds=timeout)

    def test_oversized_success_response_is_rejected_before_json_parsing(self):
        session = Mock()
        response = Mock(status_code=200, content=b"")
        consumed = []
        def chunks():
            for _ in range(40):
                consumed.append(1)
                yield b"x" * (64 * 1024)
        response.iter_content.return_value = chunks()
        session.request.return_value = response
        with self.assertRaises(IntegrationError) as ctx:
            JsonApiClient("https://example.com", session=session).request("GET", "/api")
        self.assertEqual(ctx.exception.code, "response_too_large")
        self.assertLess(len(consumed), 40)
        response.json.assert_not_called()
        response.close.assert_called_once()
        self.assertTrue(session.request.call_args.kwargs["stream"])

if __name__ == "__main__":
    unittest.main()


class LiveRequestContractTests(unittest.TestCase):
    """Mock the HTTP boundary to verify provider request contracts without network calls."""
    def _response(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        response = Mock(status_code=status, content=body)
        response.iter_content.return_value = [body]
        response.json.return_value = payload
        return response

    def _approval(self, provider, operation, payload):
        return approve_action(requester_id="demo-requester", approver_id="demo-approver",
                              provider=provider, operation=operation, payload=payload)

    def test_servicenow_approved_create_uses_table_api(self):
        session = Mock()
        session.request.return_value = self._response(201, {"result": {"sys_id": "abc", "number": "INC1001"}})
        client = ServiceNowClient("https://example.service-now.com", "fake-token")
        client.api.session = session
        args = dict(short_description="Synthetic", description="Demo", correlation_id="CASE-10")
        preview = client.create_incident(**args)
        approval = self._approval("servicenow", "create_incident", preview["payload"])
        result = client.create_incident(**args, dry_run=False, approval=approval)
        self.assertEqual(result["number"], "INC1001")
        call = session.request.call_args
        self.assertEqual(call.args[0], "POST")
        self.assertTrue(call.args[1].endswith("/api/now/table/incident"))
        self.assertEqual(call.kwargs["json"]["correlation_id"], "CASE-10")

    def test_jira_approved_create_uses_rest_v3_and_adf(self):
        session = Mock()
        session.request.return_value = self._response(201, {"id": "10001", "key": "DEMO-5"})
        client = JiraClient("https://example.atlassian.net", "demo@example.invalid", "fake-token")
        client.api.session = session
        args = dict(project_key="DEMO", summary="Synthetic", description="Demo", case_id="CASE-10")
        preview = client.create_issue(**args)
        approval = self._approval("jira", "create_issue", preview["payload"])
        result = client.create_issue(**args, dry_run=False, approval=approval)
        self.assertEqual(result["key"], "DEMO-5")
        call = session.request.call_args
        self.assertTrue(call.args[1].endswith("/rest/api/3/issue"))
        self.assertEqual(call.kwargs["json"]["fields"]["description"]["type"], "doc")

    def test_snipeit_approved_checkout_uses_asset_endpoint(self):
        session = Mock()
        session.request.return_value = self._response(200, {"status": "success"})
        client = SnipeITClient("https://assets.example.invalid/api/v1", "fake-token")
        client.api.session = session
        args = dict(asset_id=15, user_id=27, note="CASE-10")
        preview = client.checkout_to_user(**args)
        approval = self._approval("snipeit", "checkout_asset", preview["payload"])
        client.checkout_to_user(**args, dry_run=False, approval=approval)
        call = session.request.call_args
        self.assertTrue(call.args[1].endswith("/hardware/15/checkout"))
        self.assertEqual(call.kwargs["json"]["assigned_user"], 27)

    def test_github_approved_issue_creation_uses_repo_route(self):
        session = Mock()
        session.request.return_value = self._response(201, {"html_url": "https://github.com/example/repo/issues/4"})
        client = GitHubClient("fake-token")
        client.api.session = session
        args = dict(repository="example/repo", title="Synthetic", body="Demo")
        preview = client.create_issue(**args)
        approval = self._approval("github", "create_issue", preview["payload"])
        result = client.create_issue(**args, dry_run=False, approval=approval)
        self.assertTrue(result["html_url"].endswith("/issues/4"))
        self.assertTrue(session.request.call_args.args[1].endswith("/repos/example/repo/issues"))

    def test_workday_approved_post_uses_configured_relative_path(self):
        session = Mock()
        session.request.return_value = self._response(201, {"id": "demo-worker"})
        client = WorkdayClient("https://workday.example.invalid/ccx/api/v1/demo", "fake-token")
        client.api.session = session
        args = dict(endpoint_path="/workers", payload={"synthetic": True})
        preview = client.submit_configured_business_process(**args)
        approval = self._approval("workday", "submit_business_process", preview["payload"])
        result = client.submit_configured_business_process(**args, dry_run=False, approval=approval)
        self.assertEqual(result["id"], "demo-worker")
        self.assertTrue(session.request.call_args.args[1].endswith("/workers"))

    def test_graph_client_uses_client_credentials_and_selected_fields(self):
        session = Mock()
        token_response = self._response(200, {"access_token": "fake-access-token", "expires_in": 3600})
        user_response = self._response(200, {"id": "u1", "displayName": "Synthetic User"})
        session.post.return_value = token_response
        session.request.return_value = user_response
        from onboardops.integrations.graph import MicrosoftGraphClient
        client = MicrosoftGraphClient("tenant", "client", "fake-secret", session=session)
        result = client.get_user("synthetic@example.invalid")
        self.assertEqual(result["id"], "u1")
        self.assertIn("client_secret", session.post.call_args.kwargs["data"])
        self.assertIn("$select", session.request.call_args.kwargs["params"])
        self.assertEqual(session.request.call_args.kwargs["headers"]["Authorization"], "Bearer fake-access-token")


if __name__ == "__main__":
    unittest.main()
