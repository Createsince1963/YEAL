import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from yeal.core import extras, lyrics
from yeal.core.models import DownloadOptions
from yeal.core.presets import build_ydl_opts
from test_core import make_ctx

SYNCED = "[00:01.50] first line\n[00:04.00] second line\n[00:08.25] third line"


class FakeResp:
    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def read(self, n=-1):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener_for(results):
    return lambda req, timeout=0: FakeResp(results)


class LyricsTests(unittest.TestCase):
    def test_guess_track(self):
        self.assertEqual(lyrics.guess_track({"artist": "A", "track": "T (Official Video)"}), ("A", "T (Official Video)".replace(" (Official Video)", "")))
        self.assertEqual(lyrics.guess_track({"title": "Band - Song (Official Lyric Video)"}), ("Band", "Song"))
        self.assertEqual(lyrics.guess_track({"title": "Song", "uploader": "Band - Topic"}), ("Band", "Song"))

    def test_fetch_picks_matching_duration(self):
        res = [{"duration": 300, "plainLyrics": "wrong", "trackName": "x", "artistName": "y"},
               {"duration": 181, "plainLyrics": "right", "syncedLyrics": SYNCED, "trackName": "T", "artistName": "A"}]
        got = lyrics.fetch("A", "T", 180, opener_for(res))
        self.assertEqual(got["plain"], "right")
        self.assertIn("first line", got["synced"])
        self.assertEqual(lyrics.fetch("A", "T", 90, opener_for(res)), {})   # no song of that length

    def test_fetch_offline_gives_empty(self):
        def boom(req, timeout=0):
            raise OSError("offline")
        self.assertEqual(lyrics.fetch("A", "T", 100, boom), {})

    def test_plain_from_synced(self):
        got = lyrics.fetch("A", "T", 0, opener_for([{"duration": 5, "syncedLyrics": SYNCED}]))
        self.assertEqual(got["plain"].splitlines()[0], "first line")

    def test_srt_and_files(self):
        srt = lyrics.lrc_to_srt(SYNCED, 12)
        self.assertIn("00:00:01,500 --> 00:00:03,950", srt)
        self.assertTrue(srt.rstrip().endswith("third line"))
        with tempfile.TemporaryDirectory() as d:
            media = str(Path(d) / "song.mp3")
            found = {"plain": "a\nb", "synced": SYNCED, "artist": "A", "title": "T"}
            self.assertTrue(lyrics.write_lyrics(media, found))
            self.assertTrue(lyrics.write_srt(media, found, 12))
            self.assertTrue((Path(d) / "song.txt").read_text().startswith("A - T"))
            self.assertTrue((Path(d) / "song.lrc").exists())
            self.assertTrue((Path(d) / "song.srt").exists())

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg missing")
    def test_embed_into_mp3(self):
        with tempfile.TemporaryDirectory() as d:
            mp3 = Path(d) / "s.mp3"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=d=1", str(mp3)], check=True)
            self.assertTrue(lyrics.embed("ffmpeg", str(mp3), "hello\nworld"))
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags", str(mp3)],
                                 capture_output=True, text=True).stdout
            self.assertIn("hello", out)

    def test_html_shows_synced_lyrics(self):
        page = extras.description_html({"title": "T"}, "s.mp3", "audio", False, "dark",
                                       {"plain": "x", "synced": SYNCED, "source": "lrclib"})
        self.assertIn('class="ly" data-t="1.50"', page)
        self.assertIn("<h2>Lyrics</h2>", page)
        cap = extras.description_html({"title": "T"}, "s.mp3", "audio", False, "dark",
                                      {"plain": "a\nb", "synced": "", "source": "captions"})
        self.assertIn("from captions", cap)
        self.assertNotIn("Lyrics", extras.description_html({"title": "T"}))

    def test_audio_prefers_highest_bitrate_and_subs_for_lyrics(self):
        o = build_ydl_opts(DownloadOptions(mode="audio", save_lyrics=True), make_ctx(tempfile.gettempdir()))
        self.assertEqual(o["format_sort"][0], "abr")
        self.assertTrue(o["writeautomaticsub"])


if __name__ == "__main__":
    unittest.main()


class FallbackTests(unittest.TestCase):
    def test_subtitle_error_switches_subs_off(self):
        from yeal.core.engine import apply_fallback
        opts = {"writesubtitles": True, "writeautomaticsub": True, "subtitleslangs": ["de"],
                "postprocessors": [{"key": "FFmpegEmbedSubtitle"}, {"key": "FFmpegMetadata"}]}
        done = set()
        note = apply_fallback(RuntimeError("Unable to download video subtitles for 'de': HTTP Error 429"), opts, done)
        self.assertIn("Subtitles", note)
        self.assertFalse(opts["writesubtitles"])
        self.assertEqual([p["key"] for p in opts["postprocessors"]], ["FFmpegMetadata"])
        self.assertEqual(apply_fallback(RuntimeError("Unable to download video subtitles"), opts, done), "")  # once
        self.assertEqual(apply_fallback(RuntimeError("Video unavailable"), opts, done), "")

    def test_quality_and_cover_fallbacks(self):
        from yeal.core.engine import apply_fallback
        opts = {"format": "bv*[height<=2160]+ba/b", "writethumbnail": True,
                "postprocessors": [{"key": "EmbedThumbnail"}, {"key": "FFmpegMetadata"}]}
        self.assertIn("quality", apply_fallback(RuntimeError("Requested format is not available"), opts, set()))
        self.assertEqual(opts["format"], "bv*+ba/b")
        self.assertIn("cover", apply_fallback(RuntimeError("Unable to embed thumbnail"), opts, set()))
        self.assertFalse(opts["writethumbnail"])

    def test_engine_continues_after_subtitle_error(self):
        import threading
        from yeal.core.engine import Engine
        from yeal.core.models import DownloadJob, JobState

        class Ydl:
            calls = []

            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def extract_info(self, url, download=True):
                Ydl.calls.append(bool(self.opts.get("writesubtitles")))
                if self.opts.get("writesubtitles"):
                    raise RuntimeError("Unable to download video subtitles for 'de': HTTP Error 429")
                return {"title": "T"}

        with tempfile.TemporaryDirectory() as d:
            job = DownloadJob(1, "https://youtu.be/x", DownloadOptions(subtitles=True))
            Engine(make_ctx(d), ydl_class=Ydl).run(job, threading.Event(), lambda j: None)
        self.assertEqual(job.state, JobState.DONE)
        self.assertEqual(Ydl.calls, [True, False])
        self.assertIn("Subtitles", job.note)


class FriendlyErrorTests(unittest.TestCase):
    def test_reasons(self):
        from yeal.core.engine import friendly_error
        from yeal.core.queue import rate_limited
        e = friendly_error(RuntimeError("ERROR: [youtube] x: Sign in to confirm you're not a bot"))
        self.assertTrue(e.startswith("Stopped automatically:"))
        self.assertTrue(rate_limited(e))                       # the queue still pauses itself
        self.assertIn("private", friendly_error(RuntimeError("ERROR: [youtube] x: Private video. Sign in")).lower())
        self.assertIn("connection", friendly_error(OSError("<urlopen error timed out>")).lower())
        self.assertIn("Update yt-dlp", friendly_error(RuntimeError("ERROR: [youtube] x: nsig extraction failed")))
        other = friendly_error(RuntimeError("ERROR: something odd"))
        self.assertEqual(other, "Stopped automatically: something odd")
