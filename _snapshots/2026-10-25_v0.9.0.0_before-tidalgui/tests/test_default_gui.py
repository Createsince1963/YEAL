"""Standing rule: Yeal always starts in the default GUI (YouTube browser visible), whatever was saved."""
import json
import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from yeal.core.settings import Settings


class DefaultGuiTests(unittest.TestCase):
    def _load(self, raw):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "settings.json"
            p.write_text(json.dumps(raw), encoding="utf-8")
            return Settings.load(p)

    def test_saved_off_is_ignored_at_start(self):
        self.assertTrue(self._load({"show_browser": False}).show_browser)

    def test_default_is_on(self):
        self.assertTrue(Settings().show_browser)
        self.assertTrue(self._load({}).show_browser)

    def test_broken_file_gives_default(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "settings.json"
            p.write_text("{not json", encoding="utf-8")
            self.assertTrue(Settings.load(p).show_browser)

    def test_other_settings_are_kept(self):
        st = self._load({"show_browser": False, "max_parallel": 3})
        self.assertEqual(st.max_parallel, 3)


if __name__ == "__main__":
    unittest.main()
