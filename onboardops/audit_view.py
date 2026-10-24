"""Human-readable, allow-listed presentation of case audit events."""
from __future__ import annotations

from typing import Any

EVENT_LABELS = {
    "case.created": "Case created",
    "case.status_changed": "Status changed",
    "case.approved": "Case approved",
    "case.triage_updated": "Priority / assignment updated",
    "provider.approval_recorded": "Provider action approved",
    "provider.approval_consumed": "Provider approval consumed",
    "provider.approval_revoked": "Provider approval revoked",
    "provider_action.approved": "Provider action approved",
    "provider_action.approval_consumed": "Provider approval consumed",
    "provider_action.approval_revoked": "Provider approval revoked",
    "provider_action.approval_expired": "Provider approval expired",
}


def describe_event(event: dict[str, Any]) -> dict[str, str]:
    """Format known event metadata without dumping arbitrary stored payloads."""
    event_type = str(event.get("event_type", "unknown"))
    metadata = event.get("metadata") or {}
    details: list[str] = []
    if event_type == "case.triage_updated":
        old_priority, new_priority = metadata.get("priority_from"), metadata.get("priority_to")
        if old_priority != new_priority and new_priority is not None:
            details.append(f"Priority: {old_priority or 'normal'} → {new_priority}")
        old_assignee = metadata.get("assigned_to_from") or "Unassigned"
        new_assignee = metadata.get("assigned_to_to") or "Unassigned"
        if old_assignee != new_assignee:
            details.append(f"Assignment: {old_assignee} → {new_assignee}")
    elif event_type == "case.status_changed":
        if event.get("from_status") or event.get("to_status"):
            details.append(f"Status: {event.get('from_status') or '—'} → {event.get('to_status') or '—'}")
    elif event_type == "case.created":
        details.append("Initial case record created")
    elif event_type.startswith(("provider.", "provider_action.")):
        details.append("Provider action metadata is available in the approval ledger")
    return {
        "event": EVENT_LABELS.get(event_type, "Other event"),
        "event_type": event_type,
        "actor": str(event.get("actor_id") or "Unknown"),
        "from_status": str(event.get("from_status") or "—"),
        "to_status": str(event.get("to_status") or "—"),
        "occurred_at": str(event.get("occurred_at") or ""),
        "details": " · ".join(details) if details else "No additional display details",
    }
