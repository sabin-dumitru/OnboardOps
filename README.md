# OnboardOps

**A small local-first IT onboarding checklist and equipment-record helper, built with Python and Streamlit.** This is a personal portfolio project using synthetic demonstration data. It is not a production IT management system.

## What it does

- Collects a fictional new-joiner request with a date, team, location, OS, equipment, requested apps/access, and optional inventory identifiers.
- Imports exactly one synthetic request from a JSON object or one-row CSV file, then runs the same validation, checklist generation, and export pipeline. CSV list fields (`accessories`, `applications`, `access_requests`) use semicolon separators.
- Validates required fields, ISO dates, supported operating systems, duplicate demo IDs, and common follow-up gaps.
- Generates a deterministic checklist from editable JSON templates, including Windows/macOS-specific prompts and requested application/access verification tasks.
- Exports a Markdown checklist and CSV equipment allocation record.
- Uses no APIs, credentials, database, or external services. It does not create accounts, grant permissions, enroll endpoints, assign licences, or write to ticketing/inventory systems.

## Requirements

- Python 3.10 or newer
- `pip`

## Install and launch

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Streamlit prints a local URL (normally `http://localhost:8501`). Open it in your browser. No internet connection is needed after dependencies are installed.

## Quick demo

1. Run `streamlit run app.py`. Use the sidebar to import `data/examples/windows_request.csv` or `data/examples/macos_request.json`, then click **Import and process request**.
2. Review the generated tasks and validation indicators. Windows requests receive Windows update/management/BitLocker prompts; macOS requests receive macOS update/MDM/FileVault prompts. Each requested application and access item adds its own technician verification task. Equipment selections add allocation tasks and inventory CSV rows.
3. Download the `.md` checklist and `.csv` inventory record.
4. Import `data/examples/invalid_request.json` to see the invalid date, unsupported OS, and missing inventory/application/access follow-ups. Try identifier `DEMO-1042` to test duplicate detection against the shipped sample record.
5. Edit `config/templates.json` to adapt checklist prompts to a fictional or generic environment. Do not put company secrets or real employee data in this repository.

For a console walkthrough of request → validation → checklist → exports, run `python scripts/demo.py`. To measure the deterministic processing pipeline, run `python scripts/benchmark_automation.py`.

## Automation logic

1. `parse_request_file()` accepts one JSON object (or a list containing exactly one object) or a CSV with exactly one data row. Malformed files, unsupported file types, and multi-row CSV files are rejected with actionable errors.
2. `validate_request()` checks identifier format/duplicates, ISO date, supported OS, required identity fields, ticket/location/team follow-ups, equipment identifiers, and whether software/access requests need confirmation. Blocking errors are distinct from warnings.
3. `generate_checklist()` combines standard tasks, the chosen OS task set, requested equipment, and one explicit verification task for each requested application and access item. It does not infer permissions from job title.
4. Configurable role rules add review prompts for Design/Creative, Content/Editorial, and Support/Customer Operations teams. These rules never assign software or infer permissions. `render_markdown()` and `render_inventory_csv()` create downloadable artifacts. Asset rows remain pending until a technician verifies allocation in the authoritative inventory. CSV text is guarded against common spreadsheet-formula injection prefixes.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py onboardops tests scripts
```

The test suite includes three named synthetic cases in `data/test_cases.json`: valid Windows, valid macOS, and invalid/incomplete. Additional tests cover CSV/JSON import, malformed files, invalid UTF-8, multiple CSV rows, extra CSV values and duplicate headers, invalid booleans, duplicate IDs and applications, unique task IDs, multiple software requests, role-specific review prompts, CSV formula-injection mitigation, no-overwrite file writing, validation findings, OS-specific tasks, and exports. The current suite has **19 tests; all 19 passed** using `python -m unittest discover -s tests -v`. `python -m compileall -q app.py onboardops tests scripts` also passed. Streamlit could not be installed in this network-restricted environment, so browser-level behaviour remains unverified.

## Project structure

```text
app.py                      Streamlit interface
onboardops/core.py           Validation, checklist generation, Markdown/CSV exports
config/templates.json        Editable standard, OS-specific, and equipment templates
data/sample_requests.json    Synthetic example request
data/test_cases.json          Windows, macOS, and invalid test cases
data/examples/                Importable synthetic JSON/CSV requests
tests/test_core.py            Unit tests
scripts/demo.py               Console workflow demonstration
scripts/benchmark_automation.py Core processing timing benchmark
requirements.txt             Minimal runtime dependency
DEMO_GUIDE.md                Recruiter-facing walkthrough
BENCHMARK.md                 Blank timing worksheet and measurement protocol
outputs/                     Reserved for local generated files (not committed)
```

## Architecture and design decisions

The business logic lives in `onboardops/core.py` and uses only the Python standard library. `app.py` handles the UI. Checklist templates and role review prompts are external JSON so routine wording and categories can be changed without editing Python. The Streamlit app generates exports in memory and offers browser downloads; it does not persist submitted requests. The console demo writes files under `outputs/` using exclusive creation and numeric suffixes, so existing artifacts are not overwritten. Validation findings are divided into blocking errors and follow-up warnings. An error does not suppress the draft checklist, but the UI clearly marks it as not ready for use.

## Limitations and safe use

- All sample people, identifiers, ticket references, serials, and asset tags are synthetic.
- Application names and access requests are prompts for technician verification only. Job titles never infer privileges, and the tool does not determine approval.
- Device enrolment, encryption, endpoint protection, MFA, licence allocation, and identity steps must be checked against the actual organisation's approved procedures.
- Duplicate employee-ID detection checks the shipped synthetic sample records only; it is not a substitute for querying an authoritative inventory or ticketing platform. Duplicate application/access entries within a request are flagged for cleanup.
- CSV exports prefix untrusted values that start with common spreadsheet formula characters. This is a mitigation for common spreadsheet applications, not a general-purpose data sanitisation guarantee.
- The checklist checkboxes in the UI are session-only visual controls and are not saved to a system of record. The downloaded Markdown is the portable handover artifact.
- No manual-versus-automated time saving has been established. `scripts/benchmark_automation.py` measures only core Python processing latency; it excludes browser interaction and human review. Follow `BENCHMARK.md` to collect comparable end-to-end timings before making efficiency claims.

## License

For portfolio/demo use. Add a license of your choice before accepting contributions or redistributing if needed.
