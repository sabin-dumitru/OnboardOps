"""Explicitly reset only the fixed synthetic sample cases used for presentations."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from onboardops.cases import CaseStore
from onboardops.demo_fixtures import SAMPLE_CASES, reset_sample_cases


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        default=os.environ.get("ONBOARDOPS_CASE_DB", str(project_root / "data" / "onboardops_cases.sqlite3")),
        help="Case database path (defaults to ONBOARDOPS_CASE_DB or the local demo database).",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required confirmation; deletes only the four fixed CASE-SAMPLE-* fixture IDs and their history.",
    )
    args = parser.parse_args()
    if not args.confirm:
        parser.error("refusing to reset sample cases without --confirm")
    store = CaseStore(args.database)
    try:
        removed = reset_sample_cases(store)
    finally:
        store.close()
    print(f"Removed {removed} sample fixture case(s). Operator-created cases were not selected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
