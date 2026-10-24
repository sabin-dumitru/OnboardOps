# OnboardOps UI quality and accessibility checklist

This is an implementation checklist for the dark navy operations-console interface. The goal is to make common tasks obvious and safe, not merely to make the dashboard look polished.

## Visual system

- Use the shared Streamlit dark theme from `.streamlit/config.toml`; avoid per-page colours that conflict with it.
- Use navy/slate surfaces, light foreground text, and blue for primary interactive emphasis.
- Use status text in addition to colour. A status such as `pending_approval` must remain understandable without distinguishing colours.
- Keep spacing, page width, card borders, heading levels, and button labels consistent between the dashboard, case management, and integration lab.
- Prefer meaningful content hierarchy over decorative icons or excessive metrics.

## Keyboard and screen-reader usability

- Every input has a persistent visible label; do not rely on placeholders as labels.
- Use Streamlit's native buttons, forms, select boxes, tabs, and dataframes for keyboard support.
- Shared CSS adds a high-visibility `:focus-visible` outline, a forced-colors fallback, and reduced-motion overrides on the main page, case management, operations report, and Integration Lab. These are implementation aids, not proof of WCAG conformance.
- Keep the logical order of controls aligned with the visual order.
- Use descriptive action names such as “Save status change” instead of vague labels such as “Go” or “OK”.
- Ensure errors and success feedback are written as text and are not conveyed only through colour.
- Avoid emoji as the only label for a navigation item or action.
- Test keyboard-only navigation, visible focus, browser zoom, and screen-reader announcements manually before calling the interface accessible.

## Case-management interaction design

- Lead with a small number of meaningful operational metrics.
- Provide a status filter and a case-ID/summary search, with a clear “no results” state.
- Keep the case list compact; show details, approvals, and history after a case is selected.
- Make the current status and permitted next actions explicit.
- Require a separate authorised identity for approval. Do not present a button as though it will succeed when role checks will deny the action.
- Preserve optimistic concurrency/version checks so stale pages cannot silently overwrite newer case state.
- Keep a timestamped history for state transitions and approvals.

## Integration safety

- Show configuration readiness without printing secret values.
- Label mock/offline results differently from real provider responses.
- Distinguish “configured” from “connection verified”; environment variables being present do not prove credentials or permissions work.
- Never expose provider write actions in the demo UI until trusted authentication, server-side authorization, approval binding, and live test coverage are in place.
- For timeout/unknown write outcomes, instruct the operator to reconcile remote state before retrying.

## Verification before release

- [ ] Existing Python test matrix passes.
- [ ] Docker image build passes in CI.
- [ ] Case list filters handle zero results without errors.
- [ ] Case approval, transition, and history behaviour remain intact.
- [ ] Keyboard-only interaction and visible focus reviewed in a running browser.
- [ ] Text contrast and browser zoom reviewed manually.
- [ ] GitHub live integration is tested only in a disposable repository with a least-privilege token.
- [ ] Documentation explicitly distinguishes automated mocks from live verification.
