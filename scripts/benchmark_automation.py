"""Measure local deterministic processing time; this is not a manual baseline."""
from __future__ import annotations

import json
import statistics
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from onboardops.core import generate_checklist, load_templates, render_inventory_csv, render_markdown, validate_request


REPEATS = 100


def main() -> None:
    cases = json.loads((ROOT / "data" / "test_cases.json").read_text(encoding="utf-8"))
    templates = load_templates()
    print(f"Automated core-pipeline benchmark: {len(cases)} synthetic cases, {REPEATS} repeats per case")
    print("Measures validation + checklist generation + in-memory Markdown/CSV rendering; excludes browser interaction and human review.")
    for case in cases:
        request = {k: v for k, v in case.items() if k != "case_id"}
        samples_ms = []
        for _ in range(REPEATS):
            start = time.perf_counter()
            findings = validate_request(request)
            tasks = generate_checklist(request, templates)
            render_markdown(request, tasks, findings)
            render_inventory_csv(request)
            samples_ms.append((time.perf_counter() - start) * 1000)
        print(f"{case['case_id']}: median={statistics.median(samples_ms):.3f} ms; min={min(samples_ms):.3f} ms; max={max(samples_ms):.3f} ms")
    print("This is processing latency, not end-to-end technician time. No manual baseline is measured here; do not calculate or claim time savings from these figures.")


if __name__ == "__main__":
    main()
