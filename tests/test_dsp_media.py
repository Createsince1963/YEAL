"""Yeal's own audio engine with a real ffmpeg and a real sound card output (the volume is 0: you hear nothing)."""
import math
import os
import shutil
import struct
import sys
import tempfile
import time
import unittest
import wave
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import _path  # noqa: F401
from yeal.core import dsp

try:
    from PySide6.QtCore import QCoreApplication, QUrl
    from PySide6.QtMultimedia import QMediaDevices, QMediaPlayer
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


def find_ffmpeg():
    for candidate in (os.environ.get("YEAL_TEST_FFMPEG"), shutil.which("ffmpeg"),
                      str(Path(__file__).resolve().parents[2] / "Tools_Central" / "Video Tools" / "FFMPEG" / "bin" / "ffmpeg.exe")):
        if candidate and Path(candidate).is_file():
            return candidate
    return None


FFMPEG = find_ffmpeg()
SKIP = (not HAVE_QT) or (not dsp.available()) or FFMPEG is None


def write_wav(path, seconds=3.0, loud_first=True):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        frames = bytearray()
        total = int(44100 * seconds)
        for i in range(total):
            amp = 0.8 if (i < total // 2) == loud_first else 0.03
            v = int(32767 * amp * math.sin(2 * math.pi * 440 * i / 44100))
            frames += struct.pack("<hh", v, v)
        w.writeframes(bytes(frames))


@unittest.skipIf(SKIP, "needs PySide6, numpy and ffmpeg")
class DspMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.wav = Path(cls.tmp.name) / "tone.wav"
        write_wav(cls.wav)
        if QMediaDevices.defaultAudioOutput().isNull():
            raise unittest.SkipTest("no audio output on this machine")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def make(self, cfg=None):
        from yeal.ui.dsp_media import DspMedia
        media = DspMedia(FFMPEG)
        media.setVolume(0.0)                                       # silent
        if cfg is not None:
            media.setConfig(dsp.config_from(cfg))
        media.events = {"pos": [], "state": [], "status": [], "error": [], "levels": [], "duration": []}
        media.positionChanged.connect(media.events["pos"].append)
        media.playbackStateChanged.connect(media.events["state"].append)
        media.mediaStatusChanged.connect(media.events["status"].append)
        media.errorOccurred.connect(lambda e, t: media.events["error"].append(t))
        media.levels.connect(media.events["levels"].extend)
        media.durationChanged.connect(media.events["duration"].append)
        return media

    def pump(self, seconds, until):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            if until():
                return True
            time.sleep(0.005)
        return until()

    def test_plays_a_file_to_the_end(self):
        m = self.make()
        m.setSource(QUrl.fromLocalFile(str(self.wav)))
        m.play()
        self.assertTrue(self.pump(10, lambda: m.events["status"]), "the end of the song was never reported")
        self.assertEqual(m.events["status"], [QMediaPlayer.MediaStatus.EndOfMedia])
        self.assertEqual(m.playbackState(), QMediaPlayer.PlaybackState.StoppedState)
        self.assertAlmostEqual(m.duration(), 3000, delta=60)                       # read from ffmpeg's output
        self.assertTrue(m.events["pos"])
        self.assertEqual(m.events["pos"], sorted(m.events["pos"]))                 # the position never goes backwards
        self.assertAlmostEqual(m.events["pos"][-1], 3000, delta=500)
        self.assertEqual(m.events["error"], [])

    def test_levels_follow_the_loudness_of_the_music(self):
        m = self.make()
        m.setSource(QUrl.fromLocalFile(str(self.wav)))
        m.play()
        self.pump(10, lambda: m.events["status"])
        levels = dict(m.events["levels"])
        self.assertTrue(levels)
        per_second = 1_000_000 // 20_000
        first = [v for b, v in levels.items() if b < 1.2 * per_second]               # the loud half (first 1.5 s)
        second = [v for b, v in levels.items() if b > 1.8 * per_second]              # the quiet half
        self.assertGreater(sum(first) / len(first), sum(second) / len(second) + 0.3)

    def test_pause_holds_the_position_and_resume_goes_on(self):
        m = self.make()
        m.setSource(QUrl.fromLocalFile(str(self.wav)))
        m.play()
        self.assertTrue(self.pump(5, lambda: m.position() > 300))
        m.pause()
        self.assertEqual(m.playbackState(), QMediaPlayer.PlaybackState.PausedState)
        held = m.position()
        self.pump(0.6, lambda: False)
        self.assertAlmostEqual(m.position(), held, delta=60)
        m.play()
        self.assertTrue(self.pump(5, lambda: m.position() > held + 300))
        m.stop()
        self.assertEqual(m.playbackState(), QMediaPlayer.PlaybackState.StoppedState)
        self.assertEqual(m.position(), 0)

    def test_jumping_in_the_song(self):
        m = self.make()
        m.setSource(QUrl.fromLocalFile(str(self.wav)))
        m.play()
        self.assertTrue(self.pump(5, lambda: m.position() > 200))
        m.setPosition(2300)                                                          # ffmpeg is restarted at that place
        self.assertTrue(self.pump(5, lambda: m.position() >= 2300))
        self.assertGreaterEqual(m.position(), 2300)
        self.assertTrue(self.pump(5, lambda: m.events["status"]), "the song did not end after the jump")
        self.assertLess(len(m.events["levels"]), 3 * 50 * 2)

    def test_equalizer_is_applied_and_the_position_is_corrected_for_its_delay(self):
        cfg = {"eq_on": True, "eq": [0, 0, 0, 0, 0, 6.0, 0, 0, 0, 0]}
        m = self.make(cfg)
        m.setSource(QUrl.fromLocalFile(str(self.wav)))
        m.play()
        self.assertTrue(self.pump(10, lambda: m.events["status"]))
        self.assertEqual(m.events["error"], [])
        self.assertAlmostEqual(m.duration(), 3000, delta=60)

    def test_a_file_that_does_not_exist_is_reported(self):
        m = self.make()
        m.setSource(QUrl.fromLocalFile(str(Path(self.tmp.name) / "missing.wav")))
        m.play()
        self.assertTrue(self.pump(10, lambda: m.events["error"]), "no error was reported")
        self.assertEqual(m.playbackState(), QMediaPlayer.PlaybackState.StoppedState)

    def test_usable_checks_numpy_and_ffmpeg(self):
        from yeal.ui import dsp_media
        self.assertTrue(dsp_media.usable(FFMPEG))
        self.assertFalse(dsp_media.usable(""))
        self.assertFalse(dsp_media.usable(str(Path(self.tmp.name) / "no-ffmpeg.exe")))


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(SKIP, "needs PySide6, numpy and ffmpeg")
class PlayerWithOwnEngineTests(unittest.TestCase):
    """The real player for downloaded files with the own engine switched on."""
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
        cls.wav = tmp / "tone.wav"
        write_wav(cls.wav, seconds=3.0)
        cls.backend.setSetting("audio_engine", "dsp")
        cls.backend.setDsp({"replaygain": "track", "eq_on": True, "eq": [0, 0, 0, 0, 0, 3.0, 0, 0, 0, 0]})

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

    def test_play_levels_profile_replaygain_and_the_end(self):
        b = self.backend
        self.assertTrue(b.dspAvailable)
        p = b.localPlayer
        p.setVolume(0)
        item = {"kind": "track", "id": str(self.wav), "title": "Tone", "subtitle": "Test", "file": str(self.wav),
                "duration": 0, "cover": "", "url": ""}
        p.playItems([item], 0, "Test")
        self.assertEqual(p._engine_in_use, "dsp")
        self.assertTrue(self.pump(10, lambda: p.position > 500), "the position never moved")
        self.assertTrue(self.pump(6, lambda: any(v >= 0 for v in p.profile)), "no loudness profile")
        self.assertAlmostEqual(p.duration, 3000, delta=80)
        self.assertTrue(self.pump(8, lambda: p._player._gain_db != 0.0), "no ReplayGain from the scan")
        self.assertGreater(p._player._gain_db, -12.01)
        self.assertLess(p._player._gain_db, 12.01)
        self.assertTrue(self.pump(10, lambda: not p.playing and p._player.playbackState() == QMediaPlayer.PlaybackState.StoppedState),
                        "the song did not end")
        self.assertEqual([t["id"] for t in p.history], [str(self.wav)])


if __name__ == "__main__":
    unittest.main()
