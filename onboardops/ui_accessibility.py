"""Small, shared accessibility styles for Streamlit pages.

These styles supplement native controls; they do not replace keyboard or screen-reader
testing in a real browser.
"""


def accessibility_styles() -> str:
    """Return shared visible-focus, forced-colour, and reduced-motion CSS."""
    return """
<style>
:where(button, a, input, textarea, select, [role="button"], [role="tab"],
       [role="combobox"], [tabindex]):focus-visible {
    outline: 3px solid #8ab4ff !important;
    outline-offset: 3px !important;
    box-shadow: 0 0 0 2px #0c1525 !important;
}
@media (forced-colors: active) {
    :where(button, a, input, textarea, select, [role="button"], [role="tab"],
           [role="combobox"], [tabindex]):focus-visible {
        outline: 2px solid Highlight !important;
        box-shadow: none !important;
    }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}
</style>
"""
