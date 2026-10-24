import unittest
from pathlib import Path

from onboardops.ui_accessibility import accessibility_styles


class AccessibilityStyleTests(unittest.TestCase):
    def test_shared_styles_include_visible_focus_and_forced_colour_support(self):
        css = accessibility_styles()
        self.assertIn(":focus-visible", css)
        self.assertIn("outline: 3px solid #8ab4ff", css)
        self.assertIn("@media (forced-colors: active)", css)
        self.assertIn("outline: 2px solid Highlight", css)

    def test_shared_styles_respect_reduced_motion_preferences(self):
        css = accessibility_styles()
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("animation-duration: 0.01ms", css)
        self.assertIn("transition-duration: 0.01ms", css)

    def test_primary_pages_use_semantic_h1_titles(self):
        root = Path(__file__).resolve().parents[1]
        expected = {
            "pages/2_Integration_Lab.py": "Integration Lab",
            "pages/3_Case_Management.py": "Case management",
            "pages/4_Operations_Report.py": "Operations report",
        }
        for relative_path, title in expected.items():
            with self.subTest(page=relative_path):
                source = (root / relative_path).read_text(encoding="utf-8")
                self.assertIn(f'<h1 class="ops-title">{title}</h1>', source)
                self.assertNotIn(f'<div class="ops-title">{title}</div>', source)


if __name__ == "__main__":
    unittest.main()
