"""Headless Streamlit smoke tests for the pages used in the presentation."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PRESENTATION_PAGES = (
    "app.py",
    "pages/2_Integration_Lab.py",
    "pages/3_Case_Management.py",
    "pages/4_Operations_Report.py",
)


class StreamlitPageSmokeTests(unittest.TestCase):
    def test_presentation_pages_render_without_uncaught_exceptions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            environment = {
                "ONBOARDOPS_AUTH_MODE": "demo",
                "ONBOARDOPS_CASE_DB": str(root / "state" / "cases.sqlite3"),
                "ONBOARDOPS_OUTPUT_DIR": str(root / "outputs"),
            }
            (root / "state").mkdir()
            (root / "outputs").mkdir()
            with patch.dict(os.environ, environment, clear=False):
                for relative_path in PRESENTATION_PAGES:
                    with self.subTest(page=relative_path):
                        app = AppTest.from_file(str(ROOT / relative_path), default_timeout=20).run()
                        self.assertEqual(
                            len(app.exception),
                            0,
                            msg="; ".join(str(item.message) for item in app.exception),
                        )


if __name__ == "__main__":
    unittest.main()
