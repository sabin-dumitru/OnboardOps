import unittest

from onboardops.csv_safety import safe_csv_cell, safe_csv_row


class CsvSafetyTests(unittest.TestCase):
    def test_formula_prefixes_are_escaped(self):
        for value in ("=1+1", "+SUM(A1:A2)", "-cmd|' /C calc'!A0", "@SUM(A1)", "  =HYPERLINK(\"https://example.invalid\")"):
            with self.subTest(value=value):
                self.assertEqual(safe_csv_cell(value), "'" + value)

    def test_leading_control_characters_are_escaped(self):
        for value in ("\t=1+1", "\r=1+1", "\n=1+1"):
            with self.subTest(value=repr(value)):
                self.assertEqual(safe_csv_cell(value), "'" + value)

    def test_regular_text_and_numeric_values_are_preserved(self):
        self.assertEqual(safe_csv_cell("CASE-100"), "CASE-100")
        self.assertEqual(safe_csv_cell("Alice Example"), "Alice Example")
        self.assertEqual(safe_csv_cell(-2.5), -2.5)
        self.assertEqual(safe_csv_cell(0), 0)
        self.assertIsNone(safe_csv_cell(None))

    def test_row_is_copied_and_each_text_cell_is_sanitized(self):
        row = {"case_id": "=cmd", "age_days": 3.5, "summary": "Synthetic"}
        safe = safe_csv_row(row)
        self.assertEqual(safe, {"case_id": "'=cmd", "age_days": 3.5, "summary": "Synthetic"})
        self.assertEqual(row["case_id"], "=cmd")


if __name__ == "__main__":
    unittest.main()
