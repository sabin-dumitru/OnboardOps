import json
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
