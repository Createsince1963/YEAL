"""Yeal's own player for downloaded files: library of finished downloads, playing a file, loudness profile of the whole
file (QAudioDecoder), single playback with the TIDAL players, the menu entry "Play in Yeal player"."""
import math
import os
import struct
import sys
import tempfile
import time
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import _path  # noqa: F401
from yeal.core.models import DownloadJob, DownloadOptions, JobState  # noqa: E402

try:
    from PySide6.QtGui import QGuiApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

from test_core import FakeYDL, make_ctx  # noqa: E402


def job(i, filename, url="https://youtu.be/x", state=JobState.DONE, uploader="Uploader", title="Job"):
    return SimpleNamespace(id=i, filename=str(filename), url=url, state=state, uploader=uploader, title=title,
                           thumbnail="https://i.ytimg.com/vi/x/hq.jpg")


def write_wav(path: Path, seconds=3, loud_first=True):
    """A sine wave that is loud in the first half and quiet in the second half (or the other way round)."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        frames = bytearray()
        total = 44100 * seconds
        for i in range(total):
            first = i < total // 2
            amp = 0.8 if first == loud_first else 0.03
            v = int(32767 * amp * math.sin(2 * math.pi * 440 * i / 44100))
            frames += struct.pack("<hh", v, v)
        w.writeframes(bytes(frames))


class NamesAndLibraryTests(unittest.TestCase):
    def test_split_name(self):
        from yeal.ui.local_player import split_name
        self.assertEqual(split_name("01 - Highway Star", False, "Deep Purple"), ("Highway Star", "Deep Purple"))
        self.assertEqual(split_name("Deep Purple - Highway Star", True), ("Highway Star", "Deep Purple"))
        self.assertEqual(split_name("03 - Deep Purple - Highway Star", True), ("Highway Star", "Deep Purple"))
        self.assertEqual(split_name("A - B", False, "Up"), ("A - B", "Up"))          # only Tidal names are split at " - "
        self.assertEqual(split_name("Plain", True, "Up"), ("Plain", "Up"))

    def test_library_has_files_and_album_folders_but_no_junk(self):
        from yeal.ui.local_player import library_items
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            song = root / "Song.mp3"
            song.write_bytes(b"x")
            video = root / "Clip.mp4"
            video.write_bytes(b"x")
            album = root / "Tidal" / "Albums" / "DP" / "Machine Head"
            album.mkdir(parents=True)
            (album / "02 - Maybe.flac").write_bytes(b"x")
            (album / "01 - Highway Star.flac").write_bytes(b"x")
            (album / "cover.jpg").write_bytes(b"x")
            jobs = [job(3, album, url="https://tidal.com/browse/album/7", title="Machine Head", uploader="Deep Purple"),
                    job(2, song), job(1, video),
                    job(4, root / "gone.mp3"), job(5, song, state=JobState.ERROR), job(6, song)]   # 6: the same file twice
            items = library_items(jobs)
            self.assertEqual([i["title"] for i in items], ["Highway Star", "Maybe", "Song"])
            self.assertEqual(items[0]["subtitle"], "Deep Purple")
            self.assertEqual(items[0]["jobId"], 3)
            self.assertEqual(items[0]["source"], "Machine Head")
            self.assertEqual(items[2]["subtitle"], "Uploader")
            self.assertTrue(all(i["kind"] == "track" and Path(i["file"]).is_file() for i in items))
            self.assertEqual(library_items([]), [])


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class LocalPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from yeal.core.engine import Engine
        from yeal.ui.backend import Backend
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)     # Windows may still hold the audio file a moment
        ctx = make_ctx(cls.tmp.name)
        cls.backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
        cls.wav = Path(cls.tmp.name) / "sine.wav"
        write_wav(cls.wav)

    @classmethod
    def tearDownClass(cls):
        from PySide6.QtCore import QUrl
        player = cls.backend.localPlayer
        player.stop()
        if player._player is not None:
            player._player.setSource(QUrl())                 # let go of the file
        for _ in range(20):
            cls.app.processEvents()
        cls.backend.shutdown()
        cls.tmp.cleanup()

    def pump(self, seconds, until=None):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            if until and until():
                return True
            time.sleep(0.01)
        return bool(until and until())

    def test_it_is_part_of_the_backend_and_has_its_own_volume(self):
        b = self.backend
        self.assertTrue(hasattr(b, "localPlayer"))
        p = b.localPlayer
        p.setVolume(35)
        self.assertEqual(b.settings["local_volume"], 35)
        self.assertNotEqual(b.settings["tidal_volume"], 35)               # the TIDAL player keeps its own
        p.setVolume(0)

    def test_playing_a_file_scans_its_loudness_profile(self):
        p = self.backend.localPlayer
        p.setVolume(0)
        item = {"kind": "track", "id": str(self.wav), "title": "Sine", "subtitle": "Test", "file": str(self.wav),
                "duration": 0, "cover": "", "url": ""}
        p.playItems([item], 0, "Test")
        self.assertEqual(p.queue.item(p.queue.current)["file"], str(self.wav))
        self.assertTrue(self.pump(8, until=lambda: any(v >= 0 for v in p.profile)), "the profile was never filled")
        self.pump(2)
        values = p.profile
        known = [v for v in values if v >= 0]
        self.assertGreater(len(known), len(values) // 2)
        first, second = values[: len(values) // 4], values[-len(values) // 4:]
        if all(v >= 0 for v in first + second):
            self.assertGreater(sum(first) / len(first), sum(second) / len(second) + 0.2)      # loud half, then the quiet half
        p.stop()

    def test_missing_file_is_reported_and_does_not_crash(self):
        p = self.backend.localPlayer
        errors = []
        p.error.connect(errors.append)
        p.playItems([{"kind": "track", "id": "x", "title": "Gone", "file": str(Path(self.tmp.name) / "gone.mp3")}], 0)
        self.assertTrue(errors and "not there" in errors[0])

    def test_play_in_yeal_player_queues_the_download_and_asks_for_the_view(self):
        b = self.backend
        seen = []
        b.localPlayerRequested.connect(lambda: seen.append(1))
        j = DownloadJob(77, "https://youtu.be/abc", DownloadOptions(mode="audio"))
        j.state, j.filename, j.title, j.uploader = JobState.DONE, str(self.wav), "Sine job", "Test"
        b._model.upsert(j)
        b.localPlayer.setVolume(0)
        b.playInYeal(77)
        self.assertEqual(seen, [1])
        self.assertEqual(b.localPlayer.queue.item(b.localPlayer.queue.current)["jobId"], 77)
        b.localPlayer.stop()
        toasts = []
        b.toast.connect(toasts.append)
        b.playInYeal(999)                                              # no such download
        self.assertTrue(any("no audio file" in t for t in toasts))

    def test_starting_a_player_pauses_the_other_ones(self):
        b = self.backend
        calls = []
        b.tidalDiyPlaying.connect(lambda: calls.append("web"))
        original_tidal, original_local = b.tidal.player.pause, b.localPlayer.pause
        b.tidal.player.pause = lambda: calls.append("tidal")
        b.localPlayer.pause = lambda: calls.append("local")
        try:
            b.setSetting("single_playback", True)
            b.localPlayer._owner.request_single_playback()           # the local player starts
            self.assertEqual(calls, ["web", "tidal"])
            calls.clear()
            b.tidal.request_single_playback()                         # a TIDAL song starts
            self.assertEqual(calls, ["web", "local"])
            calls.clear()
            b.setSetting("single_playback", False)
            b.localPlayer._owner.request_single_playback()
            self.assertEqual(calls, [])                               # the user allowed several at once
        finally:
            b.tidal.player.pause, b.localPlayer.pause = original_tidal, original_local
            b.setSetting("single_playback", True)


if __name__ == "__main__":
    unittest.main()
