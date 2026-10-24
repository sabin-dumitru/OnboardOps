# Case persistence, authentication and one-provider workflow

## Local synthetic case management

Run `python -m streamlit run app.py`, then select **Case management** in the page navigation. The page stores synthetic cases in SQLite at `data/onboardops_cases.sqlite3` by default. Set `ONBOARDOPS_CASE_DB` to choose another path. Case status changes are recorded as events, and a version check prevents stale updates from silently overwriting a newer case. Case request data must be a JSON object and is capped at 64 KiB after secret-key redaction to prevent unexpectedly large local records.

The demo identity can create and transition synthetic cases only. Never use real employee data in this portfolio demo.

## Authentication modes

- `ONBOARDOPS_AUTH_MODE=demo` (default): fixed local demo actor; synthetic case operations only.
- `ONBOARDOPS_AUTH_MODE=trusted_proxy`: requires `ONBOARDOPS_TRUSTED_AUTH_PROXY=true` and the `X-Auth-Request-User` / `X-Auth-Request-Groups` headers supplied by a trusted authentication proxy.

The proxy must authenticate the user, strip any client-supplied copies of these headers and set its own trusted values. Streamlit must not be directly reachable by untrusted clients in this mode. Recognised roles are `onboardops-requester`, `onboardops-approver`, `onboardops-operator` and `onboardops-admin`. Unknown roles and missing identity fail closed.

This is an authentication-proxy integration seam, not a bundled OIDC provider. The local demo does not claim production-grade identity. Before team deployment, configure and independently test a real proxy, header stripping, TLS, network isolation, session expiry and account revocation.

## One provider: GitHub issue creation

`onboardops/provider_workflow.py` ties together role checking, separate-actor approval bound to the exact repository/title/body, the GitHub REST adapter, a local idempotency ledger and an audit event. Automated tests mock the HTTP boundary and verify the outbound request and recorded outcome. This proves the local workflow contract only; it does not prove live GitHub token scopes, repository policy or a successful real issue creation.

The UI does not expose live provider writes. Do not enable live writes until an isolated test repository, trusted identity proxy, persistent approval records, server-side authorisation and provider reconciliation have been verified. A timed-out POST is recorded as unknown; reconcile before retrying.

## Storage boundary

SQLite is single-machine local persistence, not a shared multi-user database. Team deployment needs a managed database, migrations, backups, concurrency tests, retention controls and monitoring. The event history is application history, not a tamper-proof enterprise audit log.

## Backup and restore (local demo)

Create a consistent SQLite backup while the app is running:

```powershell
python scripts/backup_cases.py --destination backups/cases-2026-10-24.sqlite3
```

The source defaults to `ONBOARDOPS_CASE_DB` or `data/onboardops_cases.sqlite3`. The helper uses SQLite's online backup API (so committed WAL data is included), checks the backup with `PRAGMA integrity_check`, and refuses to overwrite an existing destination unless `--overwrite` is explicitly passed. Store backups somewhere with appropriately restricted filesystem permissions; case payloads may contain sensitive data even though credentials are redacted by key name.

To restore, stop Streamlit first, preserve a copy of the current database, then copy the verified backup to the configured database path. Start the app and verify expected case counts and histories before resuming use. Do not overwrite a live database file or treat this local procedure as a tested disaster-recovery plan. This utility backs up the case database only; it does not back up the separate provider action ledger if that ledger is configured elsewhere.

## Tests

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py onboardops tests scripts
python scripts/demo.py
python scripts/integration_demo.py
```
