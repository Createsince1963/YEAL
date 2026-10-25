"""Tidal support (0.9.0.0): URL detection, tiddl command line, login state, engine run with a fake tiddl."""
import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import _path  # noqa: F401
from yeal.core import tidal
from yeal.core.engine import Engine
from yeal.core.models import DownloadJob, DownloadOptions, JobState
from yeal.core.settings import Settings

FAKE = """#!{py}
import sys
args = sys.argv[1:]
if args[:2] == ["download", "-q"]:
    sys.stdout.write("Resolving album\\r\\n")
    sys.stdout.write("\\x1b[32mDownloaded\\x1b[0m 01. Song A\\n")
    sys.stdout.write("Downloaded 02. Song B\\n")
    sys.exit(int(__import__("os").environ.get("FAKE_CODE", "0")))
sys.exit(2)
"""


def make_fake(folder: Path) -> str:
    exe = folder / ("tiddl.cmd" if os.name == "nt" else "tiddl")
    exe.write_text(FAKE.format(py=sys.executable), encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return str(exe)


class FakeCtx:
    def __init__(self, root: Path):
        self.download_dir = root / "dl"
        self.data_dir = root / "data"
        self.temp_dir = root / "tmp"

    def ensure_dirs(self):
        for d in (self.download_dir, self.data_dir, self.temp_dir):
            d.mkdir(parents=True, exist_ok=True)


class UrlTests(unittest.TestCase):
    def test_tidal_urls(self):
        for url in ("https://tidal.com/browse/album/103805723", "https://listen.tidal.com/track/103805726",
                    "https://tidal.com/playlist/1b2c3d4e-1111-2222-3333-444455556666",
                    "https://tidal.com/browse/artist/3566483", "http://www.tidal.com/browse/mix/0123abc"):
            self.assertTrue(tidal.is_tidal_url(url), url)

    def test_other_urls(self):
        for url in ("https://www.youtube.com/watch?v=abc", "https://tidal.com/", "https://evil.com/tidal.com/browse/album/1",
                    "https://tidal.com.evil.com/browse/album/1", "ftp://tidal.com/browse/album/1", "", "album/1"):
            self.assertFalse(tidal.is_tidal_url(url), url)

    def test_resource(self):
        self.assertEqual(tidal.resource_of("https://tidal.com/browse/album/103805723?x=1"), "album/103805723")


class CommandTests(unittest.TestCase):
    def test_build_command(self):
        cmd = tidal.build_command("tiddl", "https://tidal.com/browse/album/1", "max", "D:/Music", 3)
        self.assertEqual(cmd[:6], ["tiddl", "download", "-q", "max", "-t", "3"])
        self.assertEqual(cmd[-2:], ["url", "https://tidal.com/browse/album/1"])
        self.assertIn("-p", cmd)

    def test_bad_values_fall_back(self):
        cmd = tidal.build_command("tiddl", "u", "ultra", "", 99)
        self.assertEqual(cmd[3], "high")
        self.assertEqual(cmd[5], "4")

    def test_video_options(self):
        cmd = tidal.build_command("tiddl", "https://tidal.com/browse/album/1", "high", "", 2, "hd", "only")
        self.assertEqual(cmd[6:10], ["-vq", "hd", "--videos", "only"])
        cmd = tidal.build_command("tiddl", "https://tidal.com/browse/album/1")        # defaults: Full HD, videos included
        self.assertEqual(cmd[6:10], ["-vq", "fhd", "--videos", "allow"])
        # tiddl skips videos by default, even a direct video link: a single video must never be skipped
        cmd = tidal.build_command("tiddl", "https://tidal.com/browse/video/77", "high", "", 2, "fhd", "none")
        self.assertEqual(cmd[cmd.index("--videos") + 1], "allow")
        # inside collections the user's choice stays
        cmd = tidal.build_command("tiddl", "https://tidal.com/browse/playlist/abc", "high", "", 2, "fhd", "none")
        self.assertEqual(cmd[cmd.index("--videos") + 1], "none")
        cmd = tidal.build_command("tiddl", "u", "high", "", 2, "8k", "maybe")
        self.assertEqual((cmd[7], cmd[9]), ("fhd", "allow"))

    def test_output_folders(self):
        """Singles / Playlists / Videos as sub folders of the Tidal folder."""
        def tmpl(url):
            cmd = tidal.build_command("tiddl", url, "high", "D:/Tidal", 2)
            return cmd[cmd.index("-o") + 1]
        self.assertTrue(tmpl("https://tidal.com/browse/track/1").startswith("Singles/"))
        self.assertTrue(tmpl("https://listen.tidal.com/track/1").startswith("Singles/"))
        self.assertTrue(tmpl("https://tidal.com/browse/video/9").startswith("Videos/"))
        self.assertTrue(tmpl("https://tidal.com/browse/playlist/abc-def").startswith("Playlists/{playlist.title}/"))
        self.assertTrue(tmpl("https://tidal.com/browse/mix/00abc").startswith("Playlists/Mix {mix_id}/"))
        self.assertTrue(tmpl("https://tidal.com/browse/album/5").startswith("Albums/"))
        self.assertTrue(tmpl("https://tidal.com/browse/artist/5").startswith("Albums/"))
        cmd = tidal.build_command("tiddl", "https://tidal.com/browse/track/1", "high", "D:/Tidal", 2)
        self.assertEqual(cmd[-2:], ["url", "https://tidal.com/browse/track/1"])      # url stays last
        self.assertEqual(cmd[cmd.index("-p") + 1], "D:/Tidal")

    def test_classify_and_ansi(self):
        self.assertEqual(tidal.classify(tidal.strip_ansi("\x1b[32mDownloaded\x1b[0m x")), "done")
        self.assertEqual(tidal.classify("Not logged in."), "login")
        self.assertEqual(tidal.classify("Error: boom"), "error")
        self.assertEqual(tidal.classify("Resolving"), "info")

    def test_login_state(self):
        with tempfile.TemporaryDirectory() as d:
            auth = Path(d) / "auth.json"
            self.assertFalse(tidal.is_logged_in(auth))
            auth.write_text(json.dumps({"token": None}))
            self.assertFalse(tidal.is_logged_in(auth))
            auth.write_text("not json")
            self.assertFalse(tidal.is_logged_in(auth))
            auth.write_text(json.dumps({"token": "abc", "user_id": "1"}))
            self.assertTrue(tidal.is_logged_in(auth))

    def test_find_tiddl_configured(self):
        with tempfile.TemporaryDirectory() as d:
            exe = make_fake(Path(d))
            self.assertEqual(tidal.find_tiddl(exe), exe)
            self.assertEqual(tidal.find_tiddl(str(Path(d) / "missing")), "")


class SettingsTests(unittest.TestCase):
    def test_validation(self):
        s = Settings(tidal_quality="ultra", tidal_threads=99, tidal_path=None).validate()
        self.assertEqual((s.tidal_quality, s.tidal_threads, s.tidal_path), ("high", 4, ""))
        self.assertEqual(Settings(tidal_threads="x").validate().tidal_threads, 2)
        v = Settings(tidal_video_quality="8k", tidal_videos="maybe").validate()
        self.assertEqual((v.tidal_video_quality, v.tidal_videos), ("fhd", "allow"))
        self.assertEqual((Settings().tidal_video_quality, Settings().tidal_videos), ("fhd", "allow"))


@unittest.skipIf(os.name == "nt", "fake tiddl is a POSIX script")
class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "app").mkdir()
        (self.root / "app" / "auth.json").write_text(json.dumps({"token": "t"}))
        self.old = os.environ.get("TIDDL_PATH")
        os.environ["TIDDL_PATH"] = str(self.root / "app")
        self.exe = make_fake(self.root)
        self.engine = Engine(FakeCtx(self.root))
        self.engine.tidal_config = lambda: {"path": self.exe, "quality": "high", "threads": 2}

    def tearDown(self):
        if self.old is None:
            os.environ.pop("TIDDL_PATH", None)
        else:
            os.environ["TIDDL_PATH"] = self.old
        self.tmp.cleanup()

    def run_job(self, url="https://tidal.com/browse/album/1"):
        job = DownloadJob(1, url, DownloadOptions(mode="audio"))
        seen = []
        self.engine.run(job, threading.Event(), lambda j: seen.append(j.progress))
        return job, seen

    def test_success(self):
        job, seen = self.run_job()
        self.assertEqual(job.state, JobState.DONE)
        self.assertEqual(job.playlist_index, 2)
        self.assertEqual(job.progress, 1.0)
        self.assertTrue(job.filename.endswith("Tidal"))
        self.assertEqual(seen, sorted(seen))        # progress never goes backwards

    def test_failure_code(self):
        os.environ["FAKE_CODE"] = "1"
        try:
            job, _ = self.run_job()
        finally:
            os.environ.pop("FAKE_CODE")
        self.assertEqual(job.state, JobState.DONE)    # some items were downloaded
        self.assertIn("failed", job.note)

    def test_not_logged_in(self):
        (self.root / "app" / "auth.json").unlink()
        job, _ = self.run_job()
        self.assertEqual(job.state, JobState.ERROR)
        self.assertIn("Tidal", job.error)

    def test_helper_missing(self):
        self.engine.tidal_config = lambda: {"path": str(self.root / "nope"), "quality": "high", "threads": 2}
        old_path = os.environ["PATH"]
        os.environ["PATH"] = ""
        try:
            job, _ = self.run_job()
        finally:
            os.environ["PATH"] = old_path
        self.assertEqual(job.state, JobState.ERROR)
        self.assertIn("tiddl", job.error)


class LoginLinkTests(unittest.TestCase):
    def test_only_the_tidal_link_is_taken(self):
        f = tidal.find_login_link
        self.assertEqual(f("Go to 'https://link.tidal.com/ABCDE' and complete authentication!"), "https://link.tidal.com/ABCDE")
        self.assertEqual(f("Go to 'link.tidal.com/ABCDE' and complete authentication!"), "https://link.tidal.com/ABCDE")
        self.assertEqual(f("New version 3.5 available, see https://github.com/oskvr37/tiddl/blob/main/README.md"), "")
        self.assertEqual(f("Authenticating..."), "")


class JobQualityTests(unittest.TestCase):
    def test_job_quality_overrides_global_setting(self):
        """The quality picked in the download options is stored per job and wins over Settings > Tidal."""
        self.assertEqual(DownloadOptions(tidal_quality="max").normalized().tidal_quality, "max")
        self.assertEqual(DownloadOptions(tidal_quality="bogus").normalized().tidal_quality, "")
        cmd = tidal.build_command("tiddl", "https://tidal.com/browse/album/571379403", "max", "D:/x")
        self.assertEqual(cmd[cmd.index("-q") + 1], "max")
        self.assertEqual(set(tidal.TIDAL_QUALITY_LABELS), set(tidal.TIDAL_QUALITIES))


if __name__ == "__main__":
    unittest.main()
