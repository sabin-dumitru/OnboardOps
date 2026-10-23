# Safe GitHub integration verification

This checklist complements the offline tests. It does **not** enable live provider writes in the Streamlit UI.

## Current boundary

- `tests/test_provider_workflow.py` uses a mocked HTTP session. It verifies the approval and audit workflow without contacting GitHub.
- The local demo identity cannot authorise provider writes.
- The UI intentionally does not expose live write actions.
- A successful unit test or Docker build is not evidence of live GitHub permissions or API compatibility.

## Before a live test

1. Create a dedicated, disposable GitHub test repository. Do not use a work or production repository.
2. Use a dedicated GitHub account or approved test identity where possible.
3. Create a fine-grained token scoped only to the test repository, with the minimum repository permission needed to create issues (typically **Issues: Read and write**). Avoid broad classic tokens.
4. Keep the token outside Git, container images, screenshots, terminal transcripts, and issue bodies. Supply it only through a local environment variable or approved secret manager.
5. Run the test from an isolated development environment with a trusted identity and server-side role checks. The default `ONBOARDOPS_AUTH_MODE=demo` identity is not authorised for provider writes.
6. Agree on a harmless synthetic issue title/body, for example `[OnboardOps test] CASE-TEST-001`. Do not include personal or confidential data.

## Verification sequence

- [ ] Confirm the repository owner/name and token scope before making a request.
- [ ] Confirm a requester and a different authorised approver are represented by trusted identities.
- [ ] Approve the exact repository, title, and body payload.
- [ ] Execute only the approved action once.
- [ ] Confirm the issue appears in the test repository and the returned issue number matches the local action ledger.
- [ ] Confirm the approval is marked consumed and the audit chain verifies.
- [ ] Attempt to reuse the same approval; verify the workflow rejects it without a second HTTP request.
- [ ] Change one field after approval; verify the payload fingerprint check rejects the action before network I/O.
- [ ] Revoke the test token and delete the synthetic issue/repository when finished, following the test environment's retention policy.

## Ambiguous network outcomes

A timeout after sending a write can mean GitHub accepted the request but the response was lost. Do not blindly retry. Reconcile the test repository and audit ledger first; create a new approval only after the previous outcome is understood.

## Completion record

Record the date, test repository, token permission scope (never the token), test cases, issue URL, and pass/fail outcome. State explicitly which checks were mocked and which reached GitHub. Never report the integration as live-verified until this checklist has been run in an isolated environment.
