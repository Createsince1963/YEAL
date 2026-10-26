"""Audio performance and stability calibration (ui/calibration.py): verdicts, profile, applying the values, a real short run."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import _path  # noqa: F401

try:
    from PySide6.QtGui import QGuiApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

DEVICE = {"name": "Headphones", "hands_free": False, "preferred_rate": 48000, "float32_stereo_by_rate": {"48000": True}}


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class JudgeTests(unittest.TestCase):
    def setUp(self):
        from yeal.ui import calibration
        self.c = calibration

    def levels(self, verdicts):
        return [v["level"] for v in verdicts]

    def test_hands_free_is_warned(self):
        v = self.c.judge(dict(DEVICE, name="Headset Hands-Free AG Audio", hands_free=True), None, None, 0)
        self.assertEqual(self.levels(v), ["WARN"])

    def test_buffer_verdicts(self):
        ok = {"results": [{"gui_lag_max_ms": 40.0, "underruns": 0}], "smallest_stable_ms": 300, "recommended_ms": 400}
        self.assertEqual(self.levels(self.c.judge(DEVICE, ok, None, 0)), ["PASS", "PASS"])
        bad = {"results": [{"gui_lag_max_ms": 500.0, "underruns": 5}], "smallest_stable_ms": None, "recommended_ms": 1500}
        self.assertEqual(self.levels(self.c.judge(DEVICE, bad, None, 0))[0], "FAIL")

    def test_leaks_are_failed(self):
        import time
        base = {"threads": 5, "rss_mb": 100.0, "ffmpeg": 0}
        leak = {"changes": 40, "series": [base, dict(base, rss_mb=101.0), dict(base, threads=45, rss_mb=102.0)], "base": base,
                "final": dict(base, threads=45, ffmpeg=1, rss_mb=102.0), "underruns": 3, "tick_peak_ms": 30.0, "gui_lag_max_ms": 900.0}
        text = {v["text"]: v["level"] for v in self.c.judge(DEVICE, None, leak, time.time() - 60)}
        self.assertEqual([lv for t, lv in text.items() if t.startswith("Threads")], ["FAIL"])
        self.assertEqual([lv for t, lv in text.items() if t.startswith("ffmpeg")], ["FAIL"])
        self.assertEqual([lv for t, lv in text.items() if t.startswith("Dropouts")], ["FAIL"])
        self.assertEqual([lv for t, lv in text.items() if t.startswith("Largest GUI lag")], ["FAIL"])
        clean = dict(leak, final=dict(base), underruns=0, gui_lag_max_ms=60.0, series=[base, base, base])
        self.assertNotIn("FAIL", self.levels(self.c.judge(DEVICE, None, clean, time.time() - 60)))

    def test_profile_and_apply(self):
        buf = {"results": [{"gui_lag_max_ms": 300.0, "underruns": 0}], "smallest_stable_ms": 400, "recommended_ms": 600}
        prof = self.c.profile_from(DEVICE, buf, None)
        self.assertEqual((prof["audio_buffer_ms"], prof["ui_refresh_hz"]), (600, 15))      # a laggy GUI repaints less often
        from yeal.core.settings import Settings
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            Settings().save(path)
            self.c.apply_profile(path, prof)
            s = Settings.load(path)
            self.assertEqual((s.audio_buffer_ms, s.ui_refresh_hz), (600, 15))

    def test_settings_are_clamped(self):
        from yeal.core.settings import Settings
        s = Settings(audio_buffer_ms=5, ui_refresh_hz=99).validate()
        self.assertEqual((s.audio_buffer_ms, s.ui_refresh_hz), (200, 30))

    def test_outputs_are_listed(self):
        for d in self.c.list_devices():
            self.assertIn("float32_stereo_by_rate", d)
            self.assertIsInstance(d["hands_free"], bool)

    def test_a_real_short_run_counts_no_dropout_with_a_big_buffer(self):
        from yeal.platforms import desktop
        from yeal.ui import dsp_media
        ffmpeg = desktop.find_ffmpeg()
        if not dsp_media.usable(ffmpeg):
            self.skipTest("the own engine needs numpy and ffmpeg")
        app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            song = Path(tmp) / "t.wav"
            self.c._write_test_song(song, 8)
            media = dsp_media.DspMedia(ffmpeg)
            media.setVolume(0.0)
            r = self.c.test_buffer(app, media, song, 1000, 2.0, loaded=False)
            media.stop()
            self.assertEqual(r["underruns"], 0)
            self.assertEqual(r["buffer_ms"], 1000)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class RunnerTests(unittest.TestCase):
    def test_command_line_of_the_child(self):
        from yeal.ui import calibration_runner as r
        program, args = r.child_command("stress", 5.0, "Kopf")
        self.assertEqual(program, sys.executable)
        self.assertTrue(args[0].endswith("main.py"))
        self.assertEqual(args[1:], ["--calibrate", "--json", "--stress", "--minutes", "5.0", "--device", "Kopf"])
        self.assertIn("--quick", r.child_command("quick")[1])

    def test_the_sound_check_runs_as_a_process_and_applies_its_values(self):
        import time
        from test_core import FakeYDL, make_ctx
        from yeal.core.engine import Engine
        from yeal.platforms import desktop
        from yeal.ui import dsp_media
        from yeal.ui.backend import Backend
        if not dsp_media.usable(desktop.find_ffmpeg()):
            self.skipTest("the own engine needs numpy and ffmpeg")
        app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            old = os.environ.get("YEAL_DATA_DIR")
            os.environ["YEAL_DATA_DIR"] = tmp                     # the child writes its files here, not into the real data folder
            try:
                ctx = make_ctx(tmp)
                backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
                run = backend.calibration
                self.assertFalse(run.running)
                run.start("quick")
                self.assertTrue(run.running)
                end = time.time() + 150
                while run.running and time.time() < end:
                    app.processEvents()
                    time.sleep(0.02)
                self.assertFalse(run.running, "the sound check did not finish")
                self.assertTrue(run.hasResult, run.status)
                self.assertGreaterEqual(len(run.verdicts), 2)
                self.assertTrue(run.status.startswith("Ready"))
                run.apply()
                self.assertEqual(backend.settings["audio_buffer_ms"], run.profile["audio_buffer_ms"])
                self.assertEqual(backend.settings["ui_refresh_hz"], run.profile["ui_refresh_hz"])
                backend.shutdown()
            finally:
                if old is None:
                    os.environ.pop("YEAL_DATA_DIR", None)
                else:
                    os.environ["YEAL_DATA_DIR"] = old
