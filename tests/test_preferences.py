import json
import tempfile
import unittest
from pathlib import Path

from preferences import (
    DEFAULT_VISIBLE_COLUMNS,
    load_visible_columns,
    save_visible_columns,
)


class PreferencesTests(unittest.TestCase):
    def test_load_visible_columns_returns_defaults_when_file_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "preferences.json"
            self.assertEqual(load_visible_columns(path), DEFAULT_VISIBLE_COLUMNS)

    def test_save_and_load_visible_columns_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "preferences.json"
            selected = ["Projeto", "Início", "Duração"]

            save_visible_columns(selected, path)
            loaded = load_visible_columns(path)

            self.assertEqual(loaded, selected)

            with path.open("r", encoding="utf-8") as handle:
                self.assertEqual(json.load(handle), selected)


if __name__ == "__main__":
    unittest.main()
