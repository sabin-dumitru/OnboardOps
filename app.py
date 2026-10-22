from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from onboardops.core import generate_checklist, load_templates, parse_request_file, render_inventory_csv, render_markdown, validate_request

st.set_page_config(page_title="OnboardOps · IT onboarding", page_icon="🧭", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem;}
.hero {padding: 1.4rem 1.6rem; border: 1px solid #dce3eb; border-radius: 16px; background: linear-gradient(120deg, #f7faff, #ffffff); margin-bottom: 1rem;}
.hero h1 {margin: 0; color: #172b4d; letter-spacing: -0.04em;}
.hero p {color: #52627a; margin: .4rem 0 0;}
.small-note {font-size: .88rem; color: #637083;}
[data-testid="stMetric"] {background: #f7f9fc; padding: .8rem; border-radius: 12px; border: 1px solid #e3e8ef;}
</style>
<div class="hero"><h1>🧭 OnboardOps</h1><p>Turn a new-joiner request into a consistent technician checklist and equipment allocation record.</p></div>
""", unsafe_allow_html=True)
st.caption("Local-first portfolio demo · Synthetic data only · No accounts, permissions, or devices are changed")
st.info("Workflow: import or enter one request → validate it → review the tailored checklist → export Markdown and asset CSV. All generated actions are technician prompts, not provisioning.")

try:
    templates = load_templates(ROOT / "config" / "templates.json")
    sample_records = json.loads((ROOT / "data" / "sample_requests.json").read_text(encoding="utf-8"))
    known_asset_tags = {str(r.get("asset_tag", "")).strip().casefold() for r in sample_records if r.get("asset_tag")}
    known_serial_numbers = {str(r.get("serial_number", "")).strip().casefold() for r in sample_records if r.get("serial_number")}
except (OSError, json.JSONDecodeError, KeyError) as exc:
    st.error(f"Configuration could not be loaded: {exc}")
    st.stop()

def populate_form_state(request: dict) -> None:
    """Synchronise form widgets when a sample/import is loaded."""
    st.session_state["employee_id"] = str(request.get("employee_id", ""))
    st.session_state["employee_name"] = str(request.get("employee_name", ""))
    st.session_state["start_date"] = str(request.get("start_date", ""))
    st.session_state["team"] = str(request.get("team", ""))
    st.session_state["location"] = str(request.get("location", "Amsterdam"))
    os_value = request.get("operating_system", "Windows")
    st.session_state["operating_system"] = os_value if os_value in {"Windows", "macOS"} else "Unsupported / not decided"
    st.session_state["ticket_reference"] = str(request.get("ticket_reference", ""))
    st.session_state["asset_tag"] = str(request.get("asset_tag", ""))
    st.session_state["serial_number"] = str(request.get("serial_number", ""))
    st.session_state["laptop_required"] = bool(request.get("laptop_required", True))
    st.session_state["accessories"] = [x for x in (request.get("accessories", []) or []) if x in {"monitor", "keyboard", "mouse", "headset", "dock"}]
    st.session_state["applications_text"] = "\n".join(str(x) for x in (request.get("applications", []) or []))
    st.session_state["access_text"] = "\n".join(str(x) for x in (request.get("access_requests", []) or []))

with st.sidebar:
    st.subheader("Quick start")
    st.write("Load the synthetic example to explore a complete request.")
    if st.button("Load sample request", use_container_width=True):
        st.session_state["request_data"] = dict(sample_records[0])
        populate_form_state(dict(sample_records[0]))
        st.session_state["findings"] = validate_request(dict(sample_records[0]))
        st.session_state["tasks"] = generate_checklist(dict(sample_records[0]), templates)
        st.session_state["generated"] = True
        st.rerun()
    st.markdown("**Or import one request**")
    uploaded_request = st.file_uploader("Synthetic request (.json or .csv)", type=["json", "csv"], help="JSON object or one-row CSV. List fields in CSV use semicolons.")
    if st.button("Import and process request", use_container_width=True, disabled=uploaded_request is None):
        try:
            imported = parse_request_file(uploaded_request.name, uploaded_request.getvalue())
            duplicate_ids = {str(r.get("employee_id", "")).casefold() for r in sample_records}
            findings = validate_request(imported, duplicate_ids, known_asset_tags, known_serial_numbers)
            st.session_state["request_data"] = imported
            populate_form_state(imported)
            st.session_state["findings"] = findings
            st.session_state["tasks"] = generate_checklist(imported, templates)
            st.session_state["generated"] = not any(f["severity"] == "error" for f in findings)
            st.session_state["import_message"] = f"Imported {uploaded_request.name} and processed one request."
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    if st.session_state.get("import_message"):
        st.success(st.session_state["import_message"])
    st.divider()
    st.markdown("**Workflow**")
    st.markdown("1. Enter request details\n2. Review validation findings\n3. Generate checklist\n4. Download Markdown and CSV")
    st.caption("Templates: `config/templates.json`")

initial = st.session_state.get("request_data", {})
defval = lambda key, default="": initial.get(key, default)
with st.form("onboarding_request", clear_on_submit=False):
    st.subheader("1 · New-joiner request")
    c1, c2, c3 = st.columns(3)
    with c1:
        employee_id = st.text_input("Employee / demo ID *", value=defval("employee_id"), placeholder="e.g. DEMO-1043", key="employee_id")
        employee_name = st.text_input("Employee name / demo label *", value=defval("employee_name"), placeholder="e.g. Jamie Example", key="employee_name")
        start_date = st.text_input("Start date (YYYY-MM-DD) *", value=defval("start_date"), placeholder="2026-11-16", help="Use ISO format so the request is unambiguous.", key="start_date")
    with c2:
        team = st.text_input("Team or role", value=defval("team"), placeholder="e.g. Content Operations", key="team")
        location = st.text_input("Work location", value=defval("location", "Amsterdam"), placeholder="e.g. Amsterdam", key="location")
        os_options = ["Windows", "macOS", "Unsupported / not decided"]
        os_value = defval("operating_system", "Windows")
        operating_system = st.selectbox("Operating system *", os_options, index=os_options.index(os_value) if os_value in os_options else 2, key="operating_system")
    with c3:
        ticket_reference = st.text_input("Service ticket reference", value=defval("ticket_reference"), placeholder="e.g. DEMO-TICKET-205", key="ticket_reference")
        asset_tag = st.text_input("Laptop asset tag (if assigned)", value=defval("asset_tag"), placeholder="e.g. CF-DEMO-0082", key="asset_tag")
        serial_number = st.text_input("Laptop serial (if assigned)", value=defval("serial_number"), placeholder="Synthetic serial only", key="serial_number")
    st.markdown("**Equipment**")
    e1, e2 = st.columns([1, 3])
    with e1:
        laptop_required = st.checkbox("Laptop required", value=bool(defval("laptop_required", True)), key="laptop_required")
    accessory_options = ["monitor", "keyboard", "mouse", "headset", "dock"]
    accessory_defaults = [x for x in defval("accessories", templates["defaults"]["accessories"]) if x in accessory_options]
    accessories = st.multiselect("Accessories", accessory_options, default=accessory_defaults, format_func=lambda x: {"monitor":"Monitor", "keyboard":"Keyboard", "mouse":"Mouse", "headset":"Headset", "dock":"Dock / adapter"}[x], key="accessories")
    st.markdown("**Requested software and access — verification only**")
    a1, a2 = st.columns(2)
    with a1:
        applications_text = st.text_area("Applications / licences (one per line)", value="\n".join(defval("applications", templates["defaults"]["applications"])), placeholder="Office suite\nDesign application", key="applications_text")
    with a2:
        access_text = st.text_area("Approved access requests / groups (one per line)", value="\n".join(defval("access_requests", [])), placeholder="Approved group or request reference", key="access_text")
    submitted = st.form_submit_button("Validate and generate checklist", type="primary", use_container_width=True)

if submitted:
    request = {
        "employee_id": employee_id.strip(), "employee_name": employee_name.strip(), "start_date": start_date.strip(),
        "team": team.strip(), "location": location.strip(),
        "operating_system": operating_system if operating_system != "Unsupported / not decided" else "",
        "laptop_required": laptop_required, "accessories": accessories,
        "applications": [x.strip() for x in applications_text.splitlines() if x.strip()],
        "access_requests": [x.strip() for x in access_text.splitlines() if x.strip()],
        "asset_tag": asset_tag.strip(), "serial_number": serial_number.strip(), "ticket_reference": ticket_reference.strip()
    }
    existing = {r.get("employee_id", "") for r in sample_records if r.get("employee_id", "").casefold() != request["employee_id"].casefold()}
    # Keep the shipped sample identifier reserved, including when it is being entered manually.
    if any(r.get("employee_id", "").casefold() == request["employee_id"].casefold() for r in sample_records):
        existing.add(request["employee_id"])
    findings = validate_request(request, existing, known_asset_tags, known_serial_numbers)
    st.session_state["request_data"] = request
    st.session_state["findings"] = findings
    st.session_state["generated"] = not any(f["severity"] == "error" for f in findings)
    st.session_state["tasks"] = generate_checklist(request, templates)

if st.session_state.get("request_data") and st.session_state.get("findings") is not None:
    request = st.session_state["request_data"]
    findings = st.session_state["findings"]
    tasks = st.session_state.get("tasks", [])
    st.divider()
    st.subheader("2 · Validation and generated output")
    errors = sum(f["severity"] == "error" for f in findings)
    warnings = sum(f["severity"] == "warning" for f in findings)
    m1, m2, m3 = st.columns(3)
    m1.metric("Checklist tasks", len(tasks))
    m2.metric("Errors", errors)
    m3.metric("Follow-up flags", warnings)
    if errors:
        st.error("Resolve the blocking errors below, then submit the request again. A draft checklist is shown for troubleshooting but is not ready to use.")
    elif warnings:
        st.warning("Checklist generated with follow-up items. Resolve these before setup starts where applicable.")
    else:
        st.success("Validation passed with no findings. Technician verification is still required.")
    if findings:
        for f in findings:
            if f["severity"] == "error": st.error(f"**{f['field']}** — {f['message']}")
            elif f["severity"] == "warning": st.warning(f"**{f['field']}** — {f['message']}")
            else: st.info(f"**{f['field']}** — {f['message']}")
    else:
        st.info("No validation findings.")
    md = render_markdown(request, tasks, findings)
    csv_text = render_inventory_csv(request)
    tab1, tab2, tab3 = st.tabs(["Technician checklist", "Hardware allocation", "Request summary"])
    with tab1:
        st.markdown(f"### {request.get('employee_name') or 'Unnamed request'} · {request.get('operating_system') or 'OS not selected'}")
        st.caption("Tick boxes in the downloaded Markdown file as work is completed; the app does not track completion state.")
        current_category = None
        for task in tasks:
            if task["category"] != current_category:
                current_category = task["category"]
                st.markdown(f"**{current_category}**")
            st.checkbox(task["title"], key=f"task_{task['id']}")
        st.download_button("Download checklist (.md)", data=md, file_name=f"onboardops_{request.get('employee_id') or 'request'}.md", mime="text/markdown", use_container_width=True)
    with tab2:
        st.markdown("Equipment is marked as needing allocation/verification until a technician confirms it in the authoritative inventory system.")
        st.code(csv_text, language="csv")
        st.download_button("Download inventory report (.csv)", data=csv_text, file_name=f"onboardops_inventory_{request.get('employee_id') or 'request'}.csv", mime="text/csv", use_container_width=True)
    with tab3:
        st.json(request, expanded=True)
else:
    st.info("No checklist generated yet. Enter a synthetic request above or select **Load sample request** in the sidebar.")
    st.markdown("**What this helps standardise**")
    st.markdown("- A repeatable checklist adapted to Windows/macOS and selected equipment\n- Early flags for missing details and duplicate demo identifiers\n- A downloadable, auditable handover prompt and inventory row set")

st.divider()
st.caption("OnboardOps is a personal portfolio project. It is not a production IT management system and does not connect to identity, endpoint, ticketing, or inventory platforms.")
