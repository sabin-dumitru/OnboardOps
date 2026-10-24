"""Portable, privacy-conscious case export packets for review and handoff."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from onboardops.audit_view import describe_event

EXPORT_SCHEMA_VERSION = 1
_SENSITIVE_KEY_PARTS = ("password", "secret", "token", "authorization", "api_key", "client_secret")


def _redact_sensitive_fields(value: Any) -> Any:
    """Redact sensitive-looking keys even in legacy rows created before input sanitisation."""
    if isinstance(value, dict):
        return {
            str(key): ("[REDACTED]" if any(part in str(key).casefold() for part in _SENSITIVE_KEY_PARTS)
                       else _redact_sensitive_fields(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_sensitive_fields(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)



def build_case_export(
    case: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    exported_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a stable case packet with allow-listed history, never raw event metadata."""
    timestamp = exported_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)

    case_fields = (
        "case_id", "lifecycle", "status", "priority", "assigned_to",
        "requester_id", "summary", "created_at", "updated_at", "version",
    )
    exported_case = {key: case.get(key) for key in case_fields}
    request_data = case.get("request_data", {})
    exported_case["request_data"] = _redact_sensitive_fields(request_data) if isinstance(request_data, dict) else {}
    history = [describe_event(event) for event in events]
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": timestamp.isoformat(),
        "case": exported_case,
        "history": list(reversed(history)),
    }


def render_case_export_json(packet: dict[str, Any]) -> str:
    """Render an export packet as deterministic, human-readable JSON."""
    return json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
