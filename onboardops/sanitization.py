"""Shared recursive redaction for persisted data, audit metadata, and exports."""
from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEY_MARKERS = (
    "password",
    "secret",
    "token",
    "authorization",
    "apikey",
    "privatekey",
    "credential",
    "bearer",
)
_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]")


def is_sensitive_key(key: Any) -> bool:
    """Recognise common snake_case, kebab-case, and camelCase secret field names."""
    normalized = _NON_ALPHANUMERIC.sub("", str(key).casefold())
    return any(marker in normalized for marker in _SENSITIVE_KEY_MARKERS)


def redact_sensitive_fields(value: Any) -> Any:
    """Return JSON-compatible data with secret-like object fields redacted recursively."""
    if isinstance(value, dict):
        return {
            str(key): ("[REDACTED]" if is_sensitive_key(key) else redact_sensitive_fields(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_fields(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
