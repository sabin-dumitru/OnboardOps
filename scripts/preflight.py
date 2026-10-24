"""Read-only preflight checks for a local OnboardOps demo or deployment rehearsal."""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Mapping


def _check(name: str, ok: bool, message: str, *, warning: bool = False) -> dict[str, Any]:
    return {"name": name, "ok": ok, "warning": warning, "message": message}


def run_preflight(root: str | Path | None = None,
                  environ: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    """Return checks without printing configuration values or making network calls."""
    project_root = Path(root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    env = os.environ if environ is None else environ
    results: list[dict[str, Any]] = []

    for relative, expected in (
        ("config/templates.json", dict),
        ("data/sample_requests.json", list),
    ):
        path = project_root / relative
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
            valid = isinstance(parsed, expected)
        except (OSError, json.JSONDecodeError):
            valid = False
        results.append(_check(
            f"Project data: {relative}",
            valid,
            "present and valid" if valid else "missing, invalid JSON, or unexpected top-level shape",
        ))

    auth_mode = str(env.get("ONBOARDOPS_AUTH_MODE", "demo")).strip().casefold()
    if auth_mode == "demo":
        results.append(_check(
            "Authentication mode",
            True,
            "demo identity is active; synthetic data only and no production provider writes",
            warning=True,
        ))
    elif auth_mode == "trusted_proxy":
        trusted = str(env.get("ONBOARDOPS_TRUSTED_AUTH_PROXY", "")).strip().casefold() == "true"
        results.append(_check(
            "Authentication mode",
            trusted,
            "trusted-proxy flag is enabled; verify header stripping, network isolation, and role mappings"
            if trusted else "trusted_proxy mode requires ONBOARDOPS_TRUSTED_AUTH_PROXY=true",
            warning=trusted,
        ))
    else:
        results.append(_check(
            "Authentication mode", False,
            "unknown mode; expected demo or trusted_proxy",
        ))

    database_value = str(env.get("ONBOARDOPS_CASE_DB", project_root / "data" / "onboardops_cases.sqlite3"))
    database_path = Path(database_value).expanduser()
    if not database_path.is_absolute():
        database_path = project_root / database_path
    database_parent = database_path.parent
    db_ready = database_parent.is_dir() and os.access(database_parent, os.W_OK)
    results.append(_check(
        "Case database location",
        db_ready,
        "parent directory exists and is writable" if db_ready else
        "database parent directory is missing or not writable",
    ))
    if database_path.is_file() and os.name == "posix":
        mode = stat.S_IMODE(database_path.stat().st_mode)
        private = not bool(mode & 0o077)
        results.append(_check(
            "Case database file permissions",
            True,
            "existing database file is private to its owner" if private else
            "existing database is readable or writable by group/others; restrict it with chmod 600",
            warning=not private,
        ))

    output_value = str(env.get("ONBOARDOPS_OUTPUT_DIR", project_root / "outputs"))
    output_path = Path(output_value).expanduser()
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_ready = output_path.is_dir() and os.access(output_path, os.W_OK)
    results.append(_check(
        "Output directory",
        output_ready,
        "directory exists and is writable" if output_ready else
        "output directory is missing or not writable",
    ))
    return results


def main() -> int:
    checks = run_preflight()
    failed = False
    for item in checks:
        if item["warning"]:
            status = "WARN"
        elif item["ok"]:
            status = "PASS"
        else:
            status = "FAIL"
            failed = True
        print(f"[{status}] {item['name']}: {item['message']}")
    print("Preflight failed." if failed else "Preflight checks completed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
