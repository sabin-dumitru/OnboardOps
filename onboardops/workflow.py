"""Framework-neutral lifecycle transitions, approval binding and local action ledger."""
from __future__ import annotations
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class WorkflowError(ValueError):
    pass


class DuplicateActionError(WorkflowError):
    pass


TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_approval", "cancelled"},
    "pending_approval": {"approved", "rejected", "cancelled"},
    "rejected": {"draft", "cancelled"},
    "approved": {"in_progress", "cancelled"},
    "in_progress": {"blocked", "completed", "cancelled"},
    "blocked": {"in_progress", "cancelled"},
    "completed": set(), "cancelled": set(),
}


@dataclass(frozen=True)
class WorkflowCase:
    case_id: str
    lifecycle: str
    status: str = "draft"
    requester_id: str = ""

    def transition(self, target: str) -> "WorkflowCase":
        if self.lifecycle not in {"onboarding", "offboarding", "transfer", "change"}:
            raise WorkflowError("Unsupported lifecycle type.")
        if target not in TRANSITIONS.get(self.status, set()):
            raise WorkflowError(f"Transition from {self.status!r} to {target!r} is not allowed.")
        return WorkflowCase(self.case_id, self.lifecycle, target, self.requester_id)


def action_fingerprint(provider: str, operation: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps({"provider": provider, "operation": operation, "payload": payload},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Approval:
    requester_id: str
    approver_id: str
    fingerprint: str
    approved_at: str


def approve_action(*, requester_id: str, approver_id: str, provider: str,
                   operation: str, payload: dict[str, Any]) -> Approval:
    if not requester_id.strip() or not approver_id.strip():
        raise WorkflowError("Requester and approver identities are required.")
    if requester_id.casefold() == approver_id.casefold():
        raise WorkflowError("A requester cannot approve their own action.")
    return Approval(requester_id, approver_id, action_fingerprint(provider, operation, payload),
                    datetime.now(timezone.utc).isoformat())


def verify_approval(approval: Approval, *, provider: str, operation: str,
                    payload: dict[str, Any]) -> None:
    if approval.fingerprint != action_fingerprint(provider, operation, payload):
        raise WorkflowError("Approval is stale: the action payload changed after approval.")


class ActionLedger:
    """SQLite single-process ledger; not a multi-user or tamper-proof enterprise store."""
    def __init__(self, database_path: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(database_path), timeout=10, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS actions (
          idempotency_key TEXT PRIMARY KEY, provider TEXT NOT NULL, operation TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('started','succeeded','failed','unknown')),
          external_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit_events (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at TEXT NOT NULL,
          event_type TEXT NOT NULL, case_id TEXT NOT NULL, actor_id TEXT NOT NULL,
          metadata_json TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE);
        """)

    def close(self) -> None:
        self.connection.close()

    def begin_action(self, *, idempotency_key: str, provider: str, operation: str) -> bool:
        if not all(x.strip() for x in (idempotency_key, provider, operation)):
            raise WorkflowError("Idempotency key, provider and operation are required.")
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute("INSERT INTO actions VALUES (?, ?, ?, 'started', NULL, ?, ?)",
                                    (idempotency_key, provider, operation, now, now))
            self.connection.execute("COMMIT")
            return True
        except sqlite3.IntegrityError as exc:
            self.connection.execute("ROLLBACK")
            raise DuplicateActionError("Action key already exists; reconcile its outcome before retrying.") from exc
        except Exception:
            if self.connection.in_transaction:
                self.connection.execute("ROLLBACK")
            raise

    def finish_action(self, idempotency_key: str, *, status: str, external_id: str | None = None) -> None:
        if status not in {"succeeded", "failed", "unknown"}:
            raise WorkflowError("Outcome must be succeeded, failed or unknown.")
        cursor = self.connection.execute(
            "UPDATE actions SET status=?, external_id=?, updated_at=? WHERE idempotency_key=? AND status='started'",
            (status, external_id, datetime.now(timezone.utc).isoformat(), idempotency_key))
        if cursor.rowcount != 1:
            raise WorkflowError("No started action found for this idempotency key.")

    @staticmethod
    def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        blocked = ("password", "secret", "token", "authorization", "api_key", "client_secret")
        def clean(value: Any) -> Any:
            if isinstance(value, dict):
                return {str(k): ("[REDACTED]" if any(word in str(k).casefold() for word in blocked)
                                 else clean(v)) for k, v in value.items()}
            if isinstance(value, list):
                return [clean(v) for v in value]
            if isinstance(value, (str, int, float, bool)) or value is None:
                return value
            return str(value)
        return clean(metadata)

    def append_audit(self, *, event_type: str, case_id: str, actor_id: str,
                     metadata: dict[str, Any] | None = None) -> str:
        if not event_type.strip() or not case_id.strip() or not actor_id.strip():
            raise WorkflowError("Audit event type, case ID and actor ID are required.")
        safe = json.dumps(self._safe_metadata(metadata or {}), sort_keys=True, separators=(",", ":"))
        prior = self.connection.execute("SELECT event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1").fetchone()
        previous_hash = prior["event_hash"] if prior else "GENESIS"
        occurred = datetime.now(timezone.utc).isoformat()
        fields = {"occurred_at": occurred, "event_type": event_type, "case_id": case_id,
                  "actor_id": actor_id, "metadata_json": safe, "previous_hash": previous_hash}
        event_hash = hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.connection.execute("INSERT INTO audit_events (occurred_at,event_type,case_id,actor_id,metadata_json,previous_hash,event_hash) VALUES (?,?,?,?,?,?,?)",
            (occurred, event_type, case_id, actor_id, safe, previous_hash, event_hash))
        return event_hash

    def verify_audit_chain(self) -> bool:
        previous_hash = "GENESIS"
        for row in self.connection.execute("SELECT * FROM audit_events ORDER BY sequence").fetchall():
            fields = {"occurred_at": row["occurred_at"], "event_type": row["event_type"],
                      "case_id": row["case_id"], "actor_id": row["actor_id"],
                      "metadata_json": row["metadata_json"], "previous_hash": previous_hash}
            expected = hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if row["previous_hash"] != previous_hash or row["event_hash"] != expected:
                return False
            previous_hash = row["event_hash"]
        return True
