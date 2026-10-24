# Security and engineering verification matrix

**Status:** internal portfolio evidence map; not a formal security assessment, audit opinion, certification, or claim of compliance with OWASP ASVS or NIST SSDF.

This matrix uses selected concepts from the [OWASP Application Security Verification Standard (ASVS) 5.0](https://asvs.org/) and [NIST Secure Software Development Framework (SSDF), SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final). It records what is implemented, what automated evidence exists, and what still requires deployment-specific or human verification.

## Application controls

| Control area | Current implementation | Automated evidence | Status / residual gap |
|---|---|---|---|
| Authentication | Local demo identity; optional trusted-proxy identity headers with explicit trust flag and role mapping | Auth tests for missing identity, unknown mode, role matrix, and integration-read permission | **Partial.** No bundled OIDC/SSO, secure session lifecycle, account revocation, or independent proxy deployment review. |
| Authorization | Server-side role checks for case actions and live Integration Lab reads; case list applies requester/approver visibility scope before rendering history and exports | Case auth tests, role matrix tests, integration-auth tests, case-visibility tests | **Partial.** Case visibility filtering is currently a UI-layer control, not a service/database row-level authorization boundary. No bundled OIDC/SSO; live provider writes remain disabled in the UI. |
| Input validation | Case IDs, lifecycle/status, summary length, request-data object shape and 64 KiB size; strict JSON rejects NaN/Infinity | Case, workflow, and export regression tests | **Implemented for defined local boundaries.** No global rate limiting or enterprise API schema validation. |
| URL and HTTP boundary | HTTPS by default, no redirects, bounded connect/read timeouts, canonicalized path checks, streaming response cap, sanitized provider errors | Integration and mocked provider workflow tests | **Implemented for shared client behavior.** Provider-specific compatibility, DNS/network egress policy, and tenant permissions remain unverified. |
| Spreadsheet export | Shared formula-injection escaping for user-controlled text in case/report CSV exports | CSV safety tests | **Implemented for current CSV export paths.** Review any new export path before release. |
| Secret minimization | Recursive key-based redaction at persistence, audit metadata, and export boundaries | Sanitization, case, and export tests | **Partial.** Key-based redaction cannot identify every secret embedded in free text; credentials must never be stored in request fields. |
| Approval safety | Separate actor, exact payload fingerprint, persisted 15-minute approval expiry, one-time consumption and revocation; ambiguous POST outcomes are not blindly retried | Workflow, provider workflow, and case approval tests | **Partial.** The durable approval ledger is local SQLite; provider-specific reconciliation and real tenant validation remain outstanding. |
| Audit integrity | Local hash-chained action audit with verification; case events record state transitions and approval events | Workflow and case history tests | **Tamper detection only.** A local database administrator can rewrite the database and recompute the chain; no external append-only retention or SIEM integration. |
| Persistence and concurrency | SQLite transactions, foreign keys, optimistic case-version checks, schema migration tests | Case store and migration tests | **Local/single-instance scope.** No supported multi-instance deployment or managed database migration layer. |
| Backup and recovery | SQLite online backup, integrity check, overwrite protection, Compose-aware runbook | Backup utility tests and documented manual restore procedure | **Partial.** A full disaster-recovery exercise, tested recovery objectives, and backup of separately configured action ledgers are not claimed. |
| Container runtime | Non-root user, read-only root filesystem, dropped capabilities, no-new-privileges, localhost-only host binding, writable named volumes | Docker Compose CI smoke test, health endpoint, preflight, synthetic case persistence across restart | **Implemented for the supported local Compose demo.** Not a production hosting baseline without environment-specific review. |
| Supply chain | SHA-pinned GitHub Actions, Python test matrix, CodeQL, Dependabot configuration | GitHub Actions runs | **Partial.** No release provenance/SBOM attestation, signed release process, or dependency lockfile. |
| Accessibility | Shared visible-focus, forced-colors, and reduced-motion styles; semantic H1 page titles on the primary pages | Accessibility tests check style rules and page-title markup; Streamlit AppTest smoke tests cover uncaught rendering exceptions | **Partial.** The [manual accessibility review checklist](PRESENTATION_ACCESSIBILITY_CHECKLIST.md) defines the next verification step; no browser-based keyboard, screen-reader, zoom, focus-order, or measured contrast audit has been performed. |

## Selected ASVS concepts

This is a practical mapping of selected themes, not a line-by-line ASVS verification.

| ASVS theme | Evidence in this repository | Remaining work |
|---|---|---|
| Architecture and threat modeling | Architecture notes and threat model | Independent review of production trust boundaries and deployment architecture |
| Authentication and access control | Auth module, role-matrix and integration-auth tests | OIDC/SSO, session security, case-level authorization, proxy deployment review |
| Validation and business logic | Lifecycle transitions, version checks, strict JSON, approval expiry/revocation | Abuse/rate-limit controls and full service-layer authorization review |
| Error handling and logging | Sanitized integration errors, local audit chain, metadata redaction, structured authorization-denial events with pseudonymous actor/resource references | Logs currently use the local Python logging destination; central protected logging, alerting, retention and incident ownership remain deployment work |
| Data protection | Secret redaction, minimal exports, CSV formula neutralization | Data classification, retention/deletion policy, encryption and access controls appropriate to deployment |
| Communication and configuration | HTTPS-only provider URLs by default, redirects disabled, Compose localhost binding | Production TLS termination, egress restrictions, secrets manager and deployment review |

## NIST SSDF lifecycle view

| SSDF group | Current evidence | Gap |
|---|---|---|
| Prepare the Organization (PO) | Threat model, architecture notes, readiness plan, operator runbook | Named owners, formal risk acceptance, service objectives, and company-specific requirements |
| Protect the Software (PS) | SHA-pinned actions, least-privilege workflow permissions, non-root container, secret redaction | Protected release process, provenance/SBOM, managed secrets and repository governance |
| Produce Well-Secured Software (PW) | Unit/contract tests, Python matrix, CodeQL, Compose smoke test, input/export guards | Independent review, browser accessibility tests, live provider test tenants |
| Respond to Vulnerabilities (RV) | Dependabot proposals, CodeQL workflow, runbook for suspected credential exposure | Defined disclosure channel, severity/response SLAs, incident owner and external log retention |

## Release evidence checklist

Before presenting the repository, verify the latest main-branch CI run has completed successfully. For a live demo, follow the Docker demo guide with synthetic data only. Before any company deployment, additionally require:

- [ ] Reviewed OIDC/SSO integration and trusted identity propagation.
- [ ] Record-level authorization tests and a production data-retention policy.
- [ ] Managed database architecture and tested backup/restore recovery objectives.
- [ ] Provider-specific isolated-tenant tests and reconciliation for uncertain writes.
- [ ] Production secrets management, monitoring, audit retention, and incident ownership.
- [ ] Browser-based accessibility and smoke tests on the target environment.
- [ ] Independent security and operational review.

**Interpretation rule:** a passing CI run proves only the tested code paths on that commit. It does not prove live tenant compatibility, production identity, formal standards conformance, or operational readiness.
