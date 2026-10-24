# Five-minute OnboardOps presentation script

This guide is for a live portfolio/recruiter demonstration. Use synthetic data only. The local demo identity cannot perform live provider lookups or provider writes.

## Before the presentation

1. Start Docker Desktop/Engine.
2. From the repository root, run:

   ```sh
   docker compose up -d --build
   curl --fail --silent http://127.0.0.1:8501/_stcore/health
   docker compose exec -T onboardops python scripts/preflight.py
   ```

3. Open http://127.0.0.1:8501 and keep a terminal available for the offline integration demo.
4. In Case management, click **Load synthetic sample cases**. It is additive and will not reset existing sample history. For a fresh demo, use the narrowly scoped reset procedure in the Docker demo guide before loading fixtures.

A demo-mode authentication warning from preflight is expected. Any FAIL result is not expected; fix it before presenting. Do not print or paste environment values into the terminal recording.

## Talk track

### 0:00–0:40 — Problem and scope

**Say:** “OnboardOps models IT onboarding as a controlled case lifecycle rather than a loose checklist. It combines case state, triage, approval history, operations reporting, and provider-adapter safety. The demo uses synthetic records and does not write to live provider systems.”

Point out the navigation and local-first/demo boundary. Avoid claiming the application is production-ready or certified.

### 0:40–2:15 — Case management

1. Open **Case management** and load synthetic sample cases.
2. Show the different lifecycle states and use status/lifecycle/priority filters.
3. Open the awaiting-approval or in-progress sample to show case details, triage fields, and event history.
4. Point out the event timeline and version-checked changes. If making a triage or status change, explain that it creates a history entry; use a synthetic record only.
5. Show the paginated list and filtered CSV export. Explain that CSV text is escaped for spreadsheet safety and exports contain case metadata rather than arbitrary audit metadata.

**Say:** “The important design decision is that the lifecycle and authorization rules live in the Python service/store layer; a hidden button is not the security boundary.”

### 2:15–3:00 — Operations report

Open **Operations Report** and point out status/lifecycle/priority distributions, active and unassigned work, approval waiting time, and stale-work signals.

**Say:** “These are triage indicators, not an SLA engine. The page reports bounded local data and deliberately avoids exporting full request payloads.”

### 3:00–4:00 — Integration safety

Open **Integration Lab**.

1. Show configuration readiness without exposing secret values.
2. Note that live read-only lookups are disabled for the local demo identity; an authorised trusted-proxy role is required.
3. Show an offline write-payload preview, without enabling or executing a live write.

Then, in a terminal, run:

```sh
docker compose exec -T onboardops python scripts/integration_demo.py
```

**Say:** “Provider writes default to dry-run, approvals are payload-bound and short-lived, and a POST timeout is an unknown outcome rather than proof that the provider rejected the action. The local tests mock HTTP; I have not claimed live tenant verification.”

### 4:00–5:00 — Engineering evidence

If time permits, show:

- the [security verification matrix](SECURITY_VERIFICATION_MATRIX.md);
- the [threat model](THREAT_MODEL.md);
- the [operator runbook](OPERATIONS_RUNBOOK.md);
- GitHub Actions test matrix, Compose runtime smoke test, and CodeQL workflow.

**Say:** “The project distinguishes implementation from evidence. CI checks Python behavior, the container's health endpoint, mounted database writes and persistence across restart. It does not replace an OIDC review, a production database, live provider tests, or a browser accessibility audit.”

## If something goes wrong

- **App does not start:** run `docker compose logs --tail=100 onboardops`, check the Docker engine, then run `docker compose config --quiet`.
- **Health endpoint fails:** do not proceed as if the app is ready. Inspect logs and the current CI/runtime setup first.
- **No sample cases:** click **Load synthetic sample cases**. If fixture state is stale, use the documented reset command only for the fixed sample IDs.
- **Integration buttons are disabled:** this is expected in demo mode. Do not add real credentials or bypass the permission gate during the presentation.
- **A provider write appears uncertain:** do not retry blindly; follow the unknown-outcome section of the operator runbook.

## Claims to avoid

- Do not call the project production-ready, multi-tenant, or ASVS-compliant.
- Do not describe local hash chaining as tamper-proof external audit retention.
- Do not claim live provider compatibility from mocked tests.
- Do not claim WCAG conformance without manual/browser testing.
- Do not use real employee records, tokens, or production endpoints in the portfolio demo.
