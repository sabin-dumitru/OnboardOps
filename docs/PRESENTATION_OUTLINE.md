# OnboardOps presentation outline (9 slides)

**Audience:** technical recruiter, IT operations lead, or software engineering interviewer  
**Target length:** 8–10 minutes for the slides; use the separate 5–7 minute live runbook for the product walkthrough.  
**Evidence rule:** label each statement as implemented, covered by automated tests, or not yet verified live. Use synthetic records only.

## Slide 1 — The operational problem (45 sec)
- Onboarding work spans a request, checklist, hardware allocation, case status, approval history, and follow-up.
- The prototype makes those steps visible in one local workflow.
- **Visual:** Onboarding page with the synthetic sample request loaded.
- **Say:** “This is workflow preparation and tracking, not automated employee provisioning.”

## Slide 2 — Scope and boundaries (45 sec)
- Local-first Streamlit application; synthetic sample data; SQLite case persistence.
- Provider adapters are separate from the checklist engine.
- Live provider writes are not exposed in the UI.
- **Visual:** simple diagram: Request → Validate → Checklist/CSV; Case management → Operations report; Integration Lab → read-only diagnostics/offline previews.
- **Avoid:** describing the prototype as production-ready or multi-tenant.

## Slide 3 — Request to technician handoff (60 sec)
- Load the sample request; inspect required fields and validation findings.
- Generate a tailored technician checklist and export Markdown / hardware allocation CSV.
- Explain duplicate inventory and unsupported operating-system validation at a high level.
- **Visual:** validation results plus the generated checklist/download controls.

## Slide 4 — Case lifecycle and history (75 sec)
- Load synthetic sample cases; filter by status, workflow, priority, and assignment.
- Open a sample case and show its status/event history.
- Show triage fields and explain optimistic version checks prevent stale updates from silently overwriting newer state.
- **Visual:** Case management table and selected case/history. Do not show real employee information.

## Slide 5 — Approvals and access boundaries (60 sec)
- Approval is a distinct action; requester and approver must be different actors.
- Role checks are performed at action sites; a disabled button alone is not a security boundary.
- The default identity is demo-only. Trusted-proxy mode is an integration seam, not bundled OIDC/SSO.
- **Visual:** synthetic pending-approval case with role-appropriate controls, or the README/security matrix if the current demo identity cannot approve.
- **Caveat:** case visibility is not database row-level security.

## Slide 6 — Operations reporting (60 sec)
- Explain status/lifecycle/priority distributions, unassigned/high-priority work, oldest approvals, stale cases, and aging cases.
- CSV exports are scoped to cases visible to the actor and escape spreadsheet formula prefixes.
- These metrics are triage signals, not an SLA engine.
- **Visual:** Operations Report chart plus one queue/table.

## Slide 7 — Integration safety (75 sec)
- Show configuration readiness without exposing values, then an offline provider-shaped payload preview.
- Explain dry-run defaults, separate-actor payload-bound approvals, expiry, and one-time consumption.
- A timed-out POST is an unknown outcome; reconcile before retrying.
- **Visual:** Integration Lab readiness with secret values hidden and live actions disabled in demo mode; optionally show offline demo terminal output.
- **Caveat:** adapter tests mock HTTP; no live tenant compatibility is claimed.

## Slide 8 — Engineering evidence (60 sec)
- Python test matrix, Streamlit AppTest page smoke checks, Compose health/persistence smoke test, CodeQL, and dependency audit.
- SQLite lifecycle includes schema-version checks and connection cleanup; backup utility checks integrity.
- **Visual:** current successful GitHub Actions run for the exact commit, if one exists; otherwise show workflow definitions and explicitly say the run has not been verified.
- **Evidence rule:** a CI result proves only the tested commit and code paths.

## Slide 9 — Limitations and next steps (45 sec)
- Add reviewed OIDC/SSO and service-layer case authorization before team use.
- Use managed transactional storage, durable reconciliation, protected logs/retention, and tested restore objectives before production use.
- Perform target-browser accessibility checks and opt-in live contract tests against isolated provider tenants.
- **Close:** “The design emphasis is controlled workflows and honest failure states, with clear separation between local evidence and live-system proof.”

## Presenter notes
- Prefer one concrete workflow over listing every adapter.
- Keep browser zoom at a readable level; avoid tiny terminal text.
- Do not expose environment variables, tokens, real names, database contents from a non-demo environment, or private repository metadata.
- If a live screen is not reproducible, switch to a prepared screenshot or the source-based evidence matrix and disclose the substitution.
