"""Persistent local onboarding case store with explicit lifecycle and audit events."""
from __future__ import annotations
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from onboardops.workflow import TRANSITIONS, WorkflowError

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
_LIFECYCLES = {"onboarding", "offboarding", "transfer", "change"}

class CaseStoreError(ValueError):
    pass

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

class CaseStore:
    """Durable local case records. Callers must enforce identity and permission checks."""
    def __init__(self, database_path: str | Path = "data/onboardops_cases.sqlite3") -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database_path, timeout=10)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=10000")
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
          case_id TEXT PRIMARY KEY,
          lifecycle TEXT NOT NULL CHECK(lifecycle IN ('onboarding','offboarding','transfer','change')),
          status TEXT NOT NULL CHECK(status IN ('draft','pending_approval','approved','rejected','in_progress','blocked','completed','cancelled')),
          requester_id TEXT NOT NULL, summary TEXT NOT NULL, request_json TEXT NOT NULL,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS case_events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id TEXT NOT NULL REFERENCES cases(case_id), event_type TEXT NOT NULL,
          actor_id TEXT NOT NULL, from_status TEXT, to_status TEXT,
          metadata_json TEXT NOT NULL, occurred_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cases_updated_at ON cases(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_case_events_case ON case_events(case_id, event_id);
        CREATE TABLE IF NOT EXISTS provider_approvals (
          approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id TEXT NOT NULL REFERENCES cases(case_id),
          requester_id TEXT NOT NULL, approver_id TEXT NOT NULL,
          provider TEXT NOT NULL, operation TEXT NOT NULL,
          payload_json TEXT NOT NULL, fingerprint TEXT NOT NULL,
          approved_at TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('approved','consumed','revoked'))
        );
        """)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _safe_json(value: Any) -> Any:
        blocked = ("password", "secret", "token", "authorization", "api_key", "client_secret")
        if isinstance(value, dict):
            return {str(k): ("[REDACTED]" if any(b in str(k).casefold() for b in blocked)
                             else CaseStore._safe_json(v)) for k, v in value.items()}
        if isinstance(value, list):
            return [CaseStore._safe_json(v) for v in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def create_case(self, *, case_id: str, lifecycle: str, requester_id: str,
                    summary: str, request_data: dict[str, Any] | None = None) -> dict[str, Any]:
        case_id, requester_id, summary = case_id.strip(), requester_id.strip(), summary.strip()
        if not _CASE_ID_RE.fullmatch(case_id):
            raise CaseStoreError("Case ID must be 3–64 letters, numbers, dots, underscores or hyphens.")
        if lifecycle not in _LIFECYCLES:
            raise CaseStoreError("Unsupported lifecycle type.")
        if not requester_id or len(requester_id) > 128:
            raise CaseStoreError("A valid requester identity is required.")
        if not summary or len(summary) > 200:
            raise CaseStoreError("Summary must contain 1–200 characters.")
        safe_request = self._safe_json(request_data or {})
        request_json = json.dumps(safe_request, sort_keys=True, ensure_ascii=False)
        now = _now()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute(
                "INSERT INTO cases(case_id,lifecycle,status,requester_id,summary,request_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (case_id, lifecycle, "draft", requester_id, summary, request_json, now, now))
            self.connection.execute(
                "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) VALUES (?,?,?,?,?,?,?)",
                (case_id, "case.created", requester_id, None, "draft", "{}", now))
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise CaseStoreError("A case with that ID already exists.") from exc
        except Exception:
            self.connection.rollback()
            raise
        return self.get_case(case_id)

    def get_case(self, case_id: str) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
        if row is None:
            raise CaseStoreError("Case not found.")
        result = dict(row)
        result["request_data"] = json.loads(result.pop("request_json"))
        return result

    def list_cases(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise CaseStoreError("Case list limit must be between 1 and 500.")
        rows = self.connection.execute("SELECT case_id FROM cases ORDER BY updated_at DESC, case_id LIMIT ?", (limit,)).fetchall()
        return [self.get_case(row["case_id"]) for row in rows]

    def transition(self, *, case_id: str, target: str, actor_id: str, expected_version: int | None = None) -> dict[str, Any]:
        if target == "approved":
            raise WorkflowError("Use the separate-actor approval method to approve a case.")
        actor_id = actor_id.strip()
        if not actor_id:
            raise CaseStoreError("Actor identity is required.")
        if target not in TRANSITIONS:
            raise WorkflowError("Unknown lifecycle status.")
        now = _now()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            row = self.connection.execute("SELECT status, version FROM cases WHERE case_id=?", (case_id,)).fetchone()
            if row is None:
                raise CaseStoreError("Case not found.")
            current, version = row["status"], row["version"]
            if expected_version is not None and version != expected_version:
                raise CaseStoreError("This case changed in another session. Reload it before trying again.")
            if target not in TRANSITIONS.get(current, set()):
                raise WorkflowError(f"Transition from {current!r} to {target!r} is not allowed.")
            updated = self.connection.execute(
                "UPDATE cases SET status=?,updated_at=?,version=version+1 WHERE case_id=? AND version=?",
                (target, now, case_id, version))
            if updated.rowcount != 1:
                raise CaseStoreError("Concurrent case update detected; reload and retry.")
            self.connection.execute(
                "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) VALUES (?,?,?,?,?,?,?)",
                (case_id, "case.status_changed", actor_id, current, target, "{}", now))
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return self.get_case(case_id)


    def approve_case(self, *, case_id: str, approver_id: str, expected_version: int | None = None) -> dict[str, Any]:
        """Approve a pending case only when the approver differs from its requester."""
        approver_id = approver_id.strip()
        if not approver_id:
            raise CaseStoreError("Approver identity is required.")
        now = _now()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            row = self.connection.execute(
                "SELECT status, requester_id, version FROM cases WHERE case_id=?", (case_id,)).fetchone()
            if row is None:
                raise CaseStoreError("Case not found.")
            if row["requester_id"].casefold() == approver_id.casefold():
                raise WorkflowError("The requester cannot approve their own case.")
            if row["status"] != "pending_approval":
                raise WorkflowError("Only a case awaiting approval can be approved.")
            if expected_version is not None and row["version"] != expected_version:
                raise CaseStoreError("This case changed in another session. Reload it before trying again.")
            version = row["version"]
            updated = self.connection.execute(
                "UPDATE cases SET status='approved',updated_at=?,version=version+1 WHERE case_id=? AND version=? AND status='pending_approval'",
                (now, case_id, version))
            if updated.rowcount != 1:
                raise CaseStoreError("Concurrent case update detected; reload and retry.")
            self.connection.execute(
                "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) VALUES (?,?,?,?,?,?,?)",
                (case_id, "case.approved", approver_id, "pending_approval", "approved", "{}", now))
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return self.get_case(case_id)

    def record_provider_approval(self, *, case_id: str, requester_id: str, approver_id: str,
                                 provider: str, operation: str, payload: dict[str, Any],
                                 fingerprint: str) -> dict[str, Any]:
        """Persist a content-bound approval record; callers must verify authenticated roles."""
        requester_id, approver_id = requester_id.strip(), approver_id.strip()
        if not requester_id or not approver_id:
            raise CaseStoreError("Requester and approver identities are required.")
        if requester_id.casefold() == approver_id.casefold():
            raise WorkflowError("The requester cannot approve their own provider action.")
        if not all(x.strip() for x in (provider, operation, fingerprint)):
            raise CaseStoreError("Provider, operation and fingerprint are required.")
        safe_payload = json.dumps(self._safe_json(payload), sort_keys=True, ensure_ascii=False)
        now = _now()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            if not self.connection.execute("SELECT 1 FROM cases WHERE case_id=?", (case_id,)).fetchone():
                raise CaseStoreError("Case not found.")
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS provider_approvals (
                  approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  case_id TEXT NOT NULL REFERENCES cases(case_id),
                  requester_id TEXT NOT NULL, approver_id TEXT NOT NULL,
                  provider TEXT NOT NULL, operation TEXT NOT NULL,
                  payload_json TEXT NOT NULL, fingerprint TEXT NOT NULL,
                  approved_at TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('approved','consumed','revoked'))
                )
            """)
            cur = self.connection.execute(
                "INSERT INTO provider_approvals(case_id,requester_id,approver_id,provider,operation,payload_json,fingerprint,approved_at,status) VALUES (?,?,?,?,?,?,?,?, 'approved')",
                (case_id, requester_id, approver_id, provider, operation, safe_payload, fingerprint, now))
            approval_id = cur.lastrowid
            self.connection.execute(
                "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) VALUES (?,?,?,?,?,?,?)",
                (case_id, "provider_action.approved", approver_id, None, None,
                 json.dumps({"approval_id": approval_id, "provider": provider, "operation": operation, "fingerprint": fingerprint}, sort_keys=True), now))
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return self.get_provider_approval(int(approval_id))

    def get_provider_approval(self, approval_id: int) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM provider_approvals WHERE approval_id=?", (approval_id,)).fetchone()
        if row is None:
            raise CaseStoreError("Provider approval not found.")
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result


    def consume_provider_approval(self, approval_id: int, *, expected_fingerprint: str) -> dict[str, Any]:
        """Atomically consume a persisted approval once; callers must reconcile ambiguous outcomes."""
        now = _now()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            row = self.connection.execute("SELECT * FROM provider_approvals WHERE approval_id=?", (approval_id,)).fetchone()
            if row is None:
                raise CaseStoreError("Provider approval not found.")
            if row["status"] != "approved":
                raise CaseStoreError("Provider approval is no longer available for use.")
            if row["fingerprint"] != expected_fingerprint:
                raise CaseStoreError("Provider approval does not match the requested payload.")
            cur = self.connection.execute(
                "UPDATE provider_approvals SET status='consumed' WHERE approval_id=? AND status='approved' AND fingerprint=?",
                (approval_id, expected_fingerprint))
            if cur.rowcount != 1:
                raise CaseStoreError("Provider approval was already consumed; reconcile before retrying.")
            self.connection.execute(
                "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) VALUES (?,?,?,?,?,?,?)",
                (row["case_id"], "provider_action.approval_consumed", row["approver_id"], None, None,
                 json.dumps({"approval_id": approval_id, "provider": row["provider"], "operation": row["operation"]}, sort_keys=True), now))
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return self.get_provider_approval(approval_id)

    def list_events(self, case_id: str) -> list[dict[str, Any]]:
        if not self.connection.execute("SELECT 1 FROM cases WHERE case_id=?", (case_id,)).fetchone():
            raise CaseStoreError("Case not found.")
        rows = self.connection.execute(
            "SELECT event_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at FROM case_events WHERE case_id=? ORDER BY event_id",
            (case_id,)).fetchall()
        events = [dict(row) for row in rows]
        for event in events:
            event["metadata"] = json.loads(event.pop("metadata_json"))
        return events
