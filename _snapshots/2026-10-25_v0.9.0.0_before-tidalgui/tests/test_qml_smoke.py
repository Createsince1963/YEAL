"""Loads the real QML with the real Backend (fake yt-dlp) in offscreen mode."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import _path  # noqa: F401

try:
    from PySide6.QtCore import QUrl, qInstallMessageHandler
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    HAVE_QT = True
except ImportError:  # central Python without PySide6 never happens, CI helpers might
    HAVE_QT = False

from test_core import FakeYDL, make_ctx  # noqa: E402
from yeal.core.settings import Settings  # noqa: E402

ROLE_JOB_STATE = 256 + 1 + 3  # Qt.UserRole + 1 + index of "jobState" in JobModel._ROLES
QML = _path.PYMODUL / "yeal" / "ui" / "qml" / "Main.qml"


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class QmlSmokeTest(unittest.TestCase):
    def test_app_loads_and_queues_a_job(self):
        from yeal.core.engine import Engine
        from yeal.ui.backend import Backend

        messages = []
        qInstallMessageHandler(lambda mode, ctx, msg: messages.append(msg))
        QQuickStyle.setStyle("Material")
        app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = make_ctx(tmp)
            backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
            engine = QQmlApplicationEngine()
            engine.rootContext().setContextProperty("backend", backend)
            engine.rootContext().setContextProperty("jobModel", backend.model)
            engine.load(QUrl.fromLocalFile(str(QML)))
            self.assertTrue(engine.rootObjects(), "\n".join(messages))
            self.assertTrue(backend.setupRequired)
            self.assertEqual(backend.settings["cookies_browser"], "chrome")
            self.assertEqual(backend.completeSetup("chrome", backend.settings["download_dir"]), "")
            self.assertFalse(backend.setupRequired)

            self.assertEqual(backend.addUrls("see https://example.com/a and https://example.com/a\n"
                                             "https://example.com/b"), 2)
            self.assertEqual(backend.addUrls("no link here"), 0)
            self.assertEqual(backend.extractLinks("x https://a.test/v?1, https://a.test/v?1 and https://b.test)"),
                             ["https://a.test/v?1", "https://b.test"])
            end = time.time() + 5
            def states_now():
                return [backend.model.data(backend.model.index(r), ROLE_JOB_STATE)
                        for r in range(backend.model.rowCount())]

            while time.time() < end and states_now() != ["done", "done"]:
                app.processEvents()
                time.sleep(0.01)
            states = states_now()
            self.assertEqual(states, ["done", "done"])

            self.assertIn("not found", backend.extractFrames("missing.mp4", "", "", "5", "jpg"))
            self.assertFalse(backend.framesBusy)

            # settings round trip + custom option validation
            backend.setSetting("theme", "dark")
            self.assertEqual(backend.settings["theme"], "dark")
            backend.setSetting("theme", "neon")
            self.assertEqual(backend.settings["theme"], "dark")
            self.assertIn("http", backend.setProxy("ftp://x"))
            self.assertEqual(backend.setProxy("http://127.0.0.1:8080"), "")
            self.assertEqual(backend.saveProfile("", {"name": "Test", "mode": "audio"}), "")
            backend.setFormatMode("video")
            self.assertEqual(backend.settings["active_mode"], "video")
            backend.setFormatMode("audio")
            self.assertEqual(backend.settings["active_profile"], "Audio MP3")
            backend.setFormatMode("video")
            self.assertEqual(backend.settings["active_profile"], "Video 1080p")
            backend.setActiveProfile("Test")
            backend.setProfileFlag("save_transcript", True)
            self.assertTrue(backend.settings["profiles"][-1]["save_transcript"])
            self.assertEqual(backend.settings["active_profile"], "Test")
            self.assertEqual(backend.deleteProfile("Test"), "")
            st = backend.stats
            self.assertEqual((st["all"], st["done"]), (2, 2))
            self.assertEqual(st["progress"], -1.0)
            flt = backend.filteredModel
            flt.setGroup("failed")
            self.assertEqual(flt.rowCount(), 0)
            flt.setGroup("done")
            self.assertEqual(flt.rowCount(), 2)
            flt.setSearch("zzz-nothing")
            self.assertEqual(flt.rowCount(), 0)
            flt.setSearch("")
            flt.setGroup("all")
            backend.setSetting("max_parallel", 99)
            self.assertEqual(backend.settings["max_parallel"], 4)
            self.assertIn("Not allowed", backend.setCustomOptions('{"exec_cmd": "x"}'))
            self.assertIn("Invalid JSON", backend.setCustomOptions("{"))
            self.assertEqual(backend.setCustomOptions('{"ratelimit": 100}'), "")
            self.assertIn("0.8.14", backend.versionHistory)
            self.assertIn("yt-dlp", backend.thirdPartyLicenses)
            self.assertIn("FFmpeg", backend.thirdPartyLicenses)

            # download folder chooser backend
            new_dir = Path(tmp) / "chosen" / "sub"
            self.assertEqual(backend.setDownloadDir(new_dir.as_uri()), "")
            self.assertEqual(Path(backend.settings["download_dir"]), new_dir)
            self.assertTrue(new_dir.is_dir())
            blocker = Path(tmp) / "afile"
            blocker.write_text("x")
            self.assertIn("not writable", backend.setDownloadDir(str(blocker / "x")))
            self.assertEqual(Path(backend.settings["download_dir"]), new_dir)  # unchanged on failure
            self.assertEqual(backend.setDownloadDir(""), "")
            self.assertEqual(Path(backend.settings["download_dir"]), ctx.download_dir)
            self.assertEqual(Settings.load(ctx.settings_path).download_dir, "")

            # helper paths selected in Settings are persisted and immediately used by the engine
            helpers = Path(tmp) / "helpers"
            helpers.mkdir()
            ffmpeg = helpers / "ffmpeg.exe"
            node = helpers / "node.exe"
            ffmpeg.write_bytes(b"not a real executable")
            node.write_bytes(b"not a real executable")
            self.assertEqual(backend.setHelperPath("ffmpeg", ffmpeg.as_uri()), "")
            self.assertEqual(backend.setHelperPath("node", node.as_uri()), "")
            self.assertEqual(ctx.ffmpeg, ffmpeg.resolve())
            self.assertEqual(ctx.js_runtime, node.resolve())
            saved = Settings.load(ctx.settings_path)
            self.assertEqual(Path(saved.ffmpeg_path), ffmpeg.resolve())
            self.assertEqual(Path(saved.node_path), node.resolve())
            wrong = helpers / "wrong.exe"
            wrong.write_bytes(b"x")
            self.assertIn("ffmpeg.exe", backend.setHelperPath("ffmpeg", wrong.as_uri()))
            backend.setHelperPath("ffmpeg", "")
            backend.setHelperPath("node", "")
            self.assertEqual(Settings.load(ctx.settings_path).ffmpeg_path, "")
            self.assertEqual(Settings.load(ctx.settings_path).node_path, "")

            # Settings are staged: leaving can discard them, while Save persists and resets dirty state.
            original_theme = backend.settings["theme"]
            draft_theme = "light" if original_theme != "light" else "dark"
            backend.beginSettingsEdit()
            backend.setSetting("theme", draft_theme)
            self.assertTrue(backend.settingsDirty)
            self.assertEqual(Settings.load(ctx.settings_path).theme, original_theme)
            backend.finishSettingsEdit(False)
            self.assertEqual(backend.settings["theme"], original_theme)
            backend.beginSettingsEdit()
            backend.setSetting("theme", draft_theme)
            backend.commitSettingsEdit()
            self.assertFalse(backend.settingsDirty)
            self.assertEqual(Settings.load(ctx.settings_path).theme, draft_theme)
            backend.finishSettingsEdit(True)

            backend.clearFinished()
            end = time.time() + 2
            while time.time() < end and backend.model.rowCount():
                app.processEvents()
            self.assertEqual(backend.model.rowCount(), 0)

            bad = [m for m in messages if "qml" in m.lower() and
                   any(w in m for w in ("ReferenceError", "TypeError", "is not defined",
                                        "Unable to assign", "Cannot "))]
            engine.deleteLater()
            backend.shutdown()
            self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
