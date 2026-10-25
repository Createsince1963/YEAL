"""TIDAL DIY: play queue (QueueModel), player logic without any audio, and the HTML link list writer."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import _path  # noqa: F401

try:
    from PySide6.QtCore import QCoreApplication, QObject
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

from yeal.core import extras  # noqa: E402


def track(i, **kw):
    d = {"kind": "track", "id": str(i), "title": "Title %d" % i, "subtitle": "Artist", "album": "Album",
         "duration": 100 + i, "url": "https://tidal.com/browse/track/%d" % i, "cover": ""}
    d.update(kw)
    return d


def ids(model_or_items):
    items = model_or_items.items() if hasattr(model_or_items, "items") else model_or_items
    return [t["id"] for t in items]


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class QueueModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    def make(self, n=5, current=0):
        from yeal.ui.tidal_backend import QueueModel
        q = QueueModel()
        q.reset([track(i) for i in range(n)], current)
        return q

    def test_only_tracks_are_queued(self):
        from yeal.ui.tidal_backend import QueueModel
        q = QueueModel()
        q.reset([track(1), {"kind": "album", "id": "9"}, "junk", track(2)], 0)
        self.assertEqual(ids(q), ["1", "2"])
        q.insert(0, [{"kind": "video", "id": "7"}])
        self.assertEqual(q.rowCount(), 2)

    def test_reset_clamps_the_current_row(self):
        q = self.make(3, current=99)
        self.assertEqual(q.current, 0)
        q.reset([], 0)
        self.assertEqual(q.current, -1)

    def test_move_keeps_following_the_playing_track(self):
        q = self.make(5, current=2)                    # 0 1 [2] 3 4
        self.assertTrue(q.move(2, 4))                  # playing track dragged down
        self.assertEqual(ids(q), ["0", "1", "3", "4", "2"])
        self.assertEqual(q.current, 4)
        q = self.make(5, current=2)
        q.move(0, 3)                                   # a track passes the playing one from above
        self.assertEqual(ids(q), ["1", "2", "3", "0", "4"])
        self.assertEqual(q.item(q.current)["id"], "2")
        q = self.make(5, current=2)
        q.move(4, 1)                                   # ... and from below
        self.assertEqual(ids(q), ["0", "4", "1", "2", "3"])
        self.assertEqual(q.item(q.current)["id"], "2")

    def test_move_rejects_bad_rows(self):
        q = self.make(3)
        self.assertFalse(q.move(0, 0))
        self.assertFalse(q.move(-1, 1))
        self.assertFalse(q.move(0, 3))
        self.assertEqual(ids(q), ["0", "1", "2"])

    def test_remove_adjusts_the_current_row(self):
        q = self.make(4, current=2)
        q.remove(0)
        self.assertEqual(q.item(q.current)["id"], "2")
        q.remove(q.current)                            # the playing one: the next takes its place
        self.assertEqual(ids(q), ["1", "3"])
        self.assertEqual(q.current, 1)
        q.remove(1)
        self.assertEqual(q.current, 0)
        q.remove(0)
        self.assertEqual(q.current, -1)
        self.assertFalse(q.remove(0))

    def test_insert_before_the_playing_row_moves_it_along(self):
        q = self.make(3, current=1)
        q.insert(0, [track(10), track(11)])
        self.assertEqual(ids(q), ["10", "11", "0", "1", "2"])
        self.assertEqual(q.item(q.current)["id"], "1")
        q.insert(99, [track(12)])                      # beyond the end: appended
        self.assertEqual(ids(q)[-1], "12")

    def test_replace_tail_keeps_everything_up_to_the_current_row(self):
        q = self.make(5, current=1)
        q.replace_tail([track(7), track(8)])
        self.assertEqual(ids(q), ["0", "1", "7", "8"])
        q.replace_tail([])
        self.assertEqual(ids(q), ["0", "1"])

    def test_roles(self):
        q = self.make(2, current=1)
        names = {v.decode() for v in q.roleNames().values()}
        self.assertTrue({"itemId", "title", "isCurrent", "duration"} <= names)
        roles = {v.decode(): k for k, v in q.roleNames().items()}
        self.assertEqual(q.data(q.index(0), roles["itemId"]), "0")
        self.assertFalse(q.data(q.index(0), roles["isCurrent"]))
        self.assertTrue(q.data(q.index(1), roles["isCurrent"]))
        self.assertIsNone(q.data(q.index(5), roles["title"]))


class FakeOwner(QObject if HAVE_QT else object):
    """What TidalPlayer needs from TidalBackend."""
    def __init__(self):
        super().__init__()
        self.saved = {}
        self.api = None
        self.single = 0

    def settings_value(self, key, default=None):
        return self.saved.get(key, default)

    def save_setting(self, key, value):
        self.saved[key] = value

    def request_single_playback(self):
        self.single += 1

    def submit(self, fn):
        pass


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class TidalPlayerLogicTests(unittest.TestCase):
    """The queue / shuffle / repeat logic; nothing is streamed (_play_current only records the track)."""
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    def make(self):
        from yeal.ui.tidal_backend import TidalPlayer
        p = TidalPlayer(FakeOwner())
        p.played = []
        p._play_current = lambda: p.played.append(p.queue.item(p.queue.current)["id"])
        return p

    def test_play_items_starts_at_the_chosen_track(self):
        p = self.make()
        p.playItems([track(i) for i in range(5)], 2, "Album X")
        self.assertEqual(p.played, ["2"])
        self.assertEqual(p.queue.current, 2)
        self.assertEqual(p.source, "Album X")
        p.playItems([], 0, "empty")                    # nothing playable: the queue stays
        self.assertEqual(p.queue.rowCount(), 5)

    def test_queue_next_and_add(self):
        p = self.make()
        p.playItems([track(i) for i in range(3)], 0)
        p.queueNext([track(10)])
        p.queueAdd([track(11)])
        self.assertEqual(ids(p.queue), ["0", "10", "1", "2", "11"])

    def test_queue_add_on_an_empty_queue_starts_playing(self):
        p = self.make()
        p.queueAdd([track(5)])
        self.assertEqual(p.played, ["5"])

    def test_remove_the_playing_track_plays_the_next(self):
        p = self.make()
        p.playItems([track(i) for i in range(3)], 1)
        p.removeAt(1)
        self.assertEqual(p.played[-1], "2")
        p.removeAt(0)                                  # an earlier row: no new playback
        self.assertEqual(len(p.played), 2)

    def test_clear_upcoming(self):
        p = self.make()
        p.playItems([track(i) for i in range(4)], 1)
        p.clearUpcoming()
        self.assertEqual(ids(p.queue), ["0", "1"])

    def test_shuffle_only_touches_the_upcoming_tracks_and_restores_the_order(self):
        p = self.make()
        p.playItems([track(i) for i in range(30)], 3)
        before = ids(p.queue)
        p.toggleShuffle()
        after = ids(p.queue)
        self.assertEqual(after[:4], before[:4])        # played and playing tracks stay
        self.assertEqual(sorted(after), sorted(before))
        self.assertNotEqual(after, before)             # 26 tracks: shuffling to the same order is practically impossible
        p.queueAdd([track(99)])                        # added while shuffled: stays at the end after un-shuffling
        p.toggleShuffle()
        self.assertEqual(ids(p.queue), before + ["99"])

    def test_shuffle_items_starts_a_shuffled_queue(self):
        p = self.make()
        p.shuffleItems([track(i) for i in range(20)], "Mix")
        self.assertTrue(p.shuffle)
        self.assertEqual(sorted(ids(p.queue), key=int), [str(i) for i in range(20)])
        self.assertEqual(p.queue.current, 0)

    def test_repeat_cycles_off_all_one(self):
        p = self.make()
        self.assertEqual(p.repeat, "off")
        p.cycleRepeat()
        self.assertEqual(p.repeat, "all")
        p.cycleRepeat()
        self.assertEqual(p.repeat, "one")
        p.cycleRepeat()
        self.assertEqual(p.repeat, "off")

    def test_advance_at_the_end(self):
        p = self.make()
        p.playItems([track(i) for i in range(2)], 1)
        p._advance(auto=True)                          # repeat off: stops, nothing new is played
        self.assertEqual(p.played, ["1"])
        p.cycleRepeat()                                # all: wraps around
        p._advance(auto=True)
        self.assertEqual(p.played[-1], "0")
        p.cycleRepeat()                                # one: the same track again
        p._advance(auto=True)
        self.assertEqual(p.played[-1], "0")
        p._advance(auto=False)                         # the Next button ignores repeat-one
        self.assertEqual(p.played[-1], "1")

    def test_volume_is_clamped_and_remembered(self):
        p = self.make()
        p.setVolume(250)
        self.assertEqual(p.volume, 100)
        self.assertEqual(p._owner.saved["tidal_volume"], 100)
        p.setVolume(-5)
        self.assertEqual(p.volume, 0)


class LinklistTests(unittest.TestCase):
    INFO = {
        "title": "Road <Trip> & \"more\"", "subtitle": "Me", "url": "https://tidal.com/browse/playlist/abc",
        "cover": "https://resources.tidal.com/images/x/320x320.jpg",
        "items": [
            track(1, title="Song <b>one</b>", subtitle="A & B", album="Alb"),
            track(2, url="javascript:alert(1)"),                                     # not a Tidal https link: left out
            track(3, url="https://tidal.com/browse/track/3", cover="http://insecure/c.jpg"),
        ],
    }

    def test_html_is_escaped_and_links_only(self):
        page = extras.tidal_linklist_html(self.INFO)
        self.assertIn("<!doctype html>", page)
        self.assertIn("Song &lt;b&gt;one&lt;/b&gt;", page)
        self.assertNotIn("<b>one</b>", page)
        self.assertIn("A &amp; B", page)
        self.assertIn("https://tidal.com/browse/track/1", page)
        self.assertIn("https://tidal.com/browse/track/3", page)
        self.assertNotIn("javascript:", page)
        self.assertNotIn("http://insecure", page)       # only https images
        self.assertIn("Open in TIDAL", page)
        self.assertIn("2 titles", page)
        for media in (".flac", ".mp3", ".mp4", ".m4a"):  # a link list never refers to downloaded media
            self.assertNotIn(media, page)

    def test_empty_playlist_still_makes_a_page(self):
        page = extras.tidal_linklist_html({"title": "Empty", "items": []})
        self.assertIn("<title>Empty</title>", page)
        self.assertIn("0 titles", page)

    def test_files_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Tidal" / "Linklisten"
            a = extras.write_tidal_linklist(folder, self.INFO)
            b = extras.write_tidal_linklist(folder, self.INFO)
            c = extras.write_tidal_linklist(folder, self.INFO)
            self.assertEqual(len({a, b, c}), 3)
            self.assertTrue(b.name.endswith(" (2).html") and c.name.endswith(" (3).html"))
            self.assertTrue(all(p.parent == folder and p.suffix == ".html" for p in (a, b, c)))
            self.assertNotIn("<", a.name + ">" )
            self.assertTrue(a.read_text(encoding="utf-8").startswith("<!doctype html>"))

    def test_unwritable_target_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "file"
            blocker.write_text("x")
            self.assertIsNone(extras.write_tidal_linklist(blocker / "sub", self.INFO))


if __name__ == "__main__":
    unittest.main()
