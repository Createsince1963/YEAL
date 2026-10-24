"""Regression tests for switching the image extractor to another video."""
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import _path

try:
    from PySide6.QtGui import QGuiApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

from test_core import FakeYDL, make_ctx  # noqa: E402


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class FramesPreviewTests(unittest.TestCase):
    def test_switching_video_ignores_old_preview_and_uses_unique_files(self):
        from yeal.core.engine import Engine
        from yeal.ui import backend as backend_module

        app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        first_started = threading.Event()
        release_first = threading.Event()
        first_done = threading.Event()
        calls = []

        with tempfile.TemporaryDirectory() as tmp:
            ctx = make_ctx(tmp)
            first = Path(tmp) / "first.mp4"
            second = Path(tmp) / "second.mp4"
            first.write_bytes(b"first")
            second.write_bytes(b"second")
            backend = backend_module.Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
            original = backend_module.framelib.filmstrip

            def fake_filmstrip(_ffmpeg, video, out_dir, count=12, height=90):
                calls.append((Path(video), Path(out_dir)))
                if Path(video) == first:
                    first_started.set()
                    release_first.wait(5)
                out_dir.mkdir(parents=True, exist_ok=True)
                image = out_dir / "strip_00.jpg"
                image.write_text(Path(video).name, encoding="utf-8")
                if Path(video) == first:
                    first_done.set()
                return (11.0 if Path(video) == first else 22.0), [image]

            results = []
            backend.filmstripReady.connect(lambda path, seconds, urls, error:
                                           results.append((path, seconds, urls, error)))
            backend_module.framelib.filmstrip = fake_filmstrip
            try:
                backend.loadFilmstrip(str(first))
                self.assertTrue(first_started.wait(2), "first preview worker did not start")
                backend.loadFilmstrip(str(second))

                end = time.time() + 3
                while time.time() < end and not results:
                    app.processEvents()
                    time.sleep(0.01)
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0][0], str(second))
                self.assertEqual(results[0][1], 22.0)

                release_first.set()
                self.assertTrue(first_done.wait(2), "stale preview worker did not finish")
                end = time.time() + 0.2
                while time.time() < end:
                    app.processEvents()
                    time.sleep(0.01)
                self.assertEqual([r[0] for r in results], [str(second)])
                self.assertEqual(len(calls), 2)
                self.assertNotEqual(calls[0][1], calls[1][1])
                self.assertIn("request-2", results[0][2][0])
            finally:
                release_first.set()
                backend_module.framelib.filmstrip = original
                backend.shutdown()

    def test_qml_preview_resets_and_tracks_the_selected_video(self):
        qml = _path.PYMODUL / "yeal" / "ui" / "qml"
        preview = (qml / "VideoPreview.qml").read_text(encoding="utf-8")
        dialog = (qml / "FramesDialog.qml").read_text(encoding="utf-8")
        self.assertIn("onSourceChanged", preview)
        self.assertIn("ready = false", preview)
        self.assertIn("dlg.previewSource", dialog)


if __name__ == "__main__":
    unittest.main()
