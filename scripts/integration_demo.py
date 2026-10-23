"""Offline provider preview demo; makes no HTTP requests."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from onboardops.integrations import GitHubClient, JiraClient, ServiceNowClient, SnipeITClient, WorkdayClient
from onboardops.workflow import ActionLedger, WorkflowCase, approve_action, verify_approval

def main() -> int:
    case = WorkflowCase("DEMO-CASE-001", "onboarding", requester_id="demo-requester").transition("pending_approval")
    payload = {"project_key": "DEMO", "summary": "Prepare synthetic employee onboarding"}
    approval = approve_action(requester_id="demo-requester", approver_id="demo-approver", provider="jira",
                              operation="create_issue", payload=payload)
    verify_approval(approval, provider="jira", operation="create_issue", payload=payload)
    case = case.transition("approved").transition("in_progress")
    previews = [
        ServiceNowClient("https://example.service-now.com", "DEMO_TOKEN").create_incident(
            short_description="OnboardOps demo: onboarding preparation",
            description="Synthetic demo only; no real employee data.", correlation_id=case.case_id),
        JiraClient("https://example.atlassian.net", "demo@example.invalid", "DEMO_TOKEN").create_issue(
            project_key="DEMO", summary=payload["summary"], description="Synthetic demo only.", case_id=case.case_id),
        SnipeITClient("https://assets.example.invalid/api/v1", "DEMO_TOKEN").checkout_to_user(
            asset_id=101, user_id=202, note=case.case_id),
        WorkdayClient("https://workday.example.invalid/ccx/api/v1/demo", "DEMO_TOKEN").submit_configured_business_process(
            endpoint_path="/workers", payload={"demoCaseId": case.case_id}),
        GitHubClient("DEMO_TOKEN").create_issue(repository="example/onboardops-demo",
            title=payload["summary"], body="Synthetic demo only."),
    ]
    ledger = ActionLedger()
    try:
        ledger.append_audit(event_type="case.created", case_id=case.case_id, actor_id="demo-requester",
                            metadata={"lifecycle": case.lifecycle})
        ledger.append_audit(event_type="action.previewed", case_id=case.case_id, actor_id="demo-approver",
                            metadata={"providers": ["servicenow", "jira", "snipeit", "workday", "github"]})
        print(json.dumps({"demo_mode": "offline; no HTTP requests are made",
            "case": {"case_id": case.case_id, "lifecycle": case.lifecycle, "status": case.status},
            "approval": {"approver": approval.approver_id, "payload_bound": True},
            "provider_previews": previews, "audit_chain_valid": ledger.verify_audit_chain()}, indent=2))
    finally:
        ledger.close()
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
