# Presentation screenshot checklist

Use this checklist to prepare a small, truthful screenshot set for the current Streamlit pages. Capture only the local demo with synthetic records. This is a capture plan, not evidence that screenshots have already been taken or that accessibility has passed.

## Capture set

### 1. Onboarding — request and validation
- [ ] Open the main OnboardOps page.
- [ ] Click **Load sample request**.
- [ ] Capture the request form with synthetic/demo identifiers and the validation findings.
- [ ] Generate the checklist and capture the tailored task list plus Markdown / hardware CSV download controls.
- [ ] If showing an export, open it only after checking that it contains demo data and no local secrets.
- [ ] Avoid capturing the file upload widget with a real request file selected.

**Proves:** the local request → validation → checklist/export path renders in the current environment.  
**Does not prove:** that any account, device, or provider system was changed.

### 2. Case management — list and lifecycle
- [ ] Open **Case management**.
- [ ] In the “Portfolio demo helpers” expander, click **Load synthetic sample cases**.
- [ ] Capture the table with status/workflow/priority/assignment filters and synthetic case IDs visible.
- [ ] Select one sample case and capture triage fields and available status/approval controls.
- [ ] Capture the event history for the same case if it is visible on the page.
- [ ] If showing an approval control, explain the separate-actor rule; do not imply the demo identity can approve its own request.

**Proves:** the page displays local synthetic cases and offers rendered controls for the current identity.  
**Does not prove:** database row-level authorization or a production identity system.

### 3. Operations Report — charts and queues
- [ ] Open **Operations Report** after loading the synthetic sample cases.
- [ ] Capture the KPI row and status/lifecycle charts.
- [ ] Capture the approval queue or stale/aging case table if the synthetic data populates it.
- [ ] If a queue is empty, keep the truthful empty-state screenshot rather than editing the database to manufacture a claim.
- [ ] Make clear that age and idle thresholds are triage heuristics, not SLA measurements.

**Proves:** local report rendering for the current dataset.  
**Does not prove:** business outcomes, SLA compliance, or production reporting accuracy.

### 4. Integration Lab — safe preview
- [ ] Open **Integration Lab**.
- [ ] Capture **Connection readiness** with secret values absent; do not show environment settings from a terminal.
- [ ] Capture the offline write-payload preview if needed for the talk track.
- [ ] Keep live provider buttons disabled in demo mode.
- [ ] Do not add real credentials merely to make a status indicator green.

**Proves:** the readiness UI and safe preview path render.  
**Does not prove:** live API connectivity, token scopes, or tenant compatibility.

### 5. Engineering evidence
- [ ] Capture terminal output for python scripts/preflight.py.
- [ ] Capture a concise success summary from python scripts/integration_demo.py.
- [ ] Capture the latest passing GitHub Actions run only if its commit SHA matches the commit being presented.
- [ ] If no run is available, capture the workflow file or security verification matrix and label it “configured workflow,” not “passing CI.”
- [ ] Never include tokens, secret values, user home paths, or non-demo database records in screenshots.

## Capture quality
- [ ] Use consistent browser size and zoom across pages.
- [ ] Close unrelated tabs, notifications, and terminal history.
- [ ] Crop only to improve framing; do not remove warnings, error messages, or disabled states that change the meaning.
- [ ] Add a short caption with the page name and what the screenshot establishes.
- [ ] Store screenshots outside source-controlled paths unless the repository owner intentionally approves adding them.
- [ ] Run the manual accessibility review separately; screenshots do not establish keyboard or screen-reader usability. See PRESENTATION_ACCESSIBILITY_CHECKLIST.md.
