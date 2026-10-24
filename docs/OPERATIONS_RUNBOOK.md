# Operator runbook

**Scope:** local synthetic demo and pre-production rehearsal. This is not a production incident-response plan and does not authorise live provider writes.

## Routine start and health check

1. Confirm the environment is intended for synthetic/demo data. Do not load employee records or production credentials.
2. Start with `docker compose up --build -d` or the Python quick-start in the README.
3. Confirm the Streamlit health endpoint responds at `http://127.0.0.1:8501/_stcore/health` and open the app in a local browser.
4. In **Case management**, load sample cases and verify that the case list, status history, triage fields, and approval queue render.
5. In **Operations Report**, confirm the report loads and exports contain only expected operational fields.
6. Run the offline checks before a demonstration or code change:

   ```sh
   python -m unittest discover -s tests -v
   python -m compileall -q app.py onboardops tests scripts
   python scripts/demo.py
   python scripts/integration_demo.py
   ```

   These commands use synthetic data and mocked/offline provider workflows. They do not validate live tenant access.

## Safe shutdown

- Stop the app with `docker compose down` or Ctrl+C for a local Python process.
- `docker compose down` retains named volumes by default. Do not use `docker compose down -v` unless intentionally destroying demo state.
- Keep database files and exported packets private; exports can contain request details.

## Backup and restore

Create an integrity-checked online backup:

```sh
python scripts/backup_cases.py --destination backups/cases-YYYY-MM-DD.sqlite3
```

The source defaults to `ONBOARDOPS_CASE_DB` or `data/onboardops_cases.sqlite3`. The helper refuses to overwrite an existing destination unless `--overwrite` is explicit.

To restore a local case database:

1. Stop Streamlit or the Compose service.
2. Copy the current database to a separate incident-preservation path; do not delete it.
3. Confirm the intended backup file is the one to restore and that it passes SQLite `PRAGMA integrity_check`.
4. Replace the configured case database with the verified backup, preserving filesystem permissions.
5. Start the app and check case counts, selected histories, and a sample export.
6. Record the recovery point and any data created after the backup that may be missing.

This is a manual local recovery procedure. It has not been tested as a complete disaster-recovery exercise, and it does not automatically back up a separately configured provider action ledger or output volume.

## Provider write outcome is unknown

A timeout or upstream server error can occur after a provider accepted a POST. Never retry blindly.

1. Stop any automated/manual retry attempts.
2. Preserve the local action/approval identifiers and redacted error information.
3. Query the provider through an authorised read-only path using a stable external identifier or payload-specific search.
4. If the remote action exists, reconcile the local record to the confirmed outcome through an approved operational procedure.
5. If the remote outcome cannot be determined, keep the case/action flagged for manual reconciliation; do not manufacture a success or failure.
6. Record the resolution and the evidence used.

The current demo workflow records ambiguous outcomes as `unknown`. It does not include a full provider-specific reconciliation engine.

## Suspected credential exposure

1. Treat the credential as compromised; do not paste it into issues, chat, case notes, or logs.
2. Revoke or rotate it in the provider's own control plane.
3. Review provider access logs for unexpected use and narrow scopes/permissions as appropriate.
4. Inspect repository history, workflow logs, case database, exported files, and local environment files for exposure. Removing a value from the latest commit does not remove it from history.
5. Notify the appropriate system owner and preserve relevant evidence without copying secrets into the incident record.
6. Re-run tests and review permissions before issuing a replacement credential.

## Suspected case database corruption or unexpected edits

1. Stop writes and preserve a copy of the database and any associated WAL/SHM files before attempting repair.
2. Work on a copy; run `PRAGMA integrity_check` and capture the result.
3. Compare records against a known-good backup and available case-event history.
4. Do not describe local audit history as tamper-proof. Administrators with file access can alter the database.
5. Restore only from a verified backup and document the recovery point, lost changes, and follow-up action.

## Access or configuration problem

- Missing or unrecognised identity in trusted-proxy mode should fail closed. Verify proxy authentication, header stripping/overwriting, role mapping, TLS, and network isolation; never bypass the check to get a demo working.
- Environment variables being present means only that configuration values exist; it does not prove the provider credentials or permissions work.
- Do not expose the Streamlit demo directly to untrusted networks. Live provider writes remain disabled in the UI.

## Escalation and evidence

For a real company deployment, define named incident owners, contact paths, severity levels, data-retention rules, provider-specific reconciliation steps, audit-log retention, and tested recovery objectives before launch. Preserve timestamps, case IDs, action/approval IDs, redacted errors, and the steps taken. Never preserve raw tokens or unnecessary employee data as incident evidence.
