import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

import _path  # noqa: F401,E402  (side effect: sys.path)
from yeal.core.engine import Cancelled, Engine, clean_error, fmt_eta, fmt_speed
from yeal.core.models import DownloadJob, DownloadOptions, JobState
from yeal.core.presets import build_ydl_opts, normalize_proxy, sanitize_custom_options
from yeal.core.queue import DownloadQueue
from yeal.core.settings import Settings
from yeal.platforms import PlatformInfo


def make_ctx(tmp, ffmpeg=True, mobile=False):
    tmp = Path(tmp)
    return PlatformInfo("android" if mobile else "windows", mobile, tmp / "data",
                        tmp / "dl", Path("ffmpeg.exe") if ffmpeg else None)


def wait_for(cond, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


class PresetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_video_with_ffmpeg_merges(self):
        o = build_ydl_opts(DownloadOptions(max_height=720), make_ctx(self.tmp.name))
        self.assertEqual(o["format"], "bv*[height<=720]+ba/b[height<=720]/b")
        self.assertEqual(o["merge_output_format"], "mp4")
        keys = [p["key"] for p in o["postprocessors"]]
        self.assertEqual(keys, ["FFmpegThumbnailsConvertor", "FFmpegMetadata", "EmbedThumbnail"])
        self.assertTrue(o["noplaylist"])

    def test_video_without_ffmpeg_is_single_file(self):
        o = build_ydl_opts(DownloadOptions(max_height=0), make_ctx(self.tmp.name, ffmpeg=False))
        self.assertEqual(o["format"], "b[ext=mp4]/b/b")
        self.assertNotIn("postprocessors", o)
        self.assertNotIn("merge_output_format", o)

    def test_audio_variants(self):
        with_ff = build_ydl_opts(DownloadOptions(mode="audio", audio_format="mp3",
                                                 embed_metadata=False), make_ctx(self.tmp.name))
        self.assertEqual(with_ff["postprocessors"][0]["preferredcodec"], "mp3")
        without = build_ydl_opts(DownloadOptions(mode="audio"), make_ctx(self.tmp.name, ffmpeg=False))
        self.assertIn("m4a", without["format"])
        self.assertNotIn("postprocessors", without)

    def test_subtitles_and_playlist(self):
        o = build_ydl_opts(DownloadOptions(subtitles=True, playlist=True, embed_metadata=False),
                           make_ctx(self.tmp.name))
        self.assertFalse(o["noplaylist"])
        self.assertTrue(o["writesubtitles"])
        self.assertEqual(o["postprocessors"], [{"key": "FFmpegEmbedSubtitle"}])

    def test_invalid_options_are_normalized(self):
        o = DownloadOptions(mode="x", max_height=999, audio_format="wav").normalized()
        self.assertEqual((o.mode, o.max_height, o.audio_format), ("video", 1080, "mp3"))

    def test_custom_options_sanitized(self):
        clean, rejected = sanitize_custom_options({
            "ratelimit": 1000, "exec_cmd": "calc", "postprocessors": [], "outtmpl": "../x",
            "paths": {"home": "C:/"}, "external_downloader": "curl"})
        self.assertEqual(clean, {"ratelimit": 1000})
        self.assertEqual(set(rejected), {"exec_cmd", "postprocessors", "outtmpl", "paths",
                                         "external_downloader"})
        ok, _ = sanitize_custom_options({"outtmpl": "%(title)s.%(ext)s"})
        self.assertIn("outtmpl", ok)

    def test_custom_options_cannot_override_paths(self):
        o = build_ydl_opts(DownloadOptions(custom={"paths": {"home": "C:/Windows"}, "retries": 1}),
                           make_ctx(self.tmp.name))
        self.assertEqual(o["paths"]["home"], str(Path(self.tmp.name) / "dl" / "Video"))
        self.assertEqual(o["retries"], 1)


class ThumbnailEmbedTests(unittest.TestCase):
    def _keys(self, **kw):
        with tempfile.TemporaryDirectory() as d:
            o = build_ydl_opts(DownloadOptions(**kw), make_ctx(d))
        return [pp["key"] for pp in o.get("postprocessors", [])]

    def test_original_audio_has_no_thumbnail_embed(self):
        self.assertNotIn("EmbedThumbnail", self._keys(mode="audio", audio_format="best"))

    def test_supported_targets_embed(self):
        for fmt in ("mp3", "m4a", "opus"):
            self.assertIn("EmbedThumbnail", self._keys(mode="audio", audio_format=fmt))
        self.assertIn("EmbedThumbnail", self._keys(mode="video"))


class HtmlExtrasTests(unittest.TestCase):
    INFO = {"title": "T", "id": "kva9GQyBjIQ", "extractor_key": "Youtube", "description": "d",
            "webpage_url": "https://www.youtube.com/watch?v=kva9GQyBjIQ"}

    def test_online_player_embeds_youtube(self):
        from yeal.core import extras
        page = extras.description_html(self.INFO, "a.mp3", "audio", online_player=True)
        self.assertIn("youtube-nocookie.com/embed/kva9GQyBjIQ", page)
        self.assertIn('src="a.mp3"', page)
        self.assertNotIn("youtube-nocookie", extras.description_html(self.INFO, "a.mp3", "audio"))

    def test_other_sites_get_no_embed(self):
        from yeal.core import extras
        info = dict(self.INFO, extractor_key="Generic")
        self.assertNotIn("<iframe", extras.description_html(info, "a.mp4", online_player=True))

    def test_theme_is_fixed_to_the_app_theme(self):
        from yeal.core import extras
        dark = extras.description_html(self.INFO, theme="dark")
        light = extras.description_html(self.INFO, theme="light")
        self.assertIn("#121214", dark)
        self.assertNotIn("prefers-color-scheme", dark + light)
        self.assertNotIn("#121214", light)
        self.assertIn("prefers-color-scheme", extras.description_html(self.INFO))


class ChapterTests(unittest.TestCase):
    def test_markers_are_embedded_and_split_is_optional(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = make_ctx(d)
            plain = build_ydl_opts(DownloadOptions(mode="audio", audio_format="mp3"), ctx)
            split = build_ydl_opts(DownloadOptions(mode="audio", audio_format="mp3", split_chapters=True), ctx)
        meta = [p for p in plain["postprocessors"] if p["key"] == "FFmpegMetadata"][0]
        self.assertTrue(meta["add_chapters"])
        self.assertNotIn("FFmpegSplitChapters", [p["key"] for p in plain["postprocessors"]])
        self.assertEqual(split["postprocessors"][-1]["key"], "FFmpegSplitChapters")
        self.assertIn("chapter", split["outtmpl"])

    def test_tracklist_timestamps_become_seek_links(self):
        from yeal.core import extras
        info = {"title": "Mix", "chapters": [{"start_time": 0}, {"start_time": 293}],
                "description": "Tracklist:\n00:00:00 - A\n00:04:53 - B\nnot 1:00 here"}
        page = extras.description_html(info, "m.mp3", "audio")
        self.assertIn('data-t="293">00:04:53</a> - B', page)
        self.assertIn('data-t="0">00:00:00</a>', page)
        self.assertNotIn('class="ts" data-t="60"', page)
        self.assertNotIn("class=\"ts\"", extras.description_html(dict(info, chapters=[]), "m.mp3", "audio"))


class AlbumTests(unittest.TestCase):
    def test_playlist_and_folder_lookup(self):
        from yeal.core import album
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder = root / "Mix [abc123]"
            folder.mkdir()
            (root / "Mix [abc123].mp3").write_bytes(b"x")
            for n, name in ((1, "Me Sanaste"), (2, "La Noche Me Ensen\u00f3")):
                (folder / f"{n:02d} - {name}.mp3").write_bytes(b"x")
            self.assertEqual(album.find_album_dir(root, "abc123"), folder)
            n = album.finish(None, folder, "Mix", "DJ", [{"start_time": 0, "end_time": 293},
                                                         {"start_time": 293, "end_time": 600}])
            self.assertEqual(n, 2)
            lines = (folder / "Mix.m3u8").read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "#EXTM3U")
            self.assertIn("#EXTINF:293,Me Sanaste", lines)
            self.assertIn("02 - La Noche Me Ensen\u00f3.mp3", lines)

    def test_tags_are_written_without_reencoding(self):
        import shutil
        import subprocess
        from yeal.platforms.desktop import find_ffmpeg
        ff = find_ffmpeg()
        if not ff:
            self.skipTest("ffmpeg required")
        from yeal.core import album
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "01 - One.mp3"
            subprocess.run([str(ff), "-v", "error", "-f", "lavfi", "-i", "sine=duration=1", str(f)], check=True)
            self.assertTrue(album.tag_track(str(ff), f, "The Album", "DJ X", 1, 3, "One"))
            out = subprocess.run([str(ff), "-i", str(f), "-f", "ffmetadata", "-"], capture_output=True,
                                 text=True).stdout
            self.assertIn("album=The Album", out)
            self.assertIn("track=1/3", out)


class GentleModeTests(unittest.TestCase):
    def test_gentle_options_and_cookies(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = make_ctx(d)
            o = build_ydl_opts(DownloadOptions(playlist=True), ctx)
            self.assertEqual(o["sleep_interval_requests"], 1)
            self.assertEqual((o["sleep_interval"], o["max_sleep_interval"]), (3, 8))
            self.assertEqual([o["retry_sleep_functions"]["http"](n) for n in (0, 1, 5, 9)], [2, 4, 64 and 60, 60])
            single = build_ydl_opts(DownloadOptions(), ctx)
            self.assertNotIn("sleep_interval", single)
            off = build_ydl_opts(DownloadOptions(gentle=False), ctx)
            self.assertNotIn("sleep_interval_requests", off)
            self.assertNotIn("cookiesfrombrowser", single)
            c = build_ydl_opts(DownloadOptions(cookies_browser="firefox"), ctx)
            self.assertEqual(c["cookiesfrombrowser"], ("firefox",))
            bad = build_ydl_opts(DownloadOptions(cookies_browser="../x"), ctx)
            self.assertNotIn("cookiesfrombrowser", bad)

    def test_rate_limit_pauses_the_queue(self):
        from yeal.core import queue as q
        self.assertTrue(q.rate_limited("HTTP Error 429: Too Many Requests"))
        self.assertTrue(q.rate_limited("Sign in to confirm you're not a bot"))
        self.assertFalse(q.rate_limited("Video unavailable"))
        starts = []

        def runner(job, cancel, notify):
            starts.append(time.time())
            job.state = JobState.ERROR if len(starts) == 1 else JobState.DONE
            job.error = "HTTP Error 429" if len(starts) == 1 else ""
            notify(job)
        old = q.RATE_LIMIT_PAUSE
        q.RATE_LIMIT_PAUSE = 1
        try:
            queue = q.DownloadQueue(runner, 1)
            queue.add("https://a.test/1", DownloadOptions())
            queue.add("https://a.test/2", DownloadOptions())
            end = time.time() + 6
            while len(starts) < 2 and time.time() < end:
                time.sleep(0.05)
            queue.shutdown()
        finally:
            q.RATE_LIMIT_PAUSE = old
        self.assertEqual(len(starts), 2)
        self.assertGreaterEqual(starts[1] - starts[0], 0.9)


class LocalServeTests(unittest.TestCase):
    def test_serves_only_the_folder_and_no_listing(self):
        import urllib.error
        import urllib.request
        from yeal.core import localserve
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a b.html").write_text("<p>hi</p>", encoding="utf-8")
            port = localserve.serve(Path(d))
            try:
                body = urllib.request.urlopen(f"http://127.0.0.1:{port}/a%20b.html").read()
                self.assertEqual(body, b"<p>hi</p>")
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/")
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/../x")
            finally:
                localserve.shutdown_all()


class AudioProbeTests(unittest.TestCase):
    def test_opus_160_is_high_quality_and_offers_aac(self):
        from yeal.core import audioprobe
        info = {"formats": [
            {"vcodec": "none", "acodec": "opus", "abr": 160, "ext": "webm"},
            {"vcodec": "none", "acodec": "mp4a.40.2", "abr": 128, "ext": "m4a"},
            {"vcodec": "avc1", "acodec": "none", "abr": 0, "ext": "mp4"}]}
        best = audioprobe.best_audio(info)
        self.assertEqual((best["codec"], best["abr"]), ("opus", 160))
        self.assertTrue(audioprobe.is_high_quality(best))
        ids = [c["id"] for c in audioprobe.choices(best)]
        self.assertEqual(ids, ["mp3", "m4a", "best"])

    def test_normal_quality_asks_nothing(self):
        from yeal.core import audioprobe
        best = audioprobe.best_audio({"formats": [{"vcodec": "none", "acodec": "opus", "abr": 96}]})
        self.assertFalse(audioprobe.is_high_quality(best))

    def test_lossless_offers_flac_after_the_defaults(self):
        from yeal.core import audioprobe
        best = audioprobe.best_audio({"formats": [{"vcodec": "none", "acodec": "flac", "abr": 900}]})
        ch = audioprobe.choices(best)
        self.assertEqual([c["id"] for c in ch], ["mp3", "m4a", "best", "flac"])
        self.assertEqual(ch[0]["bitrate"], 320)

    def test_probe_flags_live_streams(self):
        from yeal.core import audioprobe

        class Live(FakeYDL):
            def extract_info(self, url, download=True):
                return {"title": "Radio", "is_live": True, "live_status": "is_live", "formats": []}
        self.assertTrue(audioprobe.probe("https://x.test/l", Live, {})["live"])

    def test_live_minutes_is_clamped_and_limits_the_recording(self):
        from yeal.core.models import DownloadOptions
        self.assertEqual(DownloadOptions(live_minutes=-5).normalized().live_minutes, 0)
        self.assertEqual(DownloadOptions(live_minutes=99999).normalized().live_minutes, 1440)
        self.assertEqual(DownloadOptions(live_minutes="x").normalized().live_minutes, 0)

    def test_compress_items(self):
        from yeal.core.presets import compress_items
        self.assertEqual(compress_items([1, 2, 3, 5, 7, 8]), "1-3,5,7-8")
        self.assertEqual(compress_items([4]), "4")
        self.assertEqual(compress_items([]), "")

    def test_playlist_options_layout(self):
        from yeal.core.models import DownloadOptions
        with tempfile.TemporaryDirectory() as d:
            ctx = make_ctx(d)
            o = build_ydl_opts(DownloadOptions(playlist=True, playlist_dir=True, playlist_items="1-3,7"), ctx)
            self.assertTrue(o["outtmpl"].startswith("Playlists/%(playlist_title"))
            self.assertEqual(o["paths"]["home"], str(ctx.download_dir))
            self.assertEqual(o["playlist_items"], "1-3,7")
            single = build_ydl_opts(DownloadOptions(), ctx)
            self.assertNotIn("playlist_items", single)
            self.assertNotIn("Playlists", single["outtmpl"])
        bad = DownloadOptions(playlist_items="1-3, rm -rf, 5,x;").normalized()
        self.assertEqual(bad.playlist_items, "1-3,5")

    def test_probe_playlist_lists_entries(self):
        from yeal.core import audioprobe

        class Flat(FakeYDL):
            def extract_info(self, url, download=True):
                assert self.opts["extract_flat"] == "in_playlist"
                return {"title": "Mix", "uploader": "DJ", "entries": [
                    {"id": "a", "title": "One", "duration": 61, "url": "https://x/a"},
                    {"id": "b", "title": "[Private video]"}]}
        r = audioprobe.probe_playlist("https://www.youtube.com/playlist?list=PL1", Flat, {})
        self.assertEqual([e["index"] for e in r["entries"]], [1, 2])
        self.assertEqual([e["available"] for e in r["entries"]], [True, False])
        self.assertEqual(r["title"], "Mix")

    def test_playlist_page_is_written_next_to_the_files(self):
        from yeal.core import extras
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "My Mix"
            folder.mkdir()
            (folder / "001 - One.mp3").write_bytes(b"x")
            page = extras.write_playlist_page(folder, "My Mix", "DJ", "https://y/pl", [
                {"index": 1, "title": "One <b>", "duration": "1:01", "file": "001 - One.mp3", "page": ""},
                {"index": 2, "title": "Two", "duration": "", "file": "", "page": ""}], "audio", "dark")
            self.assertEqual(page.name, "My Mix.html")
            text = page.read_text(encoding="utf-8")
            self.assertIn('data-src="001%20-%20One.mp3"', text)
            self.assertIn("One &lt;b&gt;", text)
            self.assertIn("not downloaded", text)
            self.assertIn("<audio", text)

    def test_probe_failure_is_silent(self):
        from yeal.core import audioprobe

        class Boom(FakeYDL):
            def extract_info(self, url, download=True):
                raise RuntimeError("offline")
        self.assertEqual(audioprobe.probe("https://x.test/a", Boom, {}), {})

    def test_mp3_bitrate_follows_choice(self):
        with tempfile.TemporaryDirectory() as d:
            o = build_ydl_opts(DownloadOptions(mode="audio", audio_format="mp3", audio_bitrate=320),
                               make_ctx(d))
        self.assertEqual(o["postprocessors"][1 if len(o["postprocessors"]) > 1 and
                              o["postprocessors"][0]["key"] != "FFmpegExtractAudio" else 0]["preferredquality"], "320")


class JsRuntimeTests(unittest.TestCase):
    def test_node_is_passed_to_ytdlp(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = make_ctx(d)
            self.assertNotIn("js_runtimes", build_ydl_opts(DownloadOptions(), ctx))
            ctx.js_runtime = Path("C:/node/node.exe")
            o = build_ydl_opts(DownloadOptions(), ctx)
            self.assertEqual(o["js_runtimes"], {"node": {"path": str(Path("C:/node/node.exe"))}})

    def test_find_node_and_ffmpeg_next_to_tools_central(self):
        import os
        from yeal.platforms import desktop
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / "AI_Coworker_Claude"
            node = ws / "Tools_Central" / "Dependencies" / "node" / "bin" / ("node.exe" if os.name == "nt" else "node")
            ff = ws / "Tools_Central" / "Video Tools" / "FFMPEG" / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            for f in (node, ff):
                f.parent.mkdir(parents=True)
                f.write_text("")
            app = ws / "APK YEAL" / "BIN" / "versions" / "v0.1" / "PyModul"
            app.mkdir(parents=True)
            old = os.environ.pop("YEAL_NODE", None), os.environ.pop("YEAL_FFMPEG", None)
            try:
                self.assertEqual(desktop.find_node(app), node)
                self.assertEqual(desktop.find_ffmpeg(app), ff)
            finally:
                for key, val in zip(("YEAL_NODE", "YEAL_FFMPEG"), old):
                    if val:
                        os.environ[key] = val


class SettingsTests(unittest.TestCase):
    def test_roundtrip_and_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sub" / "settings.json"
            s = Settings(theme="dark", max_parallel=9, custom_options={"ratelimit": 5})
            s.validate().save(path)
            loaded = Settings.load(path)
            self.assertEqual((loaded.theme, loaded.max_parallel), ("dark", 4))
            self.assertEqual(loaded.custom_options, {"ratelimit": 5})
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(Settings.load(path).theme, "system")
            path.write_text(json.dumps({"theme": "light", "unknown": 1}), encoding="utf-8")
            self.assertEqual(Settings.load(path).theme, "light")
            self.assertEqual(Settings.load(Path(d) / "missing.json").get_profile()["max_height"], 1080)

    def test_legacy_settings_become_a_profile(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            path.write_text(json.dumps({"mode": "audio", "audio_format": "mp3"}), encoding="utf-8")
            s = Settings.load(path)
            self.assertEqual(s.active_profile, "My previous settings")
            self.assertEqual(s.to_options().mode, "audio")
            self.assertEqual(s.to_options().audio_format, "mp3")

    def test_4k_profile_is_default_and_added_to_old_settings(self):
        self.assertIn("Video 4K", Settings().validate().profile_names())
        self.assertEqual(Settings().get_profile("Video 4K")["max_height"], 2160)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            path.write_text(json.dumps({"profiles": [{"name": "Mine", "mode": "video", "max_height": 720}],
                                        "active_profile": "Mine"}), encoding="utf-8")
            s = Settings.load(path)
            self.assertEqual(s.profile_names(), ["Video 4K", "Mine"])
            self.assertEqual(s.active_profile, "Mine")
            s.save(path)
            self.assertEqual(Settings.load(path).profile_names(), ["Video 4K", "Mine"])

    def test_profile_management(self):
        s = Settings().validate()
        n = len(s.profiles)
        self.assertEqual(s.save_profile("", {"name": "Podcast", "mode": "audio", "audio_format": "opus"}), "")
        self.assertEqual(len(s.profiles), n + 1)
        self.assertIn("exists", s.save_profile("", {"name": "podcast"}))
        self.assertIn("name", s.save_profile("", {"name": "  "}))
        s.active_profile = "Podcast"
        self.assertEqual(s.save_profile("Podcast", {"name": "Podcasts", "mode": "audio"}), "")
        self.assertEqual(s.active_profile, "Podcasts")
        copy = s.duplicate_profile("Podcasts")
        self.assertEqual(copy, "Podcasts copy")
        self.assertEqual(s.duplicate_profile("Podcasts"), "Podcasts copy 2")
        self.assertEqual(s.delete_profile("Podcasts"), "")
        self.assertNotEqual(s.active_profile, "Podcasts")
        for name in list(s.profile_names())[:-1]:
            s.delete_profile(name)
        self.assertIn("At least one", s.delete_profile(s.profile_names()[0]))

    def test_rate_limit_and_proxy_reach_ytdlp(self):
        s = Settings(rate_limit_kbps=500, proxy="socks5://127.0.0.1:9050").validate()
        with tempfile.TemporaryDirectory() as d:
            opts = build_ydl_opts(s.to_options(), make_ctx(d))
        self.assertEqual(opts["ratelimit"], 500 * 1024)
        self.assertEqual(opts["proxy"], "socks5://127.0.0.1:9050")
        with self.assertRaises(ValueError):
            normalize_proxy("ftp://nope")
        self.assertEqual(normalize_proxy("  "), "")


class FakeYDL:
    """Stands in for yt_dlp.YoutubeDL. Behaviour is chosen by the URL."""
    instances = []

    def __init__(self, opts):
        self.opts = opts
        FakeYDL.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=True):
        hook = self.opts["progress_hooks"][0]
        pp = self.opts["postprocessor_hooks"][0]
        if "fail" in url:
            raise RuntimeError("\x1b[0;31mERROR:\x1b[0m Video unavailable\nsecond line")
        info = {"title": "Fake Title", "playlist_index": 1, "n_entries": 2}
        for i in (1, 2):
            info = dict(info, playlist_index=i)
            hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100,
                  "speed": 2048, "eta": 65, "info_dict": info})
            if "slow" in url:
                time.sleep(0.2)
            hook({"status": "finished", "filename": f"/dl/f{i}.mp4", "info_dict": info})
        pp({"status": "finished", "info_dict": {"filepath": "/dl/final.mp4"}})
        return {"title": "Fake Title"}


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine = Engine(make_ctx(self.tmp.name), ydl_class=FakeYDL)
        self.events = []

    def run_job(self, url, cancel=None):
        job = DownloadJob(1, url, DownloadOptions())
        cancel = cancel or threading.Event()
        self.engine.run(job, cancel, lambda j: self.events.append((j.state, round(j.progress, 2))))
        return job

    def test_success(self):
        job = self.run_job("https://example.com/ok")
        self.assertEqual(job.state, JobState.DONE)
        self.assertEqual((job.title, job.filename, job.progress), ("Fake Title", "/dl/final.mp4", 1.0))
        self.assertTrue((Path(self.tmp.name) / "dl").is_dir())
        states = [s for s, _ in self.events]
        self.assertEqual(states[0], JobState.FETCHING)
        self.assertIn(JobState.DOWNLOADING, states)
        # one bar for every phase: never goes backwards, post-processing sits above the download part
        progress = [p for _, p in self.events]
        self.assertEqual(progress, sorted(progress))
        self.assertGreater(max(p for s, p in self.events if s == JobState.PROCESSING), 0.84)

    def test_error_is_cleaned(self):
        job = self.run_job("https://example.com/fail")
        self.assertEqual(job.state, JobState.ERROR)
        self.assertTrue(job.error.startswith("Stopped automatically: The video is unavailable"))
        self.assertEqual(job.error_detail, "Video unavailable")

    def test_cancel_before_start(self):
        ev = threading.Event()
        ev.set()
        job = self.run_job("https://example.com/ok", ev)
        self.assertEqual(job.state, JobState.CANCELED)

    def test_helpers(self):
        self.assertEqual(fmt_eta(65), "1:05")
        self.assertEqual(fmt_eta(3725), "1:02:05")
        self.assertEqual(fmt_speed(2048), "2.0 KB/s")
        self.assertEqual(fmt_speed(None), "")
        self.assertEqual(clean_error(Exception("ERROR: ERROR: boom")), "boom")
        self.assertTrue(issubclass(Cancelled, Exception))
        self.assertIn("Update yt-dlp", clean_error(Exception("ERROR: [youtube] abc: The page needs to be reloaded")))
        self.assertNotIn("Update yt-dlp", clean_error(Exception("ERROR: [generic] 404")))


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.lock = threading.Lock()
        self.current = 0
        self.peak = 0
        self.changes = []
        self.removed = []

    def runner(self, job, cancel, notify):
        with self.lock:
            self.current += 1
            self.peak = max(self.peak, self.current)
        job.state = JobState.DOWNLOADING
        notify(job)
        end = time.time() + 0.15
        while time.time() < end and not cancel.is_set():
            time.sleep(0.005)
        with self.lock:
            self.current -= 1
        job.state = JobState.CANCELED if cancel.is_set() else JobState.DONE
        notify(job)

    def make(self, parallel):
        q = DownloadQueue(self.runner, parallel, on_change=self.changes.append,
                          on_remove=self.removed.append)
        self.addCleanup(q.shutdown)
        return q

    def states(self, q):
        return {j.id: j.state for j in q.jobs()}

    def test_respects_parallel_limit(self):
        q = self.make(2)
        for i in range(5):
            q.add(f"https://x/{i}", DownloadOptions())
        self.assertTrue(wait_for(lambda: all(s is JobState.DONE for s in self.states(q).values())))
        self.assertEqual(self.peak, 2)

    def test_single_slot_serializes(self):
        q = self.make(1)
        for i in range(3):
            q.add(f"https://x/{i}", DownloadOptions())
        self.assertTrue(wait_for(lambda: all(s is JobState.DONE for s in self.states(q).values())))
        self.assertEqual(self.peak, 1)

    def test_cancel_pending_and_running_then_retry_and_remove(self):
        q = self.make(1)
        first = q.add("https://x/1", DownloadOptions())
        second = q.add("https://x/2", DownloadOptions())
        self.assertTrue(wait_for(lambda: self.states(q)[first.id] is JobState.DOWNLOADING))
        q.cancel(second.id)                       # still pending
        self.assertEqual(self.states(q)[second.id], JobState.CANCELED)
        q.cancel(first.id)                        # running
        self.assertTrue(wait_for(lambda: self.states(q)[first.id] is JobState.CANCELED))
        q.retry(second.id)
        self.assertTrue(wait_for(lambda: self.states(q)[second.id] is JobState.DONE))
        q.retry(second.id)                        # DONE jobs are not retried
        self.assertEqual(self.states(q)[second.id], JobState.DONE)
        q.clear_finished()
        self.assertEqual(q.jobs(), [])
        self.assertCountEqual(self.removed, [first.id, second.id])

    def test_runner_exception_does_not_kill_worker(self):
        calls = []

        def bad(job, cancel, notify):
            calls.append(job.id)
            if len(calls) == 1:
                raise ValueError("boom")
            job.state = JobState.DONE
            notify(job)

        q = DownloadQueue(bad, 1)
        self.addCleanup(q.shutdown)
        a = q.add("https://x/a", DownloadOptions())
        b = q.add("https://x/b", DownloadOptions())
        self.assertTrue(wait_for(lambda: {j.id: j.state for j in q.jobs()}.get(b.id) is JobState.DONE))
        self.assertEqual({j.id: j.state for j in q.jobs()}[a.id], JobState.ERROR)


class FinalPathTests(unittest.TestCase):
    def test_final_path_prefers_requested_downloads(self):
        from yeal.core.engine import final_path
        self.assertEqual(final_path({"requested_downloads": [{"filepath": "a.mp3"}], "filepath": "b"}), "a.mp3")
        self.assertEqual(final_path({"entries": [{"filepath": "c.mp4"}]}), "c.mp4")
        self.assertEqual(final_path(None), "")


class ExtrasAndPlaylistTests(unittest.TestCase):
    def test_description_html_links_and_escaping(self):
        from yeal.core.extras import description_html
        out = description_html({"title": "A <b>", "description": "see https://x.org/a?b=1&c=2. <script>",
                                "webpage_url": "https://y.tv/v"})
        self.assertIn('<a href="https://x.org/a?b=1&amp;c=2"', out)
        self.assertNotIn("<script>", out)
        self.assertIn("A &lt;b&gt;", out)

    def test_subtitle_to_text_dedupes_rolling_captions(self):
        from yeal.core.extras import subtitle_to_text
        vtt = ("WEBVTT\nKind: captions\n\n00:00:01.000 --> 00:00:02.000\nHello <c>world</c>\n\n"
               "00:00:02.000 --> 00:00:03.000\nHello world\nnext line\n")
        self.assertEqual(subtitle_to_text(vtt), "Hello world\nnext line\n")

    def test_write_extras(self):
        from yeal.core.extras import write_extras
        with tempfile.TemporaryDirectory() as d:
            sub = Path(d) / "v.en.vtt"
            sub.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhi\n", encoding="utf-8")
            info = {"description": "d", "title": "t", "requested_subtitles": {"en": {"filepath": str(sub)}}}
            self.assertEqual(write_extras(info, str(Path(d) / "v.mp4"), True, True, ["en"], False), (True, True))
            self.assertTrue((Path(d) / "v.html").exists())
            self.assertEqual((Path(d) / "v.txt").read_text(), "hi\n")
            self.assertFalse(sub.exists())
            page = (Path(d) / "v.html").read_text(encoding="utf-8")
            self.assertIn('<video controls preload="metadata" src="v.mp4">', page)
            self.assertEqual(write_extras({}, str(Path(d) / "w.mp4"), True, True, ["en"], False), (False, False))

    def test_playlist_url_detection(self):
        from yeal.core.presets import is_playlist_url
        self.assertTrue(is_playlist_url("https://www.youtube.com/playlist?list=PL123"))
        self.assertFalse(is_playlist_url("https://www.youtube.com/watch?v=abc&list=PL123"))
        self.assertTrue(is_playlist_url("https://soundcloud.com/u/sets/mix"))
        with tempfile.TemporaryDirectory() as d:
            o = build_ydl_opts(DownloadOptions(playlist=True, save_transcript=True), make_ctx(d))
            self.assertTrue(o["paths"]["home"].endswith("Video"))
            a = build_ydl_opts(DownloadOptions(mode="audio"), make_ctx(d))
            self.assertTrue(a["paths"]["home"].endswith("Audio"))
            self.assertFalse(o["noplaylist"])
            self.assertEqual(o["ignoreerrors"], "only_download")
            self.assertTrue(o["writeautomaticsub"])
            self.assertNotIn("postprocessors", {k: 1 for k in o if k == "postprocessors" and any(
                p["key"] == "FFmpegEmbedSubtitle" for p in o[k])})


if __name__ == "__main__":
    unittest.main()
