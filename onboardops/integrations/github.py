"""GitHub REST adapter for approved onboarding follow-up issue creation."""
from __future__ import annotations
import re
from .base import IntegrationError, JsonApiClient, require_approval


class GitHubClient:
    def __init__(self, token: str, *, api_base_url: str = "https://api.github.com",
                 timeout_seconds: float = 10.0) -> None:
        if not token:
            raise ValueError("GitHub token is required.")
        self.api = JsonApiClient(api_base_url, token=token, headers={
            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
            timeout_seconds=timeout_seconds)

    def create_issue(self, *, repository: str, title: str, body: str,
                     dry_run: bool = True, approval=None) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("repository must use owner/repository format.")
        if not title.strip():
            raise ValueError("Issue title is required.")
        payload = {"title": title.strip(), "body": body}
        preview = require_approval(action="github.create_issue", dry_run=dry_run,
                                   approval=approval, payload={"repository": repository, **payload})
        if preview is not None:
            return preview
        owner, repo = repository.split("/", 1)
        result = self.api.request("POST", f"/repos/{owner}/{repo}/issues", json_body=payload)
        if not isinstance(result.data, dict) or not result.data.get("html_url"):
            raise IntegrationError("invalid_response", "GitHub did not return a created issue URL.")
        return result.data
