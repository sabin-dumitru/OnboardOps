"""Console walkthrough of import -> validation -> checklist -> CSV export."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from onboardops.core import (
    generate_checklist,
    load_templates,
    parse_request_file,
    render_inventory_csv,
    render_markdown,
    validate_request,
    write_text_no_overwrite,
)




def main() -> None:
    request_path = ROOT / "data" / "examples" / "invalid_request.json"
    request = parse_request_file(request_path.name, request_path.read_bytes())
    templates = load_templates()
    sample_records = json.loads((ROOT / "data" / "sample_requests.json").read_text(encoding="utf-8"))
    existing_ids = {str(item.get("employee_id", "")) for item in sample_records}
    findings = validate_request(request, existing_ids)
    tasks = generate_checklist(request, templates)
    markdown = render_markdown(request, tasks, findings)
    inventory = render_inventory_csv(request)

    print("STEP 1 — Imported synthetic request")
    print(json.dumps(request, indent=2))
    print("\nSTEP 2 — Validation findings")
    for finding in findings:
        print(f"[{finding['severity'].upper()}] {finding['field']}: {finding['message']}")
    print(f"\nSTEP 3 — Generated {len(tasks)} checklist tasks")
    print("\n".join(f"- [ ] {task['title']}" for task in tasks[:8]))
    if len(tasks) > 8:
        print(f"... {len(tasks) - 8} more tasks")
    output_dir = ROOT / "outputs"
    output_dir.mkdir(exist_ok=True)
    employee_id = request.get("employee_id", "request")
    md_path = write_text_no_overwrite(output_dir / f"demo_{employee_id}.md", markdown)
    csv_path = write_text_no_overwrite(output_dir / f"demo_inventory_{employee_id}.csv", inventory)
    print("\nSTEP 4 — Exported artifacts")
    print(f"Markdown: {md_path.relative_to(ROOT)}")
    print(f"Inventory CSV: {csv_path.relative_to(ROOT)}")
    print("\nSafety: draft prompts only; no accounts, permissions, or devices were changed.")


if __name__ == "__main__":
    main()
