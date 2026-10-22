import json
import unittest
from pathlib import Path

from onboardops.core import (
    generate_checklist,
    load_templates,
    parse_request_file,
    render_inventory_csv,
    render_markdown,
    validate_request,
    write_text_no_overwrite,
)

ROOT = Path(__file__).resolve().parents[1]


class OnboardOpsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = load_templates(ROOT / "config" / "templates.json")
        cls.cases = json.loads((ROOT / "data" / "test_cases.json").read_text(encoding="utf-8"))
        cls.windows, cls.macos, cls.invalid = cls.cases

    def test_valid_windows_case(self):
        request = {k: v for k, v in self.windows.items() if k != "case_id"}
        self.assertEqual(validate_request(request), [])
        titles = [task["title"] for task in generate_checklist(request, self.templates)]
        self.assertTrue(any("Windows updates" in title for title in titles))
        self.assertTrue(any("BitLocker" in title for title in titles))
        self.assertTrue(any("Teams" in title for title in titles))
        self.assertTrue(any("Approved CRM group request" in title for title in titles))

    def test_valid_macos_case(self):
        request = {k: v for k, v in self.macos.items() if k != "case_id"}
        self.assertEqual(validate_request(request), [])
        titles = [task["title"] for task in generate_checklist(request, self.templates)]
        self.assertTrue(any("macOS updates" in title for title in titles))
        self.assertTrue(any("FileVault" in title for title in titles))
        self.assertTrue(any("Figma" in title for title in titles))
        self.assertFalse(any("BitLocker" in title for title in titles))

    def test_invalid_case_flags_bad_date_os_and_missing_hardware_data(self):
        request = {k: v for k, v in self.invalid.items() if k != "case_id"}
        findings = validate_request(request)
        errors = [f for f in findings if f["severity"] == "error"]
        self.assertTrue(any(f["field"] == "Start date" for f in errors))
        self.assertTrue(any(f["field"] == "Operating system" for f in errors))
        self.assertTrue(any(f["field"] == "Asset tag" for f in findings))
        self.assertTrue(any(f["field"] == "Applications" for f in findings))
        self.assertTrue(any(f["field"] == "Access requests" for f in findings))

    def test_duplicate_identifier_is_case_insensitive(self):
        request = {k: v for k, v in self.windows.items() if k != "case_id"}
        findings = validate_request(request, {request["employee_id"].lower()})
        self.assertTrue(any("already exists" in f["message"] for f in findings))

    def test_json_import_accepts_single_object_and_list_fields(self):
        payload = json.dumps({"employee_id": "DEMO-JSON-1", "accessories": ["monitor"], "applications": ["Browser"]})
        request = parse_request_file("request.json", payload)
        self.assertEqual(request["accessories"], ["monitor"])
        self.assertEqual(request["applications"], ["Browser"])

    def test_json_import_rejects_multiple_requests(self):
        with self.assertRaisesRegex(ValueError, "exactly one request"):
            parse_request_file("requests.json", '[{"employee_id":"A1"},{"employee_id":"A2"}]')

    def test_csv_import_splits_semicolon_fields_and_boolean(self):
        csv_text = (ROOT / "data" / "examples" / "windows_request.csv").read_text(encoding="utf-8")
        request = parse_request_file("windows_request.csv", csv_text)
        self.assertEqual(request["accessories"], ["monitor", "keyboard", "mouse", "dock"])
        self.assertEqual(request["applications"], ["Office suite", "Browser"])
        self.assertIs(request["laptop_required"], True)

    def test_csv_import_requires_exactly_one_data_row(self):
        with self.assertRaisesRegex(ValueError, "exactly one request row"):
            parse_request_file("two.csv", "employee_id\nDEMO-1\nDEMO-2\n")

    def test_non_utf8_import_is_a_clear_error(self):
        with self.assertRaisesRegex(ValueError, "UTF-8 encoded"):
            parse_request_file("request.json", b"\xff\xfe")

    def test_malformed_json_and_unsupported_extension_are_clear_errors(self):
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            parse_request_file("request.json", "{bad")
        with self.assertRaisesRegex(ValueError, "Unsupported file type"):
            parse_request_file("request.txt", "hello")

    def test_csv_invalid_boolean_is_flagged_not_silently_accepted(self):
        request = parse_request_file(
            "request.csv",
            "employee_id,employee_name,start_date,operating_system,laptop_required\nDEMO-BOOL-1,Example,2027-03-01,Windows,maybe\n",
        )
        findings = validate_request(request)
        self.assertTrue(any(f["field"] == "Laptop required" and f["severity"] == "error" for f in findings))

    def test_duplicate_task_sources_do_not_duplicate_task_ids(self):
        request = {k: v for k, v in self.windows.items() if k != "case_id"}
        request["accessories"] = ["dock", "dock"]
        tasks = generate_checklist(request, self.templates)
        ids = [task["id"] for task in tasks]
        self.assertEqual(len(ids), len(set(ids)))

    def test_role_specific_review_prompt_is_configurable_and_does_not_grant_access(self):
        request = {k: v for k, v in self.macos.items() if k != "case_id"}
        request["team"] = "Creative Operations"
        titles = [task["title"] for task in generate_checklist(request, self.templates)]
        self.assertTrue(any("creative tools" in title for title in titles))
        self.assertTrue(any("Verify approved access request" in title for title in titles))

    def test_multiple_software_requests_create_individual_tasks(self):
        request = {k: v for k, v in self.windows.items() if k != "case_id"}
        request["applications"] = ["Office suite", "Browser", "VPN client"]
        titles = [task["title"] for task in generate_checklist(request, self.templates)]
        for app in request["applications"]:
            self.assertTrue(any(app in title for title in titles))

    def test_duplicate_application_is_flagged(self):
        request = {k: v for k, v in self.windows.items() if k != "case_id"}
        request["applications"] = ["Browser", " browser "]
        findings = validate_request(request)
        self.assertTrue(any(f["field"] == "Applications" and "Duplicate" in f["message"] for f in findings))

    def test_csv_rejects_extra_values_and_duplicate_headers(self):
        with self.assertRaisesRegex(ValueError, "more values than header"):
            parse_request_file("bad.csv", "employee_id,employee_name\nDEMO-1,Example,extra\n")
        with self.assertRaisesRegex(ValueError, "duplicate column"):
            parse_request_file("bad.csv", "employee_id,employee_id\nDEMO-1,DEMO-2\n")

    def test_inventory_csv_neutralises_spreadsheet_formula_input(self):
        request = {k: v for k, v in self.windows.items() if k != "case_id"}
        request["employee_name"] = "=HYPERLINK(\"https://example.invalid\")"
        output = render_inventory_csv(request)
        self.assertIn("'=HYPERLINK", output)

    def test_output_writer_never_overwrites_existing_artifact(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "checklist.md"
            target.write_text("original", encoding="utf-8")
            actual = write_text_no_overwrite(target, "new")
            self.assertEqual(target.read_text(encoding="utf-8"), "original")
            self.assertEqual(actual.name, "checklist_2.md")
            self.assertEqual(actual.read_text(encoding="utf-8"), "new")

    def test_exports_contain_validation_and_inventory_status(self):
        request = {k: v for k, v in self.invalid.items() if k != "case_id"}
        findings = validate_request(request)
        markdown = render_markdown(request, generate_checklist(request, self.templates), findings)
        inventory = render_inventory_csv(request)
        self.assertIn("ERROR — Start date", markdown)
        self.assertIn("allocation_status", inventory)
        self.assertIn("Needs allocation / verification", inventory)
        self.assertIn("DEMO-BAD-2103", inventory)


if __name__ == "__main__":
    unittest.main(verbosity=2)
