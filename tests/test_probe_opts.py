import sys
import types
import unittest

import _path  # noqa: F401
from yeal.core import engine


def _fake_cookies(fail_for):
    """Install a fake `yt_dlp.cookies` whose reader fails for the browsers in `fail_for`; returns the call log."""
    calls = []

    def extract(name):
        calls.append(name)
        if name in fail_for:
            raise RuntimeError("could not copy cookie database")

    pkg = types.ModuleType("yt_dlp")
    mod = types.ModuleType("yt_dlp.cookies")
    mod.extract_cookies_from_browser = extract
    pkg.cookies = mod
    sys.modules["yt_dlp"], sys.modules["yt_dlp.cookies"] = pkg, mod
    return calls


class ProbeOptsTest(unittest.TestCase):
    def setUp(self):
        self._saved = {k: sys.modules.get(k) for k in ("yt_dlp", "yt_dlp.cookies")}
        engine._UNREADABLE_BROWSERS.clear()
        engine._READABLE_BROWSERS.clear()

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        engine._UNREADABLE_BROWSERS.clear()
        engine._READABLE_BROWSERS.clear()

    def test_without_browser_login_options_are_unchanged(self):
        opts = {"quiet": True}
        self.assertIs(engine.probe_opts(opts), opts)

    def test_unreadable_browser_is_dropped_and_asked_only_once(self):
        calls = _fake_cookies({"chrome"})
        opts = {"quiet": True, "cookiesfrombrowser": ("chrome",)}
        out = engine.probe_opts(opts)
        self.assertNotIn("cookiesfrombrowser", out)
        self.assertIn("cookiesfrombrowser", opts, "the caller's dict must not be changed")
        engine.probe_opts(opts)
        self.assertEqual(calls, ["chrome"])

    def test_readable_browser_is_kept_and_asked_only_once(self):
        calls = _fake_cookies(set())
        opts = {"cookiesfrombrowser": ("firefox",)}
        self.assertIs(engine.probe_opts(opts), opts)
        engine.probe_opts(opts)
        self.assertEqual(calls, ["firefox"])


if __name__ == "__main__":
    unittest.main()
