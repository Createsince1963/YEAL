"""MP3 tags: description parsing, writing/merging, the engine step and the backend slots."""
import os
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import _path  # noqa: F401,E402  (side effect: sys.path)
from yeal.core import mp3tags  # noqa: E402
from yeal.core.engine import Engine  # noqa: E402
from yeal.core.models import DownloadJob, DownloadOptions, JobState  # noqa: E402
from test_core import make_ctx  # noqa: E402

try:
    from PySide6.QtGui import QGuiApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

DESC = """Middle Eastern sounds. Pure instrumental flow for a relaxing and immersive experience.

\U0001F39A️ Mood: Warm | Hypnotic | Chill | Oriental Vibes
\U0001F3A7 Genre: Arabic Deep House | Ethnic House | Instrumental Electronic
\U0001F698 Ideal For: Relaxation | Night Drive | Studying | Background Vibes

\U0001F449 Like, Comment & Subscribe for more deep house journeys.

#arabicdeephouse #ethnichouse #orientalvibes #instrumental #deephousemix #desertvibes #chillhouse
"""

INFO = {"title": "Desert Nights", "uploader": "DJ X", "description": DESC, "upload_date": "20251005",
        "webpage_url": "https://example.com/watch?v=1"}

needs_mutagen = unittest.skipUnless(mp3tags.AVAILABLE, "mutagen not installed")


def write_mp3(path: Path) -> Path:
    """A few valid MPEG-1 layer 3 frames (128 kbit/s, 44.1 kHz) - enough for mutagen."""
    path.write_bytes((b"\xff\xfb\x90\x00" + b"\x00" * 413) * 12)
    return path


class ParseTests(unittest.TestCase):
    def test_description_fields(self):
        p = mp3tags.parse_description(DESC)
        self.assertEqual(p["genre"], ["Arabic Deep House", "Ethnic House", "Instrumental Electronic"])
        self.assertEqual(p["mood"], ["Warm", "Hypnotic", "Chill", "Oriental Vibes"])
        self.assertEqual(p["ideal_for"], ["Relaxation", "Night Drive", "Studying", "Background Vibes"])
        self.assertEqual(p["hashtags"][:3], ["arabicdeephouse", "ethnichouse", "orientalvibes"])
        self.assertEqual(len(p["hashtags"]), 7)

    def test_unrelated_text_is_ignored(self):
        p = mp3tags.parse_description("Track: Foo\nRecorded in: Berlin\nSee &#39;this&#39; and #1 and #2024 #ok")
        self.assertEqual((p["genre"], p["mood"], p["ideal_for"]), ([], [], []))
        self.assertEqual(p["hashtags"], ["ok"])
        self.assertEqual(mp3tags.parse_description(None)["genre"], [])

    def test_slash_inside_a_name_is_kept(self):
        p = mp3tags.parse_description("Genre: R&B/Soul / Lo-Fi, Chill")
        self.assertEqual(p["genre"], ["R&B/Soul", "Lo-Fi", "Chill"])

    def test_build_tag_data(self):
        d = mp3tags.build_tag_data(INFO)
        self.assertEqual((d.title, d.artist, d.year), ("Desert Nights", "DJ X", "2025"))
        self.assertEqual(d.genre, "Arabic Deep House; Ethnic House; Instrumental Electronic")
        self.assertEqual(d.mood, "Warm, Hypnotic, Chill, Oriental Vibes")
        self.assertEqual(d.comment, "Ideal for: Relaxation, Night Drive, Studying, Background Vibes")
        self.assertTrue(d.keywords.startswith("arabicdeephouse, ethnichouse"))
        self.assertEqual(d.source_url, "https://example.com/watch?v=1")

    def test_falls_back_to_video_tags_and_genre(self):
        d = mp3tags.build_tag_data({"title": "T", "tags": ["a", "b"], "genre": "Pop", "track": "Song",
                                    "artist": "Band", "release_year": 1999})
        self.assertEqual((d.title, d.artist, d.genre, d.keywords, d.year), ("Song", "Band", "Pop", "a, b", "1999"))

    def test_merge_keeps_title_artist_album(self):
        old = mp3tags.TagData(title="Mine", artist="", album="Alb", genre="Old", mood="old mood", comment="long text")
        new = mp3tags.TagData(title="Theirs", artist="DJ X", album="Other", genre="New", mood="", comment="")
        out = mp3tags.merge(old, new)
        self.assertEqual((out.title, out.artist, out.album), ("Mine", "DJ X", "Alb"))
        self.assertEqual((out.genre, out.mood, out.comment), ("New", "old mood", "long text"))

    def test_from_dict_takes_only_editable_fields(self):
        base = mp3tags.TagData(title="A", source_url="https://keep.me")
        out = mp3tags.from_dict({"title": "B", "source_url": "https://evil", "bogus": 1, "year": None}, base)
        self.assertEqual((out.title, out.source_url, out.year), ("B", "https://keep.me", ""))
        self.assertEqual(base.title, "A")   # the base object is not modified


@needs_mutagen
class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mp3 = write_mp3(Path(self.tmp.name) / "a.mp3")

    def test_auto_fill_untagged_file(self):
        data = mp3tags.auto_fill(self.mp3, INFO)
        self.assertIsNotNone(data)
        back = mp3tags.read_tags(self.mp3)
        self.assertEqual(asdict(back), asdict(data))
        self.assertEqual(back.genre, "Arabic Deep House; Ethnic House; Instrumental Electronic")
        self.assertEqual(back.mood, "Warm, Hypnotic, Chill, Oriental Vibes")
        self.assertEqual(back.year, "2025")

    def test_auto_fill_keeps_existing_title(self):
        mp3tags.write_tags(self.mp3, mp3tags.TagData(title="Existing title", artist="Existing artist"))
        mp3tags.auto_fill(self.mp3, INFO)
        back = mp3tags.read_tags(self.mp3)
        self.assertEqual((back.title, back.artist), ("Existing title", "Existing artist"))
        self.assertEqual(back.mood, "Warm, Hypnotic, Chill, Oriental Vibes")

    def test_edit_roundtrip_and_empty_field_removes_tag(self):
        mp3tags.auto_fill(self.mp3, INFO)
        data = mp3tags.read_tags(self.mp3)
        data.mood, data.comment, data.genre = "", "", "Deep House; Chill"
        data.title = "Zażółć gęślą – 日本語"
        mp3tags.write_tags(self.mp3, data)
        back = mp3tags.read_tags(self.mp3)
        self.assertEqual((back.mood, back.comment), ("", ""))
        self.assertEqual(back.genre, "Deep House; Chill")
        self.assertEqual(back.title, "Zażółć gęślą – 日本語")
        from mutagen.id3 import ID3
        tags = ID3(str(self.mp3))
        self.assertEqual(tags["TCON"].text, ["Deep House", "Chill"])
        self.assertNotIn("TMOO", tags)
        self.assertEqual(tags.version[:2], (2, 4))

    def test_cover_and_lyrics_survive(self):
        from mutagen.id3 import APIC, ID3, USLT
        tags = ID3()
        tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="c", data=b"\xff\xd8\xff"))
        tags.add(USLT(encoding=3, lang="eng", desc="", text="la la"))
        tags.save(str(self.mp3))
        mp3tags.auto_fill(self.mp3, INFO)
        after = ID3(str(self.mp3))
        self.assertEqual(len(after.getall("APIC")), 1)
        self.assertEqual(after.getall("USLT")[0].text, "la la")

    def test_named_comment_stays(self):
        from mutagen.id3 import COMM, ID3
        tags = ID3()
        tags.add(COMM(encoding=3, lang="eng", desc="iTunNORM", text="000001"))
        tags.add(COMM(encoding=3, lang="eng", desc="", text="old"))
        tags.save(str(self.mp3))
        mp3tags.auto_fill(self.mp3, INFO)
        comments = {c.desc: str(c.text[0]) for c in ID3(str(self.mp3)).getall("COMM")}
        self.assertEqual(comments["iTunNORM"], "000001")
        self.assertTrue(comments[""].startswith("Ideal for:"))

    def test_missing_or_broken_file_does_not_raise(self):
        self.assertIsNone(mp3tags.auto_fill(Path(self.tmp.name) / "nope.mp3", INFO))
        broken = Path(self.tmp.name) / "b.mp3"
        broken.write_bytes(b"ID3\x09\x00\x00\x00\x00\x00\x05garbage")      # unsupported ID3 version
        self.assertIsNone(mp3tags.auto_fill(broken, INFO))


def fake_ydl(folder: Path, infos: list):
    """yt-dlp stand-in that 'downloads' real (tiny) mp3 files and returns their info."""
    class FakeMp3YDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download=True):
            entries = []
            for n, base in enumerate(infos, 1):
                path = write_mp3(folder / f"track{n}.mp3")
                entries.append(dict(base, requested_downloads=[{"filepath": str(path)}]))
            return entries[0] if len(entries) == 1 else {"title": "List", "entries": entries}
    return FakeMp3YDL


@needs_mutagen
class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "files"
        self.folder.mkdir()

    def run_job(self, infos, **opts):
        engine = Engine(make_ctx(self.tmp.name), ydl_class=fake_ydl(self.folder, infos))
        job = DownloadJob(1, "https://example.com/x", DownloadOptions(mode="audio", **opts))
        engine.run(job, threading.Event(), lambda j: None)
        return job

    def test_single_mp3_is_tagged_and_asks(self):
        job = self.run_job([INFO])
        self.assertEqual(job.state, JobState.DONE)
        self.assertTrue(job.tags_ask)
        self.assertEqual(mp3tags.read_tags(self.folder / "track1.mp3").mood, "Warm, Hypnotic, Chill, Oriental Vibes")

    def test_playlist_is_tagged_without_asking(self):
        job = self.run_job([INFO, dict(INFO, title="Second")])
        self.assertEqual(job.state, JobState.DONE)
        self.assertFalse(job.tags_ask)
        self.assertEqual(mp3tags.read_tags(self.folder / "track2.mp3").genre.split("; ")[0], "Arabic Deep House")

    def test_metadata_switched_off_leaves_file_alone(self):
        job = self.run_job([INFO], embed_metadata=False)
        self.assertFalse(job.tags_ask)
        self.assertEqual(mp3tags.read_tags(self.folder / "track1.mp3"), mp3tags.TagData())

    def test_video_mode_is_skipped(self):
        engine = Engine(make_ctx(self.tmp.name), ydl_class=fake_ydl(self.folder, [INFO]))
        job = DownloadJob(1, "https://example.com/x", DownloadOptions(mode="video"))
        engine.run(job, threading.Event(), lambda j: None)
        self.assertFalse(job.tags_ask)

    def test_reset_clears_the_question(self):
        job = self.run_job([INFO])
        job.reset()
        self.assertFalse(job.tags_ask)


@needs_mutagen
@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "files"
        self.folder.mkdir()
        self.app = QGuiApplication.instance() or QGuiApplication(sys.argv)

    def make_backend(self):
        from yeal.ui.backend import Backend
        ctx = make_ctx(self.tmp.name)
        backend = Backend(ctx, engine=Engine(ctx, ydl_class=fake_ydl(self.folder, [INFO])), check_updates=False)
        self.addCleanup(backend.shutdown)
        prompts = []
        backend.tagsPrompt.connect(prompts.append)
        return backend, prompts

    def finish_job(self, backend):
        options = DownloadOptions(mode="audio")
        backend._queue.add("https://example.com/x", options)
        end = time.time() + 5
        while time.time() < end and not any(j.state.finished for j in backend._model.jobs()):
            self.app.processEvents()
            time.sleep(0.01)
        for _ in range(20):
            self.app.processEvents()
        return backend._model.jobs()[0]

    def test_prompt_read_and_save(self):
        backend, prompts = self.make_backend()
        job = self.finish_job(backend)
        self.assertEqual(job.state, JobState.DONE)
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]["jobId"], job.id)

        data = backend.tagsRead(job.id)
        self.assertNotIn("error", data)
        self.assertEqual(data["mood"], "Warm, Hypnotic, Chill, Oriental Vibes")
        self.assertEqual(backend.tagsSave(job.id, dict(data, mood="Calm", title="New title", source_url="x")), "")
        back = mp3tags.read_tags(self.folder / "track1.mp3")
        self.assertEqual((back.mood, back.title), ("Calm", "New title"))
        self.assertEqual(back.source_url, "https://example.com/watch?v=1")     # not editable, unchanged
        self.assertTrue(backend.mp3TagsAvailable)

        # the question is asked once per job, even when the job changes again
        backend._ask_tags(job)
        self.assertEqual(len(prompts), 1)

    def test_no_prompt_when_switched_off(self):
        backend, prompts = self.make_backend()
        backend.setSetting("ask_mp3_tags", False)
        self.assertFalse(backend.settings["ask_mp3_tags"])
        job = self.finish_job(backend)
        self.assertEqual(job.state, JobState.DONE)
        self.assertEqual(prompts, [])
        self.assertNotIn("error", backend.tagsRead(job.id))   # the editor still works from the menu

    def test_errors_are_reported_as_text(self):
        backend, _ = self.make_backend()
        self.assertIn("not found", backend.tagsRead(999)["error"])
        self.assertIn("not found", backend.tagsSave(999, {}))

    def test_dialog_question_then_editor_then_save(self):
        """The real TagsDialog.qml: the question first (No is the default), then the editor, then Save."""
        from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuickControls2 import QQuickStyle

        qml_dir = _path.PYMODUL / "yeal" / "ui" / "qml"
        harness = b"""
import QtQuick
import QtQuick.Controls.Basic
ApplicationWindow {
    id: root
    visible: true; width: 700; height: 720
    function typeInto(k, v) { dlg.edited[k] = v }
    TagsDialog { id: dlg }
}
"""
        QQuickStyle.setStyle("Basic")
        backend, _ = self.make_backend()
        job = self.finish_job(backend)
        engine = QQmlApplicationEngine()
        self.addCleanup(engine.deleteLater)
        engine.rootContext().setContextProperty("backend", backend)
        engine.loadData(harness, QUrl.fromLocalFile(str(qml_dir / "Harness.qml")))
        self.assertTrue(engine.rootObjects())
        root = engine.rootObjects()[0]
        dlg = root.findChild(QObject, "tagsDialog")

        def pump():
            for _ in range(20):
                self.app.processEvents()
                time.sleep(0.005)

        QMetaObject.invokeMethod(dlg, "enqueue", Q_ARG("QVariant", {"jobId": job.id, "title": job.title}))
        pump()
        self.assertTrue(dlg.property("opened"))
        self.assertFalse(dlg.property("editing"))              # the question comes first
        QMetaObject.invokeMethod(dlg, "next")                  # = answer "No": nothing changes
        pump()
        self.assertFalse(dlg.property("opened"))
        self.assertEqual(mp3tags.read_tags(self.folder / "track1.mp3").mood, "Warm, Hypnotic, Chill, Oriental Vibes")

        QMetaObject.invokeMethod(dlg, "edit", Q_ARG("QVariant", job.id), Q_ARG("QVariant", job.title))
        pump()
        self.assertTrue(dlg.property("opened") and dlg.property("editing"))   # menu entry: straight to the editor
        self.assertEqual(dlg.property("loadError"), "")
        QMetaObject.invokeMethod(root, "typeInto", Q_ARG("QVariant", "mood"), Q_ARG("QVariant", "Calm"))
        QMetaObject.invokeMethod(dlg, "save")
        pump()
        self.assertFalse(dlg.property("opened"))
        self.assertEqual(mp3tags.read_tags(self.folder / "track1.mp3").mood, "Calm")

        QMetaObject.invokeMethod(dlg, "edit", Q_ARG("QVariant", 999), Q_ARG("QVariant", "x"))   # unknown job
        pump()
        self.assertIn("not found", dlg.property("loadError"))
        QMetaObject.invokeMethod(dlg, "next")
        pump()


if __name__ == "__main__":
    unittest.main()
