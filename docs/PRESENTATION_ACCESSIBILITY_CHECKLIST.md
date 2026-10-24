# Presentation accessibility review checklist

**Purpose:** a repeatable manual review for the local Streamlit presentation. This checklist is not evidence of conformance until a person runs it in the target browser and records results. Automated AppTest checks catch render exceptions; they do not test actual browser accessibility.

Reference: [W3C Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/). This is a practical smoke checklist, not a full WCAG audit.

## Record the test session

- Date/time:
- Reviewer:
- Browser and version:
- Operating system:
- Display size and scaling:
- App commit:
- Overall result: Not run / Pass with notes / Blocked

## Before testing

- [ ] Start the supported local Compose demo and confirm the health endpoint at http://127.0.0.1:8501/_stcore/health responds successfully.
- [ ] Run the read-only preflight command inside the app container and resolve every FAIL.
- [ ] Load only synthetic sample cases.
- [ ] Record the commit being tested. Do not test with real employee data or provider credentials.

## Keyboard-only navigation

Use the keyboard without a mouse on **Onboarding**, **Integration Lab**, **Case management**, and **Operations Report**.

- [ ] Tab and Shift+Tab move through controls in a logical order.
- [ ] Every interactive control can be reached and operated with the keyboard.
- [ ] Focus is clearly visible on buttons, links, tabs, inputs, selects, and download controls.
- [ ] Focus is not hidden behind sticky or overlay content.
- [ ] No keyboard trap occurs; Escape or standard navigation exits menus/dialogs where applicable.
- [ ] After form submission, validation messages and success/error feedback are discoverable.
- [ ] Disabled live integration actions are visibly disabled and explained; no workaround is attempted.

Record page, action, expected behavior, actual behavior, and a screenshot or short screen recording for each failure.

## Structure, labels, and reading order

- [ ] Each page has a descriptive browser title and one clear primary heading.
- [ ] Heading hierarchy describes the page and sections in a meaningful order.
- [ ] Inputs have visible, descriptive labels; placeholders are not the only labels.
- [ ] Buttons and download actions have names that explain their purpose.
- [ ] Tables can be understood from their headers and reading order.
- [ ] Error messages identify the problem and next step without exposing secrets or raw provider responses.
- [ ] Status, priority, and permission differences are not conveyed by color alone.

## Zoom, contrast, and display preferences

- [ ] At 200% browser zoom, text and controls remain usable without losing information or actions.
- [ ] At a narrow viewport, important controls and tables remain reachable; horizontal scrolling is understandable where unavoidable.
- [ ] Normal text contrast is at least 4.5:1 and large text contrast at least 3:1, measured rather than guessed.
- [ ] Focus indicators are distinguishable from adjacent colors.
- [ ] Forced-colors/high-contrast mode preserves focus and control boundaries.
- [ ] Reduced-motion preference suppresses non-essential animation.
- [ ] Text remains readable when browser/system font scaling is increased.

## Screen-reader spot check

Using an available screen reader (for example, NVDA with Firefox/Chrome on Windows or VoiceOver with Safari on macOS):

- [ ] Page title and primary heading are announced meaningfully.
- [ ] Form labels and required/disabled states are announced.
- [ ] Tab navigation and form submission feedback are announced in a useful order.
- [ ] Case tables and event history expose meaningful row/column context.
- [ ] Charts have a nearby textual summary that conveys the same important information.
- [ ] The user can tell when a control is unavailable because of role or demo-mode restrictions.

## Workflow-specific checks

- [ ] Case management: no-case, no-filter-match, requester-scoped, and approver-scoped states are understandable.
- [ ] Case management: validation failures for invalid JSON, duplicate IDs, stale updates, and forbidden actions are actionable.
- [ ] Operations Report: empty approval/stale/aging queues have clear explanations.
- [ ] Integration Lab: missing configuration, denied live reads, and failed provider calls explain the next safe step.
- [ ] Presentation script: each step can be completed with synthetic data without live provider access.

## Findings and sign-off

For each issue, record severity, page, reproduction steps, expected result, actual result, and an owner. Fix blocking keyboard or information-access failures before presenting. Re-run affected checks after changes.

| Check | Result (Pass / Fail / Not run) | Evidence or notes |
|---|---|---|
| Keyboard-only | Not run | |
| Focus visibility | Not run | |
| Labels and headings | Not run | |
| 200% zoom / narrow viewport | Not run | |
| Contrast measurements | Not run | |
| Forced colors / reduced motion | Not run | |
| Screen-reader spot check | Not run | |
| Workflow empty/error states | Not run | |

**Do not mark the application WCAG-conformant based on this checklist alone.** A complete assessment requires broader success-criteria coverage, representative assistive technology testing, and documented results on the target deployment.
