"""Structured, privacy-minimised security events for authorization denials."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone

from onboardops.auth import Actor

_LOGGER = logging.getLogger("onboardops.security")
_PERMISSION_RE = re.compile(r"^[a-z:_-]{1,64}$")
_ALLOWED_REASONS = frozenset({"permission_denied", "case_not_visible"})


def _reference(value: str) -> str:
    """Create a stable pseudonymous reference without logging the raw identifier."""
    return hashlib.sha256(value.casefold().encode("utf-8")).hexdigest()[:16]


def log_authorization_denial(
    actor: Actor, *, permission: str, reason: str, resource_id: str | None = None,
) -> None:
    """Emit one bounded JSON event; never include raw identity, case IDs, or request data."""
    safe_permission = permission if _PERMISSION_RE.fullmatch(permission) else "unknown"
    safe_reason = reason if reason in _ALLOWED_REASONS else "permission_denied"
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "authorization.denied",
        "outcome": "denied",
        "actor_ref": _reference(actor.subject),
        "role_names": sorted(role for role in actor.roles if _PERMISSION_RE.fullmatch(role))[:8],
        "permission": safe_permission,
        "reason": safe_reason,
    }
    if resource_id:
        event["resource_ref"] = _reference(resource_id)
    _LOGGER.warning("%s", json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False))
