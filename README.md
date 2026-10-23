# OnboardOps

**A local-first IT onboarding workflow prototype with optional provider adapters, approval-bound action previews, and offline tests.**

This portfolio project was developed with AI assistance. The repository owner remains responsible for reviewing, testing, understanding and being able to explain the code.

OnboardOps standardises onboarding preparation for Windows and macOS. The Streamlit flow validates a synthetic request and generates a technician checklist plus a hardware allocation CSV. The integration foundation adds reusable Python adapters for Microsoft Graph / Intune, ServiceNow, Jira Cloud, Snipe-IT, Workday and GitHub.

> **Honest scope:** provider adapters are implemented but have not been verified against live tenant environments. The Streamlit Integration Lab supports configured read-only lookups and offline write previews; live writes are not exposed in the UI until authentication and server-side RBAC are implemented. Writes default to dry-run. Do not use this project for production employee data or production changes.

## What it demonstrates

- IT operations: consistent onboarding checklist and hardware handover outputs.
- Software engineering: pure core logic, provider adapter boundaries, lifecycle transitions, approval fingerprints, action ledger and automated tests.
- Cybersecurity: HTTPS-by-default API client, redirects disabled, bounded timeouts, least-privilege guidance, dry-run writes, sanitised errors and secret-redacting audit metadata.
- Integration design: JSON REST payloads aligned to provider APIs where the schema is stable, plus configurable Workday paths where schemas vary by tenant.

## Quick start on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Offline demo and tests

No credentials or external service access are required:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py onboardops tests scripts
python scripts/demo.py
python scripts/integration_demo.py
```

The integration demo previews provider payloads, exercises a synthetic approval flow and verifies a local audit hash chain. It makes no HTTP requests. Tests use mocks and synthetic data; they do not prove live tenant permissions or live API compatibility.

## Optional integration adapters

Launch the app and select **Integration Lab** in the Streamlit multipage navigation to check environment configuration, perform configured read-only lookups, and preview provider-shaped write payloads. See [Integration setup and limitations](docs/INTEGRATIONS.md) and [Architecture notes](docs/ARCHITECTURE.md).

| Provider | Implemented capability | Live writes default |
|---|---|---|
| Microsoft Graph / Entra | App-only user lookup | Not implemented |
| Intune through Graph | Bounded managed-device lookup | Not implemented |
| ServiceNow | Incident lookup and Table API create preview/write | Dry-run |
| Jira Cloud | Issue lookup and REST v3 create preview/write | Dry-run |
| Snipe-IT | Hardware search and checkout preview/write | Dry-run |
| Workday | Configured worker GET and tenant-specific POST preview/write | Dry-run |
| GitHub | Repository issue create preview/write | Dry-run |

Credentials are passed into adapter constructors by application code; they are not stored in the repository. The committed environment example is a list of variable names only and is not automatically loaded. Use a secret manager or local environment variables. Never commit real tokens.

## Important security and reliability boundaries

- Payload-bound approval objects are not a team authorisation system. They do not replace authenticated identity or server-side role checks; do not expose live writes through an unauthenticated public UI.
- The SQLite action ledger is local single-process scaffolding, not multi-user transactional storage.
- A local hash-chained audit trail is tamper-evident for ordinary row edits, not tamper-proof against an administrator who can rewrite the database.
- A POST timeout may occur after the provider committed the request. Do not blindly retry; reconcile with the provider first.
- Workday paths, permissions and payload schemas vary by tenant/API version. Validate them against that tenant's API Explorer.
- Intune's managed-device API requires an active Intune licence and appropriate consented permissions.
- No live integration tests were run because no provider test tenants were available.

## Roadmap

1. Integrate adapters into persistent lifecycle cases with server-side authentication and RBAC.
2. Add PostgreSQL and versioned migrations for team use.
3. Add a transactional action queue/outbox and provider-specific reconciliation.
4. Add an isolated, opt-in live integration test suite.
5. Provide a synthetic-only hosted demo and Docker Compose environment.

OnboardOps is a personal portfolio project. It is an integration and workflow prototype, not a production provisioning system.
