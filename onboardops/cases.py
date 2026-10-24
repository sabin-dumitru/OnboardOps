"""Persistent local onboarding case store with explicit lifecycle and audit events."""
from __future__ import annotations
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from onboardops.workflow import TRANSITIONS, WorkflowError
from onboardops.sanitization import redact_sensitive_fields

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
_LIFECYCLES = {"onboarding", "offboarding", "transfer", "change"}
_MAX_REQUEST_DATA_BYTES = 64 * 1024
_PROVIDER_APPROVAL_TTL = timedelta(minutes=15)
_SCHEMA_VERSION = 1

class CaseStoreError(ValueError):
    pass

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

class CaseStore:
    """Durable local case records. Callers must enforce identity and permission checks."""
    def __init__(self, database_path: str | Path = "data/onboardops_cases.sqlite3") -> None:
        raw_path = str(database_path)
        if raw_path == ":memory:":
            self.database_path = raw_path
        else:
            expanded_path = Path(raw_path).expanduser()
            self.database_path = str(expanded_path)
            missing_parents = []
            parent = expanded_path.parent
            while not parent.exists():
                missing_parents.append(parent)
                parent = parent.parent
            for directory in reversed(missing_parents):
                try:
                    directory.mkdir(mode=0o700)
                except FileExistsError:
                    if not directory.is_dir():
                        raise
            try:
                descriptor = os.open(
                    self.database_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
        self.connection = sqlite3.connect(self.database_path, timeout=10)
        try:
            self.connection.row_factory = sqlite3.Row
            current_schema = int(self.connection.execute("PRAGMA user_version").fetchone()[0])
            if current_schema > _SCHEMA_VERSION:
                self.connection.close()
                raise CaseStoreError(
                    "Database schema is newer than this application supports; upgrade the app before opening it."
                )
            self.connection.execute("PRAGMA foreign_keys=ON")
            self.connection.execute("PRAGMA busy_timeout=10000")
            self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS cases (
              case_id TEXT PRIMARY KEY,
              lifecycle TEXT NOT NULL CHECK(lifecycle IN ('onboarding','offboarding','transfer','change')),
              status TEXT NOT NULL CHECK(status IN ('draft','pending_approval','approved','rejected','in_progress','blocked','completed','cancelled')),
              requester_id TEXT NOT NULL, summary TEXT NOT NULL, request_json TEXT NOT NULL,
              priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('low','normal','high','urgent')),
              assigned_to TEXT,
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
              approved_at TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('approved','consumed','revoked'))
            );
            """)
            # Backward-compatible migrations for databases created by earlier demos.
            existing_columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(cases)")}
            if "priority" not in existing_columns:
                self.connection.execute("ALTER TABLE cases ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal'")
            if "assigned_to" not in existing_columns:
                self.connection.execute("ALTER TABLE cases ADD COLUMN assigned_to TEXT")
            approval_columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(provider_approvals)")}
            if "expires_at" not in approval_columns:
                self.connection.execute("ALTER TABLE provider_approvals ADD COLUMN expires_at TEXT")
                rows = self.connection.execute("SELECT approval_id, approved_at FROM provider_approvals").fetchall()
                for approval in rows:
                    try:
                        approved_at = datetime.fromisoformat(str(approval["approved_at"]).replace("Z", "+00:00"))
                        if approved_at.tzinfo is None:
                            approved_at = approved_at.replace(tzinfo=timezone.utc)
                        expires_at = (approved_at.astimezone(timezone.utc) + _PROVIDER_APPROVAL_TTL).isoformat()
                    except (TypeError, ValueError):
                        expires_at = "1970-01-01T00:00:00+00:00"
                    self.connection.execute(
                        "UPDATE provider_approvals SET expires_at=? WHERE approval_id=?",
                        (expires_at, approval["approval_id"]),
                    )
            # PRAGMA user_version is SQLite's durable schema-version marker. Future
            # migrations must increment _SCHEMA_VERSION and run before advancing it.
            self.connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
            self.connection.commit()
        except BaseException:
            self.connection.close()
            raise

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _safe_json(value: Any) -> Any:
        """Backward-compatible wrapper around the shared sanitization policy."""
        return redact_sensitive_fields(value)

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
        if request_data is not None and not isinstance(request_data, dict):
            raise CaseStoreError("Request data must be a JSON object.")
        try:
            safe_request = self._safe_json(request_data or {})
            request_json = json.dumps(safe_request, sort_keys=True, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, RecursionError) as exc:
            raise CaseStoreError("Request data must be valid JSON-compatible data.") from exc
        if len(request_json.encode("utf-8")) > _MAX_REQUEST_DATA_BYTES:
            raise CaseStoreError("Request data exceeds the 64 KiB limit.")
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

    def list_cases(
        self, limit: int = 100, *, requester_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return a bounded newest-first case page, optionally filtering before the limit."""
        if not 1 <= limit <= 500:
            raise CaseStoreError("Case list limit must be between 1 and 500.")
        clauses: list[str] = []
        parameters: list[Any] = []
        if requester_id is not None:
            if not requester_id.strip() or len(requester_id) > 128:
                raise CaseStoreError("Requester filter must be a valid identity.")
            clauses.append("requester_id = ?")
            parameters.append(requester_id)
        if status is not None:
            if status not in TRANSITIONS:
                raise CaseStoreError("Unsupported case status filter.")
            clauses.append("status = ?")
            parameters.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"SELECT case_id FROM cases{where} ORDER BY updated_at DESC, case_id LIMIT ?",
            (*parameters, limit),
        ).fetchall()
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
        if not isinstance(payload, dict):
            raise CaseStoreError("Provider approval payload must be a JSON object.")
        try:
            safe_payload = json.dumps(self._safe_json(payload), sort_keys=True, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, RecursionError) as exc:
            raise CaseStoreError("Provider approval payload must be valid JSON-compatible data.") from exc
        approved_at = datetime.now(timezone.utc)
        now = approved_at.isoformat()
        expires_at = (approved_at + _PROVIDER_APPROVAL_TTL).isoformat()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            case_row = self.connection.execute("SELECT requester_id FROM cases WHERE case_id=?", (case_id,)).fetchone()
            if case_row is None:
                raise CaseStoreError("Case not found.")
            if case_row["requester_id"].casefold() != requester_id.casefold():
                raise WorkflowError("Provider approval requester must match the case requester.")
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS provider_approvals (
                  approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  case_id TEXT NOT NULL REFERENCES cases(case_id),
                  requester_id TEXT NOT NULL, approver_id TEXT NOT NULL,
                  provider TEXT NOT NULL, operation TEXT NOT NULL,
                  payload_json TEXT NOT NULL, fingerprint TEXT NOT NULL,
                  approved_at TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('approved','consumed','revoked'))
                )
            """)
            cur = self.connection.execute(
                "INSERT INTO provider_approvals(case_id,requester_id,approver_id,provider,operation,payload_json,fingerprint,approved_at,expires_at,status) VALUES (?,?,?,?,?,?,?,?,?, 'approved')",
                (case_id, requester_id, approver_id, provider, operation, safe_payload, fingerprint, now, expires_at))
            approval_id = cur.lastrowid
            self.connection.execute(
                "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) VALUES (?,?,?,?,?,?,?)",
                (case_id, "provider_action.approved", approver_id, None, None,
                 json.dumps({"approval_id": approval_id, "provider": provider, "operation": operation, "fingerprint": fingerprint, "expires_at": expires_at}, sort_keys=True, allow_nan=False), now))
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
        """Atomically consume an unexpired approval once; callers reconcile ambiguous outcomes."""
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        expired = False
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            row = self.connection.execute("SELECT * FROM provider_approvals WHERE approval_id=?", (approval_id,)).fetchone()
            if row is None:
                raise CaseStoreError("Provider approval not found.")
            if row["status"] != "approved":
                raise CaseStoreError("Provider approval is no longer available for use.")
            try:
                expires_at = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                expired = expires_at.astimezone(timezone.utc) <= now_dt
            except (TypeError, ValueError):
                expired = True

            if expired:
                self.connection.execute(
                    "UPDATE provider_approvals SET status='revoked' WHERE approval_id=? AND status='approved'",
                    (approval_id,),
                )
                self.connection.execute(
                    "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) VALUES (?,?,?,?,?,?,?)",
                    (row["case_id"], "provider_action.approval_expired", row["approver_id"], None, None,
                     json.dumps({"approval_id": approval_id, "provider": row["provider"], "operation": row["operation"]}, sort_keys=True, allow_nan=False), now),
                )
                self.connection.commit()
            else:
                if row["fingerprint"] != expected_fingerprint:
                    raise CaseStoreError("Provider approval does not match the requested payload.")
                cur = self.connection.execute(
                    "UPDATE provider_approvals SET status='consumed' WHERE approval_id=? AND status='approved' AND fingerprint=?",
                    (approval_id, expected_fingerprint),
                )
                if cur.rowcount != 1:
                    raise CaseStoreError("Provider approval was already consumed; reconcile before retrying.")
                self.connection.execute(
                    "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) VALUES (?,?,?,?,?,?,?)",
                    (row["case_id"], "provider_action.approval_consumed", row["approver_id"], None, None,
                     json.dumps({"approval_id": approval_id, "provider": row["provider"], "operation": row["operation"]}, sort_keys=True), now),
                )
                self.connection.commit()
        except Exception:
            if self.connection.in_transaction:
                self.connection.rollback()
            raise
        if expired:
            raise CaseStoreError("Provider approval expired or had an invalid expiry; request a new approval.")
        return self.get_provider_approval(approval_id)

    def revoke_provider_approval(self, approval_id: int, *, actor_id: str) -> dict[str, Any]:
        """Revoke an unused provider approval and record the actor in case history."""
        actor_id = actor_id.strip()
        if not actor_id:
            raise CaseStoreError("Actor identity is required.")
        now = _now()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            row = self.connection.execute("SELECT * FROM provider_approvals WHERE approval_id=?", (approval_id,)).fetchone()
            if row is None:
                raise CaseStoreError("Provider approval not found.")
            if row["status"] != "approved":
                raise CaseStoreError("Only an unused approved action can be revoked.")
            cur = self.connection.execute(
                "UPDATE provider_approvals SET status='revoked' WHERE approval_id=? AND status='approved'",
                (approval_id,),
            )
            if cur.rowcount != 1:
                raise CaseStoreError("Provider approval is no longer available for revocation.")
            self.connection.execute(
                "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) VALUES (?,?,?,?,?,?,?)",
                (row["case_id"], "provider_action.approval_revoked", actor_id, None, None,
                 json.dumps({"approval_id": approval_id, "provider": row["provider"], "operation": row["operation"]}, sort_keys=True), now),
            )
            self.connection.commit()
        except Exception:
            if self.connection.in_transaction:
                self.connection.rollback()
            raise
        return self.get_provider_approval(approval_id)

    def update_triage(self, *, case_id: str, priority: str, assigned_to: str | None,
                      actor_id: str, expected_version: int | None = None) -> dict[str, Any]:
        """Update triage fields atomically and record an auditable case event."""
        allowed_priorities = {"low", "normal", "high", "urgent"}
        if priority not in allowed_priorities:
            raise CaseStoreError("Priority must be low, normal, high or urgent.")
        actor_id = actor_id.strip()
        if not actor_id:
            raise CaseStoreError("Actor identity is required.")
        assignee = (assigned_to or "").strip() or None
        if assignee is not None and len(assignee) > 128:
            raise CaseStoreError("Assignee must be 128 characters or fewer.")
        now = _now()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            row = self.connection.execute(
                "SELECT priority, assigned_to, version FROM cases WHERE case_id=?", (case_id,)
            ).fetchone()
            if row is None:
                raise CaseStoreError("Case not found.")
            if expected_version is not None and row["version"] != expected_version:
                raise CaseStoreError("This case changed in another session. Reload it before trying again.")
            old_priority, old_assignee = row["priority"], row["assigned_to"]
            updated = self.connection.execute(
                "UPDATE cases SET priority=?, assigned_to=?, updated_at=?, version=version+1 "
                "WHERE case_id=? AND version=?",
                (priority, assignee, now, case_id, row["version"]),
            )
            if updated.rowcount != 1:
                raise CaseStoreError("Concurrent case update detected; reload and retry.")
            metadata = json.dumps({
                "priority_from": old_priority, "priority_to": priority,
                "assigned_to_from": old_assignee, "assigned_to_to": assignee,
            }, sort_keys=True, allow_nan=False)
            self.connection.execute(
                "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (case_id, "case.triage_updated", actor_id, None, None, metadata, now),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return self.get_case(case_id)

    def list_events(self, case_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        """Return the most recent bounded event history, in chronological order."""
        if not 1 <= limit <= 500:
            raise CaseStoreError("Event history limit must be between 1 and 500.")
        if not self.connection.execute("SELECT 1 FROM cases WHERE case_id=?", (case_id,)).fetchone():
            raise CaseStoreError("Case not found.")
        rows = self.connection.execute(
            "SELECT event_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at "
            "FROM (SELECT event_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at "
            "FROM case_events WHERE case_id=? ORDER BY event_id DESC LIMIT ?) "
            "ORDER BY event_id ASC",
            (case_id, limit),
        ).fetchall()
        events = [dict(row) for row in rows]
        for event in events:
            event["metadata"] = json.loads(event.pop("metadata_json"))
        return events
