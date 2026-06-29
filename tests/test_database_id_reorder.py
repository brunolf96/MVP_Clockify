import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

import database

class DatabaseIdReorderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = database.DB_NAME
        database.DB_NAME = str(Path(self.temp_dir.name) / "tracker.db")
        database.init_db()

    def tearDown(self):
        database.DB_NAME = self.original_db
        self.temp_dir.cleanup()

    def test_ids_renumbered_after_delete(self):
        database.insert_entry("Projeto A", "Desc A", "2026-01-01T08:00:00", "2026-01-01T09:00:00", 3600)
        database.insert_entry("Projeto B", "Desc B", "2026-01-02T08:00:00", "2026-01-02T09:00:00", 3600)
        database.insert_entry("Projeto C", "Desc C", "2026-01-03T08:00:00", "2026-01-03T09:00:00", 3600)

        database.delete_entry(2)

        conn = sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, start_time FROM time_entries ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(rows, [
            (1, "2026-01-01T08:00:00"),
            (2, "2026-01-03T08:00:00")
        ])

    def test_ids_restart_at_one_after_delete_all(self):
        database.insert_entry("Projeto A", "Desc A", "2026-01-01T08:00:00", "2026-01-01T09:00:00", 3600)
        database.delete_entry(1)

        database.insert_entry("Projeto B", "Desc B", "2026-01-02T08:00:00", "2026-01-02T09:00:00", 3600)

        conn = sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, start_time FROM time_entries ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(rows, [
            (1, "2026-01-02T08:00:00")
        ])

    def test_ids_renumbered_after_edit_start_time(self):
        database.insert_entry("Projeto A", "Desc A", "2026-01-01T08:00:00", "2026-01-01T09:00:00", 3600)
        database.insert_entry("Projeto B", "Desc B", "2026-01-02T08:00:00", "2026-01-02T09:00:00", 3600)

        database.update_entry(1, "Projeto A", "Desc A", "2026-01-03T08:00:00", "2026-01-03T09:00:00", 3600)

        conn = sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, start_time FROM time_entries ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(rows, [
            (1, "2026-01-02T08:00:00"),
            (2, "2026-01-03T08:00:00")
        ])

if __name__ == "__main__":
    unittest.main()
