# OnboardOps — recruiter demo (3–4 minutes)

## Story to tell

"I wanted to standardise the repetitive planning and documentation steps in IT onboarding. This local Python/Streamlit tool validates a synthetic request and generates a checklist and equipment record. It does not provision accounts, assign access, or enrol devices."

## Walkthrough

1. **Start with a request.** Launch with `streamlit run app.py`; import `data/examples/windows_request.csv`.
2. **Explain the rules.** Show the Windows-specific update, management, and BitLocker prompts. Point out the application and access tasks are based on the request and require technician verification.
3. **Compare operating systems.** Import `data/examples/macos_request.json`; show macOS update, MDM, and FileVault prompts and the different selected applications/accessories.
4. **Demonstrate validation.** Import `data/examples/invalid_request.json`. Explain the malformed date and unsupported OS errors and the missing asset/software/access follow-ups. A draft is displayed for troubleshooting but is not ready to use while blocking errors remain.
5. **Show the exports.** Download the Markdown checklist and CSV allocation report. Equipment is marked pending verification; no production inventory is modified.
6. **Show engineering discipline.** Run the tests with `python -m unittest discover -s tests -v`. Mention GitHub Actions runs tests, compilation, and the console demo on pushes and pull requests.
7. **Discuss evaluation honestly.** `python scripts/benchmark_automation.py` measures core processing latency only. A manual-vs-automated end-to-end baseline has not been measured; don't claim quantified savings until you run the paired experiment in `BENCHMARK.md`.

## Commands

```bash
python -m pip install -r requirements.txt
streamlit run app.py
python -m unittest discover -s tests -v
python scripts/demo.py
python scripts/benchmark_automation.py
```

All sample data is synthetic. The project was developed with AI assistance and is a personal portfolio project, not a production IT system.
