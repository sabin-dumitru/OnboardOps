"""Shared secure defaults for local SQLite database paths."""
from __future__ import annotations

import os
from pathlib import Path


def prepare_sqlite_path(database_path: str | Path) -> str:
    """Expand user paths and privately create a new local SQLite file if needed.

    Existing file permissions are deliberately not changed automatically. Callers
    can use the environment preflight to detect overly broad POSIX permissions.
    """
    raw_path = str(database_path)
    if raw_path == ":memory:":
        return raw_path

    expanded_path = Path(raw_path).expanduser()
    missing_parents = []
    parent = expanded_path.parent
    while not parent.exists():
        missing_parents.append(parent)
        parent = parent.parent
    for directory in reversed(missing_parents):
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError:
            if not directory.is_dir():
                raise

    try:
        descriptor = os.open(
            str(expanded_path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
    except FileExistsError:
        pass
    else:
        os.close(descriptor)
    return str(expanded_path)
