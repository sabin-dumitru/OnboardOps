"""Persistent local case management with fail-closed role checks."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from onboardops.auth import AuthorizationError, require_permission, resolve_actor
from onboardops.cases import CaseStore, CaseStoreError
from onboardops.demo_fixtures import seed_sample_cases
from onboardops.workflow import TRANSITIONS, WorkflowError

st.set_page_config(page_title="OnboardOps · Cases",page_icon="🗂️",layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1280px; padding-top: 1.6rem; padding-bottom: 3rem;}
.ops-eyebrow {color: #91a8c5; text-transform: uppercase; letter-spacing: .12em; font-size: .74rem; font-weight: 700;}
.ops-title {font-size: 2rem; font-weight: 750; letter-spacing: -.04em; margin: .15rem 0 .25rem;}
.ops-subtitle {color: #a9bad0; margin-bottom: 1rem;}
[data-testid="stMetric"] {background: #111c2e; border: 1px solid #263852; border-radius: 12px; padding: .85rem;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-color: #263852;}
</style>
<div class="ops-eyebrow">WORKSPACE · CASES</div>
<div class="ops-title">Case management</div>
<div class="ops-subtitle">Track onboarding work, review approvals, and inspect a timestamped case history.</div>
""", unsafe_allow_html=True)
st.caption("Local synthetic records · Role-aware actions · Provider writes disabled")
headers={}
try:
    headers=dict(st.context.headers)
except Exception:
    pass
try:
    actor=resolve_actor(headers)
except AuthorizationError as exc:
    st.error(f"Access denied: {exc}")
    st.stop()

db_path=os.environ.get("ONBOARDOPS_CASE_DB",str(ROOT/"data"/"onboardops_cases.sqlite3"))
store=CaseStore(db_path)
st.info("Local demo stores synthetic cases in SQLite on this machine. Single-user demo only. Provider writes are disabled.")
st.caption(f"Identity: {actor.subject} · Mode: {actor.mode} · Roles: {', '.join(sorted(actor.roles))}")
def show_error(exc):
    if isinstance(exc,(AuthorizationError,CaseStoreError,WorkflowError,ValueError)):
        st.error(str(exc))
    else:
        st.error("Operation failed; sensitive details were withheld.")

# Demo fixtures are synthetic and isolated from provider integrations.
with st.expander("Portfolio demo helpers", expanded=False):
    st.caption("Optional sample records for demonstrations. These are synthetic fixtures, not employee records.")
    if st.button("Load synthetic sample cases", key="load_sample_cases"):
        try:
            require_permission(actor, "cases:create")
            created = seed_sample_cases(store)
            if created:
                st.success(f"Added {created} synthetic sample case(s). Existing sample cases were left unchanged.")
            else:
                st.info("The synthetic sample cases are already present; no records were changed.")
            st.rerun()
        except Exception as exc:
            show_error(exc)


try:
    require_permission(actor,"cases:read")
    cases=store.list_cases()
except Exception as exc:
    show_error(exc)
    cases=[]

# Overview metrics provide a quick scan without replacing the detailed case table.
metric_cols=st.columns(4)
metric_cols[0].metric("Total cases",len(cases))
metric_cols[1].metric("Awaiting approval",sum(c["status"]=="pending_approval" for c in cases))
metric_cols[2].metric("In progress",sum(c["status"] in {"approved","in_progress"} for c in cases))
metric_cols[3].metric("Completed",sum(c["status"]=="completed" for c in cases))

tab_list,tab_create=st.tabs(["Saved cases and history","Create synthetic case"])
with tab_list:
    st.subheader("Saved cases")
    if cases:
        filter_col, lifecycle_col, search_col = st.columns([1, 1, 2])
        with filter_col:
            status_options = ["All statuses"] + sorted({str(c["status"]) for c in cases})
            status_filter = st.selectbox("Filter by status", status_options)
        with lifecycle_col:
            lifecycle_options = ["All workflows"] + sorted({str(c["lifecycle"]) for c in cases})
            lifecycle_filter = st.selectbox("Filter by workflow", lifecycle_options)
        with search_col:
            search_term = st.text_input("Search cases", placeholder="Case ID or summary")
        visible_cases = [
            c for c in cases
            if (status_filter == "All statuses" or c["status"] == status_filter)
            and (lifecycle_filter == "All workflows" or c["lifecycle"] == lifecycle_filter)
            and search_term.casefold() in (str(c["case_id"]) + " " + str(c["summary"])).casefold()
        ]
        st.caption(f"Showing {len(visible_cases)} of {len(cases)} case(s).")
        if visible_cases:
            import csv
            from io import StringIO
            export_buffer = StringIO()
            writer = csv.DictWriter(export_buffer, fieldnames=["case_id", "lifecycle", "status", "summary", "updated_at", "version"])
            writer.writeheader()
            writer.writerows({
                "case_id": c["case_id"], "lifecycle": c["lifecycle"], "status": c["status"],
                "summary": c["summary"], "updated_at": c["updated_at"], "version": c["version"]
            } for c in visible_cases)
            st.download_button("Export filtered cases (.csv)", export_buffer.getvalue(),
                               file_name="onboardops_cases.csv", mime="text/csv")
        if visible_cases:
            st.dataframe([{"Case ID":c["case_id"],"Lifecycle":c["lifecycle"],"Status":c["status"],
                           "Summary":c["summary"],"Updated":c["updated_at"],"Version":c["version"]}
                          for c in visible_cases],use_container_width=True,hide_index=True)
            selected=st.selectbox("Open case",[c["case_id"] for c in visible_cases])
            case=store.get_case(selected)
        else:
            st.info("No cases match these filters. Clear the search or choose another status.")
            case=None
        if case is not None:
            left,right=st.columns(2)
            with left:
                st.write("**Synthetic request data**")
                st.json(case["request_data"],expanded=False)
            with right:
                targets=sorted(t for t in TRANSITIONS.get(case["status"],set()) if t != "approved")
                if case["status"] == "pending_approval":
                    st.caption("Approval must come from a different identity than the requester.")
                    if st.button("Approve case", key=f"approve_{selected}"):
                        try:
                            require_permission(actor, "approvals:review")
                            approved = store.approve_case(case_id=selected, approver_id=actor.subject,
                                                          expected_version=case["version"])
                            st.success(f"{approved['case_id']} approved.")
                            st.rerun()
                        except Exception as exc:
                            show_error(exc)
                if targets:
                    target=st.selectbox("Move to status",targets,key=f"status_{selected}")
                    if st.button("Save status change"):
                        try:
                            require_permission(actor,"cases:transition")
                            store.transition(case_id=selected,target=target,actor_id=actor.subject,expected_version=case["version"])
                            st.success("Status saved.")
                            st.rerun()
                        except Exception as exc:
                            show_error(exc)
                else:
                    st.caption("This case is in a terminal state.")
            st.write("**Case history**")
            events = store.list_events(selected)
            st.dataframe([{"Event": e["event_type"], "Actor": e["actor_id"],
                           "From": e["from_status"] or "—", "To": e["to_status"] or "—",
                           "At (UTC)": e["occurred_at"], "Details": json.dumps(e["metadata"], sort_keys=True)}
                          for e in events], use_container_width=True, hide_index=True)
            st.caption(f"{len(events)} recorded event(s). Timestamps are stored in UTC.")
    else:
        st.info("No saved cases yet. Create one in the next tab.")

with tab_create:
    st.subheader("Create a local synthetic case")
    with st.form("create_case",clear_on_submit=False):
        case_id=st.text_input("Case ID",value="CASE-DEMO-1001")
        lifecycle=st.selectbox("Lifecycle",["onboarding","offboarding","transfer","change"])
        summary=st.text_input("Summary",value="Prepare synthetic employee onboarding")
        payload_text=st.text_area("Optional synthetic request JSON",value='{"employee_id":"DEMO-1001","operating_system":"Windows"}')
        submitted=st.form_submit_button("Save case")
    if submitted:
        try:
            require_permission(actor,"cases:create")
            payload=json.loads(payload_text or "{}")
            if not isinstance(payload,dict):
                raise ValueError("Request payload must be a JSON object.")
            saved=store.create_case(case_id=case_id,lifecycle=lifecycle,requester_id=actor.subject,
                                    summary=summary,request_data=payload)
            st.success(f"Saved {saved['case_id']} as a draft.")
            st.rerun()
        except Exception as exc:
            show_error(exc)
store.close()
