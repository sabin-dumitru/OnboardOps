"""Pure validation and generation logic; no external systems are contacted."""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE_PATH = ROOT / "config" / "templates.json"


def load_templates(path: str | Path = DEFAULT_TEMPLATE_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)



def parse_request_file(filename: str, content: bytes | str) -> dict[str, Any]:
    """Parse exactly one request from a JSON object or one-row CSV file.

    CSV list fields (accessories, applications, access_requests) use semicolons.
    This parser only reads the supplied content; it never contacts external systems.
    """
    try:
        text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    except UnicodeDecodeError as exc:
        raise ValueError("Request file must be UTF-8 encoded.") from exc
    suffix = Path(filename).suffix.casefold()
    if suffix == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}).") from exc
        if isinstance(payload, list):
            if len(payload) != 1:
                raise ValueError("JSON must contain one request object, or a list containing exactly one request.")
            payload = payload[0]
        if not isinstance(payload, dict):
            raise ValueError("JSON must contain a request object.")
        request = dict(payload)
    elif suffix == ".csv":
        try:
            reader = csv.DictReader(io.StringIO(text, newline=""))
            if not reader.fieldnames:
                raise ValueError("CSV must include a header row.")
            headers = [str(name).strip() for name in reader.fieldnames if name is not None]
            if len(headers) != len(set(headers)):
                raise ValueError("CSV contains duplicate column names; make each header unique.")
            reader.fieldnames = headers
            rows = list(reader)
            if any(None in row for row in rows):
                raise ValueError("CSV contains more values than header columns; check the row separators.")
        except csv.Error as exc:
            raise ValueError(f"Invalid CSV: {exc}") from exc
        if len(rows) != 1:
            raise ValueError(f"CSV must contain exactly one request row; found {len(rows)}.")
        request = dict(rows[0])
        for field in ("accessories", "applications", "access_requests"):
            value = request.get(field, "")
            request[field] = [part.strip() for part in value.split(";") if part.strip()] if value else []
        raw_laptop = str(request.get("laptop_required", "true")).strip().casefold()
        if raw_laptop in {"true", "1", "yes", "y"}:
            request["laptop_required"] = True
        elif raw_laptop in {"false", "0", "no", "n"}:
            request["laptop_required"] = False
        else:
            request["laptop_required"] = False
            request["laptop_required_raw"] = raw_laptop
    else:
        raise ValueError("Unsupported file type. Upload a .json or .csv request.")

    for field in ("accessories", "applications", "access_requests"):
        value = request.get(field, [])
        if isinstance(value, str):
            request[field] = [part.strip() for part in value.split(";") if part.strip()]
        elif value is None:
            request[field] = []
        elif not isinstance(value, list):
            raise ValueError(f"'{field}' must be a list in JSON or a semicolon-separated CSV field.")
        else:
            request[field] = [str(part).strip() for part in value if part is not None]
    if isinstance(request.get("laptop_required"), str):
        value = request["laptop_required"].strip().casefold()
        if value in {"true", "1", "yes", "y"}:
            request["laptop_required"] = True
        elif value in {"false", "0", "no", "n"}:
            request["laptop_required"] = False
        else:
            request["laptop_required"] = False
            request["laptop_required_raw"] = value
    return request


def validate_request(
    request: dict[str, Any],
    existing_ids: set[str] | None = None,
    existing_asset_tags: set[str] | None = None,
    existing_serial_numbers: set[str] | None = None,
) -> list[dict[str, str]]:
    """Return actionable validation findings with severity, field and message.

    Existing identifiers and asset references are optional synthetic inventory
    context. The function never queries an external inventory system.
    """
    existing_ids = {x.strip().casefold() for x in (existing_ids or set())}
    existing_asset_tags = {x.strip().casefold() for x in (existing_asset_tags or set())}
    existing_serial_numbers = {x.strip().casefold() for x in (existing_serial_numbers or set())}
    findings: list[dict[str, str]] = []

    def add(severity: str, field: str, message: str) -> None:
        findings.append({"severity": severity, "field": field, "message": message})

    employee_id = str(request.get("employee_id", "")).strip()
    if not employee_id:
        add("error", "Employee ID", "Employee/demo identifier is required.")
    elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,39}", employee_id):
        add("error", "Employee ID", "Use 2–40 letters, numbers, dots, underscores, or hyphens; start with a letter or number.")
    elif employee_id.casefold() in existing_ids:
        add("error", "Employee ID", f"Identifier '{employee_id}' already exists in the loaded sample records.")

    if not str(request.get("employee_name", "")).strip():
        add("error", "Employee name", "Enter a name or a synthetic demo label.")
    raw_date = str(request.get("start_date", "")).strip()
    try:
        parsed_date = date.fromisoformat(raw_date)
        if parsed_date < date.today():
            add("warning", "Start date", "Start date is in the past; confirm this is intentional.")
    except (ValueError, TypeError):
        add("error", "Start date", "Enter a valid date in YYYY-MM-DD format.")

    for field, label in [("team", "Team or role"), ("location", "Work location"), ("ticket_reference", "Ticket reference")]:
        if not str(request.get(field, "")).strip():
            add("warning", label, f"{label} is blank; complete it before setup starts.")

    os_name = str(request.get("operating_system", "")).strip()
    if os_name not in {"Windows", "macOS"}:
        add("error", "Operating system", "Choose a supported operating system: Windows or macOS.")

    if "laptop_required_raw" in request:
        add("error", "Laptop required", "Use true/false (or yes/no) for laptop_required in the imported request.")
    if not request.get("laptop_required"):
        add("warning", "Laptop", "No laptop requested; confirm whether this is a BYOD or non-standard onboarding.")
    if request.get("laptop_required") and not str(request.get("asset_tag", "")).strip():
        add("warning", "Asset tag", "Laptop requested but no asset tag is assigned yet.")
    asset_tag_value = str(request.get("asset_tag", "")).strip()
    serial_value = str(request.get("serial_number", "")).strip()
    if request.get("laptop_required") and not serial_value:
        add("warning", "Serial number", "Record the laptop serial number when equipment is allocated.")
    if not request.get("laptop_required") and (asset_tag_value or serial_value):
        add("warning", "Laptop equipment", "Asset tag or serial number is present although no laptop is requested; confirm the equipment selection.")
    if asset_tag_value and asset_tag_value.casefold() in existing_asset_tags:
        add("error", "Asset tag", "This asset tag is already assigned in the loaded synthetic inventory records.")
    if serial_value and serial_value.casefold() in existing_serial_numbers:
        add("error", "Serial number", "This serial number is already assigned in the loaded synthetic inventory records.")

    accessories = request.get("accessories", []) or []
    if not isinstance(accessories, list):
        add("error", "Accessories", "Accessories must be a list of supported equipment names.")
        accessories = []
    supported_accessories = {"monitor", "keyboard", "mouse", "headset", "dock"}
    unknown_accessories = sorted({str(item).strip() for item in accessories if str(item).strip() and str(item).strip() not in supported_accessories})
    if unknown_accessories:
        add("error", "Accessories", "Unsupported accessory value(s): " + ", ".join(unknown_accessories) + ". Use monitor, keyboard, mouse, headset, or dock.")
    normalised_accessories = [str(item).strip().casefold() for item in accessories if str(item).strip()]
    if len(normalised_accessories) != len(set(normalised_accessories)):
        add("warning", "Accessories", "Duplicate accessory entries were supplied; review the equipment request.")

    applications = request.get("applications", []) or []
    accesses = request.get("access_requests", []) or []
    if not isinstance(applications, list):
        add("error", "Applications", "Applications must be a list of names.")
        applications = []
    if not isinstance(accesses, list):
        add("error", "Access requests", "Access requests must be a list of explicit requests.")
        accesses = []
    if not applications:
        add("warning", "Applications", "No applications listed; confirm the standard application profile with the request owner.")
    if not accesses:
        add("warning", "Access requests", "No access requests listed; verify whether standard access is sufficient.")
    for value in applications + accesses:
        if not str(value).strip():
            add("warning", "Requested items", "A blank application or access item was supplied; remove it or provide a name.")
            break
    for field, values, label, field_label in (("applications", applications, "application", "Applications"), ("access_requests", accesses, "access request", "Access requests")):
        normalised = [str(value).strip().casefold() for value in values if str(value).strip()]
        if len(normalised) != len(set(normalised)):
            add("warning", field_label, f"Duplicate {label} entries were supplied; review the request for duplicates.")

    asset_tag = str(request.get("asset_tag", "")).strip()
    if asset_tag and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,39}", asset_tag):
        add("warning", "Asset tag", "Asset tag has an unusual format; verify it against the inventory system.")
    return findings


def generate_checklist(request: dict[str, Any], templates: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    templates = templates or load_templates()
    tasks: list[dict[str, Any]] = []
    tasks.extend(dict(task) for task in templates["standard_tasks"])
    os_name = request.get("operating_system")
    if os_name in templates["os_tasks"]:
        tasks.extend(dict(task) for task in templates["os_tasks"][os_name])
    if request.get("laptop_required"):
        tasks.append({"id": "laptop-allocation", "title": "Prepare and allocate the requested laptop", "category": "Hardware allocation", "required": True})
    for accessory in request.get("accessories", []) or []:
        item = templates.get("equipment_tasks", {}).get(accessory)
        if item:
            tasks.append(dict(item))
    for app in request.get("applications", []) or []:
        if str(app).strip():
            tasks.append({"id": f"app-{slug(app)}", "title": f"Verify requested application: {str(app).strip()} (approval/licence and installation)", "category": "Applications and licences", "required": True})
    for access in request.get("access_requests", []) or []:
        if str(access).strip():
            tasks.append({"id": f"access-{slug(access)}", "title": f"Verify approved access request: {str(access).strip()}", "category": "Identity and access", "required": True})
    # Role rules add review prompts only; they never infer software or permissions.
    team = str(request.get("team", "")).casefold()
    for rule in templates.get("role_rules", []):
        keywords = [str(word).casefold() for word in rule.get("keywords", [])]
        if keywords and any(word in team for word in keywords):
            tasks.extend(dict(task) for task in rule.get("tasks", []))
    # Keep IDs unique even when an item is selected more than once.
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for task in tasks:
        if task["id"] not in seen:
            unique.append(task)
            seen.add(task["id"])
    return unique


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")
    return cleaned[:48] or "item"


def render_markdown(request: dict[str, Any], tasks: list[dict[str, Any]], findings: list[dict[str, str]]) -> str:
    lines = [
        f"# OnboardOps checklist — {request.get('employee_name', 'Unnamed demo request')}", "",
        "> Portfolio demo only. Verify all actions against approved requests and your organisation's procedures. This file does not create accounts or change systems.", "",
        "## Request summary", "",
        f"- **Employee/demo ID:** {request.get('employee_id', 'Not provided')}",
        f"- **Start date:** {request.get('start_date', 'Not provided')}",
        f"- **Team/role:** {request.get('team') or 'Not provided'}",
        f"- **Location:** {request.get('location') or 'Not provided'}",
        f"- **Operating system:** {request.get('operating_system') or 'Not provided'}",
        f"- **Ticket reference:** {request.get('ticket_reference') or 'Not provided'}",
        f"- **Asset tag:** {request.get('asset_tag') or 'Pending'}",
        f"- **Serial number:** {request.get('serial_number') or 'Pending'}", "",
        "## Pre-flight validation", ""
    ]
    if findings:
        for finding in findings:
            lines.append(f"- **{finding['severity'].upper()} — {finding['field']}:** {finding['message']}")
    else:
        lines.append("- No validation findings.")
    lines.extend(["", "## Technician checklist", ""])
    category = None
    for task in tasks:
        if task["category"] != category:
            category = task["category"]
            lines.extend([f"### {category}", ""])
        lines.append(f"- [ ] {task['title']}")
    lines.extend(["", "## Notes / outstanding actions", "", "- Owner and due date: ", "- Blockers / approvals: ", "- Handover confirmation: ", ""])
    return "\n".join(lines)


def render_inventory_csv(request: dict[str, Any]) -> str:
    """Create one row per requested hardware item, with an explicit pending state."""
    output = io.StringIO(newline="")
    fields = ["employee_id", "employee_name", "start_date", "location", "item_type", "item_name", "asset_tag", "serial_number", "allocation_status", "ticket_reference"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    items: list[tuple[str, str]] = []
    if request.get("laptop_required"):
        items.append(("laptop", "Laptop"))
    labels = {"monitor": "Monitor", "keyboard": "Keyboard", "mouse": "Mouse", "headset": "Headset", "dock": "Dock / adapter"}
    items.extend((key, labels[key]) for key in (request.get("accessories", []) or []) if key in labels)
    for item_type, item_name in items:
        is_laptop = item_type == "laptop"
        writer.writerow({
            "employee_id": _spreadsheet_safe(request.get("employee_id", "")),
            "employee_name": _spreadsheet_safe(request.get("employee_name", "")),
            "start_date": _spreadsheet_safe(request.get("start_date", "")),
            "location": _spreadsheet_safe(request.get("location", "")),
            "item_type": item_type, "item_name": item_name,
            "asset_tag": _spreadsheet_safe(request.get("asset_tag", "")) if is_laptop else "",
            "serial_number": _spreadsheet_safe(request.get("serial_number", "")) if is_laptop else "",
            "allocation_status": "Needs allocation / verification",
            "ticket_reference": _spreadsheet_safe(request.get("ticket_reference", ""))
        })
    return output.getvalue()


def _spreadsheet_safe(value: Any) -> str:
    """Prefix untrusted CSV text that spreadsheet apps may treat as a formula."""
    text = str(value or "")
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def write_text_no_overwrite(path: str | Path, content: str) -> Path:
    """Write a UTF-8 artifact without replacing an existing file.

    If the target exists, append a numeric suffix (for example, report_2.md).
    Exclusive creation also avoids clobbering a file created between checks.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    stem, suffix = target.stem, target.suffix
    index = 1
    while True:
        candidate = target if index == 1 else target.with_name(f"{stem}_{index}{suffix}")
        try:
            with candidate.open("x", encoding="utf-8", newline="") as handle:
                handle.write(content)
            return candidate
        except FileExistsError:
            index += 1
