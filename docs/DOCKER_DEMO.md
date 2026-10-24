# Run OnboardOps with Docker

This is the simplest cross-platform route if Docker Desktop (Windows/macOS) or Docker Engine (Linux) is installed. It runs the synthetic demo locally and does not need provider credentials.

1. Download or clone the repository.
2. From the repository folder, run:

   ```sh
   docker compose up --build
   ```

3. Open http://localhost:8501 in your browser.
4. Use **Load sample request** on the main page. Open **Case management** to create a synthetic case, restart the container, and confirm the case is still present.
5. Use **Integration Lab** to view configuration readiness and offline payload previews. No live writes are exposed from the UI.

Stop the app with `Ctrl+C`; use `docker compose down` to stop and remove the container. To permanently erase the saved demo case database and generated files too, run `docker compose down --volumes`. Docker-managed named volumes preserve local case records and generated files across container restarts. These volumes stay on your computer and do not require host-folder write permissions.

The container runs as a non-root user with a read-only root filesystem, dropped Linux capabilities, and `no-new-privileges`; only the named state/output volumes and temporary filesystems are writable. The Compose configuration is validated in CI.

The service binds only to `127.0.0.1` on the host. Do not change this to a public interface or expose the app to a network: the default identity is a local demo identity and is not suitable for shared or production access. Use synthetic data only.

To run the checks without Docker, follow the README quick start and test commands.


## Repeatable presentation reset

The **Load synthetic sample cases** button is intentionally additive: it never overwrites existing fixture history. To reset only the four fixed sample cases before a fresh presentation, stop the app and run the command against the same database path:

```sh
docker compose stop onboardops
docker compose run --rm onboardops python scripts/reset_demo_cases.py --confirm
docker compose up -d onboardops
```

The command requires `--confirm` and deletes only the fixed `CASE-SAMPLE-1001` through `CASE-SAMPLE-1004` fixture records and their case-event/approval rows. Other cases are preserved. It does not clear the whole database or reset provider action ledgers. In a Python environment, run `python scripts/reset_demo_cases.py --confirm` with `ONBOARDOPS_CASE_DB` set to the intended demo database. Use synthetic data only.
