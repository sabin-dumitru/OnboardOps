"""Synthetic case fixtures used by the local portfolio demo.

This module intentionally has no provider or network dependencies.
"""
from __future__ import annotations

from typing import Any

SAMPLE_CASES = (
    ("CASE-SAMPLE-1001", "Draft", "draft"),
    ("CASE-SAMPLE-1002", "Awaiting approval", "pending_approval"),
    ("CASE-SAMPLE-1003", "Work in progress", "in_progress"),
    ("CASE-SAMPLE-1004", "Completed onboarding", "completed"),
)


def seed_sample_cases(store: Any) -> int:
    """Add missing sample cases and return the number created.

    Existing fixture IDs are deliberately left untouched so reruns never reset
    a demo operator's sample case history.
    """
    existing_ids = {case["case_id"] for case in store.list_cases(limit=500)}
    created = 0
    for case_id, summary, target_status in SAMPLE_CASES:
        if case_id in existing_ids:
            continue
        store.create_case(
            case_id=case_id,
            lifecycle="onboarding",
            requester_id="synthetic-demo-requester",
            summary=summary,
            request_data={
                "employee_id": "DEMO-" + case_id[-4:],
                "operating_system": "Windows",
                "synthetic": True,
            },
        )
        created += 1
        if target_status != "draft":
            store.transition(
                case_id=case_id,
                target="pending_approval",
                actor_id="synthetic-demo-requester",
            )
        if target_status in {"in_progress", "completed"}:
            store.approve_case(
                case_id=case_id,
                approver_id="synthetic-demo-approver",
            )
            store.transition(
                case_id=case_id,
                target="in_progress",
                actor_id="synthetic-demo-technician",
            )
        if target_status == "completed":
            store.transition(
                case_id=case_id,
                target="completed",
                actor_id="synthetic-demo-technician",
            )
        existing_ids.add(case_id)
    return created
