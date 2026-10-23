"""One-provider workflow: role check, exact-payload approval, ledger and GitHub issue.

This is a tested integration seam. Tests mock the HTTP boundary; live GitHub writes are
not enabled in the Streamlit UI and have not been verified against a live repository.
"""
from __future__ import annotations
from typing import Any
from onboardops.auth import Actor, require_permission, AuthorizationError
from onboardops.workflow import ActionLedger, Approval, WorkflowError, approve_action
from onboardops.integrations.github import GitHubClient

def github_issue_payload(repository: str, title: str, body: str) -> dict[str, Any]:
    return {"repository": repository, "title": title.strip(), "body": body}

def approve_github_issue(*, requester_id: str, approver: Actor, repository: str,
                         title: str, body: str) -> Approval:
    require_permission(approver, "approvals:review", production_only=True)
    return approve_action(requester_id=requester_id, approver_id=approver.subject,
                          provider="github", operation="create_issue",
                          payload=github_issue_payload(repository, title, body))

def create_github_followup(*, actor: Actor, approver_id: str, approval: Approval,
                           client: GitHubClient, ledger: ActionLedger, case_id: str,
                           repository: str, title: str, body: str) -> dict[str, Any]:
    """Execute one approved issue creation, recording ambiguous outcomes for reconciliation."""
    require_permission(actor, "provider:write", production_only=True)
    if actor.subject.casefold() == approver_id.casefold():
        raise WorkflowError("Requester and approver must be different identities.")
    if approval.requester_id.casefold() != actor.subject.casefold() or approval.approver_id.casefold() != approver_id.casefold():
        raise WorkflowError("Approval identities do not match the requesting actor and approver.")
    payload = github_issue_payload(repository, title, body)
    from onboardops.workflow import verify_approval
    verify_approval(approval, provider="github", operation="create_issue", payload=payload)
    key = f"{case_id}:github:create_issue"
    ledger.begin_action(idempotency_key=key, provider="github", operation="create_issue")
    try:
        result = client.create_issue(repository=repository, title=title, body=body,
                                     dry_run=False, approval=approval)
    except Exception:
        ledger.finish_action(key, status="unknown")
        raise
    external_id = str(result.get("number", "")) or None
    ledger.finish_action(key, status="succeeded", external_id=external_id)
    ledger.append_audit(event_type="provider.github_issue_created", case_id=case_id,
                        actor_id=actor.subject, metadata={"repository": repository, "external_id": external_id})
    return result
