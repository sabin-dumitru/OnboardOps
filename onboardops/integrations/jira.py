"""Jira Cloud REST v3 adapter for issue lookup and approved issue creation."""
from __future__ import annotations
import re
from typing import Any
from .base import IntegrationError, JsonApiClient, require_approval


class JiraClient:
    def __init__(self, site_url: str, email: str, api_token: str, *,
                 timeout_seconds: float = 10.0) -> None:
        if not email.strip() or not api_token:
            raise ValueError("Jira account email and API token are required.")
        self.api = JsonApiClient(site_url, auth=(email.strip(), api_token), timeout_seconds=timeout_seconds)

    def get_issue(self, issue_key: str) -> dict[str, Any]:
        key = issue_key.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]+-\d+", key):
            raise ValueError("Issue key must look like PROJECT-123.")
        result = self.api.request("GET", f"/rest/api/3/issue/{key}")
        if not isinstance(result.data, dict):
            raise IntegrationError("invalid_response", "Jira returned an unexpected issue response.")
        return result.data

    def create_issue(self, *, project_key: str, summary: str, description: str,
                     issue_type: str = "Task", case_id: str,
                     dry_run: bool = True, approval=None) -> dict[str, Any]:
        project = project_key.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]+", project):
            raise ValueError("Project key has an invalid format.")
        if not summary.strip() or not case_id.strip():
            raise ValueError("summary and case_id are required.")
        safe_case = re.sub(r"[^A-Za-z0-9-]", "-", case_id)[:40].lower()
        payload = {"fields": {"project": {"key": project}, "summary": summary.strip(),
            "issuetype": {"name": issue_type},
            "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph",
                "content": [{"type": "text", "text": description.strip() or "Onboarding task created by OnboardOps."}]}]},
            "labels": ["onboardops", f"onboardops-{safe_case}"]}}
        preview = require_approval(action="jira.create_issue", dry_run=dry_run,
                                   approval=approval, payload=payload)
        if preview is not None:
            return preview
        result = self.api.request("POST", "/rest/api/3/issue", json_body=payload)
        if not isinstance(result.data, dict) or not result.data.get("key"):
            raise IntegrationError("invalid_response", "Jira response omitted the created issue key.")
        return result.data
