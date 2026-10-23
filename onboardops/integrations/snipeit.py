"""Snipe-IT asset inventory adapter with approved checkout support."""
from __future__ import annotations
from typing import Any
from .base import IntegrationError, JsonApiClient, require_approval


class SnipeITClient:
    def __init__(self, api_base_url: str, api_token: str, *, timeout_seconds: float = 10.0) -> None:
        if not api_token:
            raise ValueError("Snipe-IT API token is required.")
        self.api = JsonApiClient(api_base_url, token=api_token, timeout_seconds=timeout_seconds)

    def search_hardware(self, search: str, *, limit: int = 50) -> list[dict[str, Any]]:
        if not search.strip():
            raise ValueError("Search term is required.")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100.")
        result = self.api.request("GET", "/hardware", params={"search": search.strip(), "limit": limit})
        rows = result.data.get("rows") if isinstance(result.data, dict) else None
        if not isinstance(rows, list):
            raise IntegrationError("invalid_response", "Snipe-IT returned an unexpected hardware collection.")
        return rows

    def checkout_to_user(self, *, asset_id: int, user_id: int, note: str,
                         dry_run: bool = True, approval=None) -> dict[str, Any]:
        if asset_id <= 0 or user_id <= 0:
            raise ValueError("asset_id and user_id must be positive numeric IDs from Snipe-IT.")
        payload = {"checkout_to_type": "user", "assigned_user": user_id, "note": note.strip()}
        preview = require_approval(action="snipeit.checkout_asset", dry_run=dry_run,
                                   approval=approval, payload={"asset_id": asset_id, **payload})
        if preview is not None:
            return preview
        result = self.api.request("POST", f"/hardware/{asset_id}/checkout", json_body=payload)
        if not isinstance(result.data, dict):
            raise IntegrationError("invalid_response", "Snipe-IT returned an unexpected checkout response.")
        return result.data
