"""Authorization-aware case operations for the Streamlit UI and future API entry points.

Callers should use this facade rather than exposing raw CaseStore methods. The store
remains a persistence primitive and intentionally does not infer identity on its own.
"""
from __future__ import annotations

from typing import Any

from onboardops.auth import Actor, require_permission
from onboardops.case_access import can_read_case, visible_cases
from onboardops.cases import CaseStore, CaseStoreError


class CaseService:
    """Enforce role permissions and record visibility before case operations."""

    def __init__(self, store: CaseStore, actor: Actor) -> None:
        self._store = store
        self._actor = actor

    def _require_visible_case(self, case_id: str) -> dict[str, Any]:
        try:
            case = self._store.get_case(case_id)
        except CaseStoreError as exc:
            # Return the same message for missing and inaccessible IDs.
            raise CaseStoreError("Case not found or access denied.") from exc
        if not can_read_case(self._actor, case):
            raise CaseStoreError("Case not found or access denied.")
        return case

    def list_cases(self, *, limit: int = 500) -> list[dict[str, Any]]:
        require_permission(self._actor, "cases:read")
        return visible_cases(self._actor, self._store.list_cases(limit=limit))

    def get_case(self, case_id: str) -> dict[str, Any]:
        require_permission(self._actor, "cases:read")
        return self._require_visible_case(case_id)

    def list_events(self, case_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        require_permission(self._actor, "cases:read")
        self._require_visible_case(case_id)
        return self._store.list_events(case_id, limit=limit)

    def create_case(self, *, case_id: str, lifecycle: str, summary: str,
                    request_data: dict[str, Any] | None = None) -> dict[str, Any]:
        require_permission(self._actor, "cases:create")
        return self._store.create_case(
            case_id=case_id,
            lifecycle=lifecycle,
            requester_id=self._actor.subject,
            summary=summary,
            request_data=request_data,
        )

    def transition(self, *, case_id: str, target: str,
                   expected_version: int | None = None) -> dict[str, Any]:
        require_permission(self._actor, "cases:transition")
        self._require_visible_case(case_id)
        return self._store.transition(
            case_id=case_id,
            target=target,
            actor_id=self._actor.subject,
            expected_version=expected_version,
        )

    def approve_case(self, *, case_id: str, expected_version: int | None = None) -> dict[str, Any]:
        require_permission(self._actor, "approvals:review")
        self._require_visible_case(case_id)
        return self._store.approve_case(
            case_id=case_id,
            approver_id=self._actor.subject,
            expected_version=expected_version,
        )

    def update_triage(self, *, case_id: str, priority: str,
                      assigned_to: str | None,
                      expected_version: int | None = None) -> dict[str, Any]:
        require_permission(self._actor, "cases:transition")
        self._require_visible_case(case_id)
        return self._store.update_triage(
            case_id=case_id,
            priority=priority,
            assigned_to=assigned_to,
            actor_id=self._actor.subject,
            expected_version=expected_version,
        )
