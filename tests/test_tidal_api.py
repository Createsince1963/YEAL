"""TIDAL DIY API (0.9.1): parsing, BTS manifests, token refresh on 401, playlist ETag - against a fake HTTP server."""
import base64
import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import _path  # noqa: F401

from yeal.core import tidal_api as T


def bts(url="https://cdn.test/a.flac", mime="audio/flac"):
    return base64.b64encode(json.dumps({"mimeType": mime, "codecs": "flac", "encryptionType": "NONE",
                                        "urls": [url]}).encode()).decode()


TRACK = {"id": 11, "title": "Highway Star", "version": "Remastered", "duration": 366, "trackNumber": 1,
         "explicit": False, "audioQuality": "LOSSLESS", "mediaMetadata": {"tags": ["LOSSLESS", "HIRES_LOSSLESS"]},
         "artists": [{"id": 3355, "name": "Deep Purple"}], "album": {"id": 7, "title": "Machine Head", "cover": "aa-bb"}}
ALBUM = {"id": 7, "title": "Machine Head", "cover": "aa-bb-cc", "numberOfTracks": 1, "releaseDate": "1972-03-25",
         "audioQuality": "LOSSLESS", "artists": [{"id": 3355, "name": "Deep Purple"}], "duration": 366}
PLAYLIST = {"uuid": "pl-1", "title": "Mine", "numberOfTracks": 2, "creator": {"id": 42}, "squareImage": "sq-1",
            "type": "USER", "duration": 600}


class Fake:
    """Shared state of the fake Tidal server."""
    def __init__(self):
        self.calls = []
        self.token_ok = "new-token"
        self.etag = '"17"'


def make_handler(state: Fake):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body=None, headers=None):
            raw = json.dumps(body if body is not None else {}).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _handle(self, method):
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            length = int(self.headers.get("Content-Length") or 0)
            form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()} if length else {}
            state.calls.append((method, u.path, q, form, dict(self.headers)))
            if self.headers.get("Authorization") != "Bearer " + state.token_ok:
                return self._send(401, {"userMessage": "expired"})
            p = u.path
            if p == "/v1/pages/home":
                return self._send(200, {"rows": [
                    {"modules": [{"type": "TRACK_LIST", "title": "New", "pagedList": {"items": [TRACK], "dataApiPath": "pages/data/x"}}]},
                    {"modules": [{"type": "PAGE_LINKS_CLOUD", "title": "Genres", "pagedList": {"items": [{"title": "Pop", "apiPath": "pages/genre_pop"}]}}]},
                    {"modules": [{"type": "FEATURED_PROMOTIONS", "title": "Featured", "items": [{"type": "ALBUM", "artifactId": "7", "shortHeader": "MH", "imageId": "i-1"}]}]},
                    {"modules": [{"type": "UNKNOWN_THING", "title": "skip"}]}]})
            if p == "/v2/feed/activities":
                return self._send(200, {"activities": [
                    {"followableActivity": {"album": ALBUM, "activityType": "NEW_ALBUM_RELEASE", "occurredAt": "2026-10-01T00:00:00Z"}, "seen": True},
                    {"followableActivity": {"historyMix": {"id": "m1", "titleTextInfo": {"text": "September"}, "images": {"SMALL": {"url": "https://img/m1"}}},
                                            "activityType": "NEW_HISTORY_MIX", "occurredAt": "2026-10-20T00:00:00Z"}, "seen": False}],
                    "stats": {}})
            if p == "/v1/albums/7":
                return self._send(200, ALBUM)
            if p == "/v1/albums/7/items":
                off = int(q.get("offset", 0))
                items = [{"item": dict(TRACK, id=100 + i, trackNumber=i + 1), "type": "track"} for i in range(off, min(off + int(q["limit"]), 60))]
                return self._send(200, {"items": items, "totalNumberOfItems": 60})
            if p == "/v1/tracks/11/playbackinfopostpaywall":
                if q["audioquality"] == "HI_RES_LOSSLESS":
                    return self._send(200, {"audioQuality": "HI_RES_LOSSLESS", "manifestMimeType": "application/dash+xml",
                                            "manifest": base64.b64encode(b"<MPD/>").decode()})
                return self._send(200, {"audioQuality": "LOSSLESS", "manifestMimeType": "application/vnd.tidal.bts",
                                        "manifest": bts(), "bitDepth": 16, "sampleRate": 44100})
            if p == "/v1/tracks/11/lyrics":
                return self._send(200, {"lyrics": "a\nb", "subtitles": "[00:01.50] a\n[01:02.00] b\nnoise"})
            if p == "/v1/playlists/pl-1":
                if method == "GET":
                    return self._send(200, PLAYLIST, {"ETag": state.etag})
                if self.headers.get("If-None-Match") != state.etag:
                    return self._send(412, {"userMessage": "precondition"})
                return self._send(200 if method == "POST" else 204)
            if p.startswith("/v1/playlists/pl-1/items"):
                if method == "GET":
                    return self._send(200, {"items": [{"item": TRACK, "type": "track"}], "totalNumberOfItems": 1})
                if self.headers.get("If-None-Match") != state.etag:
                    return self._send(412, {"userMessage": "precondition"})
                return self._send(200)
            if p == "/v1/users/42/playlists" and method == "POST":
                return self._send(201, dict(PLAYLIST, uuid="pl-new", title=form.get("title")))
            if p == "/v1/users/42/playlistsAndFavoritePlaylists":
                return self._send(200, {"items": [{"type": "USER_CREATED", "playlist": PLAYLIST},
                                                  {"type": "FAVORITE", "playlist": dict(PLAYLIST, uuid="pl-2", creator={"id": 0}, type="EDITORIAL")}],
                                        "totalNumberOfItems": 2})
            if p.startswith("/v1/users/42/favorites"):
                return self._send(200, {"items": [], "totalNumberOfItems": 0})
            return self._send(404, {"userMessage": "nope"})

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def do_DELETE(self):
            self._handle("DELETE")
    return H


class TidalApiTest(unittest.TestCase):
    def setUp(self):
        self.state = Fake()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.state))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d/" % self.server.server_address[1]
        self.tmp = tempfile.TemporaryDirectory()
        self.auth_file = Path(self.tmp.name) / "auth.json"
        self.write_auth("new-token")
        self.refreshes = 0
        self.auth = T.Auth(self.auth_file, refresher=self.refresh)
        self.api = T.TidalApi(self.auth, base=base + "v1/", base2=base + "v2/")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def write_auth(self, token, expires=None):
        self.auth_file.write_text(json.dumps({"token": token, "user_id": 42, "country_code": "DE",
                                              "expires_at": expires or time.time() + 3600}), encoding="utf-8")

    def refresh(self):          # stands in for `tiddl auth refresh`
        self.refreshes += 1
        self.write_auth("new-token")
        return True

    def test_page_rows(self):
        rows = self.api.home()
        self.assertEqual([r["kind"] for r in rows], ["track", "link", "promo"])
        track = rows[0]["items"][0]
        self.assertEqual(track["title"], "Highway Star (Remastered)")
        self.assertEqual(track["subtitle"], "Deep Purple")
        self.assertEqual(track["quality"], "MAX")
        self.assertEqual(track["url"], "https://tidal.com/browse/track/11")
        self.assertEqual(track["cover"], "https://resources.tidal.com/images/aa/bb/160x160.jpg")
        self.assertEqual(rows[1]["items"][0]["id"], "pages/genre_pop")
        self.assertEqual(rows[2]["items"][0]["url"], "https://tidal.com/browse/album/7")
        self.assertEqual(rows[0]["more"], "pages/data/x")
        # every request carries the country of the sign-in
        self.assertEqual(self.state.calls[-1][2]["countryCode"], "DE")

    def test_cache_reuses_answers(self):
        self.api.home()
        self.api.home()
        self.assertEqual(len([c for c in self.state.calls if c[1] == "/v1/pages/home"]), 1)

    def test_feed_sorted_newest_first(self):
        feed = self.api.feed()
        self.assertEqual([f["kind"] for f in feed], ["mix", "album"])
        self.assertEqual(feed[0]["title"], "September")
        self.assertEqual(feed[0]["cover"], "https://img/m1")
        self.assertEqual(feed[1]["date"], "2026-10-01")
        call = [c for c in self.state.calls if c[1] == "/v2/feed/activities"][0]
        self.assertEqual(call[2]["userId"], "42")       # no trailing slash, userId in the query

    def test_album_reads_all_pages(self):
        album = self.api.album(7)
        self.assertEqual(album["year"], "1972")
        self.assertEqual(len(album["items"]), 60)
        self.assertEqual(album["items"][-1]["number"], 60)
        limits = {c[2]["limit"] for c in self.state.calls if c[1] == "/v1/albums/7/items"}
        self.assertEqual(limits, {str(T.PAGE_LIMIT)})

    def test_bts_manifest_and_hires_fallback(self):
        st = self.api.stream(11, "HI_RES_LOSSLESS")
        self.assertEqual(st["url"], "https://cdn.test/a.flac")
        self.assertEqual(st["mime"], "audio/flac")
        self.assertTrue(st["downgraded"])
        self.assertEqual(st["badge"], "16-bit 44.1kHz")
        self.assertFalse(self.api.stream(11)["downgraded"])

    def test_quality_badges(self):
        self.assertEqual(T.quality_badge({"bitDepth": 24, "sampleRate": 96000}), "24-bit 96kHz")
        self.assertEqual(T.quality_badge({"audioQuality": "HIGH"}), "AAC 320")
        self.assertEqual(T.quality_badge({"audioQuality": "LOW"}), "AAC 96")

    def test_lyrics_synced(self):
        ly = self.api.lyrics(11)
        self.assertEqual(ly["text"], "a\nb")
        self.assertEqual(ly["synced"], [[1500, "a"], [62000, "b"]])

    def test_401_refreshes_once_and_retries(self):
        self.write_auth("old-token")
        self.auth.load()
        self.assertEqual(self.api.lyrics(11)["text"], "a\nb")
        self.assertEqual(self.refreshes, 1)
        self.assertEqual(self.auth.token, "new-token")

    def test_401_after_refresh_is_an_error(self):
        self.state.token_ok = "never"
        with self.assertRaises(T.TidalError) as cm:
            self.api.lyrics(11)
        self.assertEqual(cm.exception.status, 401)
        self.assertEqual(self.refreshes, 1)

    def test_expired_token_is_refreshed_first(self):
        self.write_auth("old-token", expires=time.time() - 10)
        self.auth.load()
        self.api.lyrics(11)
        self.assertEqual(self.refreshes, 1)
        self.assertEqual(len([c for c in self.state.calls if c[1].endswith("/lyrics")]), 1)

    def test_not_signed_in(self):
        self.auth_file.unlink()
        api = T.TidalApi(T.Auth(self.auth_file, refresher=lambda: False), base="http://127.0.0.1:1/")
        with self.assertRaises(T.TidalError) as cm:
            api.home()
        self.assertEqual(cm.exception.status, 0)

    def test_playlist_writes_send_etag(self):
        self.api.add_to_playlist("pl-1", [11, 12])
        post = [c for c in self.state.calls if c[0] == "POST" and c[1] == "/v1/playlists/pl-1/items"][0]
        self.assertEqual(post[3]["trackIds"], "11,12")
        self.assertEqual(post[4].get("If-None-Match"), self.state.etag)
        self.api.remove_from_playlist("pl-1", [3, 1])
        self.assertTrue(any(c[0] == "DELETE" and c[1] == "/v1/playlists/pl-1/items/1,3" for c in self.state.calls))
        self.api.rename_playlist("pl-1", "New name")
        self.api.delete_playlist("pl-1")
        writes = [c for c in self.state.calls if c[0] != "GET"]
        self.assertTrue(all(c[4].get("If-None-Match") == self.state.etag for c in writes))

    def test_changed_playlist_gives_412_message(self):
        real = self.api._etag
        self.api._etag = lambda uuid: '"old"'
        with self.assertRaises(T.TidalError) as cm:
            self.api.rename_playlist("pl-1", "x")
        self.assertEqual(cm.exception.status, 412)
        self.api._etag = real

    def test_create_playlist_and_user_playlists(self):
        new = self.api.create_playlist("Road trip")
        self.assertEqual((new["id"], new["title"], new["mine"]), ("pl-new", "Road trip", True))
        pls = self.api.user_playlists()
        self.assertEqual([p["mine"] for p in pls], [True, False])
        self.assertEqual(pls[1]["subtitle"], "TIDAL")

    def test_write_clears_cache(self):
        self.api.home()
        self.api.add_favorite("track", 11)
        self.api.home()
        self.assertEqual(len([c for c in self.state.calls if c[1] == "/v1/pages/home"]), 2)
        fav = [c for c in self.state.calls if c[0] == "POST" and "favorites" in c[1]][0]
        self.assertEqual((fav[1], fav[3]), ("/v1/users/42/favorites/tracks", {"trackIds": "11"}))

    def test_image_url(self):
        self.assertEqual(T.image_url("ab-cd", 640), "https://resources.tidal.com/images/ab/cd/640x640.jpg")
        self.assertEqual(T.image_url(""), "")
        self.assertEqual(T.image_url("https://x/y"), "https://x/y")


if __name__ == "__main__":
    unittest.main()
