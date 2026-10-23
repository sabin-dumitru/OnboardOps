# OnboardOps — recruiter demo (4–5 minutes)

## Story to tell

"I built a local Python/Streamlit prototype to standardise repetitive IT onboarding preparation. It validates a synthetic request and generates a technician checklist plus a hardware allocation report. It does not provision accounts, grant access, or enrol devices."

## Walkthrough

1. **Start the app.** Run `python -m streamlit run app.py` and open the local address printed in the terminal.
2. **Use the sample preset.** Select **Load sample request** in the sidebar. The sample uses a reserved synthetic employee ID and leaves laptop assignment details blank, so the app should show follow-up warnings rather than duplicate-record errors.
3. **Explain the validation.** Show the task, error and follow-up counts. Errors block readiness; warnings are reminders to verify missing information. An unassigned asset is not invented just to make validation look clean.
4. **Review the checklist.** Explain the Windows/macOS prompts, application/licence checks and access-verification steps. These are technician prompts, not automatic provisioning.
5. **Show both exports.** Download the Markdown checklist and CSV hardware report. Explain that the CSV is a handover/record format and does not update a live inventory system.
6. **Compare sample files.** Import `data/examples/macos_request.json` and `data/examples/invalid_request.json` from the sidebar to show OS-specific tasks and blocking validation errors.
7. **Open Integration Lab.** Use the Streamlit page navigation to open **Integration Lab**. With no credentials configured, show provider readiness statuses and offline write previews. Do not add real credentials for the portfolio demo and do not claim the provider connections have been verified against live tenants.
8. **Explain engineering safeguards.** Show the dry-run defaults, payload-bound approval checks, bounded HTTP timeouts, redirect rejection, safe error handling and local audit-chain tests. Clarify that these are prototype safeguards, not a complete multi-user authorisation system.
9. **Show the automated checks.** Run the commands below or open the GitHub Actions workflow. The workflow tests Python 3.10–3.13, compiles the source and exercises both console demos.
10. **Discuss measurement honestly.** `python scripts/benchmark_automation.py` measures core processing latency only. End-to-end manual-vs-automated time savings have not been measured; do not claim quantified savings until the paired experiment in `BENCHMARK.md` has been run.

## Windows PowerShell commands

Run these from the repository folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For the automated checks and offline demonstrations:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py onboardops tests scripts
python scripts/demo.py
python scripts/integration_demo.py
```

## Claims to avoid

- Do not say that OnboardOps provisions accounts or devices.
- Do not say the provider adapters have been tested against real company tenants.
- Do not claim a measured time-saving percentage.
- Do not describe the local SQLite ledger as a tamper-proof enterprise audit system or the approval object as production-grade access control.

All sample data is synthetic. The project was developed with AI assistance. It is a personal portfolio prototype, not a production IT system.
