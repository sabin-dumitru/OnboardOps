"""Defensive JSON REST client shared by provider adapters."""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any
from urllib.parse import unquote, urlsplit
import requests

_MAX_TIMEOUT_SECONDS = 120.0
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
from ..workflow import Approval, verify_approval


class IntegrationError(RuntimeError):
    """Sanitised provider error; excludes response bodies and secrets."""
    def __init__(self, code: str, message: str, *, status_code: int | None = None,
                 retryable: bool = False) -> None:
        super().__init__(message)
        self.code, self.status_code, self.retryable = code, status_code, retryable


@dataclass(frozen=True)
class ApiResult:
    status_code: int
    data: Any


def validate_base_url(value: str, *, allow_local_http: bool = False) -> str:
    value = (value or "").strip()
    parsed = urlsplit(value)
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    local_http = allow_local_http and parsed.scheme == "http" and parsed.hostname in local_hosts
    if parsed.scheme != "https" and not local_http:
        raise ValueError("Integration base URL must use HTTPS; HTTP is allowed only for explicit localhost development.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Integration base URL must contain a host and must not embed credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError("Integration base URL must not contain a query string or fragment.")
    decoded_base_path = unquote(parsed.path)
    if chr(92) in decoded_base_path or any(ord(char) < 32 or ord(char) == 127 for char in decoded_base_path):
        raise ValueError("Integration base URL path contains invalid characters.")
    if any(part == ".." for part in decoded_base_path.split("/")):
        raise ValueError("Integration base URL must not contain parent-directory path segments.")
    return value.rstrip("/")


def require_approval(*, action: str, dry_run: bool, approval: Approval | None,
                     payload: dict[str, Any]) -> dict[str, Any] | None:
    """Preview writes by default; live writes need a payload-bound, non-self approval."""
    if dry_run:
        return {"mode": "dry_run", "action": action, "payload": payload}
    if approval is None:
        raise IntegrationError("approval_required", f"Live action {action!r} requires a payload-bound approval.")
    try:
        provider, operation = action.split(".", 1)
    except ValueError as exc:
        raise ValueError("Action must use provider.operation format.") from exc
    try:
        verify_approval(approval, provider=provider, operation=operation, payload=payload)
    except ValueError as exc:
        raise IntegrationError("approval_invalid", "Approval is missing, stale or does not match this exact action.") from exc
    return None


class JsonApiClient:
    """HTTP client with bounded timeouts, redirects disabled and sanitised failures."""
    def __init__(self, base_url: str, *, token: str | None = None,
                 headers: dict[str, str] | None = None, auth: Any = None,
                 timeout_seconds: float = 10.0, session: requests.Session | None = None,
                 allow_local_http: bool = False) -> None:
        self.base_url = validate_base_url(base_url, allow_local_http=allow_local_http)
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise ValueError("Provider timeout must be a finite number between 0 and 120 seconds.")
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= _MAX_TIMEOUT_SECONDS:
            raise ValueError("Provider timeout must be a finite number between 0 and 120 seconds.")
        self.token, self.headers, self.auth = token, dict(headers or {}), auth
        self.timeout_seconds = float(timeout_seconds)
        self.session = session or requests.Session()

    def request(self, method: str, path: str, *, params: dict[str, Any] | None = None,
                json_body: dict[str, Any] | None = None,
                headers: dict[str, str] | None = None) -> ApiResult:
        if not path.startswith("/") or path.startswith("//") or "://" in path:
            raise ValueError("API path must be a relative path beginning with one slash.")
        decoded_path = unquote(path)
        if chr(92) in decoded_path or any(ord(char) < 32 or ord(char) == 127 for char in decoded_path):
            raise ValueError("API path contains invalid characters.")
        if any(part == ".." for part in decoded_path.split("/")):
            raise ValueError("API path must not contain parent-directory segments.")
        request_headers = {"Accept": "application/json", **self.headers, **(headers or {})}
        if self.token:
            request_headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = self.session.request(
                method.upper(), f"{self.base_url}{path}", params=params, json=json_body,
                headers=request_headers, auth=self.auth,
                timeout=(3.05, self.timeout_seconds), allow_redirects=False,
            )
        except requests.Timeout as exc:
            raise IntegrationError("timeout", "Provider request timed out; a write outcome may be unknown.",
                                   retryable=True) from exc
        except requests.RequestException as exc:
            raise IntegrationError("network_error", "Could not reach provider; check connectivity and endpoint configuration.",
                                   retryable=True) from exc
        if 300 <= response.status_code < 400:
            raise IntegrationError("redirect_rejected", "Provider redirect was not followed for security.",
                                   status_code=response.status_code)
        if response.status_code == 429 or response.status_code >= 500:
            raise IntegrationError("provider_unavailable", "Provider is temporarily unavailable or rate-limited.",
                                   status_code=response.status_code, retryable=True)
        if not 200 <= response.status_code < 300:
            raise IntegrationError("provider_rejected_request",
                                   "Provider rejected the request. Check permissions, configuration and payload schema.",
                                   status_code=response.status_code)
        if response.status_code == 204 or not response.content:
            return ApiResult(response.status_code, None)
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise IntegrationError(
                "response_too_large",
                "Provider response exceeded the 2 MiB safety limit.",
                status_code=response.status_code,
            )
        try:
            data = response.json()
        except (ValueError, requests.JSONDecodeError) as exc:
            raise IntegrationError("invalid_response", "Provider returned a successful response that was not valid JSON.",
                                   status_code=response.status_code) from exc
        return ApiResult(response.status_code, data)
