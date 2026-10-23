"""ServiceNow Table API adapter: incident lookup and approved incident creation."""
from __future__ import annotations
from typing import Any
from .base import IntegrationError, JsonApiClient, require_approval


class ServiceNowClient:
    def __init__(self, instance_url: str, token: str, *, timeout_seconds: float = 10.0) -> None:
        if not token:
            raise ValueError("ServiceNow bearer token is required.")
        self.api = JsonApiClient(instance_url, token=token, timeout_seconds=timeout_seconds)

    def find_incidents_by_correlation_id(self, correlation_id: str) -> list[dict[str, Any]]:
        if not correlation_id.strip():
            raise ValueError("correlation_id is required.")
        result = self.api.request("GET", "/api/now/table/incident", params={
            "sysparm_query": f"correlation_id={correlation_id}",
            "sysparm_fields": "sys_id,number,short_description,state,correlation_id", "sysparm_limit": 10})
        rows = result.data.get("result") if isinstance(result.data, dict) else None
        if not isinstance(rows, list):
            raise IntegrationError("invalid_response", "ServiceNow returned an unexpected incident collection.")
        return rows

    def create_incident(self, *, short_description: str, description: str, correlation_id: str,
                        dry_run: bool = True, approval=None) -> dict[str, Any]:
        if not short_description.strip() or not correlation_id.strip():
            raise ValueError("short_description and correlation_id are required.")
        payload = {"short_description": short_description.strip(), "description": description.strip(),
                   "correlation_id": correlation_id.strip()}
        preview = require_approval(action="servicenow.create_incident", dry_run=dry_run,
                                   approval=approval, payload=payload)
        if preview is not None:
            return preview
        # Never automatically retry POST: the provider may have committed before a timeout.
        result = self.api.request("POST", "/api/now/table/incident", json_body=payload)
        body = result.data.get("result") if isinstance(result.data, dict) else None
        if not isinstance(body, dict) or not body.get("sys_id"):
            raise IntegrationError("invalid_response", "ServiceNow response omitted the created incident identifier.")
        return body
