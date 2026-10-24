import os
import tempfile
import unittest
from onboardops.auth import AuthorizationError, require_permission, resolve_actor
from onboardops.cases import CaseStore, CaseStoreError
from onboardops.demo_fixtures import SAMPLE_CASES, seed_sample_cases
from onboardops.workflow import WorkflowError

class AuthTests(unittest.TestCase):
    def test_demo_cannot_authorise_production_write(self):
        actor = resolve_actor(environ={"ONBOARDOPS_AUTH_MODE":"demo"})
        require_permission(actor, "cases:create")
        with self.assertRaises(AuthorizationError):
            require_permission(actor, "provider:write", production_only=True)

    def test_unknown_mode_fails_closed(self):
        with self.assertRaises(AuthorizationError):
            resolve_actor(environ={"ONBOARDOPS_AUTH_MODE":"unexpected"})

    def test_proxy_identity_requires_explicit_trust_and_role(self):
        headers={"X-Auth-Request-User":"alice@example.invalid","X-Auth-Request-Groups":"onboardops-requester"}
        with self.assertRaises(AuthorizationError):
            resolve_actor(headers, environ={"ONBOARDOPS_AUTH_MODE":"trusted_proxy"})
        actor=resolve_actor(headers,environ={"ONBOARDOPS_AUTH_MODE":"trusted_proxy","ONBOARDOPS_TRUSTED_AUTH_PROXY":"true"})
        require_permission(actor,"cases:create")
        with self.assertRaises(AuthorizationError):
            require_permission(actor,"provider:write")

    def test_missing_identity_is_denied(self):
        with self.assertRaises(AuthorizationError):
            resolve_actor({},environ={"ONBOARDOPS_AUTH_MODE":"trusted_proxy","ONBOARDOPS_TRUSTED_AUTH_PROXY":"true"})

class CaseStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=os.path.join(self.temp.name,"cases.sqlite3")
        self.store=CaseStore(self.path)
    def tearDown(self):
        self.store.close()
        self.temp.cleanup()
    def test_synthetic_fixtures_cover_lifecycle_and_are_idempotent(self):
        created = seed_sample_cases(self.store)
        self.assertEqual(created, 4)
        self.assertEqual(seed_sample_cases(self.store), 0)
        cases = {case["case_id"]: case for case in self.store.list_cases(limit=500)}
        self.assertEqual(
            {case_id: cases[case_id]["status"] for case_id, _, _ in SAMPLE_CASES},
            {
                "CASE-SAMPLE-1001": "draft",
                "CASE-SAMPLE-1002": "pending_approval",
                "CASE-SAMPLE-1003": "in_progress",
                "CASE-SAMPLE-1004": "completed",
            },
        )
        for case_id, _, _ in SAMPLE_CASES:
            self.assertTrue(cases[case_id]["request_data"]["synthetic"])
            self.assertTrue(cases[case_id]["request_data"]["employee_id"].startswith("DEMO-"))

    def test_triage_updates_are_validated_versioned_and_audited(self):
        self.store.create_case(case_id="CASE-TRIAGE-1", lifecycle="onboarding",
                               requester_id="alice", summary="Synthetic triage test")
        case = self.store.get_case("CASE-TRIAGE-1")
        self.assertEqual(case["priority"], "normal")
        self.assertIsNone(case["assigned_to"])
        updated = self.store.update_triage(
            case_id="CASE-TRIAGE-1", priority="urgent", assigned_to="tech@example.invalid",
            actor_id="dispatcher", expected_version=case["version"],
        )
        self.assertEqual(updated["priority"], "urgent")
        self.assertEqual(updated["assigned_to"], "tech@example.invalid")
        event = self.store.list_events("CASE-TRIAGE-1")[-1]
        self.assertEqual(event["event_type"], "case.triage_updated")
        self.assertEqual(event["actor_id"], "dispatcher")
        self.assertEqual(event["metadata"]["priority_from"], "normal")
        with self.assertRaises(CaseStoreError):
            self.store.update_triage(
                case_id="CASE-TRIAGE-1", priority="critical", assigned_to=None,
                actor_id="dispatcher",
            )
        with self.assertRaises(CaseStoreError):
            self.store.update_triage(
                case_id="CASE-TRIAGE-1", priority="low", assigned_to=None,
                actor_id="dispatcher", expected_version=case["version"],
            )

    def test_triage_schema_migrates_existing_database(self):
        self.store.create_case(case_id="CASE-MIGRATE-1", lifecycle="onboarding",
                               requester_id="alice", summary="Existing case")
        self.store.connection.execute("ALTER TABLE cases DROP COLUMN priority")
        self.store.connection.execute("ALTER TABLE cases DROP COLUMN assigned_to")
        self.store.connection.commit()
        self.store.close()
        self.store = CaseStore(self.path)
        case = self.store.get_case("CASE-MIGRATE-1")
        self.assertEqual(case["priority"], "normal")
        self.assertIsNone(case["assigned_to"])

    def test_case_persists_and_history_is_recorded(self):
        self.store.create_case(case_id="CASE-100",lifecycle="onboarding",requester_id="alice",summary="Synthetic onboarding",request_data={"employee_id":"DEMO-100"})
        self.store.transition(case_id="CASE-100",target="pending_approval",actor_id="alice",expected_version=1)
        self.store.close()
        self.store=CaseStore(self.path)
        self.assertEqual(self.store.get_case("CASE-100")["status"],"pending_approval")
        self.assertEqual([e["event_type"] for e in self.store.list_events("CASE-100")],["case.created","case.status_changed"])
    def test_duplicate_case_is_rejected(self):
        args=dict(case_id="CASE-101",lifecycle="onboarding",requester_id="alice",summary="Demo")
        self.store.create_case(**args)
        with self.assertRaises(CaseStoreError): self.store.create_case(**args)
    def test_bad_transition_and_stale_version_are_rejected(self):
        self.store.create_case(case_id="CASE-102",lifecycle="onboarding",requester_id="alice",summary="Demo")
        with self.assertRaises(WorkflowError): self.store.transition(case_id="CASE-102",target="completed",actor_id="alice")
        self.store.transition(case_id="CASE-102",target="pending_approval",actor_id="alice",expected_version=1)
        with self.assertRaises(WorkflowError): self.store.transition(case_id="CASE-102",target="approved",actor_id="bob",expected_version=1)
    def test_case_approval_requires_a_different_actor_and_cannot_be_bypassed(self):
        self.store.create_case(case_id="CASE-104",lifecycle="onboarding",requester_id="alice",summary="Demo")
        self.store.transition(case_id="CASE-104",target="pending_approval",actor_id="alice",expected_version=1)
        with self.assertRaises(WorkflowError):
            self.store.approve_case(case_id="CASE-104",approver_id="alice",expected_version=2)
        with self.assertRaises(WorkflowError):
            self.store.transition(case_id="CASE-104",target="approved",actor_id="bob",expected_version=2)
        approved=self.store.approve_case(case_id="CASE-104",approver_id="bob",expected_version=2)
        self.assertEqual(approved["status"],"approved")
        self.assertEqual(self.store.list_events("CASE-104")[-1]["actor_id"],"bob")

    def test_provider_approval_is_persisted_and_secret_payload_is_redacted(self):
        self.store.create_case(case_id="CASE-105",lifecycle="onboarding",requester_id="alice",summary="Demo")
        record=self.store.record_provider_approval(case_id="CASE-105",requester_id="alice",approver_id="bob",
            provider="github",operation="create_issue",payload={"title":"Demo","api_token":"secret"},
            fingerprint="fingerprint-demo")
        self.store.close()
        self.store=CaseStore(self.path)
        restored=self.store.get_provider_approval(record["approval_id"])
        self.assertEqual(restored["status"],"approved")
        self.assertEqual(restored["payload"]["api_token"],"[REDACTED]")
        self.assertEqual(restored["approver_id"],"bob")

    def test_provider_approval_must_belong_to_case_requester(self):
        self.store.create_case(case_id="CASE-106",lifecycle="onboarding",requester_id="alice",summary="Demo")
        with self.assertRaises(WorkflowError):
            self.store.record_provider_approval(case_id="CASE-106",requester_id="mallory",approver_id="bob",
                provider="github",operation="create_issue",payload={"title":"Demo"},fingerprint="fp")

    def test_secret_values_are_redacted_from_stored_request(self):
        case=self.store.create_case(case_id="CASE-103",lifecycle="onboarding",requester_id="alice",summary="Demo",request_data={"api_token":"must-not-persist","team":"IT"})
        self.assertEqual(case["request_data"]["api_token"],"[REDACTED]")
        self.assertEqual(case["request_data"]["team"],"IT")


    def test_request_data_must_be_an_object(self):
        with self.assertRaises(CaseStoreError):
            self.store.create_case(
                case_id="CASE-PAYLOAD-1", lifecycle="onboarding", requester_id="alice",
                summary="Invalid payload", request_data=["not", "an", "object"],
            )

    def test_request_data_is_bounded_after_secret_redaction(self):
        with self.assertRaises(CaseStoreError):
            self.store.create_case(
                case_id="CASE-PAYLOAD-2", lifecycle="onboarding", requester_id="alice",
                summary="Oversized payload", request_data={"description": "x" * (65 * 1024)},
            )
        self.assertEqual(self.store.list_cases(limit=500), [])

    def test_payload_size_limit_counts_utf8_bytes(self):
        case = self.store.create_case(
            case_id="CASE-PAYLOAD-3", lifecycle="onboarding", requester_id="alice",
            summary="Unicode payload", request_data={"department": "équipe"},
        )
        self.assertEqual(case["request_data"]["department"], "équipe")


    def test_provider_approval_expiry_revokes_and_audits_without_consuming(self):
        self.store.create_case(case_id="CASE-EXPIRY-1", lifecycle="onboarding",
                               requester_id="alice", summary="Approval expiry")
        approval = self.store.record_provider_approval(
            case_id="CASE-EXPIRY-1", requester_id="alice", approver_id="bob",
            provider="github", operation="create_issue", payload={"title": "Demo"},
            fingerprint="fingerprint-demo",
        )
        self.assertTrue(approval["expires_at"])
        self.store.connection.execute(
            "UPDATE provider_approvals SET expires_at=? WHERE approval_id=?",
            ("2000-01-01T00:00:00+00:00", approval["approval_id"]),
        )
        self.store.connection.commit()
        with self.assertRaisesRegex(CaseStoreError, "expired"):
            self.store.consume_provider_approval(
                approval["approval_id"], expected_fingerprint="fingerprint-demo",
            )
        self.assertEqual(self.store.get_provider_approval(approval["approval_id"])["status"], "revoked")
        self.assertEqual(self.store.list_events("CASE-EXPIRY-1")[-1]["event_type"],
                         "provider_action.approval_expired")

    def test_unused_provider_approval_can_be_revoked_once(self):
        self.store.create_case(case_id="CASE-REVOKE-1", lifecycle="onboarding",
                               requester_id="alice", summary="Approval revoke")
        approval = self.store.record_provider_approval(
            case_id="CASE-REVOKE-1", requester_id="alice", approver_id="bob",
            provider="github", operation="create_issue", payload={"title": "Demo"},
            fingerprint="fingerprint-demo",
        )
        revoked = self.store.revoke_provider_approval(approval["approval_id"], actor_id="admin")
        self.assertEqual(revoked["status"], "revoked")
        self.assertEqual(self.store.list_events("CASE-REVOKE-1")[-1]["actor_id"], "admin")
        with self.assertRaisesRegex(CaseStoreError, "no longer available"):
            self.store.consume_provider_approval(
                approval["approval_id"], expected_fingerprint="fingerprint-demo",
            )

    def test_legacy_provider_approval_schema_migrates_with_expiry(self):
        self.store.create_case(case_id="CASE-EXPIRY-MIGRATE", lifecycle="onboarding",
                               requester_id="alice", summary="Legacy approval")
        approval = self.store.record_provider_approval(
            case_id="CASE-EXPIRY-MIGRATE", requester_id="alice", approver_id="bob",
            provider="github", operation="create_issue", payload={"title": "Demo"},
            fingerprint="fingerprint-demo",
        )
        self.store.connection.execute("ALTER TABLE provider_approvals DROP COLUMN expires_at")
        self.store.connection.commit()
        self.store.close()
        self.store = CaseStore(self.path)
        migrated = self.store.get_provider_approval(approval["approval_id"])
        self.assertTrue(migrated["expires_at"])
        self.assertEqual(migrated["status"], "approved")

    def test_camel_case_credentials_are_redacted(self):
        case = self.store.create_case(
            case_id="CASE-KEYS-1", lifecycle="onboarding", requester_id="alice",
            summary="Secret-key conventions",
            request_data={"apiKey": "never-store", "privateKey": "never-store-either",
                          "department": "IT"},
        )
        self.assertEqual(case["request_data"]["apiKey"], "[REDACTED]")
        self.assertEqual(case["request_data"]["privateKey"], "[REDACTED]")
        self.assertEqual(case["request_data"]["department"], "IT")

    def test_event_history_returns_only_bounded_most_recent_events(self):
        self.store.create_case(case_id="CASE-EVENT-LIMIT", lifecycle="onboarding",
                               requester_id="alice", summary="Bounded event history")
        for index in range(205):
            self.store.connection.execute(
                "INSERT INTO case_events(case_id,event_type,actor_id,from_status,to_status,metadata_json,occurred_at) "
                "VALUES (?,?,?,?,?,?,?)",
                ("CASE-EVENT-LIMIT", "case.test_event", "tester", None, None,
                 "{}", f"2026-01-01T00:{index // 60:02d}:{index % 60:02d}+00:00"),
            )
        self.store.connection.commit()
        events = self.store.list_events("CASE-EVENT-LIMIT")
        self.assertEqual(len(events), 200)
        self.assertEqual(events, sorted(events, key=lambda event: event["event_id"]))
        self.assertEqual(events[0]["event_id"], 7)
        self.assertEqual(events[-1]["event_id"], 206)
        with self.assertRaisesRegex(CaseStoreError, "limit"):
            self.store.list_events("CASE-EVENT-LIMIT", limit=501)

    def test_case_request_data_rejects_non_standard_nan_values(self):
        with self.assertRaisesRegex(CaseStoreError, "valid JSON-compatible"):
            self.store.create_case(
                case_id="CASE-NAN-1", lifecycle="onboarding", requester_id="alice",
                summary="Reject NaN", request_data={"numeric": float("nan")},
            )

    def test_provider_approval_rejects_non_object_and_non_standard_payloads(self):
        self.store.create_case(case_id="CASE-NAN-2", lifecycle="onboarding",
                               requester_id="alice", summary="Approval JSON boundary")
        base = dict(case_id="CASE-NAN-2", requester_id="alice", approver_id="bob",
                    provider="github", operation="create_issue", fingerprint="fingerprint-demo")
        with self.assertRaisesRegex(CaseStoreError, "JSON object"):
            self.store.record_provider_approval(**base, payload=["not", "an", "object"])
        with self.assertRaisesRegex(CaseStoreError, "valid JSON-compatible"):
            self.store.record_provider_approval(**base, payload={"score": float("inf")})

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits are not portable to Windows")
    def test_new_case_database_and_parent_directory_are_private_by_default(self):
        import stat
        from pathlib import Path

        database = Path(self.temp.name) / "private" / "nested" / "cases.sqlite3"
        store = CaseStore(database)
        try:
            self.assertEqual(stat.S_IMODE(database.stat().st_mode) & 0o077, 0)
            self.assertEqual(stat.S_IMODE(database.parent.stat().st_mode) & 0o077, 0)
            self.assertEqual(store.database_path, str(database))
        finally:
            store.close()

if __name__ == "__main__":
    unittest.main()
