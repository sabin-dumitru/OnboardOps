# OnboardOps

**A local-first IT onboarding workflow prototype with optional provider adapters, approval-bound action previews, and offline tests.**

This portfolio project was developed with AI assistance. The repository owner remains responsible for reviewing, testing, understanding and being able to explain the code.

**Copyright and usage:** Copyright © 2026 Sabin Dumitru. All rights reserved. No permission is granted to use, copy, modify, or redistribute this code. The repository is public for viewing as a portfolio; public visibility does not mean the code is open source. This notice states the owner's intent but is not legal advice.

OnboardOps standardises onboarding preparation for Windows and macOS. The Streamlit flow validates a synthetic request and generates a technician checklist plus a hardware allocation CSV. The integration foundation adds reusable Python adapters for Microsoft Graph / Intune, ServiceNow, Jira Cloud, Snipe-IT, Workday and GitHub. A separate Case Management page now stores synthetic cases and status history locally in SQLite, with a demo-only identity and a trusted-proxy role-checking seam.

> **Honest scope:** provider adapters are implemented but have not been verified against live tenant environments. The Streamlit Integration Lab supports configured read-only lookups and offline write previews; live writes are not exposed in the UI until authentication and server-side RBAC are implemented. Writes default to dry-run. Do not use this project for production employee data or production changes.

## What it demonstrates

- IT operations: consistent onboarding checklist and hardware handover outputs.
- Software engineering: pure core logic, provider adapter boundaries, lifecycle transitions, approval fingerprints, action ledger and automated tests.
- Cybersecurity: HTTPS-by-default API client, redirects disabled, bounded timeouts, least-privilege guidance, dry-run writes, sanitised errors and secret-redacting audit metadata.
- Integration design: JSON REST payloads aligned to provider APIs where the schema is stable, plus configurable Workday paths where schemas vary by tenant.

## Quick start (Windows, macOS or Linux)

### Option A — Docker (recommended for a quick demo)

Install Docker Desktop or Docker Engine, then run:

```sh
docker compose up --build
```

Open [http://localhost:8501](http://localhost:8501). The app is bound to your own computer only. Synthetic case data persists in Docker-managed local volumes. See [Docker demo guide](docs/DOCKER_DEMO.md).

### Option B — Python virtual environment

**Windows PowerShell**

```powershell
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

**macOS / Linux**

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Recruiter-friendly walkthrough

For a short, repeatable demonstration, use synthetic data only:

1. Start the app with Docker or the Python environment above.
2. Open **Case management** and load the synthetic sample cases.
3. Filter for cases waiting for approval; inspect the requester and status history, then demonstrate that the requester cannot approve their own case.
4. Assign a technician and change priority on a sample case; show the versioned audit event.
5. Open **Operations Report** to review workload distribution, oldest pending approvals, and active cases with no updates for at least three days.
6. Export one case as a JSON handoff packet and export the approval queue as CSV.
7. Run the offline integration demo from a terminal to show payload-bound approval, duplicate-action protection, and the local audit-chain check without contacting a provider.

**Suggested interview framing:** explain one end-to-end flow, one safety invariant, one failure mode, and one known production limitation. For example, approvals bind to an exact payload; a POST timeout may still mean a provider accepted a request, so blind retries are unsafe. Be explicit that the UI uses synthetic local data and live writes are not enabled.

## Offline demo and tests

No credentials or external service access are required:

```powershell
python scripts/preflight.py
python -m unittest discover -s tests -v
python -m compileall -q app.py onboardops tests scripts
python scripts/demo.py
python scripts/integration_demo.py
```

The preflight command checks local configuration files, auth-mode readiness, and writable database/output locations without printing secrets or making network calls. The integration demo previews provider payloads, exercises a synthetic approval flow and verifies a local audit hash chain. It makes no HTTP requests. Tests use mocks and synthetic data; they do not prove live tenant permissions or live API compatibility.

## Persistent cases and authentication boundary

Run `python -m streamlit run app.py` and choose **Case management** in the multipage navigation to create and revisit synthetic cases. The local SQLite store persists status and event history across restarts and detects stale status updates. The default demo identity can only manage synthetic cases; it cannot authorise provider writes.

The optional `ONBOARDOPS_AUTH_MODE=trusted_proxy` mode requires an explicitly trusted authentication proxy and recognised role headers. This is an integration seam, not a bundled OIDC provider. Follow [Case persistence and authentication notes](docs/AUTH_AND_CASES.md) before configuring it. Do not expose Streamlit directly to untrusted clients or enter real employee data.

A tested GitHub issue workflow connects role checks, separate-actor payload-bound approval, the GitHub adapter, local action ledger and audit event. The HTTP boundary is mocked in tests; no live GitHub write has been verified. Live writes remain disabled in the UI.

## Optional integration adapters

Launch the app and select **Integration Lab** in the Streamlit multipage navigation to check environment configuration, perform configured read-only lookups, and preview provider-shaped write payloads. See [Integration setup and limitations](docs/INTEGRATIONS.md), [Architecture notes](docs/ARCHITECTURE.md), the [threat model and deployment checklist](docs/THREAT_MODEL.md), and the [operator runbook](docs/OPERATIONS_RUNBOOK.md).

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

The next production-oriented milestones are deliberately separate from the current local demo:

1. Replace the trusted-proxy seam with reviewed OIDC integration and enforce case-level authorisation in the service layer.
2. Introduce versioned migrations and PostgreSQL only alongside a concrete multi-user deployment requirement.
3. Add a durable transactional outbox and provider-specific reconciliation for ambiguous write outcomes.
4. Add structured redacted logs, retention/backup policy, and restore tests.
5. Add opt-in live contract tests against isolated provider test tenants; keep them out of ordinary CI.

OnboardOps is a personal portfolio project. It is an integration and workflow prototype, not a production provisioning system.


## Engineering roadmap

See the [presentation and company-readiness plan](docs/PRESENTATION_READINESS_PLAN.md) for the risk-first improvement sequence, and the [security verification matrix](docs/SECURITY_VERIFICATION_MATRIX.md) for implementation evidence and remaining gaps.


For a repeatable live walkthrough, use the [five-minute presentation script](docs/PRESENTATION_SCRIPT.md).
