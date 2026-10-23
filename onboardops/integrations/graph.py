"""Microsoft Graph app-only read adapters for users and Intune managed devices."""
from __future__ import annotations
import time
from typing import Any
from urllib.parse import quote
import requests
from .base import IntegrationError, JsonApiClient


class MicrosoftGraphClient:
    """OAuth client credentials; admin consent and least-privilege app roles are required."""
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, *,
                 session: requests.Session | None = None, timeout_seconds: float = 10.0) -> None:
        if not all((tenant_id.strip(), client_id.strip(), client_secret)):
            raise ValueError("Tenant ID, client ID and client secret are required.")
        self.tenant_id, self.client_id, self.client_secret = tenant_id.strip(), client_id.strip(), client_secret
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self._token: str | None = None
        self._token_expiry = 0.0

    def _access_token(self) -> str:
        if self._token and time.monotonic() < self._token_expiry - 60:
            return self._token
        token_url = f"https://login.microsoftonline.com/{quote(self.tenant_id, safe='')}/oauth2/v2.0/token"
        try:
            response = self.session.post(
                token_url, data={"client_id": self.client_id, "client_secret": self.client_secret,
                "grant_type": "client_credentials", "scope": "https://graph.microsoft.com/.default"},
                headers={"Accept": "application/json"}, timeout=(3.05, self.timeout_seconds),
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise IntegrationError("token_network_error", "Could not reach Microsoft identity token endpoint.",
                                   retryable=True) from exc
        if response.status_code != 200:
            raise IntegrationError("token_rejected", "Microsoft identity rejected client authentication or consent.",
                                   status_code=response.status_code, retryable=response.status_code >= 500)
        try:
            body = response.json()
            token, expires = str(body["access_token"]), int(body.get("expires_in", 3600))
        except (ValueError, KeyError, TypeError) as exc:
            raise IntegrationError("invalid_token_response", "Microsoft identity returned an invalid token response.") from exc
        if not token:
            raise IntegrationError("invalid_token_response", "Microsoft identity returned an empty access token.")
        self._token, self._token_expiry = token, time.monotonic() + max(expires, 60)
        return token

    def _api(self) -> JsonApiClient:
        return JsonApiClient("https://graph.microsoft.com/v1.0", token=self._access_token(),
                             session=self.session, timeout_seconds=self.timeout_seconds)

    def get_user(self, user_id_or_upn: str) -> dict[str, Any]:
        if not user_id_or_upn.strip():
            raise ValueError("A user ID or user principal name is required.")
        result = self._api().request("GET", f"/users/{quote(user_id_or_upn.strip(), safe='@._-')}",
            params={"$select": "id,displayName,userPrincipalName,accountEnabled,department,jobTitle,officeLocation"})
        if not isinstance(result.data, dict):
            raise IntegrationError("invalid_response", "Microsoft Graph returned an unexpected user response.")
        return result.data

    def list_managed_devices(self, *, top: int = 50) -> list[dict[str, Any]]:
        if not 1 <= top <= 100:
            raise ValueError("top must be between 1 and 100.")
        result = self._api().request("GET", "/deviceManagement/managedDevices", params={
            "$top": top, "$select": "id,deviceName,operatingSystem,complianceState,managedDeviceOwnerType,userPrincipalName,lastSyncDateTime"})
        if not isinstance(result.data, dict) or not isinstance(result.data.get("value"), list):
            raise IntegrationError("invalid_response", "Microsoft Graph returned an unexpected device collection.")
        return result.data["value"]
