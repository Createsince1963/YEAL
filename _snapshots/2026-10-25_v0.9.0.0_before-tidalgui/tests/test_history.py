import datetime as dt
import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from yeal.core import history
from yeal.core.models import DownloadJob, DownloadOptions, JobState


def _job(url, state=JobState.DONE, created=1.0, filename="", mode="audio"):
    j = DownloadJob(1, url, DownloadOptions(mode=mode).normalized())
    j.state, j.created, j.filename, j.title = state, created, filename, "T"
    return j


class HistoryTests(unittest.TestCase):
    def test_video_key(self):
        a = history.video_key("https://www.youtube.com/watch?v=abcDEF12345&t=5")
        b = history.video_key("https://youtu.be/abcDEF12345")
        self.assertEqual(a, b)

    def test_sections(self):
        now = dt.datetime(2026, 10, 23, 12)
        ts = lambda d: (now - dt.timedelta(days=d)).timestamp()
        self.assertEqual(history.section_label(ts(0), now), "Today")
        self.assertEqual(history.section_label(ts(1), now), "Yesterday")
        self.assertTrue(history.section_label(ts(20), now).startswith("Week"))
        self.assertEqual(history.section_label(ts(500), now), "2025")

    def test_roundtrip_and_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a.mp3"
            f.write_bytes(b"x")
            p = Path(d) / "history.json"
            jobs = [_job("https://youtu.be/abcDEF12345", filename=str(f)),
                    _job("https://youtu.be/zzzzzzzzzzz", state=JobState.ERROR)]
            history.save(p, jobs)
            loaded = history.load(p)
            self.assertEqual(len(loaded), 2)
            hit = history.find_done(loaded, "https://www.youtube.com/watch?v=abcDEF12345", "audio")
            self.assertIsNotNone(hit)
            self.assertIsNone(history.find_done(loaded, "https://youtu.be/abcDEF12345", "video"))
            f.unlink()
            self.assertIsNone(history.find_done(loaded, "https://youtu.be/abcDEF12345", "audio"))

    def test_corrupt_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "h.json"
            p.write_text("{nope")
            self.assertEqual(history.load(p), [])


if __name__ == "__main__":
    unittest.main()


class AlbumTitleTests(unittest.TestCase):
    def test_track_title_from_tracklist(self):
        from yeal.core import album
        ch = [{"title": "Setting the burden down (Intro)."}, {"title": ""}]
        self.assertEqual(album.track_title(ch, 1, Path("01 - x.mp3")), "Setting the burden down (Intro).")
        self.assertEqual(album.track_title(ch, 2, Path("02 - Fallback name.mp3")), "Fallback name")
        self.assertEqual(album.track_title([], 1, Path("01 - A.mp3")), "A")

    def test_keep_whole_default(self):
        self.assertTrue(DownloadOptions().normalized().keep_whole)
        self.assertFalse(DownloadOptions(keep_whole=False).normalized().keep_whole)


class ProbeChapterTests(unittest.TestCase):
    def test_probe_reports_chapters(self):
        from yeal.core import audioprobe

        class FakeYdl:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def extract_info(self, url, download=False):
                return {"title": "t", "formats": [], "chapters": [{"title": "a"}, {"title": "b"}]}
        self.assertEqual(audioprobe.probe("https://x", FakeYdl, {})["chapters"], 2)
