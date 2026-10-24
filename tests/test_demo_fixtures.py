import os
import tempfile
import unittest

from onboardops.cases import CaseStore
from onboardops.demo_fixtures import SAMPLE_CASES, reset_sample_cases, seed_sample_cases


class DemoFixtureResetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = CaseStore(os.path.join(self.temp.name, "cases.sqlite3"))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_reset_removes_only_fixed_fixture_cases_and_history(self):
        self.assertEqual(seed_sample_cases(self.store), 4)
        self.store.create_case(
            case_id="CASE-USER-1001",
            lifecycle="onboarding",
            requester_id="alice",
            summary="Operator-created synthetic case",
            request_data={"synthetic": True},
        )
        self.assertEqual(reset_sample_cases(self.store), 4)
        self.assertEqual(reset_sample_cases(self.store), 0)
        remaining = {case["case_id"] for case in self.store.list_cases(limit=500)}
        self.assertEqual(remaining, {"CASE-USER-1001"})
        self.assertEqual(self.store.list_events("CASE-USER-1001")[0]["event_type"], "case.created")
        for case_id, _, _ in SAMPLE_CASES:
            self.assertNotIn(case_id, remaining)
            self.assertEqual(
                self.store.connection.execute(
                    "SELECT COUNT(*) FROM case_events WHERE case_id=?", (case_id,)
                ).fetchone()[0],
                0,
            )

    def test_reset_is_transactional_and_does_not_require_fixture_seeding(self):
        self.store.create_case(
            case_id="CASE-USER-1002", lifecycle="onboarding",
            requester_id="alice", summary="Keep this case",
        )
        self.assertEqual(reset_sample_cases(self.store), 0)
        self.assertEqual(self.store.get_case("CASE-USER-1002")["summary"], "Keep this case")


if __name__ == "__main__":
    unittest.main()
