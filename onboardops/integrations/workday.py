"""Configurable Workday REST adapter; endpoint schemas are tenant-specific."""
from __future__ import annotations
from typing import Any
from .base import IntegrationError, JsonApiClient, require_approval


class WorkdayClient:
    def __init__(self, api_root: str, access_token: str, *, timeout_seconds: float = 10.0) -> None:
        if not access_token:
            raise ValueError("Workday OAuth access token is required.")
        self.api = JsonApiClient(api_root, token=access_token, timeout_seconds=timeout_seconds)

    def get_workers(self, *, endpoint_path: str = "/workers",
                    params: dict[str, Any] | None = None) -> Any:
        """Read workers from a tenant-configured REST API path."""
        return self.api.request("GET", endpoint_path, params=params).data

    def submit_configured_business_process(self, *, endpoint_path: str, payload: dict[str, Any],
                                           dry_run: bool = True, approval=None) -> dict[str, Any]:
        """POST a configured endpoint only after the tenant-specific schema is reviewed."""
        if not endpoint_path.startswith("/") or endpoint_path.startswith("//") or "://" in endpoint_path:
            raise ValueError("Workday endpoint_path must be a relative API path.")
        if any(part == ".." for part in endpoint_path.split("/")):
            raise ValueError("Workday endpoint_path must not contain parent-directory segments.")
        preview = require_approval(action="workday.submit_business_process", dry_run=dry_run,
                                   approval=approval, payload={"endpoint_path": endpoint_path, "body": payload})
        if preview is not None:
            return preview
        result = self.api.request("POST", endpoint_path, json_body=payload)
        if result.data is None:
            return {"status_code": result.status_code, "accepted": True}
        if not isinstance(result.data, dict):
            raise IntegrationError("invalid_response", "Workday returned an unexpected response.")
        return result.data
