import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from yeal.core import album, extras


class AlbumFilesTest(unittest.TestCase):
    def test_playlist_is_utf8_crlf_with_encoding_line(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            tracks = []
            for n, name in enumerate(["01 - With or Without You.mp3", "02 - I Still Haven’t Found.mp3"], 1):
                (folder / name).write_bytes(b"x")
                tracks.append(folder / name)
            chapters = [{"title": "With or Without You", "start_time": 0, "end_time": 189},
                        {"title": "I Still Haven’t Found", "start_time": 189, "end_time": 300}]
            out = album.write_playlist(folder, "Best of U2— Covers | Instrumental", tracks, chapters)
            raw = out.read_bytes()
            self.assertTrue(raw.startswith(b"#EXTM3U\r\n#EXTENC:UTF-8\r\n"))
            text = raw.decode("utf-8")
            self.assertIn("I Still Haven’t Found.mp3\r\n", text)
            self.assertNotIn("\n\n", text.replace("\r\n", "\n").rstrip("\n") + "")

    def test_album_page_written_into_the_album_folder(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "Album [abc]"
            folder.mkdir()
            items = [{"index": 1, "title": "One", "file": "01 - One.mp3", "duration": "3:25", "page": ""}]
            page = extras.write_playlist_page(folder, "Album", "Artist", "https://example.org", items, "audio", "dark")
            self.assertEqual(page, folder / "Album [abc].html")
            self.assertIn("01%20-%20One.mp3", page.read_text(encoding="utf-8"))

    def test_playlist_page_layouts_differ_for_audio_and_video(self):
        items = [{"index": 1, "title": "One", "file": "01.mp4", "duration": "1:00", "page": "",
                  "thumb": "https://i.ytimg.com/vi/abc/mqdefault.jpg"}]
        v = extras.playlist_html("PL", "Me", "https://y", items, "video", "dark")
        a = extras.playlist_html("PL", "Me", "https://y", items, "audio", "dark")
        self.assertIn('class="v"', v)
        self.assertIn('class="a"', a)
        self.assertIn("mqdefault.jpg", v)
        self.assertIn('class="cv"', a)          # cover header only for audio
        self.assertIn("Shuffle", v)

    def test_no_online_player_when_embedding_is_forbidden(self):
        info = {"id": "tAYWPCBlNBA", "extractor_key": "Youtube"}
        self.assertTrue(extras.embed_url(info))
        self.assertEqual(extras.embed_url(dict(info, playable_in_embed=False)), "")

    def test_html_create_modes_write_linked_relative_pages(self):
        info = {"id": "abcdefghijk", "extractor_key": "Youtube", "title": "T", "description": "d",
                "webpage_url": "https://www.youtube.com/watch?v=abcdefghijk"}
        for mode, names in (("both", {"v.html", "v.file.html"}), ("server", {"v.html"}), ("file", {"v.html"})):
            with tempfile.TemporaryDirectory() as d:
                (Path(d) / "v.mp3").write_bytes(b"x")
                extras.write_extras(info, str(Path(d) / "v.mp3"), True, False, [], False, "audio", True, "dark",
                                    None, mode)
                self.assertEqual({p.name for p in Path(d).glob("*.html")}, names, mode)
                main = (Path(d) / "v.html").read_text(encoding="utf-8")
                self.assertNotIn(d, main)                       # no absolute path anywhere
                self.assertIn('src="v.mp3"', main)
                if mode == "both":
                    alt = (Path(d) / "v.file.html").read_text(encoding="utf-8")
                    self.assertIn('href="v.file.html"', main)   # relative link to the other page
                    self.assertIn('href="v.html"', alt)
                    self.assertIn("iframe", main)
                    self.assertNotIn("createElement(\"iframe\")", alt)
                if mode == "file":
                    self.assertNotIn("createElement(\"iframe\")", main)


if __name__ == "__main__":
    unittest.main()
