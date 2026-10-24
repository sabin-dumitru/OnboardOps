import unittest

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


if __name__ == "__main__":
    unittest.main()
