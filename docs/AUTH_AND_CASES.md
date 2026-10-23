# Case persistence, authentication and one-provider workflow

## Local synthetic case management

Run `python -m streamlit run app.py`, then select **Case management** in the page navigation. The page stores synthetic cases in SQLite at `data/onboardops_cases.sqlite3` by default. Set `ONBOARDOPS_CASE_DB` to choose another path. Case status changes are recorded as events, and a version check prevents stale updates from silently overwriting a newer case.

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

## Tests

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py onboardops tests scripts
python scripts/demo.py
python scripts/integration_demo.py
```
