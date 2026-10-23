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
