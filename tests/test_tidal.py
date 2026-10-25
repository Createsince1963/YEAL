"""Tidal support (0.9.0.0, extended in 0.9.1): URL detection, tiddl command line, login state, Yeal's own tiddl
folder (config.toml, auth.json mirror), HTML pages, engine run with a fake tiddl."""
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
    import os
    out = os.environ.get("FAKE_ENV_OUT")
    if out:
        open(out, "w", encoding="utf-8").write(os.environ.get("TIDDL_PATH", "") + "\\n" + " ".join(args))
    if os.environ.get("FAKE_WRITE"):
        base = args[args.index("-p") + 1]
        folder = os.path.join(base, "Albums", "Deep Purple", "Machine Head")
        os.makedirs(folder, exist_ok=True)
        for name in ("01 - Highway Star.flac", "02 - Maybe I'm a Leo.flac"):
            open(os.path.join(folder, name), "wb").write(b"fLaC")
    sys.stdout.write("Resolving album\\r\\n")
    sys.stdout.write("\\x1b[32mDownloaded\\x1b[0m 01. Song A\\n")
    sys.stdout.write("Downloaded 02. Song B\\n")
    sys.exit(int(__import__("os").environ.get("FAKE_CODE", "0")))
sys.exit(2)
"""


def make_fake(folder: Path) -> str:
    if os.name == "nt":          # Windows: a .cmd wrapper starts the fake script with this Python
        script = folder / "fake_tiddl.py"
        script.write_text(FAKE.format(py=sys.executable), encoding="utf-8")
        exe = folder / "tiddl.cmd"
        exe.write_text('@"%s" "%s" %%*\r\n' % (sys.executable, script), encoding="utf-8")
        return str(exe)
    exe = folder / "tiddl"
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

    def test_runs_in_own_tiddl_folder_with_options(self):
        out = self.root / "env.txt"
        os.environ["FAKE_ENV_OUT"] = str(out)
        self.engine.tidal_config = lambda: {"path": self.exe, "quality": "high", "threads": 2, "atmos": "allow",
                                            "no_skip": True, "extras": {"m3u": True}}
        try:
            job, _ = self.run_job()
        finally:
            os.environ.pop("FAKE_ENV_OUT")
        self.assertEqual(job.state, JobState.DONE)
        home, args = out.read_text(encoding="utf-8").splitlines()
        self.assertEqual(Path(home), self.root / "data" / "tiddl")
        self.assertIn("--dolby-atmos allow", args)
        self.assertIn("--no-skip", args)
        self.assertIn("save = true", (Path(home) / "config.toml").read_text(encoding="utf-8").split("[m3u]")[1])
        self.assertEqual(json.loads((Path(home) / "auth.json").read_text())["token"], "t")

    def test_html_page_after_download(self):
        os.environ["FAKE_WRITE"] = "1"
        self.engine.tidal_config = lambda: {"path": self.exe, "quality": "high", "threads": 2, "html": True}
        try:
            job, _ = self.run_job()
        finally:
            os.environ.pop("FAKE_WRITE")
        self.assertEqual(job.state, JobState.DONE)
        page = self.root / "dl" / "Tidal" / "Albums" / "Deep Purple" / "Machine Head" / "Machine Head.html"
        self.assertTrue(page.is_file())

    def test_job_points_at_the_album_folder(self):
        os.environ["FAKE_WRITE"] = "1"
        try:
            job, _ = self.run_job()
        finally:
            os.environ.pop("FAKE_WRITE")
        self.assertTrue(job.filename.replace("\\", "/").endswith("Albums/Deep Purple/Machine Head"), job.filename)

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


class OwnTiddlFolderTests(unittest.TestCase):
    """0.9.1: downloads run with TIDDL_PATH=<data>/tiddl, the user's ~/.tiddl setup is not changed."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.glob = self.root / "global"
        self.glob.mkdir()
        self.home = self.root / "data" / "tiddl"

    def tearDown(self):
        self.tmp.cleanup()

    def auth(self, folder, token, expires):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "auth.json").write_text(json.dumps({"token": token, "expires_at": expires}), encoding="utf-8")

    def token(self, folder):
        return json.loads((folder / "auth.json").read_text(encoding="utf-8"))["token"]

    def test_new_options_on_the_command_line(self):
        cmd = tidal.build_command("tiddl", "https://tidal.com/browse/artist/5", "max", "D:/x", 2, "fhd", "allow",
                                  "only", "include", True, True)
        self.assertEqual(cmd[cmd.index("--dolby-atmos") + 1], "only")
        self.assertEqual(cmd[cmd.index("--singles") + 1], "include")
        self.assertIn("--no-skip", cmd)
        self.assertIn("--rewrite-metadata", cmd)
        self.assertEqual(cmd[-2:], ["url", "https://tidal.com/browse/artist/5"])
        cmd = tidal.build_command("tiddl", "https://tidal.com/browse/album/5", "high", "", 2, "fhd", "allow", "bogus", "only")
        self.assertEqual(cmd[cmd.index("--dolby-atmos") + 1], "none")
        self.assertNotIn("--singles", cmd)             # singles only matter for artist links
        self.assertNotIn("--no-skip", cmd)

    def test_config_toml_is_valid_toml(self):
        import tomllib
        data = tomllib.loads(tidal.config_toml(lyrics=True, lrc=False, cover_embed=True, cover_file=True, m3u=False))
        self.assertEqual(data["metadata"], {"enable": True, "lyrics": True, "cover": True})
        self.assertEqual(data["download"], {"write_lrc_file": False})
        self.assertEqual(data["cover"]["save"], True)
        self.assertEqual(data["m3u"]["save"], False)
        self.assertEqual(data["m3u"]["allowed"], ["album", "playlist", "mix"])

    def test_prepare_home_writes_config_and_copies_login(self):
        self.auth(self.glob, "global", 100)
        tidal.prepare_home(self.home, {"lyrics": True}, global_dir=self.glob)
        self.assertIn("lyrics = true", (self.home / "config.toml").read_text(encoding="utf-8"))
        self.assertEqual(self.token(self.home), "global")
        self.assertFalse((self.glob / "config.toml").exists())       # the user's tiddl setup is untouched

    def test_newer_token_is_never_replaced_by_an_older_one(self):
        self.auth(self.glob, "old", 100)
        self.auth(self.home, "renewed", 200)
        tidal.prepare_home(self.home, global_dir=self.glob)
        self.assertEqual(self.token(self.home), "renewed")
        self.assertTrue(tidal.sync_auth_back(self.home, global_dir=self.glob))
        self.assertEqual(self.token(self.glob), "renewed")
        self.assertFalse(tidal.sync_auth_back(self.home, global_dir=self.glob))   # same age: nothing to copy

    def test_html_pages_for_new_album_folders(self):
        import time
        base = self.root / "Tidal"
        album = base / "Albums" / "A" / "B"
        album.mkdir(parents=True)
        single = base / "Singles"
        single.mkdir()
        start = time.time()
        (album / "01 - One.flac").write_bytes(b"x")
        (album / "02 - Two.flac").write_bytes(b"x")
        (single / "X - Y.flac").write_bytes(b"x")
        pages = tidal.write_html_pages(base, start, "https://tidal.com/browse/album/1")
        self.assertEqual(pages, [album / "B.html"])
        text = pages[0].read_text(encoding="utf-8")
        self.assertIn("01%20-%20One.flac", text)
        self.assertIn("One", text)
        self.assertNotIn(str(album), text)       # relative links only


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


class JobDescriptionTests(unittest.TestCase):
    """The download list shows song / album / playlist, artist and cover - never the technical id - and the HTML page
    carries the id (as a link) and the cover of every title."""
    TRACKS = [
        {"kind": "track", "id": "111", "title": "Highway Star", "subtitle": "Deep Purple", "url": "https://tidal.com/browse/track/111",
         "cover": "https://resources.tidal.com/images/aa/bb/160x160.jpg"},
        {"kind": "track", "id": "222", "title": "Maybe I'm a Leo", "subtitle": "Deep Purple", "url": "https://tidal.com/browse/track/222",
         "cover": "https://resources.tidal.com/images/cc/dd/160x160.jpg"},
    ]
    META = {"kind": "album", "id": "1", "title": "Machine Head", "artist": "Deep Purple",
            "cover": "https://resources.tidal.com/images/aa/bb/320x320.jpg", "items": TRACKS}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "app").mkdir()
        (self.root / "app" / "auth.json").write_text(json.dumps({"token": "t"}))
        self.old = os.environ.get("TIDDL_PATH")
        os.environ["TIDDL_PATH"] = str(self.root / "app")
        self.exe = make_fake(self.root)
        self.engine = Engine(FakeCtx(self.root))
        self.engine.tidal_config = lambda: {"path": self.exe, "quality": "high", "threads": 2, "html": True}

    def tearDown(self):
        if self.old is None:
            os.environ.pop("TIDDL_PATH", None)
        else:
            os.environ["TIDDL_PATH"] = self.old
        self.tmp.cleanup()

    def run_job(self, url="https://tidal.com/browse/album/1"):
        job = DownloadJob(1, url, DownloadOptions(mode="audio"))
        seen = []
        self.engine.run(job, threading.Event(), lambda j: seen.append((j.title, j.uploader, j.thumbnail)))
        return job, seen

    def test_job_gets_title_artist_and_cover(self):
        self.engine.tidal_meta = lambda url: self.META
        job, seen = self.run_job()
        self.assertEqual((job.title, job.uploader), ("Machine Head", "Deep Purple"))
        self.assertTrue(job.thumbnail.startswith("https://resources.tidal.com/"))
        self.assertEqual(job.playlist_count, 2)
        self.assertFalse(any("album/1" in t for t, _, _ in seen[1:]))     # after the lookup the id is gone from the title

    def test_single_song_shows_song_and_artist(self):
        meta = dict(self.META, kind="track", id="111", title="Highway Star", items=self.TRACKS[:1])
        self.engine.tidal_meta = lambda url: meta
        job, _ = self.run_job("https://tidal.com/browse/track/111")
        self.assertEqual((job.title, job.uploader), ("Highway Star", "Deep Purple"))
        self.assertEqual(job.playlist_count, 0)

    def test_lookup_failure_keeps_the_link_and_the_download_works(self):
        def boom(url):
            raise RuntimeError("offline")
        self.engine.tidal_meta = boom
        job, _ = self.run_job()
        self.assertEqual(job.state, JobState.DONE)
        self.assertEqual(job.title, "album/1")
        self.assertEqual(job.thumbnail, "")

    def test_html_page_has_cover_artist_and_id_per_title(self):
        os.environ["FAKE_WRITE"] = "1"
        self.engine.tidal_meta = lambda url: self.META
        try:
            job, _ = self.run_job()
        finally:
            os.environ.pop("FAKE_WRITE")
        page = self.root / "dl" / "Tidal" / "Albums" / "Deep Purple" / "Machine Head" / "Machine Head.html"
        text = page.read_text(encoding="utf-8")
        self.assertIn('data-th="https://resources.tidal.com/images/aa/bb/320x320.jpg"', text)    # cover of title 1
        self.assertIn('data-th="https://resources.tidal.com/images/cc/dd/320x320.jpg"', text)    # cover of title 2
        self.assertIn('href="https://tidal.com/browse/track/111"', text)
        self.assertIn(">#111<", text)
        self.assertIn('data-sub="Deep Purple"', text)
        self.assertIn('id="cv"', text)                   # the header cover follows the playing title
        self.assertIn('id="np"', text)

    def test_match_tracks_by_name_then_by_order(self):
        files = [Path("01 - Highway Star.flac"), Path("02 - Maybe I'm a Leo.flac")]
        found = tidal.match_tracks(files, list(reversed(self.TRACKS)))
        self.assertEqual([t["id"] for t in found], ["111", "222"])
        playlist_style = [Path("01 - Deep Purple - Highway Star.flac")]
        self.assertEqual(tidal.match_tracks(playlist_style, self.TRACKS)[0]["id"], "111")
        odd = [Path("01 - Something else.flac"), Path("02 - Another.flac")]
        self.assertEqual([t["id"] for t in tidal.match_tracks(odd, self.TRACKS)], ["111", "222"])   # same count: order
        self.assertEqual(tidal.match_tracks([Path("x.flac")], self.TRACKS), [None])                 # nothing to go by


class DownloadTargetTests(unittest.TestCase):
    """The folder button of a finished Tidal tile opens the song / album / playlist / video, not just the Tidal folder."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "Tidal"
        self.base.mkdir()
        self.since = __import__("time").time()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, *parts):
        p = self.base.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        return p

    def test_one_song_is_the_file_itself(self):
        song = self.write("Singles", "Deep Purple - Highway Star.flac")
        self.assertEqual(tidal.downloaded_target(self.base, self.since), song)

    def test_a_video_is_the_file_itself(self):
        video = self.write("Videos", "Artist - Clip.mp4")
        self.assertEqual(tidal.downloaded_target(self.base, self.since), video)

    def test_album_and_playlist_open_their_folder(self):
        self.write("Albums", "Deep Purple", "Machine Head", "01 - A.flac")
        self.write("Albums", "Deep Purple", "Machine Head", "02 - B.flac")
        self.assertEqual(tidal.downloaded_target(self.base, self.since), self.base / "Albums" / "Deep Purple" / "Machine Head")

    def test_artist_with_several_albums_opens_the_artist_folder(self):
        self.write("Albums", "Deep Purple", "A", "01 - x.flac")
        self.write("Albums", "Deep Purple", "B", "01 - y.flac")
        self.assertEqual(tidal.downloaded_target(self.base, self.since), self.base / "Albums" / "Deep Purple")

    def test_old_files_do_not_count(self):
        old = self.write("Singles", "old.flac")
        os.utime(old, (self.since - 3600, self.since - 3600))
        self.assertEqual(tidal.downloaded_target(self.base, self.since), self.base)

    def test_nothing_new_guesses_the_folder_from_the_name(self):
        folder = self.base / "Playlists" / "Cabrio 350SL"
        folder.mkdir(parents=True)
        old = folder / "01 - a.flac"
        old.write_bytes(b"x")
        os.utime(old, (self.since - 3600, self.since - 3600))
        meta = {"kind": "playlist", "title": "Cabrio 350SL", "artist": "me"}
        self.assertEqual(tidal.downloaded_target(self.base, self.since, meta), folder)
        self.assertEqual(tidal.downloaded_target(self.base, self.since, {"kind": "album", "title": "Nope", "artist": "x"}), self.base)

