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


if __name__ == "__main__":
    unittest.main()
