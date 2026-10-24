"""Create a consistent, integrity-checked backup of the local OnboardOps case database."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from onboardops.database_backup import BackupError, backup_sqlite_database


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=os.environ.get("ONBOARDOPS_CASE_DB", "data/onboardops_cases.sqlite3"),
        help="SQLite database path (defaults to ONBOARDOPS_CASE_DB or the app's local database).",
    )
    parser.add_argument("--destination", required=True, help="New backup file path.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly replace an existing destination after the new backup passes integrity_check.",
    )
    args = parser.parse_args()
    try:
        destination = backup_sqlite_database(args.source, args.destination, overwrite=args.overwrite)
    except BackupError as exc:
        parser.error(str(exc))
    print(f"Backup created and verified: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
