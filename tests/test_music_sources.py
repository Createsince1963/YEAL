"""Music folders of the user (0.9.1.19): validation, scan, library source, folders / albums dragged into the queue."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import _path  # noqa: F401
from yeal.core import music_sources  # noqa: E402

try:
    from PySide6.QtGui import QGuiApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

from test_core import FakeYDL, make_ctx  # noqa: E402


class SourcesTests(unittest.TestCase):
    def test_validation(self):
        out = music_sources.validate_sources([{"path": "C:/Music"}, {"path": "c:/music"}, {"path": ""}, "x",
                                              {"path": "//nas/music", "name": "NAS"}])
        self.assertEqual([s["name"] for s in out], ["Music", "NAS"])
        self.assertEqual(out[1]["kind"], "network")
        self.assertEqual(out[0]["id"], music_sources.validate_sources([{"path": "C:/Music"}])[0]["id"])      # stable id
        self.assertEqual(len(music_sources.validate_sources([{"path": "C:/m%d" % i} for i in range(40)])), music_sources.MAX_SOURCES)
        self.assertEqual(music_sources.validate_sources("nonsense"), [])

    def test_network_paths(self):
        self.assertTrue(music_sources.is_network_path("\\\\server\\share\\music"))
        self.assertTrue(music_sources.is_network_path("//server/share"))
        self.assertFalse(music_sources.is_network_path("relative/dir"))

    def test_scan_finds_audio_in_sub_folders_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Album B").mkdir()
            (root / "Album A").mkdir()
            (root / "Album B" / "01 - Two.flac").write_bytes(b"x")
            (root / "Album A" / "Artist - One.mp3").write_bytes(b"x")
            (root / "Album A" / "cover.jpg").write_bytes(b"x")
            items = music_sources.scan_folder(str(root))
            self.assertEqual([i["title"] for i in items], ["One", "Two"])
            self.assertEqual(items[0]["subtitle"], "Artist")
            self.assertEqual(items[1]["source"], "Album B")
            self.assertIsNone(music_sources.check_folder(str(root)))
            self.assertIsNotNone(music_sources.check_folder(str(root / "missing")))
            self.assertIsNotNone(music_sources.check_folder(str(root / "Album A" / "cover.jpg")))


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class PlayerSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from yeal.core.engine import Engine
        from yeal.ui.backend import Backend
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        ctx = make_ctx(cls.tmp.name)
        cls.backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
        cls.music = Path(cls.tmp.name) / "MyMusic"
        (cls.music / "Album").mkdir(parents=True)
        for n in ("a", "b", "c"):
            (cls.music / "Album" / f"{n}.mp3").write_bytes(b"x")

    @classmethod
    def tearDownClass(cls):
        cls.backend.shutdown()
        cls.tmp.cleanup()

    def pump(self, seconds, until):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            if until():
                return True
            time.sleep(0.01)
        return until()

    def test_add_choose_remove_and_queue_a_folder(self):
        b = self.backend
        p = b.localPlayer
        self.assertNotEqual(b.addMusicSource(str(self.music / "nope"), ""), "")           # does not exist
        self.assertEqual(b.addMusicSource(str(self.music), "Mine"), "")
        self.assertNotEqual(b.addMusicSource(str(self.music), ""), "")                    # twice
        sources = b.settings["music_sources"]
        self.assertEqual([s["name"] for s in sources], ["Mine"])
        sid = sources[0]["id"]
        p.chooseSource(sid)
        self.assertTrue(self.pump(5, lambda: len(p.library) == 3), "the folder was not read")
        self.assertFalse(p.libraryBusy)
        # a whole folder dragged into the queue
        p.queue.clear() if hasattr(p.queue, "clear") else None
        before = p.queue.rowCount()
        p.enqueue([{"kind": "folder", "id": sid, "path": str(self.music), "title": "Mine"}], -1)
        self.assertTrue(self.pump(5, lambda: p.queue.rowCount() == before + 3), "the folder did not reach the queue")
        # an album (group of songs) of the library
        p.enqueue([{"kind": "group", "id": "g", "title": "Album", "tracks": p.library[:2]}], -1)
        self.assertEqual(p.queue.rowCount(), before + 5)
        # removing the chosen source puts the library back on the downloads
        b.removeMusicSource(sid)
        self.assertEqual(b.settings["music_sources"], [])
        self.assertEqual(b.settings["library_source"], "")
        p.stop()

    def test_clear_all_and_saved_lists(self):
        b = self.backend
        p = b.localPlayer
        songs = [{"kind": "track", "id": str(self.music / "Album" / (n + ".mp3")), "title": n, "subtitle": "",
                  "file": str(self.music / "Album" / (n + ".mp3")), "cover": "", "duration": 0, "url": ""} for n in "ab"]
        p.setVolume(0)
        p.clearAll()
        p.enqueue(songs, -1)
        self.assertEqual(p.queue.rowCount(), 2)
        self.assertEqual(b.saveQueueList("", p.queueSnapshot()), "Enter a name for the list.")
        self.assertEqual(b.saveQueueList("Evening", p.queueSnapshot()), "")
        self.assertEqual(b.saveQueueList("evening", p.queueSnapshot()), "")             # same name replaces
        self.assertEqual([l["name"] for l in b.settings["queue_lists"]], ["evening"])
        p.clearAll()
        self.assertEqual(p.queue.rowCount(), 0)
        p.enqueue([{"kind": "group", "id": "g", "title": "evening", "tracks": b.settings["queue_lists"][0]["items"]}], -1)
        self.assertEqual(p.queue.rowCount(), 2)
        b.deleteQueueList("evening")
        self.assertEqual(b.settings["queue_lists"], [])
        p.clearAll()


if __name__ == "__main__":
    unittest.main()
