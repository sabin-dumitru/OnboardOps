"""One-provider workflow: persistent approval, role check, ledger and GitHub issue.

HTTP is mocked in CI. The workflow is not exposed by the UI and live writes remain
disabled until a trusted identity deployment and isolated live test are verified.
"""
from __future__ import annotations
from typing import Any
from onboardops.auth import Actor, require_permission
from onboardops.cases import CaseStore
from onboardops.workflow import ActionLedger, Approval, WorkflowError, action_fingerprint
from onboardops.integrations.github import GitHubClient
from onboardops.integrations.base import IntegrationError


def _failure_status(exc: Exception) -> str:
    """Distinguish known pre-write/rejection failures from uncertain remote outcomes."""
    if isinstance(exc, ValueError):
        return "failed"
    if isinstance(exc, IntegrationError) and exc.code in {
        "approval_required", "approval_invalid", "provider_rejected_request",
    }:
        return "failed"
    # Network errors, timeouts, 5xx responses and invalid success responses can
    # occur after the provider accepted the request, so they require reconciliation.
    return "unknown"


def github_issue_payload(repository: str, title: str, body: str) -> dict[str, Any]:
    return {"repository": repository, "title": title.strip(), "body": body}

def approve_github_issue(*, store: CaseStore, case_id: str, requester_id: str, approver: Actor,
                         repository: str, title: str, body: str) -> dict[str, Any]:
    """Persist a distinct approver's exact-payload approval for an existing case."""
    require_permission(approver, "approvals:review", production_only=True)
    payload = github_issue_payload(repository, title, body)
    return store.record_provider_approval(
        case_id=case_id, requester_id=requester_id, approver_id=approver.subject,
        provider="github", operation="create_issue", payload=payload,
        fingerprint=action_fingerprint("github", "create_issue", payload))

def create_github_followup(*, store: CaseStore, approval_id: int, actor: Actor,
                           client: GitHubClient, ledger: ActionLedger, case_id: str,
                           repository: str, title: str, body: str) -> dict[str, Any]:
    """Consume a persisted approval once, call GitHub and record success/unknown outcome."""
    require_permission(actor, "provider:write", production_only=True)
    payload = github_issue_payload(repository, title, body)
    fingerprint = action_fingerprint("github", "create_issue", payload)
    record = store.get_provider_approval(approval_id)
    if record["case_id"] != case_id or record["provider"] != "github" or record["operation"] != "create_issue":
        raise WorkflowError("Approval does not belong to this case and provider operation.")
    if record["requester_id"].casefold() != actor.subject.casefold():
        raise WorkflowError("Approval requester does not match the authenticated actor.")
    if record["approver_id"].casefold() == actor.subject.casefold():
        raise WorkflowError("Requester and approver must be different identities.")
    if record["payload"] != payload or record["fingerprint"] != fingerprint:
        raise WorkflowError("Approval does not match the exact action payload.")
    key = f"{case_id}:github:create_issue:{approval_id}"
    ledger.begin_action(idempotency_key=key, provider="github", operation="create_issue")
    # A local approval/ledger failure is known to have occurred before provider I/O.
    try:
        store.consume_provider_approval(approval_id, expected_fingerprint=fingerprint)
    except Exception:
        ledger.finish_action(key, status="failed")
        raise

    # Once the provider client is entered, classify known rejections separately from
    # transport/response failures where the remote write may already have succeeded.
    try:
        result = client.create_issue(repository=repository, title=title, body=body, dry_run=False,
                                     approval=Approval(record["requester_id"], record["approver_id"],
                                                       record["fingerprint"], record["approved_at"]))
    except Exception as exc:
        ledger.finish_action(key, status=_failure_status(exc))
        raise
    external_id = str(result.get("number", "")) or None
    ledger.finish_action(key, status="succeeded", external_id=external_id)
    ledger.append_audit(event_type="provider.github_issue_created", case_id=case_id,
                        actor_id=actor.subject, metadata={"repository": repository, "external_id": external_id})
    return result
