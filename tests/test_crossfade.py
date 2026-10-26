"""Seamless change from song to song, the engine switch without a stop, the custom colours and the band strength."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import _path  # noqa: F401
from yeal.core import dsp
from yeal.core.settings import Settings

try:
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtMultimedia import QMediaDevices, QMediaPlayer
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

from test_dsp_media import FFMPEG, write_wav  # noqa: E402


class SettingsTests(unittest.TestCase):
    def test_crossfade_is_off_or_3_to_10_seconds(self):
        for given, wanted in ((0, 0), (2, 0), (3, 3), (7, 7), (99, 10), ("x", 0), (None, 0)):
            s = Settings(crossfade=given)
            s.validate()
            self.assertEqual(s.crossfade, wanted, given)

    def test_band_strength_is_kept_between_50_and_300_percent(self):
        for given, wanted in ((100, 100), (10, 50), (1000, 300), ("x", 100)):
            s = Settings(level_amp=given)
            s.validate()
            self.assertEqual(s.level_amp, wanted, given)

    def test_glow_and_outer_ring_settings(self):
        for given, wanted in ((100, 100), (0, 0), (-5, 0), (999, 300), ("x", 100)):
            s = Settings(glow_amp=given)
            s.validate()
            self.assertEqual(s.glow_amp, wanted, given)
        s = Settings()
        s.validate()
        self.assertEqual(s.outer_ring, "list")
        s = Settings(outer_ring="spiral")
        s.validate()
        self.assertEqual(s.outer_ring, "list")

    def test_custom_colours_are_clean_unique_and_at_most_five(self):
        s = Settings(custom_colors=["#12ABEF", "#12abef", "red", "#ff0000", "#00ff00", "#0000ff", "#111111", "#222222", "#333333"])
        s.validate()
        self.assertEqual(s.custom_colors, ["#12abef", "#ff0000", "#00ff00", "#0000ff", "#111111"])
        s = Settings(custom_colors="nope")
        s.validate()
        self.assertEqual(s.custom_colors, [])
        s = Settings(tidal_player_color="#12AbEf")                          # a made colour can be the player colour
        s.validate()
        self.assertEqual(s.tidal_player_color, "#12abef")


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class CrossfaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    class Obj:
        def __init__(self):
            self.vol, self.stopped, self.deleted = None, False, False

        def setVolume(self, v):
            self.vol = v

        def stop(self):
            self.stopped = True

        def deleteLater(self):
            self.deleted = True

    def test_phase_of_the_extra_ring(self):
        from yeal.ui.crossfade import phase_after, phase_before
        self.assertEqual(phase_before(60000, 8000), -1.0)                    # far from the end: no ring
        self.assertEqual(phase_before(13000, 8000), 0.0)                     # 5 s before the fade starts
        self.assertAlmostEqual(phase_before(10500, 8000), 0.25)
        self.assertAlmostEqual(phase_before(8000, 8000), 0.5)                # the fade starts
        self.assertAlmostEqual(phase_after(0), 0.5)
        self.assertAlmostEqual(phase_after(2500), 0.75)
        self.assertEqual(phase_after(5000), -1.0)                            # 5 s after: the ring is over

    def test_volumes_cross_and_the_old_song_is_dropped(self):
        from yeal.ui.crossfade import Crossfader
        fader = Crossfader()
        old, new = self.Obj(), self.Obj()
        fader.hold(old, old, 0.8)
        self.assertTrue(fader.waiting)
        fader.begin(new, lambda: 0.8, 4.0)
        self.assertEqual(new.vol, 0.0)                                        # starts silent
        fader._t0 -= 2.0                                                      # half way
        fader._step()
        self.assertAlmostEqual(old.vol, 0.8 * 0.7071, places=2)               # equal power: both about -3 dB
        self.assertAlmostEqual(new.vol, 0.8 * 0.7071, places=2)
        self.assertFalse(old.stopped)
        fader._t0 -= 3.0
        fader._step()                                                         # over
        self.assertTrue(old.stopped and old.deleted)
        self.assertAlmostEqual(new.vol, 0.8)                                  # the new song has its full volume
        self.assertFalse(fader.running)

    def test_cancel_stops_everything(self):
        from yeal.ui.crossfade import Crossfader
        fader = Crossfader()
        old = self.Obj()
        fader.hold(old, old, 1.0)
        fader.cancel()
        self.assertTrue(old.stopped)
        self.assertFalse(fader.waiting)


SKIP = (not HAVE_QT) or (not dsp.available()) or FFMPEG is None


@unittest.skipIf(SKIP, "needs PySide6, numpy and ffmpeg")
class PlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from yeal.core.engine import Engine
        from yeal.platforms import PlatformInfo
        from yeal.ui.backend import Backend
        from test_core import FakeYDL
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        tmp = Path(cls.tmp.name)
        if QMediaDevices.defaultAudioOutput().isNull():
            raise unittest.SkipTest("no audio output on this machine")
        ctx = PlatformInfo("windows", False, tmp / "data", tmp / "dl", Path(FFMPEG))
        cls.backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
        cls.files = []
        for n in range(2):
            f = tmp / ("tone%d.wav" % n)
            write_wav(f, seconds=14.0)
            cls.files.append(f)

    @classmethod
    def tearDownClass(cls):
        cls.backend.localPlayer.stop()
        cls.backend.shutdown()
        cls.tmp.cleanup()

    def pump(self, seconds, until):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            if until():
                return True
            time.sleep(0.005)
        return until()

    def items(self):
        return [{"kind": "track", "id": str(f), "title": "Tone %d" % i, "subtitle": "Test", "file": str(f),
                 "duration": 0, "cover": "", "url": ""} for i, f in enumerate(self.files)]

    def start(self, engine):
        b = self.backend
        b.setSetting("audio_engine", engine)
        p = b.localPlayer
        p.stop()
        p._player = p._audio = p._abuf = None
        p._engine_in_use = ""
        p.queue.clear() if hasattr(p.queue, "clear") else None
        p.setVolume(0)
        p.playItems(self.items(), 0, "Test")
        self.assertTrue(self.pump(10, lambda: p.position > 300), "the song did not start")
        return p

    def test_the_next_song_starts_before_the_old_one_ends(self):
        b = self.backend
        b.setSetting("crossfade", 3)
        p = self.start("dsp")
        self.assertEqual(p.queue.current, 0)
        p.seek(8500)                                                    # 5.5 s before the end: the hand over comes at 3 s + 1.5 s
        phases = []

        def watch():
            phases.append(p.fade)
            return p.queue.current == 1 and p._fade_state == "run"
        self.assertTrue(self.pump(12, watch), "the next song never started")
        self.assertTrue(any(0 <= v <= 0.5 for v in phases), "the extra ring was not shown before the fade")
        self.assertTrue(p._fader.running)
        self.assertEqual([t["id"] for t in p.history][:2], [str(self.files[1]), str(self.files[0])])
        self.assertTrue(self.pump(8, lambda: not p._fader.running and p._fade_state == ""))
        self.assertFalse(p._fader._out)                                 # the old song is gone
        self.assertTrue(p.playing)
        b.setSetting("crossfade", 0)

    def test_outer_ring_follows_the_whole_list(self):
        b = self.backend
        p = self.start("dsp")
        self.assertAlmostEqual(p.listProgress, 0.0, delta=0.15)           # song 1 of 2, just begun
        p.playItems(self.items(), 1, "Test")
        self.assertTrue(self.pump(10, lambda: p.position > 300))
        self.assertGreaterEqual(p.listProgress, 0.5)                      # song 2 of 2: at least half of the list
        p.playItems(self.items()[:1], 0, "Test")
        self.assertEqual(p.listProgress, -1.0)                            # a single song: no list ring
        p.stop()

    def test_no_fade_when_it_is_off(self):
        b = self.backend
        b.setSetting("crossfade", 0)
        p = self.start("dsp")
        p.seek(12000)
        self.assertTrue(self.pump(6, lambda: p.queue.current == 1), "the next song never came")
        self.assertEqual(p._fade_state, "")
        self.assertLess(p.fade, 0)

    def test_switching_the_engine_does_not_stop_the_song(self):
        b = self.backend
        b.setSetting("crossfade", 0)
        p = self.start("dsp")
        self.assertEqual(p._engine_in_use, "dsp")
        self.assertTrue(self.pump(10, lambda: p.position > 1500))
        before, history = p.position, len(p.history)
        b.setAudioEngine("qt")                                           # the other engine takes over at the same place
        self.assertTrue(self.pump(10, lambda: p._engine_in_use == "qt" and p._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                                  and p.position >= before - 200), "the new engine did not go on at the same place")
        self.assertLess(p.fade, 0)                                       # no ring for a plain switch
        self.assertEqual(len(p.history), history)                        # not counted as another song
        self.assertTrue(self.pump(6, lambda: p.position > before + 1000))
        self.assertTrue(p.playing)
        self.assertTrue(self.pump(6, lambda: not p._fader.running))
        self.assertFalse(p._fader._out)
        b.setAudioEngine("dsp")                                          # and back
        self.assertTrue(self.pump(10, lambda: p._engine_in_use == "dsp" and p.playing and p._player.position() > before))


if __name__ == "__main__":
    unittest.main()
