"""Optional integration lab: read-only live diagnostics and offline write previews."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from onboardops.auth import AuthorizationError, require_integration_read
from onboardops.ui_accessibility import accessibility_styles
from onboardops.integrations import (  # noqa: E402
    GitHubClient, IntegrationError, JiraClient, MicrosoftGraphClient,
    ServiceNowClient, SnipeITClient, WorkdayClient,
)

st.set_page_config(page_title="OnboardOps · Integration Lab", page_icon="🔌", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1280px; padding-top: 1.6rem; padding-bottom: 3rem;}
[data-testid="stMetric"] {background: #111c2e; border: 1px solid #263852; border-radius: 12px; padding: .85rem;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-color: #263852;}
.ops-eyebrow {color: #91a8c5; text-transform: uppercase; letter-spacing: .12em; font-size: .74rem; font-weight: 700;}
.ops-title {font-size: 2rem; font-weight: 750; letter-spacing: -.04em; margin: .15rem 0 .25rem;}
.ops-subtitle {color: #a9bad0; margin-bottom: 1.1rem;}
</style>
<div class="ops-eyebrow">PLATFORM · CONNECTIVITY</div>
<h1 class="ops-title">Integration Lab</h1>
<div class="ops-subtitle">Provider readiness, read-only diagnostics, and safe action previews.</div>
""", unsafe_allow_html=True)

st.markdown(accessibility_styles(), unsafe_allow_html=True)

st.warning(
    "This page is intended for local development and uses configured provider credentials only when explicitly authorised. "
    "Live read-only lookups require an admin/operator identity supplied by the trusted-proxy seam; the local demo identity is denied. "
    "Live writes are not exposed in this UI. The proxy seam is not a bundled OIDC/SSO implementation, so do not expose a credentialed "
    "instance to a network until identity propagation, header stripping, TLS, and network isolation have been independently reviewed."
)

headers = {}
try:
    headers = dict(st.context.headers)
except Exception:
    pass
try:
    require_integration_read(headers)
    live_lookup_allowed = True
except AuthorizationError:
    live_lookup_allowed = False
    st.info(
        "Live provider lookups are disabled for the local demo identity. "
        "Use a reviewed trusted-proxy deployment with an authorised integration-reader role."
    )


def enforce_live_lookup_access() -> None:
    """Re-check permission at the action site; a disabled widget is not authorization."""
    try:
        require_integration_read(headers)
    except AuthorizationError:
        st.error("Live provider lookup is not authorised for this identity.")
        st.stop()


def setting(name: str) -> str:
    """Read configuration without ever displaying secret values."""
    return os.environ.get(name, "").strip()


def configured(*names: str) -> bool:
    return all(setting(name) for name in names)


def provider_status(label: str, variables: tuple[str, ...]) -> None:
    present = [name for name in variables if setting(name)]
    missing = [name for name in variables if not setting(name)]
    if not missing:
        st.success(f"{label}: configured (secret values hidden)")
    elif present:
        st.warning(f"{label}: incomplete configuration; missing {', '.join(missing)}")
    else:
        st.info(f"{label}: not configured; offline previews remain available")


def safe_error(exc: Exception) -> None:
    if isinstance(exc, IntegrationError):
        st.error(f"Provider request failed ({exc.code}). {exc}")
    elif isinstance(exc, ValueError):
        st.error(str(exc))
    else:
        # Never surface raw request exceptions, headers, tokens or provider response bodies.
        st.error("Unexpected integration error. Details were withheld to avoid exposing sensitive data.")


def show_json(value: Any) -> None:
    st.json(value, expanded=False)


graph_vars = ("ONBOARDOPS_GRAPH_TENANT_ID", "ONBOARDOPS_GRAPH_CLIENT_ID", "ONBOARDOPS_GRAPH_CLIENT_SECRET")
snow_vars = ("ONBOARDOPS_SERVICENOW_INSTANCE_URL", "ONBOARDOPS_SERVICENOW_TOKEN")
jira_vars = ("ONBOARDOPS_JIRA_SITE_URL", "ONBOARDOPS_JIRA_EMAIL", "ONBOARDOPS_JIRA_API_TOKEN")
snipe_vars = ("ONBOARDOPS_SNIPEIT_API_BASE_URL", "ONBOARDOPS_SNIPEIT_TOKEN")
workday_vars = ("ONBOARDOPS_WORKDAY_API_ROOT", "ONBOARDOPS_WORKDAY_ACCESS_TOKEN")
github_vars = ("ONBOARDOPS_GITHUB_TOKEN",)

with st.expander("Connection readiness", expanded=True):
    for label, variables in (
        ("Microsoft Graph / Entra ID and Intune", graph_vars),
        ("ServiceNow", snow_vars),
        ("Jira Cloud", jira_vars),
        ("Snipe-IT", snipe_vars),
        ("Workday", workday_vars),
        ("GitHub", github_vars),
    ):
        provider_status(label, variables)
    st.caption("Set variables in the environment before launching Streamlit. Values are never printed by this page.")
    st.code("python -m streamlit run app.py", language="powershell")

st.header("Read-only live lookups")
left, right = st.columns(2)

with left:
    with st.container(border=True):
        st.subheader("Microsoft Graph · User lookup")
        st.caption("Requires application permissions and admin consent. Returns selected directory fields only.")
        graph_upn = st.text_input("User ID or user principal name", placeholder="synthetic.user@example.invalid")
        if st.button("Look up user", disabled=not configured(*graph_vars) or not live_lookup_allowed, key="graph_user"):
            enforce_live_lookup_access()
            try:
                client = MicrosoftGraphClient(*(setting(v) for v in graph_vars))
                result = client.get_user(graph_upn)
                show_json({k: result.get(k) for k in (
                    "id", "displayName", "userPrincipalName", "accountEnabled", "department", "jobTitle", "officeLocation"
                ) if k in result})
            except Exception as exc:
                safe_error(exc)

    with st.container(border=True):
        st.subheader("Microsoft Intune · Managed devices")
        st.caption("Read-only, bounded page. Requires an active Intune licence and consented permissions.")
        device_limit = st.slider("Maximum devices to retrieve", min_value=1, max_value=50, value=10)
        if st.button("List managed devices", disabled=not configured(*graph_vars) or not live_lookup_allowed, key="intune_devices"):
            enforce_live_lookup_access()
            try:
                client = MicrosoftGraphClient(*(setting(v) for v in graph_vars))
                rows = client.list_managed_devices(top=device_limit)
                st.write(f"Returned {len(rows)} device record(s).")
                show_json([{k: row.get(k) for k in (
                    "id", "deviceName", "operatingSystem", "complianceState",
                    "managedDeviceOwnerType", "userPrincipalName", "lastSyncDateTime"
                ) if k in row} for row in rows])
            except Exception as exc:
                safe_error(exc)

    with st.container(border=True):
        st.subheader("ServiceNow · Incident lookup")
        correlation_id = st.text_input("Correlation ID", value="DEMO-CASE-001")
        if st.button("Find incidents", disabled=not configured(*snow_vars) or not live_lookup_allowed, key="snow_lookup"):
            enforce_live_lookup_access()
            try:
                client = ServiceNowClient(setting(snow_vars[0]), setting(snow_vars[1]))
                show_json(client.find_incidents_by_correlation_id(correlation_id))
            except Exception as exc:
                safe_error(exc)

with right:
    with st.container(border=True):
        st.subheader("Jira Cloud · Issue lookup")
        issue_key = st.text_input("Issue key", placeholder="DEMO-123")
        if st.button("Look up issue", disabled=not configured(*jira_vars) or not live_lookup_allowed, key="jira_lookup"):
            enforce_live_lookup_access()
            try:
                client = JiraClient(*(setting(v) for v in jira_vars))
                issue = client.get_issue(issue_key)
                fields = issue.get("fields", {}) if isinstance(issue, dict) else {}
                show_json({"id": issue.get("id"), "key": issue.get("key"),
                           "summary": fields.get("summary"),
                           "status": (fields.get("status") or {}).get("name")})
            except Exception as exc:
                safe_error(exc)

    with st.container(border=True):
        st.subheader("Snipe-IT · Asset search")
        asset_search = st.text_input("Asset tag, model or search term", placeholder="DEMO-LAPTOP")
        if st.button("Search assets", disabled=not configured(*snipe_vars) or not live_lookup_allowed, key="snipe_search"):
            enforce_live_lookup_access()
            try:
                client = SnipeITClient(setting(snipe_vars[0]), setting(snipe_vars[1]))
                rows = client.search_hardware(asset_search, limit=50)
                show_json([{"id": row.get("id"), "name": row.get("name"), "asset_tag": row.get("asset_tag"),
                            "serial": row.get("serial"), "status_label": row.get("status_label"),
                            "assigned_to": row.get("assigned_to")} for row in rows])
            except Exception as exc:
                safe_error(exc)

    with st.container(border=True):
        st.subheader("Workday · Configured read endpoint")
        st.caption("The API root, endpoint schema and permissions must match your tenant.")
        workday_path = st.text_input("Relative endpoint path", value="/workers")
        if st.button("Read Workday endpoint", disabled=not configured(*workday_vars) or not live_lookup_allowed, key="workday_read"):
            enforce_live_lookup_access()
            try:
                client = WorkdayClient(setting(workday_vars[0]), setting(workday_vars[1]))
                result = client.get_workers(endpoint_path=workday_path)
                if isinstance(result, dict):
                    st.write("Top-level response fields:", ", ".join(map(str, result.keys())))
                    rows = result.get("data") or result.get("workers") or result.get("Worker")
                    if isinstance(rows, list):
                        st.write(f"Record count in recognised collection: {len(rows)}")
                    else:
                        st.caption("Raw HR records are intentionally not rendered in the dashboard.")
                else:
                    st.write("Workday returned a non-object response; raw HR data is not rendered.")
            except Exception as exc:
                safe_error(exc)

st.divider()
st.header("Offline write previews")
st.write("These previews build provider-shaped payloads without sending anything to an external service.")

case_id = st.text_input("Synthetic case ID for previews", value="DEMO-CASE-001")
summary = st.text_input("Task summary", value="Prepare synthetic employee onboarding")
description = st.text_area("Task description", value="Synthetic portfolio demo only. No real employee data.")
project_key = st.text_input("Jira project key", value=setting("ONBOARDOPS_JIRA_PROJECT_KEY") or "DEMO")
p1, p2 = st.columns(2)
with p1:
    if st.button("Preview ServiceNow incident payload", key="snow_preview"):
        try:
            client = ServiceNowClient(
                setting(snow_vars[0]) or "https://example.service-now.com",
                setting(snow_vars[1]) or "DEMO_TOKEN",
            )
            show_json(client.create_incident(short_description=summary, description=description,
                                             correlation_id=case_id, dry_run=True))
        except Exception as exc:
            safe_error(exc)
    if st.button("Preview Jira issue payload", key="jira_preview"):
        try:
            client = JiraClient(setting(jira_vars[0]) or "https://example.atlassian.net",
                                setting(jira_vars[1]) or "demo@example.invalid",
                                setting(jira_vars[2]) or "DEMO_TOKEN")
            show_json(client.create_issue(project_key=project_key, summary=summary, description=description,
                                          case_id=case_id, dry_run=True))
        except Exception as exc:
            safe_error(exc)
    if st.button("Preview GitHub issue payload", key="github_preview"):
        try:
            client = GitHubClient(setting(github_vars[0]) or "DEMO_TOKEN")
            show_json(client.create_issue(
                repository=setting("ONBOARDOPS_GITHUB_REPOSITORY") or "example/onboardops-demo",
                title=summary, body=description, dry_run=True))
        except Exception as exc:
            safe_error(exc)
with p2:
    if st.button("Preview Snipe-IT checkout payload", key="snipe_preview"):
        try:
            client = SnipeITClient(setting(snipe_vars[0]) or "https://assets.example.invalid/api/v1",
                                   setting(snipe_vars[1]) or "DEMO_TOKEN")
            show_json(client.checkout_to_user(asset_id=101, user_id=202, note=case_id, dry_run=True))
        except Exception as exc:
            safe_error(exc)
    if st.button("Preview Workday request payload", key="workday_preview"):
        try:
            client = WorkdayClient(setting(workday_vars[0]) or "https://workday.example.invalid/ccx/api/v1/demo",
                                   setting(workday_vars[1]) or "DEMO_TOKEN")
            show_json(client.submit_configured_business_process(
                endpoint_path="/workers", payload={"demoCaseId": case_id, "summary": summary}, dry_run=True))
        except Exception as exc:
            safe_error(exc)

st.info(
    "Live writes are intentionally not exposed by this page yet. Before enabling them for a team, "
    "OnboardOps needs real user authentication, server-side role enforcement, persisted approvals, "
    "and a reconciliation flow for uncertain provider outcomes. The provider adapter methods already "
    "support live writes when supplied with an exact payload-bound approval object."
)
