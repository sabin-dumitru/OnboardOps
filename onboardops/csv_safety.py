"""Spreadsheet-safe helpers for CSV exports containing untrusted text."""
from __future__ import annotations

import re
from typing import Any, Mapping

_FORMULA_PREFIX = re.compile(r"^[\s]*[=+@-]")


def safe_csv_cell(value: Any) -> Any:
    """Prefix dangerous text cells so spreadsheet software treats them as text.

    Numeric values remain numeric. String values with leading whitespace followed by
    a formula marker, or beginning with spreadsheet control characters, are escaped
    with an apostrophe. This is a defensive export convention, not data validation.
    """
    if not isinstance(value, str):
        return value
    if value.startswith(("\t", "\r", "\n")) or _FORMULA_PREFIX.match(value):
        return "'" + value
    return value


def safe_csv_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copied CSV row with every untrusted string cell neutralised."""
    return {key: safe_csv_cell(value) for key, value in row.items()}
