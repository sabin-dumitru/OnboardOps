# Threat model and security requirements

**Status:** portfolio/demo threat model, not a formal security assessment. Review whenever trust boundaries, identity, storage, or provider write paths change.

## System boundary

OnboardOps is a local-first Streamlit application with:
- a Python workflow and validation layer;
- a local SQLite case database and case-event history;
- optional provider adapters (Microsoft Graph/Intune, ServiceNow, Jira, Snipe-IT, Workday, GitHub);
- a demo identity mode and an optional trusted reverse-proxy identity seam;
- GitHub Actions for unit/contract tests and CodeQL analysis.

The supported default is synthetic data and offline tests. Live provider writes are not exposed in the UI. Adapter code and mocked tests do not prove compatibility with a real tenant.

## Assets and security objectives

| Asset | Objective |
|---|---|
| Provider credentials and access tokens | Keep out of source, case payloads, exports, logs, and exception messages |
| Employee and onboarding request data | Minimise collection; use synthetic data in demos; limit export scope |
| Case status, approvals, and assignments | Enforce valid transitions, separate-actor approval, stale-version rejection, and least privilege |
| Provider write payloads | Bind approval to the exact provider, operation, case, and payload; reject modifications and duplicate consumption |
| Audit evidence | Record actor and state changes; avoid raw sensitive payloads; detect changes to the action-ledger chain |
| CI workflow permissions and dependencies | Read-only defaults, narrowly scoped write permissions, reviewed third-party actions |

## Trust boundaries

1. **Browser to Streamlit:** browser input is untrusted. Validate identifiers, lifecycle values, status transitions, priority, assignment, and request fields server-side.
2. **Identity proxy to app:** forwarded identity headers are trustworthy only when the deployment guarantees the proxy overwrites them and the app is unreachable except through that proxy. The current trusted-proxy mode is a seam, not a complete OIDC implementation.
3. **Application to SQLite:** database access is local-process scaffolding. File permissions, backups, concurrent multi-user behavior, and administrator access are deployment responsibilities.
4. **Application to provider API:** provider credentials and remote APIs are outside the local demo boundary. Use TLS, bounded timeouts, redirects disabled, least-privilege scopes, sanitised errors, dry-run by default, and explicit approval. A timeout after POST is an unknown outcome; reconcile before retrying.
5. **Repository to CI actions:** workflow files and dependencies are executable supply-chain inputs. Minimise permissions, review/pin actions, and keep secrets out of untrusted pull-request contexts.

## Threat scenarios and required controls

| Threat | Existing controls | Residual risk / next control |
|---|---|---|
| Forged or missing identity | Unknown auth mode and missing proxy identity fail closed; demo mode cannot authorise production provider writes | Replace proxy seam with reviewed OIDC, secure session handling, and deployment network restrictions before company use |
| Requester self-approves | Case approval requires a different actor; provider approval checks separate actor | Test role separation against real identity groups and enforce case-level authorisation at every service entry point |
| Approved payload is changed or replayed | Fingerprinted payload approval, persisted approval state, action ledger duplicate protection | Add expiry/revocation UX and provider-specific reconciliation; do not blindly retry ambiguous POSTs |
| Concurrent stale update | SQLite transaction and optimistic case version checks | SQLite is not a multi-instance shared database; move to a transactional server database if multi-user deployment is required |
| Secrets leak through case data or logs | Recursive key-based redaction and sanitised integration errors; exports allow-list event history | Key-name redaction cannot identify every secret embedded in arbitrary free text; avoid storing credentials and classify/minimise request fields |
| Audit history is altered | Local action ledger hash-chain verification; case events record actors and transitions | Local database administrators can rewrite files; use access controls and externally retained, append-only audit storage for production |
| Provider endpoint or network behavior is unsafe | HTTPS defaults, bounded timeouts, redirects disabled in shared client | Validate every adapter and tenant scope with isolated test tenants; add reconciliation for uncertain write outcomes |
| Malicious dependency or workflow change | Unit tests, Docker build, scheduled CodeQL, least-privilege workflow permissions | Review dependency updates and pin GitHub Actions to verified immutable commit SHAs where feasible |
| Unbounded or malformed input degrades service | Case ID, summary, lifecycle and list-limit validation | Add explicit request-size limits, rate limiting, retention and abuse monitoring before exposure beyond localhost |

## Security invariants to preserve

- Deny by default; identity and authorisation must be checked server-side, not inferred from UI visibility.
- Demo mode never grants production provider-write permission.
- An approval is valid only for its original case, requester, provider, operation, and exact canonical payload; requester and approver must differ.
- An ambiguous provider write is recorded as unknown and must not be automatically retried.
- Audit and export surfaces use allow-lists and must not emit raw event metadata or credentials.
- Production data, provider credentials, and live writes are out of scope for the public demo.

## Verification checklist before any company deployment

- [ ] Replace the trusted-proxy seam with reviewed OIDC/OAuth, MFA for privileged users, secure session settings, and deployment-level proxy isolation.
- [ ] Define case-level RBAC/ABAC for read, edit, approve, export, and provider actions; test both allowed and denied paths.
- [ ] Complete a privacy/data-retention review; minimise employee fields and define deletion, backup, and restore procedures.
- [ ] Use managed secrets, rotation, least-privilege provider scopes, and tenant-specific contract tests.
- [ ] Move to a supported transactional database for multi-user/multi-instance use; implement versioned migrations and concurrency tests.
- [ ] Implement durable provider-action reconciliation, idempotency where supported, approval expiry/revocation, and operational runbooks.
- [ ] Define structured redacted logs, monitoring/alerts, audit retention, incident response, and restore drills.
- [ ] Run dependency auditing, review CodeQL findings, pin workflow actions, and establish a vulnerability-reporting process.
- [ ] Conduct an independent security review and user acceptance test in an isolated environment.

## Reference frameworks

This lightweight model is informed by the [OWASP Application Security Verification Standard](https://asvs.owasp.org/), the [OWASP Secure by Design Framework](https://owasp.org/projects/secure-by-design-framework), the [NIST Secure Software Development Framework (SP 800-218)](https://csrc.nist.gov/pubs/sp/800/218/final), and [GitHub Actions secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use). These frameworks guide prioritisation; this document does not claim conformance or certification.
