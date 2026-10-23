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
