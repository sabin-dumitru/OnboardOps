# Presentation and company-readiness plan

**Purpose:** deliver a reliable, explainable presentation of OnboardOps while progressively closing the highest-risk gaps between a local-first portfolio prototype and a company-operated service.

**Current baseline:** local Streamlit UI, synthetic cases, SQLite persistence, approval-bound provider adapter previews, offline adapter contract tests, Python 3.10–3.13 CI, Docker build, CodeQL, backup utility, threat model, and operator runbook.

**Non-goal:** declaring the project production-ready simply because the demo is polished or CI is green. Do not use real employee data or enable live provider writes until identity, authorisation, persistence, reconciliation, and deployment controls have been independently verified.

**Progress note (2026-10-24):** the original risk-first batch has been implemented across PRs #37–#52, including HTTP/URL hardening, export safety, role-matrix tests, Compose runtime smoke coverage, preflight, repeatable sample reset, and strict JSON boundaries. Accessibility improvements are in review; the [security verification matrix](SECURITY_VERIFICATION_MATRIX.md) records current evidence and explicitly open production gates.

## Delivery sequence (next 15 pull requests)

The sequence is risk-first. Each change should remain small, include regression tests where behavior changes, and be merged only after current-head CI passes. Reorder if investigation uncovers a blocker.

| # | Focus | Intended outcome / acceptance evidence |
|---|---|---|
| 1 | HTTP client hardening | Validate timeout and request configuration; cap successful response bodies before JSON parsing; tests for malformed configuration and oversized responses. |
| 2 | Integration error semantics | Separate retryability from write safety; document ambiguous POST outcomes; tests that callers cannot mistake timeout for confirmed failure. |
| 3 | Input validation | Bound provider paths, identifiers, and payload shape without breaking valid provider contracts. |
| 4 | CSV export safety | Neutralise spreadsheet-formula cells in case/report exports; tests for formula prefixes, tabs and newlines. |
| 5 | Pagination and query limits | Make case/event list limits explicit and deterministic; protect UI/database from unbounded reads. |
| 6 | SQLite transaction consistency | Review connection lifecycle, concurrent updates, and transaction rollback behavior; add concurrency/migration regression tests. |
| 7 | Approval integrity | Test expiry, revocation, requester/approver separation, exact payload binding, and replay behavior at boundaries. |
| 8 | Authorization matrix | Exercise every role against read/create/transition/triage/export/provider-write operations; ensure default deny. |
| 9 | Error handling and safe diagnostics | Make user-facing failures actionable without leaking secrets or raw provider response bodies. |
| 10 | Dependency and code-quality checks | Add lightweight static/style checks only after establishing a clean baseline; pin actions and avoid brittle/duplicative checks. |
| 11 | Docker runtime hardening | Verify non-root execution, health checks, writable-volume paths, and local-only binding; build-test the resulting image. |
| 12 | Presentation flow | Make the synthetic end-to-end path easy to follow with a predictable seed/reset story and clear demo-only banners. |
| 13 | Accessibility pass | Implement practical keyboard, semantic-label, contrast, and focus improvements that Streamlit supports; record manual checks honestly. |
| 14 | Operational readiness | Improve backup verification/restore rehearsal and configuration preflight; distinguish tested behavior from manual operator steps. |
| 15 | Architecture and evidence pack | Update architecture/decision records, map controls to OWASP ASVS and NIST SSDF, and produce a recruiter-friendly readiness matrix with known gaps. |

## Design principles used

1. **Secure by default:** least privilege, deny by default, strict server-side validation, and no implicit live writes.
2. **Explicit state:** approvals are short-lived, payload-bound, one-time, and auditable; an uncertain remote write is marked unknown until reconciled.
3. **Bounded work:** timeouts, response/payload limits, pagination, and predictable failure modes.
4. **Data minimisation:** synthetic fixtures, redaction at storage and export boundaries, operational exports that exclude request payloads unless explicitly needed.
5. **Observable but not leaky:** useful event history and diagnostics without credentials or arbitrary upstream response content.
6. **Recoverable:** backup/restore steps and migration tests, with realistic limits around local SQLite and single-instance deployment.
7. **Small verified increments:** regression tests, CI, code-reviewable diffs, and no claims of live integration or visual validation without evidence.

## Research basis

- [OWASP Application Security Verification Standard 5.0](https://asvs.owasp.org/) is used as a practical web-application security verification catalogue, not as a certification claim.
- [NIST SP 800-218 Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final) informs the security-in-the-lifecycle approach. NIST has also published a draft SP 800-218 Rev. 1; the plan should be revisited as that work matures.
- [GitHub Actions secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use) informs immutable action pins and least-privilege workflow permissions.
- OWASP access-control and logging guidance informs default-deny authorization tests, protected audit events, and redacted diagnostics.

## Company-readiness gates (must not be waved through)

- Reviewed OIDC/SSO integration, trusted identity propagation, session security, and enforced role/record-level authorization.
- Production database and migration/backup/restore strategy appropriate for concurrency and availability requirements.
- Provider-specific isolated-tenant tests, least-privilege credentials, idempotency and reconciliation for ambiguous writes.
- Deployment secrets management, network boundaries, TLS, monitoring/alerting, audit retention, incident ownership, and data retention.
- Accessibility and browser smoke tests on the actual target environment.
- Security review and operational recovery rehearsal by a responsible human owner.

A successful unit-test run is evidence for the tested code paths only. It is not proof of production readiness, provider compatibility, security certification, or disaster-recovery capability.
