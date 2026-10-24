import sqlite3
import tempfile
from contextlib import closing
import unittest
from pathlib import Path

from onboardops.database_backup import BackupError, backup_sqlite_database


class DatabaseBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "cases.sqlite3"
        with closing(sqlite3.connect(self.source)) as connection:
            connection.execute("CREATE TABLE cases (case_id TEXT PRIMARY KEY, summary TEXT NOT NULL)")
            connection.execute("INSERT INTO cases VALUES (?, ?)", ("CASE-DEMO-1", "Synthetic case"))
            connection.commit()

    def tearDown(self):
        self.temp.cleanup()

    def test_backup_contains_committed_data_and_passes_integrity_check(self):
        destination = backup_sqlite_database(self.source, self.root / "backups" / "snapshot.sqlite3")
        self.assertTrue(destination.is_file())
        with closing(sqlite3.connect(destination)) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(
                connection.execute("SELECT summary FROM cases WHERE case_id='CASE-DEMO-1'").fetchone()[0],
                "Synthetic case",
            )

    def test_existing_destination_is_not_overwritten_by_default(self):
        destination = self.root / "snapshot.sqlite3"
        destination.write_bytes(b"preserve this file")
        with self.assertRaises(BackupError):
            backup_sqlite_database(self.source, destination)
        self.assertEqual(destination.read_bytes(), b"preserve this file")

    def test_overwrite_must_be_explicit(self):
        destination = self.root / "snapshot.sqlite3"
        destination.write_bytes(b"old backup")
        backup_sqlite_database(self.source, destination, overwrite=True)
        with closing(sqlite3.connect(destination)) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_source_and_destination_must_differ(self):
        with self.assertRaises(BackupError):
            backup_sqlite_database(self.source, self.source)

    def test_missing_source_fails_without_creating_destination(self):
        destination = self.root / "should-not-exist.sqlite3"
        with self.assertRaises(BackupError):
            backup_sqlite_database(self.root / "missing.sqlite3", destination)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
