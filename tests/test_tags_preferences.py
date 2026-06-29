import json
import tempfile
import unittest
from pathlib import Path

from preferences import load_tags, save_tags


class TagsPreferencesTests(unittest.TestCase):
    def test_load_tags_returns_empty_when_file_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tags.json"
            self.assertEqual(load_tags(path), [])

    def test_save_and_load_tags_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tags.json"
            tags = ["Tag1", "Tag2"]

            save_tags(tags, path)
            loaded = load_tags(path)

            self.assertEqual(loaded, tags)

            with path.open("r", encoding="utf-8") as handle:
                self.assertEqual(json.load(handle), tags)

    def test_save_tags_filters_invalid_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tags.json"
            tags = ["Tag1", "", "  ", None, "Tag1", "Tag2"]

            save_tags(tags, path)
            loaded = load_tags(path)

            self.assertEqual(loaded, ["Tag1", "Tag2"])


if __name__ == "__main__":
    unittest.main()
