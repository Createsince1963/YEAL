"""Login pack: logins in one file encrypted with its own password (core/loginpack.py) and the backend export / import."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import _path  # noqa: F401
from yeal.core import loginpack  # noqa: E402

try:
    from PySide6.QtGui import QGuiApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

from test_core import FakeYDL, make_ctx  # noqa: E402

PASSWORD = "correct horse battery"


class PackTests(unittest.TestCase):
    def test_round_trip(self):
        payload = loginpack.build_payload('{"expires_at": 5, "token": "abc"}',
                                          [{"service": "YouTube", "user": "me", "password": "pw", "note": "n", "id": "x"}])
        blob = loginpack.seal(payload, PASSWORD, rounds=2000)
        self.assertNotIn(b"abc", blob)                                     # nothing readable in the file
        self.assertNotIn(b"YouTube", blob)
        back = loginpack.open_pack(blob, PASSWORD)
        self.assertEqual(back["vault"][0]["password"], "pw")
        self.assertEqual(json.loads(back["tidal_auth"])["token"], "abc")
        self.assertNotIn("id", back["vault"][0])

    def test_wrong_password_and_changes_are_refused(self):
        blob = loginpack.seal(loginpack.build_payload("", []), PASSWORD, rounds=2000)
        with self.assertRaises(loginpack.PackError):
            loginpack.open_pack(blob, "another password!")
        for i in (len(loginpack.MAGIC) + 3, len(blob) // 2, len(blob) - 1):    # a changed byte anywhere
            bad = bytearray(blob)
            bad[i] ^= 1
            with self.assertRaises(loginpack.PackError):
                loginpack.open_pack(bytes(bad), PASSWORD)
        with self.assertRaises(loginpack.PackError):
            loginpack.open_pack(b"not a pack at all, really not", PASSWORD)

    def test_short_password_is_refused_and_every_pack_is_different(self):
        with self.assertRaises(loginpack.PackError):
            loginpack.seal({}, "short")
        p = loginpack.build_payload("", [])
        self.assertNotEqual(loginpack.seal(p, PASSWORD, rounds=2000), loginpack.seal(p, PASSWORD, rounds=2000))   # random salt / nonce


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class BackendTests(unittest.TestCase):
    def test_export_and_import_between_two_homes(self):
        from yeal.core import tidal
        from yeal.core.engine import Engine
        from yeal.ui.backend import Backend
        QGuiApplication.instance() or QGuiApplication(sys.argv)
        old = os.environ.get("TIDDL_PATH")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            try:
                tmp = Path(tmp)
                home_a, home_b = tmp / "tiddl_a", tmp / "tiddl_b"
                home_a.mkdir()
                (home_a / "auth.json").write_text(json.dumps({"token": "secret-token", "expires_at": 9999999999}), encoding="utf-8")
                os.environ["TIDDL_PATH"] = str(home_a)
                ctx_a = make_ctx(str(tmp / "a"))
                a = Backend(ctx_a, engine=Engine(ctx_a, ydl_class=FakeYDL), check_updates=False)
                a.vaultUnlock("1234")
                self.assertNotEqual(a.exportLogins(str(tmp / "p.yealpack"), PASSWORD), "")      # still the initial password: refused
                self.assertEqual(a.vaultChangePassword("1234", "my private admin pw"), "")
                self.assertEqual(a.vaultSave({"service": "YouTube", "user": "u", "password": "p", "note": ""}), "")
                self.assertEqual(a.exportLogins(str(tmp / "p.yealpack"), PASSWORD), "")
                self.assertNotEqual(a.exportLogins(str(tmp / "q.yealpack"), "short"), "")
                self.assertNotIn(b"secret-token", (tmp / "p.yealpack").read_bytes())
                a.shutdown()
                # the other PC: another tiddl folder, another vault
                os.environ["TIDDL_PATH"] = str(home_b)
                ctx_b = make_ctx(str(tmp / "b"))
                b = Backend(ctx_b, engine=Engine(ctx_b, ydl_class=FakeYDL), check_updates=False)
                b.vaultUnlock("1234")
                b.vaultChangePassword("1234", "another private admin pw")
                self.assertNotEqual(b.importLogins(str(tmp / "p.yealpack"), "wrong password!!"), "")
                self.assertEqual(b.importLogins(str(tmp / "p.yealpack"), PASSWORD), "")
                self.assertTrue(tidal.is_logged_in(home_b / "auth.json"))
                self.assertEqual([e["service"] for e in b.vaultEntries()], ["YouTube"])
                self.assertEqual(b.importLogins(str(tmp / "p.yealpack"), PASSWORD), "")        # twice: no duplicate entry
                self.assertEqual(len(b.vaultEntries()), 1)
                b.shutdown()
            finally:
                if old is None:
                    os.environ.pop("TIDDL_PATH", None)
                else:
                    os.environ["TIDDL_PATH"] = old


COOKIES = "# Netscape HTTP Cookie File" + chr(10) + ".youtube.com" + chr(9) + "TRUE" + chr(9) + "/" + chr(9) + "TRUE" + chr(9) + "2000000000" + chr(9) + "SID" + chr(9) + "abc" + chr(10)


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class CookiesFileTests(unittest.TestCase):
    def test_cookie_file_is_checked_copied_used_and_packed(self):
        from yeal.core.engine import Engine
        from yeal.core.models import DownloadOptions
        from yeal.core.presets import build_ydl_opts
        from yeal.ui.backend import Backend
        QGuiApplication.instance() or QGuiApplication(sys.argv)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tmp = Path(tmp)
            ctx = make_ctx(str(tmp / "a"))
            b = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
            bad = tmp / "bad.txt"
            bad.write_text("hello", encoding="utf-8")
            self.assertNotEqual(b.setCookiesFile(str(bad)), "")
            other = tmp / "other.txt"
            other.write_text(COOKIES.replace("youtube.com", "example.org"), encoding="utf-8")
            self.assertNotEqual(b.setCookiesFile(str(other)), "")
            good = tmp / "cookies.txt"
            good.write_text(COOKIES, encoding="utf-8")
            self.assertEqual(b.setCookiesFile(str(good)), "")
            used = b.settings["cookies_file"]
            self.assertTrue(used.endswith("youtube_cookies.txt") and Path(used).is_file())      # its own copy
            opts = build_ydl_opts(DownloadOptions(cookies_file=used, cookies_browser="chrome").normalized(), ctx)
            self.assertEqual(opts.get("cookiefile"), used)
            self.assertNotIn("cookiesfrombrowser", opts)                                       # the file wins
            # into the pack and out again on another PC
            b.vaultUnlock("1234")
            b.vaultChangePassword("1234", "my private admin pw")
            self.assertEqual(b.exportLogins(str(tmp / "p.yealpack"), PASSWORD), "")
            self.assertNotIn(b"abc", (tmp / "p.yealpack").read_bytes())
            self.assertEqual(b.setCookiesFile(""), "")
            self.assertEqual(b.settings["cookies_file"], "")
            self.assertFalse(Path(used).exists())
            self.assertEqual(b.importLogins(str(tmp / "p.yealpack"), PASSWORD), "")
            self.assertEqual(Path(b.settings["cookies_file"]).read_text(encoding="utf-8"), COOKIES)
            b.shutdown()


if __name__ == "__main__":
    unittest.main()
