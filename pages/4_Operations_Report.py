"""Local, read-only operations reporting for synthetic/local case records."""
from __future__ import annotations

import csv
import os
import sys
from io import StringIO
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from onboardops.auth import AuthorizationError, require_permission, resolve_actor
from onboardops.cases import CaseStore
from onboardops.csv_safety import safe_csv_row
from onboardops.reporting import build_operations_report

st.set_page_config(page_title="OnboardOps · Operations Report", page_icon="📊", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1280px; padding-top: 1.6rem; padding-bottom: 3rem;}
.ops-eyebrow {color: #91a8c5; text-transform: uppercase; letter-spacing: .12em; font-size: .74rem; font-weight: 700;}
.ops-title {font-size: 2rem; font-weight: 750; letter-spacing: -.04em; margin: .15rem 0 .25rem;}
.ops-subtitle {color: #a9bad0; margin-bottom: 1rem;}
[data-testid="stMetric"] {background: #111c2e; border: 1px solid #263852; border-radius: 12px; padding: .85rem;}
</style>
<div class="ops-eyebrow">WORKSPACE · REPORTING</div>
<div class="ops-title">Operations report</div>
<div class="ops-subtitle">A read-only snapshot of workload, approval waiting time, stale work, prioritisation, and aging cases.</div>
""", unsafe_allow_html=True)
st.caption("Local records only · No provider calls · Counts are not SLA measurements")

headers = {}
try:
    headers = dict(st.context.headers)
except Exception:
    pass
try:
    actor = resolve_actor(headers)
    require_permission(actor, "cases:read")
except AuthorizationError as exc:
    st.error(f"Access denied: {exc}")
    st.stop()

db_path = os.environ.get("ONBOARDOPS_CASE_DB", str(ROOT / "data" / "onboardops_cases.sqlite3"))
store = CaseStore(db_path)
try:
    cases = store.list_cases(limit=500)
    report = build_operations_report(cases)
except Exception:
    st.error("Report could not be generated. Sensitive details were withheld.")
    st.stop()

metrics = st.columns(5)
metrics[0].metric("Total cases", report["total"])
metrics[1].metric("Active workload", report["active"])
metrics[2].metric("Closed", report["closed"])
metrics[3].metric("Urgent / high active", report["high_priority_active"])
metrics[4].metric("Unassigned active", report["unassigned_active"])

left, right = st.columns(2)
with left:
    st.subheader("Cases by status")
    st.bar_chart({"Cases": report["status_counts"]}, horizontal=True)
with right:
    st.subheader("Cases by lifecycle")
    st.bar_chart({"Cases": report["lifecycle_counts"]}, horizontal=True)

left, right = st.columns(2)
with left:
    st.subheader("Priority distribution")
    st.bar_chart({"Cases": {k.title(): v for k, v in report["priority_counts"].items()}}, horizontal=True)
with right:
    st.subheader("Workload signals")
    st.write(f"**{report['high_priority_active']}** active cases have high or urgent priority.")
    st.write(f"**{report['unassigned_active']}** active cases have no assignee.")
    st.write(f"**{len(report['aging_cases'])}** active cases are at least seven days old.")
    st.caption("Age is measured from case creation in UTC. This is a triage aid, not an SLA or breach calculation.")

st.subheader("Approval queue · oldest first")
if report["approval_queue"]:
    st.dataframe([{
        "Case ID": c["case_id"], "Waiting (hours)": c["age_hours"],
        "Lifecycle": c["lifecycle"], "Priority": c["priority"].title(),
        "Assignee": c["assigned_to"] or "Unassigned", "Created (UTC)": c["created_at"],
    } for c in report["approval_queue"]], use_container_width=True, hide_index=True)
    approval_export = StringIO()
    approval_writer = csv.DictWriter(approval_export, fieldnames=[
        "case_id", "waiting_hours", "lifecycle", "priority", "assigned_to", "created_at"
    ])
    approval_writer.writeheader()
    approval_writer.writerows(safe_csv_row({
        "case_id": c["case_id"], "waiting_hours": c["age_hours"],
        "lifecycle": c["lifecycle"], "priority": c["priority"],
        "assigned_to": c["assigned_to"], "created_at": c["created_at"],
    }) for c in report["approval_queue"])
    st.download_button(
        "Export approval queue (.csv)", approval_export.getvalue(),
        file_name="onboardops_approval_queue.csv", mime="text/csv",
    )
else:
    st.success("No cases are waiting for approval.")

st.caption("Waiting time is measured from case creation in UTC. It is a prioritisation signal, not an SLA target.")

st.subheader("Stale active cases · no update for 3+ days")
if report["stale_cases"]:
    st.dataframe([{
        "Case ID": c["case_id"], "Idle (days)": c["idle_days"], "Status": c["status"],
        "Lifecycle": c["lifecycle"], "Priority": c["priority"].title(),
        "Assignee": c["assigned_to"] or "Unassigned", "Updated (UTC)": c["updated_at"],
    } for c in report["stale_cases"]], use_container_width=True, hide_index=True)
    stale_export = StringIO()
    stale_writer = csv.DictWriter(stale_export, fieldnames=[
        "case_id", "idle_days", "status", "lifecycle", "priority", "assigned_to", "updated_at"
    ])
    stale_writer.writeheader()
    stale_writer.writerows(safe_csv_row({
        "case_id": c["case_id"], "idle_days": c["idle_days"], "status": c["status"],
        "lifecycle": c["lifecycle"], "priority": c["priority"],
        "assigned_to": c["assigned_to"], "updated_at": c["updated_at"],
    }) for c in report["stale_cases"])
    st.download_button(
        "Export stale cases (.csv)", stale_export.getvalue(),
        file_name="onboardops_stale_cases.csv", mime="text/csv",
    )
else:
    st.success("No active cases have been idle for three or more days.")

st.caption("Staleness is measured from the last update in UTC. The three-day threshold is a configurable product heuristic, not an SLA.")

st.subheader("Aging active cases · 7+ days")
if report["aging_cases"]:
    st.dataframe([{
        "Case ID": c["case_id"], "Age (days)": c["age_days"], "Status": c["status"],
        "Lifecycle": c["lifecycle"], "Priority": c["priority"].title(), "Assignee": c["assigned_to"] or "Unassigned",
        "Created (UTC)": c["created_at"],
    } for c in report["aging_cases"]], use_container_width=True, hide_index=True)
else:
    st.success("No active cases are at least seven days old.")

export = StringIO()
writer = csv.DictWriter(export, fieldnames=[
    "case_id", "status", "lifecycle", "priority", "assigned_to", "age_days", "created_at"
])
writer.writeheader()
writer.writerows(safe_csv_row({
    "case_id": c["case_id"], "status": c["status"], "lifecycle": c["lifecycle"],
    "priority": c["priority"], "assigned_to": c["assigned_to"],
    "age_days": c["age_days"], "created_at": c["created_at"],
}) for c in report["aging_cases"])
st.download_button("Export aging cases (.csv)", export.getvalue(), file_name="onboardops_aging_cases.csv", mime="text/csv")
st.caption(f"Identity: {actor.subject} · Read-only report · Showing up to 500 most recently updated cases")
store.close()
