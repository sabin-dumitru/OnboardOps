"""Pure, deterministic helpers for local case operations reporting."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable

CLOSED_STATUSES = {"completed", "cancelled", "rejected"}
ACTIVE_STATUSES = {"approved", "in_progress", "blocked"}
PRIORITY_ORDER = ("urgent", "high", "normal", "low")


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def build_operations_report(cases: Iterable[dict[str, Any]], *, now: datetime | None = None) -> dict[str, Any]:
    """Aggregate case metadata without mutating inputs or exposing request payloads."""
    items = list(cases)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)

    status_counts = Counter(str(c.get("status", "unknown")) for c in items)
    lifecycle_counts = Counter(str(c.get("lifecycle", "unknown")) for c in items)
    priority_counts = Counter(str(c.get("priority", "normal")) for c in items)
    active = [c for c in items if c.get("status") not in CLOSED_STATUSES]
    unassigned = [c for c in active if not str(c.get("assigned_to") or "").strip()]
    aged = []
    for case in active:
        created = _parse_timestamp(case.get("created_at"))
        if created is None:
            continue
        age_days = max(0, (current - created).total_seconds() / 86400)
        if age_days >= 7:
            aged.append({"case_id": str(case.get("case_id", "")), "status": str(case.get("status", "unknown")),
                         "lifecycle": str(case.get("lifecycle", "unknown")),
                         "priority": str(case.get("priority", "normal")),
                         "assigned_to": str(case.get("assigned_to") or ""),
                         "age_days": round(age_days, 1), "created_at": created.isoformat()})

    return {
        "total": len(items),
        "active": len(active),
        "closed": len(items) - len(active),
        "unassigned_active": len(unassigned),
        "high_priority_active": sum(c.get("priority", "normal") in {"urgent", "high"} for c in active),
        "status_counts": dict(sorted(status_counts.items())),
        "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
        "priority_counts": {priority: priority_counts.get(priority, 0) for priority in PRIORITY_ORDER},
        "aging_cases": sorted(aged, key=lambda c: (-c["age_days"], c["case_id"])),
    }
