# OnboardOps architecture notes

## Current release boundary

The existing Streamlit UI and pure checklist engine remain intact. New provider adapters and workflow primitives are framework-neutral Python modules. This is an incremental integration foundation, not yet a complete multi-user production deployment.

```text
Streamlit UI (current request/checklist flow)
       |
       +--> Pure validation and checklist generation
       +--> Optional REST adapters: Graph/Intune, ServiceNow, Jira,
       |    Snipe-IT, Workday and GitHub
       +--> Lifecycle and action safety primitives:
            state transitions, payload-bound approval fingerprints,
            SQLite action ledger and hash-chained local audit events
```

## Design principles

1. No hidden network calls: core validation and the offline demo do not contact external systems.
2. Safe-by-default writes: write methods default to dry-run and require a payload-bound approval object for live actions.
3. No blind retries: a POST timeout may mean the provider accepted the request. Reconcile before retrying.
4. Approval binds to content: fingerprints include provider, operation and canonical JSON payload. Changes invalidate approval; requester self-approval is rejected.
5. Minimal error disclosure: provider response bodies and exception strings are not copied into user-facing errors.
6. Least privilege: Graph/Intune methods are read-only here. Other writes require only permissions needed for the chosen operation.
7. Audit integrity is detectable, not guaranteed: an administrator able to rewrite the entire SQLite database can recompute its hash chain. This is not a tamper-proof enterprise log.

## Next engineering boundary

The SQLite ledger is a local single-process foundation. Team use needs PostgreSQL migrations, OIDC authentication, server-side RBAC, case ownership, concurrency controls and a transactional outbox/reconciliation model. Do not describe this foundation as a secure multi-user production system until those are implemented and reviewed.

## Test layers

- Unit tests for lifecycle transitions and approval fingerprints.
- Adapter contract tests for payload shapes and provider response handling.
- Safety tests for dry-run defaults, explicit approval, redirect rejection and secret-safe errors.
- Offline demo using synthetic IDs and no external network calls.
- Future opt-in live tests, isolated from normal CI and dedicated test tenants.


## Case dashboard and demo fixtures

The Case Management page supports status and lifecycle filters, case-ID/summary search, CSV export of the filtered view, and event history with UTC timestamps and metadata. Synthetic fixture generation lives in `onboardops/demo_fixtures.py`, separate from presentation code, so its lifecycle behavior can be tested without launching Streamlit.

The fixture seeder is idempotent by case ID: existing fixture records are not reset. Automated tests assert the expected four lifecycle states and repeat-run behavior. The CSV export contains case metadata only; it is not intended as a production reporting or access-control boundary.

## Future production architecture

Keep the next steps in this order:

1. **Authentication and authorisation:** integrate a real OIDC-backed identity boundary, enforce role and case-ownership checks server-side, and test direct API/service calls rather than relying on UI visibility.
2. **Persistence:** add versioned database migrations and a PostgreSQL implementation behind a storage interface only when multi-user deployment is a real requirement.
3. **Provider execution:** add an explicit action queue/outbox, durable idempotency keys, per-provider reconciliation, and observable outcomes for ambiguous POST timeouts.
4. **Operations:** add structured, redacted logs, health checks, backup/restore tests, retention rules and monitoring.
5. **Live integration tests:** keep them opt-in, isolated to dedicated test tenants and separate from ordinary CI.

Do not combine these into one large refactor. Each boundary should have a small reviewable change and a test strategy before live execution is considered.


## Case triage and queue management

The case queue supports priority (low, normal, high, urgent) and technician assignment, with filters for priority and assigned/unassigned work. Summary metrics highlight active urgent/high-priority cases and unassigned active work. Changes are version-checked and written to the case event history. Existing SQLite demo databases are migrated in place with conservative defaults (normal priority, no assignee).

This is a local single-user workflow feature, not a paging system or an SLA engine. Assignment is a text identity field and is not proof that the named technician is authenticated or available. The interface continues to use role checks and synthetic demo data.


## Operations reporting

The Operations Report page aggregates local case metadata into status, lifecycle and priority distributions, active/unassigned/high-priority counts, and a seven-day aging view. Aggregation lives in a pure helper with deterministic tests and does not include request payloads in report rows. Reports cover up to the 500 most recently updated cases and aging is a triage signal only, not an SLA measurement. The page is read-only and uses the same case-read permission as the case queue.
