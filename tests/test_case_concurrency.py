import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from onboardops.cases import CaseStore, CaseStoreError


class ConcurrentCaseUpdateTests(unittest.TestCase):
    def test_only_one_stale_concurrent_transition_commits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = os.path.join(temp_dir, "cases.sqlite3")
            initial = CaseStore(database)
            initial.create_case(
                case_id="CASE-RACE-1", lifecycle="onboarding",
                requester_id="alice", summary="Concurrent update test",
            )
            initial.close()

            barrier = threading.Barrier(2)

            def attempt(target):
                store = CaseStore(database)
                try:
                    barrier.wait(timeout=5)
                    return ("success", store.transition(
                        case_id="CASE-RACE-1", target=target, actor_id=f"worker-{target}",
                        expected_version=1,
                    )["status"])
                except CaseStoreError as exc:
                    return ("rejected", str(exc))
                finally:
                    store.close()

            with ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = list(executor.map(attempt, ("pending_approval", "cancelled")))

            self.assertEqual(sum(kind == "success" for kind, _ in outcomes), 1, outcomes)
            rejected = [detail for kind, detail in outcomes if kind == "rejected"]
            self.assertEqual(len(rejected), 1, outcomes)
            self.assertIn("changed in another session", rejected[0])

            verify = CaseStore(database)
            try:
                case = verify.get_case("CASE-RACE-1")
                self.assertEqual(case["version"], 2)
                self.assertIn(case["status"], {"pending_approval", "cancelled"})
                events = verify.list_events("CASE-RACE-1")
                self.assertEqual(len(events), 2)
                self.assertEqual(events[-1]["to_status"], case["status"])
            finally:
                verify.close()


if __name__ == "__main__":
    unittest.main()
