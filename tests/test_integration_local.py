"""End-to-end with the REAL yt-dlp and ffmpeg, but no internet: a tiny test video is
generated locally and served from 127.0.0.1 (yt-dlp's generic extractor downloads it).
Skipped automatically when yt-dlp or ffmpeg is missing."""
import functools
import http.server
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

import _path  # noqa: F401
from test_core import make_ctx

try:
    import yt_dlp  # noqa: F401
    HAVE_YTDLP = True
except ImportError:
    HAVE_YTDLP = False

from yeal.platforms.desktop import find_ffmpeg  # noqa: E402

FFMPEG = find_ffmpeg()


@unittest.skipUnless(HAVE_YTDLP and FFMPEG, "yt-dlp and ffmpeg required")
class LocalIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        (root / "www").mkdir()
        subprocess.run([str(FFMPEG), "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=2",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-shortest",
                        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
                        str(root / "www" / "clip.mp4")], check=True)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root / "www"))
        handler.log_message = lambda *a, **k: None
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/clip.mp4"
        cls.root = root

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def run_engine(self, name, options, ffmpeg=True):
        from yeal.core.engine import Engine
        from yeal.core.models import DownloadJob
        ctx = make_ctx(self.root / name, ffmpeg=False)
        ctx.ffmpeg = FFMPEG if ffmpeg else None
        job = DownloadJob(1, self.url, options)
        Engine(ctx).run(job, threading.Event(), lambda j: None)
        return job, ctx

    def test_video_download(self):
        from yeal.core.models import DownloadOptions, JobState
        job, ctx = self.run_engine("video", DownloadOptions(embed_metadata=False))
        self.assertEqual(job.state, JobState.DONE, job.error)
        files = list((ctx.download_dir / "Video").glob("*.mp4"))
        self.assertEqual(len(files), 1)
        self.assertGreater(files[0].stat().st_size, 1000)

    def test_mp3_has_two_separate_progress_parts(self):
        from yeal.core.engine import Engine
        from yeal.core.models import DownloadJob, DownloadOptions, JobState
        ctx = make_ctx(self.root / "mp3", ffmpeg=False)
        ctx.ffmpeg = FFMPEG
        job = DownloadJob(1, self.url, DownloadOptions(mode="audio", audio_format="mp3").normalized())
        seen = []
        Engine(ctx).run(job, threading.Event(), lambda j: seen.append((j.dl_progress, j.pp_progress, j.progress)))
        self.assertEqual(job.state, JobState.DONE, job.error)
        self.assertEqual((job.dl_progress, job.pp_progress, job.progress), (1.0, 1.0, 1.0))
        # download part finishes before the creation part starts, and neither goes backwards
        self.assertTrue(any(dl == 1.0 and pp == 0.0 for dl, pp, _ in seen))
        self.assertEqual([x[2] for x in seen], sorted(x[2] for x in seen))
        self.assertEqual([x[1] for x in seen], sorted(x[1] for x in seen))
        self.assertEqual(len(list((ctx.download_dir / "Audio").glob("*.mp3"))), 1)

    def test_default_options_with_metadata_postprocessing(self):
        from yeal.core.models import DownloadOptions, JobState
        job, ctx = self.run_engine("meta", DownloadOptions())  # embed_metadata=True
        self.assertEqual(job.state, JobState.DONE, job.error)
        self.assertEqual(len(list((ctx.download_dir / "Video").glob("*.mp4"))), 1)

    def test_audio_extraction_needs_ffmpeg(self):
        from yeal.core.models import DownloadOptions, JobState
        job, ctx = self.run_engine("audio", DownloadOptions(mode="audio", audio_format="mp3",
                                                            embed_metadata=False))
        self.assertEqual(job.state, JobState.DONE, job.error)
        self.assertEqual(len(list((ctx.download_dir / "Audio").glob("*.mp3"))), 1)

    def test_android_like_mode_without_ffmpeg(self):
        from yeal.core.models import DownloadOptions, JobState
        job, ctx = self.run_engine("noff", DownloadOptions(), ffmpeg=False)
        self.assertEqual(job.state, JobState.DONE, job.error)
        self.assertEqual(len(list((ctx.download_dir / "Video").glob("*.mp4"))), 1)

    def test_bad_url_reports_error(self):
        from yeal.core.engine import Engine
        from yeal.core.models import DownloadJob, DownloadOptions, JobState
        ctx = make_ctx(self.root / "bad", ffmpeg=False)
        job = DownloadJob(2, f"http://127.0.0.1:{self.server.server_port}/missing.mp4", DownloadOptions())
        Engine(ctx).run(job, threading.Event(), lambda j: None)
        self.assertEqual(job.state, JobState.ERROR)
        self.assertTrue(job.error)


class FramesTest(unittest.TestCase):
    def test_extract_frames_every_two_seconds(self):
        import shutil, subprocess
        from yeal.core import frames
        ff = shutil.which("ffmpeg")
        if not ff:
            self.skipTest("ffmpeg not installed")
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / "clip one.mp4"
            subprocess.run([ff, "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=10:size=160x90:rate=10",
                            "-pix_fmt", "yuv420p", str(video)], check=True)
            out = frames.target_dir(d, video)
            self.assertEqual(out, Path(d) / "Frames" / "clip one")
            n = frames.extract(ff, video, out, 2, 8, 2, "jpg")
            self.assertEqual(n, 3)
            names = sorted(p.name for p in out.iterdir())
            self.assertEqual(names[0], "clip one_00h00m02s.jpg")
            self.assertEqual(names[-1], "clip one_00h00m06s.jpg")
            out.mkdir(exist_ok=True)
            self.assertEqual(frames.target_dir(d, video).name, "clip one (2)")
            with self.assertRaises(ValueError):
                frames.extract(ff, video, out, 5, 3, 1)
            self.assertAlmostEqual(frames.probe_duration(ff, video), 10.0, delta=0.2)
            dur, strip = frames.filmstrip(ff, video, Path(d) / "tmp", count=5)
            self.assertEqual(len(strip), 5)
            self.assertEqual(frames.parse_time("1:02:03"), 3723.0)
            with self.assertRaises(ValueError):
                frames.parse_time("abc")


if __name__ == "__main__":
    unittest.main()
