import sqlite3
import tempfile
import unittest
from pathlib import Path

import database
from reports import build_report_text


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = database.DB_NAME
        database.DB_NAME = str(Path(self.temp_dir.name) / "tracker.db")
        database.init_db()

    def tearDown(self):
        database.DB_NAME = self.original_db
        self.temp_dir.cleanup()

    def test_build_report_text_shows_only_requested_columns(self):
        database.insert_entry(
            "Projeto X",
            "Descrição X",
            "2026-06-01T08:00:00",
            "2026-06-01T09:00:00",
            3600,
        )

        report = build_report_text()

        self.assertIn("[1] Projeto: Projeto X", report)
        self.assertIn("Descrição: Descrição X", report)
        self.assertIn("Data: 2026-06-01", report)
        self.assertIn("Duração: 01:00:00", report)
        self.assertNotIn("Início:", report)
        self.assertNotIn("Fim:", report)


if __name__ == "__main__":
    unittest.main()
