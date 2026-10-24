"""Record-level visibility rules for the local case-management UI.

These rules are an additional boundary, not a replacement for a production identity
provider, database row-level security, or service-layer authorization.
"""
from __future__ import annotations

from typing import Any, Iterable

from onboardops.auth import Actor

_BROAD_READ_ROLES = frozenset({"onboardops-admin", "onboardops-operator"})


def can_read_case(actor: Actor, case: dict[str, Any]) -> bool:
    """Return whether this actor may see the case in the current demo role model."""
    if actor.is_demo or actor.roles & _BROAD_READ_ROLES:
        return True
    if "onboardops-requester" in actor.roles and case.get("requester_id") == actor.subject:
        return True
    if "onboardops-approver" in actor.roles and case.get("status") == "pending_approval":
        return True
    return False


def visible_cases(actor: Actor, cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter a case collection according to explicit role and record scope."""
    return [case for case in cases if can_read_case(actor, case)]
