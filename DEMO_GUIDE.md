# OnboardOps — 3-minute recruiter demonstration

## 1. Show the incoming request (30 seconds)

In the sidebar, import `data/examples/windows_request.csv` or `data/examples/macos_request.json`. The CSV uses semicolons inside the `accessories`, `applications`, and `access_requests` cells. Point out that the imported file contains one synthetic request and no credentials.

## 2. Show processing (60 seconds)

Click **Import and process request**. OnboardOps parses the request, checks required fields and date/OS formats, applies the selected OS template, adds equipment-specific tasks, adds one verification task per requested application and access item, and renders Markdown and CSV exports. Role rules add configurable review prompts only; they never assign software or infer permissions. Show Windows update/BitLocker tasks versus macOS update/FileVault tasks.

## 3. Demonstrate validation (45 seconds)

Import `data/examples/invalid_request.json`. The request should be flagged for the malformed date and unsupported OS, as well as missing asset/serial details and absent application/access requests. A draft checklist is shown for diagnosis, but blocking errors mark it not ready for use. Also try an ID that matches a shipped synthetic sample to demonstrate duplicate detection.

## 4. Show outputs and safety (30 seconds)

Open the Markdown checklist and CSV allocation export. Equipment remains marked as needing allocation/verification. Explain that the tool does not create accounts, grant access, enroll devices, assign licences, or write to an inventory/ticketing system.

## Optional console demonstration

```bash
python scripts/demo.py
python scripts/benchmark_automation.py
```

The demo script prints the incoming synthetic request, validation findings, a checklist excerpt, and the generated artifacts. It does not overwrite existing files: repeated runs use numeric suffixes. The benchmark script measures the local core processing pipeline only, not manual time or end-to-end technician time.
