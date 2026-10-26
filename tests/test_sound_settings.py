"""Settings of the own audio engine through the backend: the engine switch, the filter settings, the players that follow."""
import os
import sys
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import _path  # noqa: F401
from yeal.core import dsp  # noqa: E402

try:
    from PySide6.QtGui import QGuiApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

from test_core import FakeYDL, make_ctx  # noqa: E402


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class SoundSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from yeal.core.engine import Engine
        from yeal.ui.backend import Backend
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        ctx = make_ctx(cls.tmp.name)
        cls.backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)

    @classmethod
    def tearDownClass(cls):
        cls.backend.shutdown()
        cls.tmp.cleanup()

    def settle(self, seconds=0.6):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)

    def test_defaults(self):
        b = self.backend
        self.assertEqual(b.settings["audio_engine"], "qt")
        self.assertEqual(b.settings["dsp"], dsp.validate_config({}))
        self.assertEqual(b.audio_engine(), "qt")

    def test_engine_choice_is_validated_and_the_players_are_told(self):
        b = self.backend
        told = []
        original = (b.tidal.player.applyEngine, b.localPlayer.applyEngine)
        b.tidal.player.applyEngine = lambda: told.append("tidal")
        b.localPlayer.applyEngine = lambda: told.append("local")
        try:
            b.setAudioEngine("dsp")
            self.assertEqual(b.settings["audio_engine"], "dsp")
            self.assertEqual(b.audio_engine(), "dsp")
            self.assertEqual(sorted(told), ["local", "tidal"])
            b.setAudioEngine("magic")                                   # not an engine: the standard one
            self.assertEqual(b.settings["audio_engine"], "qt")
        finally:
            b.tidal.player.applyEngine, b.localPlayer.applyEngine = original
            b.setSetting("audio_engine", "qt")

    def test_filter_settings_are_merged_cleaned_and_applied_after_a_pause(self):
        b = self.backend
        applied = []
        original = (b.tidal.player.applyDsp, b.localPlayer.applyDsp)
        b.tidal.player.applyDsp = lambda: applied.append("tidal")
        b.localPlayer.applyDsp = lambda: applied.append("local")
        try:
            b.setDsp({"eq_on": True, "eq": [30, -30, 3.14] + [0] * 7})
            b.setDsp({"crossfeed": "medium"})                           # merged into what is there, nothing is lost
            b.setDsp({"preamp": 99})
            cfg = b.settings["dsp"]
            self.assertIs(cfg["eq_on"], True)
            self.assertEqual(cfg["eq"][:3], [12.0, -12.0, 3.1])
            self.assertEqual(cfg["crossfeed"], "medium")
            self.assertEqual(cfg["preamp"], 12.0)
            self.assertEqual(applied, [])                                # not yet: moving a slider must not restart the song
            self.settle(0.8)
            self.assertEqual(sorted(applied), ["local", "tidal"])        # once, after the pause
            b.setDsp("not a dict")                                       # ignored
            b.setDsp({"crossfeed": "huge", "replaygain": "album"})
            self.assertEqual(b.settings["dsp"]["crossfeed"], "off")
            self.assertEqual(b.settings["dsp"]["replaygain"], "off")
            self.assertEqual(dsp.config_from(b.dsp_config()).crossfeed, "off")
        finally:
            b.tidal.player.applyDsp, b.localPlayer.applyDsp = original
            b.setSetting("dsp", {})

    def test_availability_and_ffmpeg_path(self):
        b = self.backend
        self.assertEqual(b.ffmpeg_path(), str(b._ctx.ffmpeg))
        self.assertIsInstance(b.dspAvailable, bool)                      # the test ffmpeg path does not exist: False here
        self.assertFalse(b.dspAvailable)

    def test_a_missing_engine_falls_back_to_the_standard_player(self):
        b = self.backend
        errors = []
        b.localPlayer.error.connect(errors.append)
        b.setSetting("audio_engine", "dsp")                               # chosen, but no usable ffmpeg here
        try:
            p = b.localPlayer
            p._player = None
            self.assertTrue(p._ensure())
            self.assertEqual(p._engine_in_use, "qt")
            self.assertTrue(any("numpy and ffmpeg" in e for e in errors))
        finally:
            b.setSetting("audio_engine", "qt")
            p = b.localPlayer
            old, p._player, p._audio, p._abuf = p._player, None, None, None
            if old is not None:
                old.deleteLater()


if __name__ == "__main__":
    unittest.main()
