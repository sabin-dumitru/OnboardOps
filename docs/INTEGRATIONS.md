# Optional integrations

Provider adapters are separate from the pure checklist engine. Importing a connector does not make a network request; a request occurs only when a caller explicitly invokes a method.

| Provider | Read | Write | Configuration caveats |
|---|---|---|---|
| Microsoft Graph / Entra ID | User lookup | None | App-only OAuth client credentials; admin consent and least-privilege application permissions |
| Microsoft Intune | One bounded page of managed devices | None | Active Intune licence and appropriate permission, e.g. DeviceManagementManagedDevices.Read.All |
| ServiceNow | Incident lookup by correlation ID | Create incident | Table API and instance ACLs must allow the operation |
| Jira Cloud | Get issue | Create issue | Site URL, account email, API token, project permissions; REST v3 description uses Atlassian Document Format |
| Snipe-IT | Search hardware | Checkout asset to user | API root should include /api/v1; IDs must come from that instance |
| Workday | Configurable worker endpoint | Configurable, explicitly approved POST | API root, endpoint, schema, security domain and permissions vary by tenant/API version |
| GitHub | Not exposed yet | Create issue | Fine-grained token scoped to the intended repository with Issues: write |

## Configuration and secrets

No credentials belong in source code, issue comments, screenshots or committed files. Use environment variables or a deployment secret manager. The committed environment example contains names only and is not automatically loaded. The Integration Lab reads configured values from environment variables, exposes selected read-only lookups and renders offline write previews. It does not collect or display secrets, and it intentionally does not execute live writes from the UI. Adapters accept credentials as constructor arguments so callers can connect a suitable secret source.

## Safe write contract

Write methods default to dry-run. Dry-run returns the intended provider operation and JSON payload without sending a request. A live write requires dry-run to be disabled and an Approval object created by the workflow helper for the exact provider, operation and payload. The helper rejects self-approval and the adapter rejects a stale or mismatched approval.

This approval object is a low-level safety gate, not a complete team authorisation system. It is not a cryptographic identity assertion and does not replace server-side authentication or role checks. Before enabling live writes from a multi-user UI, verify identity and roles server-side, bind approval to the exact payload, record the action in a persistent ledger, and reconcile uncertain outcomes. A browser checkbox alone must not authorise production changes.

POST timeouts are ambiguous: a provider may have committed before the response was lost. Adapters do not automatically retry writes. ServiceNow supports correlation IDs; Jira labels carry a case marker, but neither is a universal idempotency guarantee.

## Workday caveat

Workday's API Explorer documents endpoint-specific schemas and security domains. There is no universal create-employee payload that works across tenants. This adapter accepts a configured API root and explicit endpoint path, previews the exact request, and requires explicit approval for POST. Validate the endpoint, schema, business process and permissions with the tenant owner before a live call. No Workday tenant was available for live verification.

## Test and demo

```powershell
python -m unittest discover -s tests -v
python scripts/integration_demo.py
```

The offline demo makes no network calls and uses no real credentials. Mock-based tests prove local payload and safety behaviour, not that a particular tenant grants access or accepts every provider-specific field. Live verification remains opt-in for a dedicated test environment.
