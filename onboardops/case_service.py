"""Authorization-aware case operations for the Streamlit UI and future API entry points.

Callers should use this facade rather than exposing raw CaseStore methods. The store
remains a persistence primitive and intentionally does not infer identity on its own.
"""
from __future__ import annotations

from typing import Any

from onboardops.auth import Actor, AuthorizationError, require_permission
from onboardops.case_access import can_read_case, visible_cases
from onboardops.cases import CaseStore, CaseStoreError
from onboardops.security_events import log_authorization_denial


class CaseService:
    """Enforce role permissions and record visibility before case operations."""

    def __init__(self, store: CaseStore, actor: Actor) -> None:
        self._store = store
        self._actor = actor

    def _require(self, permission: str) -> None:
        try:
            require_permission(self._actor, permission)
        except AuthorizationError:
            log_authorization_denial(
                self._actor, permission=permission, reason="permission_denied",
            )
            raise

    def _require_visible_case(self, case_id: str) -> dict[str, Any]:
        try:
            case = self._store.get_case(case_id)
        except CaseStoreError as exc:
            # Return the same message for missing and inaccessible IDs.
            log_authorization_denial(
                self._actor, permission="cases:read", reason="case_not_visible",
                resource_id=case_id,
            )
            raise CaseStoreError("Case not found or access denied.") from exc
        if not can_read_case(self._actor, case):
            log_authorization_denial(
                self._actor, permission="cases:read", reason="case_not_visible",
                resource_id=case_id,
            )
            raise CaseStoreError("Case not found or access denied.")
        return case

    def list_cases(self, *, limit: int = 500) -> list[dict[str, Any]]:
        self._require("cases:read")
        roles = self._actor.roles
        if self._actor.is_demo or roles & frozenset({"onboardops-admin", "onboardops-operator"}):
            candidates = self._store.list_cases(limit=limit)
        else:
            scoped: dict[str, dict[str, Any]] = {}
            if "onboardops-requester" in roles:
                scoped.update({
                    case["case_id"]: case
                    for case in self._store.list_cases(limit=limit, requester_id=self._actor.subject)
                })
            if "onboardops-approver" in roles:
                scoped.update({
                    case["case_id"]: case
                    for case in self._store.list_cases(limit=limit, status="pending_approval")
                })
            ordered = sorted(scoped.values(), key=lambda case: case["case_id"])
            ordered.sort(key=lambda case: case["updated_at"], reverse=True)
            candidates = ordered[:limit]
        # Retain the policy filter as defense in depth if a query scope is broadened later.
        return visible_cases(self._actor, candidates)

    def get_case(self, case_id: str) -> dict[str, Any]:
        self._require("cases:read")
        return self._require_visible_case(case_id)

    def list_events(self, case_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        self._require("cases:read")
        self._require_visible_case(case_id)
        return self._store.list_events(case_id, limit=limit)

    def create_case(self, *, case_id: str, lifecycle: str, summary: str,
                    request_data: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require("cases:create")
        return self._store.create_case(
            case_id=case_id,
            lifecycle=lifecycle,
            requester_id=self._actor.subject,
            summary=summary,
            request_data=request_data,
        )

    def transition(self, *, case_id: str, target: str,
                   expected_version: int | None = None) -> dict[str, Any]:
        self._require("cases:transition")
        self._require_visible_case(case_id)
        return self._store.transition(
            case_id=case_id,
            target=target,
            actor_id=self._actor.subject,
            expected_version=expected_version,
        )

    def approve_case(self, *, case_id: str, expected_version: int | None = None) -> dict[str, Any]:
        self._require("approvals:review")
        self._require_visible_case(case_id)
        return self._store.approve_case(
            case_id=case_id,
            approver_id=self._actor.subject,
            expected_version=expected_version,
        )

    def update_triage(self, *, case_id: str, priority: str,
                      assigned_to: str | None,
                      expected_version: int | None = None) -> dict[str, Any]:
        self._require("cases:transition")
        self._require_visible_case(case_id)
        return self._store.update_triage(
            case_id=case_id,
            priority=priority,
            assigned_to=assigned_to,
            actor_id=self._actor.subject,
            expected_version=expected_version,
        )
