"""Consistent SQLite backup helper for local case-store files."""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
import tempfile
from pathlib import Path


class BackupError(ValueError):
    """Raised when a database backup cannot be safely completed."""


def backup_sqlite_database(
    source: str | Path,
    destination: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Create and integrity-check a consistent backup without copying live DB files.

    SQLite's online backup API includes committed WAL content and avoids the
    inconsistency risks of copying only the main database file while it is open.
    Existing backups are preserved unless overwrite=True is explicit.
    """
    source_path = Path(source).expanduser().resolve()
    destination_path = Path(destination).expanduser().resolve()

    if source_path == destination_path:
        raise BackupError("Source and destination must be different paths.")
    if not source_path.is_file():
        raise BackupError("Source database does not exist or is not a file.")
    if destination_path.exists() and not overwrite:
        raise BackupError("Destination already exists; choose a new path or explicitly allow overwrite.")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination_path.name}.",
            suffix=".tmp",
            dir=destination_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        source_uri = f"{source_path.as_uri()}?mode=ro"
        with closing(sqlite3.connect(source_uri, uri=True, timeout=10)) as source_db:
            with closing(sqlite3.connect(temporary_path, timeout=10)) as backup_db:
                source_db.backup(backup_db)
                result = backup_db.execute("PRAGMA integrity_check").fetchone()
                if not result or result[0] != "ok":
                    raise BackupError("SQLite integrity check failed for the backup.")

        if overwrite:
            os.replace(temporary_path, destination_path)
        else:
            # Hard-link creation is atomic and refuses to replace an existing file.
            os.link(temporary_path, destination_path)
            temporary_path.unlink()
        return destination_path
    except BackupError:
        raise
    except FileExistsError as exc:
        raise BackupError("Destination already exists; choose a new path or explicitly allow overwrite.") from exc
    except (OSError, sqlite3.Error) as exc:
        raise BackupError("Database backup failed; the original database was not modified.") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
