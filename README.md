# OnboardOps

**A local-first Python and Streamlit tool that turns an onboarding request into a validated technician checklist and hardware allocation report.**

OnboardOps is a personal portfolio project developed with AI assistance. It uses synthetic demonstration data only. It is not a production IT management system and has not been deployed or used by a real IT department.

## The problem

IT onboarding repeats a familiar set of administrative steps: confirm the request, prepare a device, verify approved software and access, record equipment, test the setup, and document handover. Repeating these steps manually can make omissions harder to spot.

OnboardOps standardises the *planning and documentation* part of that work. It does not perform the actual device setup or provision accounts.

## What it does

- Accepts one onboarding request from a JSON object, a single-row CSV, or the manual-entry form.
- Validates required fields, date and operating-system formats, duplicate demo identifiers, duplicate asset/serial references against bundled synthetic records, accessory values, and common inconsistencies.
- Generates a deterministic checklist tailored to Windows or macOS, selected equipment, requested applications, explicit access requests, and configurable role-review prompts.
- Produces a Markdown checklist and CSV equipment allocation report. Equipment remains marked as needing allocation/verification.
- Reports blocking errors separately from follow-up warnings. A draft can be inspected when errors exist, but the UI marks it as not ready for use.
- Keeps generated exports in memory in the web UI. The console demo writes local files without overwriting existing artifacts.
- Runs without external APIs, paid services, AI calls, production credentials, or integrations.

## Example scenarios

| Example | Expected result |
|---|---|
| `data/examples/windows_request.csv` | Windows updates, management and BitLocker prompts; selected accessories; per-application and access verification tasks |
| `data/examples/macos_request.json` | macOS updates, MDM and FileVault prompts; different equipment and software tasks |
| `data/examples/invalid_request.json` | Blocking findings for an invalid date and unsupported OS, plus warnings for missing asset details and absent software/access requests |

CSV list fields (`accessories`, `applications`, `access_requests`) are separated with semicolons. JSON list fields use arrays.

## Quick start

Requirements: Python 3.10+ and pip.

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell (use this instead of the command above)
.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL Streamlit prints, normally `http://localhost:8501`.

### First demo

1. Select **Load sample request** or import `data/examples/windows_request.csv` from the sidebar.
2. Review the validation status and the generated checklist.
3. Open the **Hardware allocation** tab and download the CSV.
4. Import `data/examples/macos_request.json` and compare the OS-specific tasks.
5. Import `data/examples/invalid_request.json` to see actionable validation findings.
6. Download the Markdown checklist and inspect its pre-flight findings and handover prompts.

For a terminal walkthrough that prints the incoming request, findings, checklist excerpt, and local export paths:

```bash
python scripts/demo.py
```

The console demo uses exclusive file creation; repeated runs create a numbered filename instead of overwriting an existing output.

## Tests and continuous integration

Run the complete unit suite:

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py onboardops tests scripts
python scripts/demo.py
```

The suite covers valid Windows and macOS requests, invalid/incomplete requests, duplicate identifiers and asset references, malformed JSON/CSV, invalid UTF-8, unsupported extensions, duplicate CSV headers, extra CSV values, boolean parsing, multiple software requests, role-specific review tasks, duplicate/unsupported accessories, formula-injection mitigation, export content, and no-overwrite file writing.

GitHub Actions runs the tests, compilation check, and console demonstration on pushes and pull requests. A green workflow confirms these automated checks pass; it does not replace manually launching and checking the Streamlit browser UI.

## How the automation works

```text
CSV / JSON / manual form
          |
          v
   Parse and normalise
          |
          v
  Validate request and
  known synthetic records
          |
          v
  Config-driven checklist
  (OS + equipment + apps +
   access + role review)
          |
          v
  Markdown checklist + CSV
  asset allocation report
```

- `app.py` owns the Streamlit presentation and form state.
- `onboardops/core.py` contains parsing, validation, deterministic generation, rendering, and safe local file writing.
- `config/templates.json` contains standard tasks, Windows/macOS tasks, equipment prompts, defaults, and role-review rules.
- `data/examples/` contains importable synthetic requests.
- `tests/test_core.py` tests the business logic without needing Streamlit to run.
- `scripts/demo.py` demonstrates the workflow; `scripts/benchmark_automation.py` measures core processing latency.

### Rules and safety choices

- OS rules add relevant prompts: Windows includes Windows update/management/BitLocker checks; macOS includes macOS update/MDM/FileVault checks. These are prompts to follow the organisation's approved process, not assumptions about every environment.
- Each requested application gets a licence/installation verification task; each requested access item gets an explicit approval-verification task. Job title never grants or implies access.
- Role rules add review prompts only. They do not auto-select software or infer permissions.
- Known asset tags and serial numbers are compared only against the bundled synthetic sample inventory. This is a demo safeguard, not a live inventory check.
- CSV export escapes values beginning with common spreadsheet formula characters.
- The app does not save submitted requests to a database or send them externally.

## Benchmark and measured value

The benchmark script uses `time.perf_counter()` for 100 repetitions per synthetic case. It measures validation, checklist generation, and in-memory Markdown/CSV rendering only.

```bash
python scripts/benchmark_automation.py
```

These timings represent core Python processing latency, not end-to-end technician time. **Manual-versus-automated checklist preparation time has not been measured**, so this project makes no quantified time-saving or productivity claim. Use `BENCHMARK.md` for the paired manual-versus-automated measurement procedure, including what to time and how to record omissions and corrections. Actual device provisioning and account setup are out of scope.

## Screenshots

Capture a genuine screenshot after launching the app locally and exercising the sample request. Recommended image: the validation summary and generated checklist, with synthetic identifiers visible. Save it as `docs/screenshots/onboardops-demo.png`, then embed it here using:

```markdown
![OnboardOps running locally](docs/screenshots/onboardops-demo.png)
```

A screenshot is not included in this source package because the current build environment did not have Streamlit installed and could not reach the package index. Do not substitute a mockup for a screenshot of the running application.

## Limitations and future improvements

Current limitations:
- No real identity, ticketing, endpoint-management, licensing, or inventory integration.
- No account creation, access changes, device enrolment, or licence assignment.
- Asset collision checks use only bundled synthetic records.
- No persistent audit history; requests in the web UI remain in session state.
- Browser-level UI behaviour must be checked after installing dependencies locally.
- No manual-versus-automated time-saving result is claimed.

Potential future improvements, only if useful:
1. Add a small, optional CSV/JSON batch preview while preserving one-request-per-run validation.
2. Add a local, privacy-conscious history of generated plan metadata without retaining employee names or request contents.
3. Add a manually verified screenshot and a measured paired benchmark.
4. Add more tests or UI automation only if a new feature justifies them.

## Security and privacy

Use synthetic identities and fictional asset references in demos. Do not import employer data or production credentials. Keep `.env`, Streamlit secrets, virtual environments, caches, and local outputs out of version control. Review `git status` before committing. OnboardOps is a planning aid, not a security control or a substitute for approved IT processes.

## License

No license is currently specified. Add one before inviting reuse if you want to grant explicit permissions to others.
