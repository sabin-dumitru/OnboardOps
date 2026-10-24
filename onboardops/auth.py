"""Fail-closed identity and role checks for OnboardOps.

Local demo identity is deliberately limited to synthetic case work. Production identity
must be asserted by a trusted authentication proxy that strips inbound copies of the
identity headers before setting them. Never expose Streamlit directly to untrusted clients.
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass

class AuthorizationError(PermissionError):
    """Raised when identity or role checks fail."""

@dataclass(frozen=True)
class Actor:
    subject: str
    roles: frozenset[str]
    mode: str

    @property
    def is_demo(self) -> bool:
        return self.mode == "demo"

_ROLE_PERMISSIONS = {
    "onboardops-admin": frozenset({"cases:read", "cases:create", "cases:transition", "approvals:review", "provider:write", "integrations:read"}),
    "onboardops-requester": frozenset({"cases:read", "cases:create"}),
    "onboardops-approver": frozenset({"cases:read", "approvals:review"}),
    "onboardops-operator": frozenset({"cases:read", "cases:transition", "provider:write", "integrations:read"}),
    "onboardops-demo": frozenset({"cases:read", "cases:create", "cases:transition"}),
}
_SUBJECT_RE = re.compile(r"^[A-Za-z0-9@._:-]{1,128}$")

def resolve_actor(headers: dict[str, str] | None = None, *, environ: dict[str, str] | None = None) -> Actor:
    """Resolve local demo identity or identity asserted by an explicitly trusted proxy."""
    env = os.environ if environ is None else environ
    mode = env.get("ONBOARDOPS_AUTH_MODE", "demo").strip().casefold()
    if mode == "demo":
        return Actor("local-demo", frozenset({"onboardops-demo"}), "demo")
    if mode != "trusted_proxy":
        raise AuthorizationError("Authentication is not configured; access is denied.")
    if env.get("ONBOARDOPS_TRUSTED_AUTH_PROXY", "").strip().casefold() != "true":
        raise AuthorizationError("Trusted authentication proxy is not enabled; access is denied.")
    normalised = {str(k).casefold(): str(v).strip() for k, v in (headers or {}).items()}
    subject = normalised.get("x-auth-request-user", "")
    raw_roles = normalised.get("x-auth-request-groups", "")
    if not subject or not _SUBJECT_RE.fullmatch(subject):
        raise AuthorizationError("Authenticated identity is missing or malformed.")
    roles = frozenset(role.strip() for role in raw_roles.split(",") if role.strip())
    if not roles.intersection(_ROLE_PERMISSIONS):
        raise AuthorizationError("No recognised OnboardOps role was supplied.")
    return Actor(subject, roles, "trusted_proxy")

def has_permission(actor: Actor, permission: str, *, production_only: bool = False) -> bool:
    """Return whether an actor has a permission; use require_permission at action sites."""
    if production_only and actor.is_demo:
        return False
    return any(permission in _ROLE_PERMISSIONS.get(role, frozenset()) for role in actor.roles)


def require_permission(actor: Actor, permission: str, *, production_only: bool = False) -> None:
    if production_only and actor.is_demo:
        raise AuthorizationError("This action is disabled in local demo mode.")
    if not has_permission(actor, permission):
        raise AuthorizationError(f"Your assigned role does not permit {permission}.")



def require_integration_read(headers: dict[str, str] | None = None, *,
                             environ: dict[str, str] | None = None) -> Actor:
    """Resolve and enforce permission for live read-only provider lookups."""
    actor = resolve_actor(headers, environ=environ)
    require_permission(actor, "integrations:read", production_only=True)
    return actor
