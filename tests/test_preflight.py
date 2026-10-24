import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.preflight import run_preflight


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "config").mkdir()
        (self.root / "data").mkdir()
        (self.root / "outputs").mkdir()
        (self.root / "config" / "templates.json").write_text("{}", encoding="utf-8")
        (self.root / "data" / "sample_requests.json").write_text("[]", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_local_demo_preflight_warns_without_revealing_secrets(self):
        checks = run_preflight(self.root, {
            "ONBOARDOPS_AUTH_MODE": "demo",
            "ONBOARDOPS_CASE_DB": str(self.root / "data" / "cases.sqlite3"),
            "ONBOARDOPS_OUTPUT_DIR": str(self.root / "outputs"),
            "ONBOARDOPS_GITHUB_TOKEN": "never-print-this",
        })
        self.assertTrue(all(item["ok"] for item in checks))
        auth = next(item for item in checks if item["name"] == "Authentication mode")
        self.assertTrue(auth["warning"])
        rendered = repr(checks)
        self.assertNotIn("never-print-this", rendered)

    def test_unknown_auth_mode_fails_preflight(self):
        checks = run_preflight(self.root, {"ONBOARDOPS_AUTH_MODE": "typo"})
        auth = next(item for item in checks if item["name"] == "Authentication mode")
        self.assertFalse(auth["ok"])

    def test_trusted_proxy_mode_requires_explicit_flag(self):
        checks = run_preflight(self.root, {"ONBOARDOPS_AUTH_MODE": "trusted_proxy"})
        auth = next(item for item in checks if item["name"] == "Authentication mode")
        self.assertFalse(auth["ok"])

    def test_missing_project_data_and_output_path_are_reported(self):
        (self.root / "config" / "templates.json").write_text("{", encoding="utf-8")
        (self.root / "outputs").rmdir()
        checks = run_preflight(self.root, {"ONBOARDOPS_AUTH_MODE": "demo"})
        by_name = {item["name"]: item for item in checks}
        self.assertFalse(by_name["Project data: config/templates.json"]["ok"])
        self.assertFalse(by_name["Output directory"]["ok"])


    @unittest.skipUnless(os.name == "posix", "POSIX permission bits are not portable to Windows")
    def test_preflight_warns_about_existing_group_readable_database(self):
        database = self.root / "data" / "cases.sqlite3"
        database.write_text("synthetic placeholder", encoding="utf-8")
        database.chmod(0o644)
        checks = run_preflight(self.root, {
            "ONBOARDOPS_AUTH_MODE": "demo",
            "ONBOARDOPS_CASE_DB": str(database),
            "ONBOARDOPS_OUTPUT_DIR": str(self.root / "outputs"),
        })
        permissions = next(item for item in checks if item["name"] == "Case database file permissions")
        self.assertTrue(permissions["ok"])
        self.assertTrue(permissions["warning"])
        self.assertNotIn(str(database), permissions["message"])

    def test_preflight_checks_existing_case_database_read_only(self):
        database = self.root / "data" / "cases.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("CREATE TABLE cases (case_id TEXT PRIMARY KEY)")
            connection.execute("CREATE TABLE case_events (event_id INTEGER PRIMARY KEY)")
            connection.commit()
        checks = run_preflight(self.root, {
            "ONBOARDOPS_AUTH_MODE": "demo",
            "ONBOARDOPS_CASE_DB": str(database),
            "ONBOARDOPS_OUTPUT_DIR": str(self.root / "outputs"),
        })
        integrity = next(item for item in checks if item["name"] == "Case database integrity")
        self.assertTrue(integrity["ok"])
        self.assertFalse(integrity["warning"])

    def test_preflight_reports_corrupt_database_without_echoing_path(self):
        database = self.root / "data" / "cases.sqlite3"
        database.write_text("not a sqlite database", encoding="utf-8")
        checks = run_preflight(self.root, {
            "ONBOARDOPS_AUTH_MODE": "demo",
            "ONBOARDOPS_CASE_DB": str(database),
            "ONBOARDOPS_OUTPUT_DIR": str(self.root / "outputs"),
        })
        integrity = next(item for item in checks if item["name"] == "Case database integrity")
        self.assertFalse(integrity["ok"])
        self.assertNotIn(str(database), integrity["message"])
        self.assertNotIn(str(self.root), integrity["message"])

    def test_preflight_warns_for_empty_database_file(self):
        database = self.root / "data" / "cases.sqlite3"
        database.touch()
        checks = run_preflight(self.root, {
            "ONBOARDOPS_AUTH_MODE": "demo",
            "ONBOARDOPS_CASE_DB": str(database),
            "ONBOARDOPS_OUTPUT_DIR": str(self.root / "outputs"),
        })
        integrity = next(item for item in checks if item["name"] == "Case database integrity")
        self.assertTrue(integrity["ok"])
        self.assertTrue(integrity["warning"])

if __name__ == "__main__":
    unittest.main()
