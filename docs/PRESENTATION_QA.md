# OnboardOps technical talking points and likely Q&A

Use these as concise answers, not claims to memorise without understanding. Be explicit about the difference between code, automated evidence, and live verification.

## Talking points

### Architecture
- The checklist/validation core is separated from Streamlit and provider adapters.
- SQLite stores local case state and events; the operations report derives bounded local indicators from cases visible to the current actor.
- Provider HTTP calls occur only when an adapter method is explicitly invoked. The offline integration demo uses no HTTP requests.
- The Docker demo binds to localhost and runs as a non-root user with a read-only root filesystem plus explicit writable state/output volumes.

### Safety and failure handling
- Write adapters default to dry-run and require an approval bound to the exact provider operation and payload.
- Approval is separate-actor, expires after 15 minutes, and is consumed or revoked. It is a safety control, not proof of authenticated identity.
- A provider timeout can happen after the remote side committed. The correct state can be “unknown”; reconcile before retrying.
- CSV exports use a shared formula-injection escape helper. Key-based secret redaction is useful but cannot reliably detect every secret embedded in free text.

### Evidence
- Unit/contract tests exercise local behavior and mock HTTP boundaries.
- Streamlit AppTest checks pages for uncaught render exceptions; it is not a browser visual or accessibility audit.
- Compose smoke checks the health endpoint, writes a synthetic case to the mounted SQLite database, restarts the container, and verifies persistence.
- CI, if cited, must be for the exact commit under discussion. User-run Windows results should be attributed as such unless reproduced independently.

## Likely Q&A

### “Is this production-ready?”
No. It is a local-first portfolio prototype. Production use needs reviewed OIDC/SSO, service-layer record authorization, a managed multi-user database, backup/restore objectives, protected logs and retention, monitoring, and provider-specific reconciliation.

### “What prevents someone from approving their own request?”
The approval workflow requires a different actor from the requester and binds approval to the exact provider operation/payload. That protects the local workflow contract, but identity is only as trustworthy as the configured authentication boundary. The default demo identity is not production authentication.

### “Is the trusted-proxy mode equivalent to SSO?”
No. It is a seam for a separately configured trusted proxy. The proxy must authenticate users, strip client-supplied identity headers, set trusted headers, and be protected by TLS/network isolation. The repository does not bundle an OIDC provider or independently validate a deployment.

### “Can the app create accounts or provision devices?”
The onboarding page generates technician instructions and exports; it does not provision accounts or devices. Provider adapters exist, but live writes are not exposed in the UI. Do not conflate an adapter method or mocked test with a successful live operation.

### “How do you handle an HTTP timeout on a write?”
Treat the result as potentially ambiguous. Do not automatically retry a POST that may already have committed. Reconcile using provider-specific lookup/correlation mechanisms and record the confirmed outcome. Not every provider offers a universal idempotency guarantee.

### “Why SQLite?”
It is simple, local, and sufficient for a single-machine demonstration. It provides transactions and a durable schema version, but it is not a shared multi-user database or a complete enterprise audit store. A team deployment would need an explicit migration and managed-storage design.

### “What do the exports contain?”
The case CSV contains bounded case metadata rather than full request payloads; report exports contain selected queue/aging fields. Text values are escaped to reduce spreadsheet formula injection. JSON handoff export still requires data minimization and should only contain synthetic demo data here.

### “How do you know the app works?”
State the evidence precisely: focused/full tests and Streamlit smoke tests have been reported by the user on Windows; source inspection shows a Python-version CI matrix, offline demos, and a Compose persistence smoke test. Do not say a check passed unless you can point to a result for the exact commit. None of these proves live provider compatibility.

### “Why are accessibility claims limited?”
AppTest catches uncaught page exceptions, not keyboard order, focus visibility in the browser, screen-reader announcements, zoom behavior, or measured contrast. Those require a manual review in the target browser and assistive technology.

### “What would you build next?”
1. Review and test the identity boundary with OIDC/SSO and service-layer case authorization.
2. Add durable reconciliation for ambiguous provider outcomes and a clear action state model.
3. Define data retention, protected logging, backup/restore recovery objectives, and operational ownership.
4. Run browser accessibility checks and opt-in live contract tests against isolated provider test tenants.

## Claims to avoid
- “Production-ready,” “fully secure,” “tamper-proof,” “multi-tenant,” or “ASVS-compliant.”
- “Live integration tested” based only on mocks.
- “CI is green” without a successful run for the commit shown.
- “Accessible” based only on screenshots or Streamlit AppTest.
- Any implication that the prototype has modified real accounts, devices, tickets, or employee records.
