# OnboardOps benchmark: reproducible timing, honest limits

**Manual-versus-automated time savings: not measured.** This repository does not invent a human baseline. The included script measures only the deterministic Python processing pipeline; it excludes the Streamlit form/import interaction, download actions, and technician review. These figures must not be presented as end-to-end time savings.

## Reproduce the automated processing measurement

From the project root, run:

```bash
python scripts/benchmark_automation.py
```

It runs validation, checklist generation, Markdown rendering, and CSV rendering 100 times for each of three synthetic cases, and reports median/min/max elapsed milliseconds using `time.perf_counter()`. It reports the environment's observed timings when run; timings can vary by machine and load.

## Measure the manual baseline before claiming savings

Use the same operator and each same request from `data/test_cases.json`. For each case:

1. Start the timer when the request is first read.
2. Manually prepare a checklist and hardware allocation record using a fixed template and the same scope as OnboardOps.
3. Stop when both documents are ready for review. Include correction/follow-up time.
4. Repeat with OnboardOps: import the same request, inspect validation, generate and download both artifacts, and review them for correctness.
5. Alternate which method is performed first where practical. Record omissions and corrections as well as elapsed time.

Do not include actual account creation or device setup; OnboardOps does not perform these actions. Prefer at least five paired runs; this project supplies three baseline cases, which can be expanded by copying and editing synthetic records.

## Results log

### Actual core-pipeline timing observed in this environment

- Run date: 2026-10-22
- Python: 3.13.5; Linux execution container; host hardware details not captured
- Method: `time.perf_counter()`, 100 repetitions per case; each iteration validates, generates the checklist, and renders Markdown and CSV in memory
- This was rerun after the role-rule and validation improvements. Timings are processing latency, not end-to-end technician time. They cannot be compared directly to a manual baseline.

| Case | Median (ms) | Min (ms) | Max (ms) |
|---|---:|---:|---:|
| VALID-WINDOWS-01 | 0.041 | 0.039 | 0.391 |
| VALID-MACOS-01 | 0.037 | 0.036 | 0.060 |
| INVALID-INCOMPLETE-01 | 0.023 | 0.022 | 0.043 |

### Manual-versus-automated end-to-end results

**Not measured. No time-saving figure can be calculated yet.** The UI dependency could not be installed in this network-restricted environment, and a genuine human manual baseline cannot be measured from the core-processing benchmark. Fill this table after running the app locally using the method above.

| Date / environment | Case | Manual time (s) | OnboardOps end-to-end time incl. review (s) | Manual omissions | OnboardOps omissions | Notes |
|---|---|---:|---:|---|---|---|
| Not yet measured | VALID-WINDOWS-01 | | | | | |
| Not yet measured | VALID-MACOS-01 | | | | | |
| Not yet measured | INVALID-INCOMPLETE-01 | | | | | |

## Calculations after collecting real paired data

- Difference (seconds) = manual time − OnboardOps time.
- Percentage difference = difference / manual time × 100, only if manual time is greater than zero.
- Report median paired difference and range; retain negative results if automation takes longer.
- Explain the sample size, operator, machine, and limitations. Do not generalise a small synthetic exercise to a real organisation.

## Validation catch demonstration

Import `data/examples/invalid_request.json`. Expected findings include an invalid ISO date, unsupported OS, missing laptop asset tag and serial number, and no listed applications/access requests. Record these as caught validation findings, not as quantified time savings. Import a request using an identifier already present in `data/sample_requests.json` to demonstrate duplicate detection.
