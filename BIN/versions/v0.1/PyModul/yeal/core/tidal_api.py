"""Tidal catalogue and library access for TIDAL DIY (Yeal 0.9.1): the API behind Yeal's own TIDAL view.

Standard library only (like core/streaming.py), no Qt, no tiddl internals. The sign-in is the one of the tiddl
helper (`~/.tiddl/auth.json`, see core/tidal.py): Yeal reads the token from there and never stores it itself.
When the token has expired (or Tidal answers 401) `tiddl auth refresh` is run once and the request repeated.

Every answer is reduced to small, uniform dicts for QML:
    {kind, id, title, subtitle, cover, duration, explicit, quality, url, ...}
`url` is the canonical link https://tidal.com/browse/<kind>/<id>, which the tiddl download path understands.

Tidal's web API is not documented; endpoints were checked against a real account on 2026-10-25. Each call fails
on its own (TidalError), so one broken area (feed, lyrics) never blocks the rest of the view.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import tidal

API = "https://api.tidal.com/v1/"
API2 = "https://api.tidal.com/v2/"
IMAGES = "https://resources.tidal.com/images/"
BROWSE = "https://tidal.com/browse/"
TIMEOUT = 20
CACHE_TTL = 300            # seconds a GET answer is reused
MAX_PARALLEL = 2           # Tidal may flag accounts that send many requests at once
PAGE_LIMIT = 50            # items per request for long lists (Tidal refuses more on some endpoints)
_LRC = re.compile(r"^\[(\d+):(\d+(?:\.\d+)?)\]\s?(.*)$")
_DASH = "application/dash+xml"


class TidalError(Exception):
    """A request failed. `status` is the HTTP status (0 = no connection / not signed in)."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


# ---- images and small helpers ------------------------------------------------------------------------------

def image_url(image_id: Optional[str], size: int = 320, wide: bool = False) -> str:
    """resources.tidal.com address of a cover / picture id ('ab12-cd34-...' -> 'ab12/cd34/.../320x320.jpg')."""
    if not image_id or not isinstance(image_id, str):
        return ""
    if image_id.startswith("http"):
        return image_id
    height = round(size * 9 / 16) if wide else size
    return "%s%s/%dx%d.jpg" % (IMAGES, image_id.replace("-", "/"), size, height)


def resize_image(url: str, size: int) -> str:
    """The same resources.tidal.com picture in another square size ('.../160x160.jpg' -> '.../320x320.jpg')."""
    return re.sub(r"/\d+x\d+\.jpg$", "/%dx%d.jpg" % (size, size), url or "") if (url or "").startswith(IMAGES) else (url or "")


def browse_url(kind: str, item_id) -> str:
    return "%s%s/%s" % (BROWSE, kind, item_id)


def _artists(obj: dict) -> str:
    names = [a.get("name", "") for a in obj.get("artists") or [] if isinstance(a, dict)]
    if not names and isinstance(obj.get("artist"), dict):
        names = [obj["artist"].get("name", "")]
    return ", ".join(n for n in names if n)


def _main_artist(obj: dict) -> dict:
    if isinstance(obj.get("artist"), dict):
        return obj["artist"]
    for a in obj.get("artists") or []:
        if isinstance(a, dict):
            return a
    return {}


def quality_label(audio_quality: str = "", tags=None) -> str:
    """Short badge as Tidal shows it: MAX (hi-res), HiFi (CD quality), Atmos, or '' for AAC."""
    tags = set(tags or [])
    if "DOLBY_ATMOS" in tags:
        return "Atmos"
    if "HIRES_LOSSLESS" in tags or audio_quality in ("HI_RES", "HI_RES_LOSSLESS"):
        return "MAX"
    if "LOSSLESS" in tags or audio_quality == "LOSSLESS":
        return "HiFi"
    return ""


def _tags(obj: dict) -> list:
    return ((obj.get("mediaMetadata") or {}).get("tags")) or []


def _year(date: str) -> str:
    return (date or "")[:4]


# ---- normalizers ---------------------------------------------------------------------------------------------

def norm_track(t: dict) -> dict:
    album = t.get("album") or {}
    artist = _main_artist(t)
    title = t.get("title", "")
    if t.get("version"):
        title = "%s (%s)" % (title, t["version"])
    return {
        "kind": "track", "id": str(t.get("id", "")), "title": title, "subtitle": _artists(t),
        "artistId": str(artist.get("id", "")), "album": album.get("title", ""), "albumId": str(album.get("id", "")),
        "cover": image_url(album.get("cover"), 160), "duration": int(t.get("duration") or 0),
        "explicit": bool(t.get("explicit")), "quality": quality_label(t.get("audioQuality", ""), _tags(t)),
        "number": int(t.get("trackNumber") or 0), "volume": int(t.get("volumeNumber") or 0),
        "streamable": bool(t.get("allowStreaming", True)), "url": browse_url("track", t.get("id", "")),
    }


def norm_video(v: dict) -> dict:
    artist = _main_artist(v)
    return {
        "kind": "video", "id": str(v.get("id", "")), "title": v.get("title", ""), "subtitle": _artists(v),
        "artistId": str(artist.get("id", "")), "cover": image_url(v.get("imageId"), 320, wide=True),
        "duration": int(v.get("duration") or 0), "explicit": bool(v.get("explicit")),
        "quality": (v.get("quality") or "").replace("MP4_", ""), "year": _year(v.get("releaseDate", "")),
        "url": browse_url("video", v.get("id", "")),
    }


def norm_album(a: dict) -> dict:
    artist = _main_artist(a)
    return {
        "kind": "album", "id": str(a.get("id", "")), "title": a.get("title", ""), "subtitle": _artists(a),
        "artistId": str(artist.get("id", "")), "cover": image_url(a.get("cover"), 320),
        "coverLarge": image_url(a.get("cover"), 640), "duration": int(a.get("duration") or 0),
        "explicit": bool(a.get("explicit")), "quality": quality_label(a.get("audioQuality", ""), _tags(a)),
        "year": _year(a.get("releaseDate", "")), "date": a.get("releaseDate", "") or "",
        "tracks": int(a.get("numberOfTracks") or 0), "type": a.get("type", "") or "",
        "copyright": a.get("copyright", "") or "", "url": browse_url("album", a.get("id", "")),
    }


def norm_artist(a: dict) -> dict:
    return {
        "kind": "artist", "id": str(a.get("id", "")), "title": a.get("name", ""), "subtitle": "",
        "cover": image_url(a.get("picture"), 320), "url": browse_url("artist", a.get("id", "")),
    }


def norm_playlist(p: dict, my_id: str = "") -> dict:
    creator = p.get("creator") or {}
    owner = str(creator.get("id", "")) if creator else ""
    by = creator.get("name") or ("TIDAL" if p.get("type") in ("EDITORIAL", "ARTIST") or owner in ("", "0") else "")
    return {
        "kind": "playlist", "id": str(p.get("uuid", "")), "title": p.get("title", ""),
        "subtitle": by or ("%d" % int(p.get("numberOfTracks") or 0)),
        "cover": image_url(p.get("squareImage") or p.get("image"), 320),
        "duration": int(p.get("duration") or 0), "tracks": int(p.get("numberOfTracks") or 0),
        "description": p.get("description") or "", "owner": owner, "mine": bool(my_id) and owner == str(my_id),
        "url": browse_url("playlist", p.get("uuid", "")),
    }


def _mix_image(m: dict) -> str:
    images = m.get("images") or {}
    for key in ("MEDIUM", "SMALL", "LARGE"):
        if isinstance(images.get(key), dict) and images[key].get("url"):
            return images[key]["url"]
    return ""


def norm_mix(m: dict) -> dict:
    title = m.get("title") or (m.get("titleTextInfo") or {}).get("text", "")
    sub = m.get("subTitle") or (m.get("subTitleTextInfo") or {}).get("text", "") or m.get("shortSubtitle", "")
    return {
        "kind": "mix", "id": str(m.get("id", "")), "title": title or "Mix", "subtitle": sub or "",
        "cover": _mix_image(m), "url": browse_url("mix", m.get("id", "")),
    }


_NORMALIZERS = {"track": norm_track, "video": norm_video, "album": norm_album, "artist": norm_artist,
                "playlist": norm_playlist, "mix": norm_mix}


def norm_item(obj: dict, kind: str = "") -> Optional[dict]:
    """Normalize one item of any kind; list entries of the form {"item": {...}, "type": "track"} are unwrapped."""
    if not isinstance(obj, dict):
        return None
    if isinstance(obj.get("item"), dict):
        kind = (obj.get("type") or kind or "").lower()
        obj = obj["item"]
    if not kind:
        kind = "playlist" if "uuid" in obj else "artist" if "name" in obj and "title" not in obj else \
            "album" if "numberOfTracks" in obj and "cover" in obj else "video" if "imageId" in obj else "track"
    fn = _NORMALIZERS.get(kind)
    return fn(obj) if fn else None


# ---- pages (home, explore, genre pages) ----------------------------------------------------------------------

_MODULE_KIND = {"TRACK_LIST": "track", "ALBUM_LIST": "album", "ARTIST_LIST": "artist", "PLAYLIST_LIST": "playlist",
                "VIDEO_LIST": "video", "MIX_LIST": "mix"}
_PROMO_KIND = {"PLAYLIST": "playlist", "ALBUM": "album", "ARTIST": "artist", "VIDEO": "video", "TRACK": "track",
               "MIX": "mix"}


def parse_page(data: dict) -> List[dict]:
    """Tidal page JSON -> rows: {title, kind, items, more}. kind 'link' rows hold sub pages ({title, path})."""
    rows: List[dict] = []
    for row in (data or {}).get("rows") or []:
        for module in row.get("modules") or []:
            mtype = module.get("type", "")
            title = module.get("title") or ""
            paged = module.get("pagedList") or {}
            if mtype in _MODULE_KIND:
                kind = _MODULE_KIND[mtype]
                items = [x for x in (norm_item(i, kind) for i in paged.get("items") or []) if x]
                if items:
                    rows.append({"title": title, "kind": kind, "items": items, "more": paged.get("dataApiPath", "")})
            elif mtype in ("PAGE_LINKS_CLOUD", "PAGE_LINKS"):
                links = [{"kind": "link", "id": i.get("apiPath", ""), "title": i.get("title", ""),
                          "subtitle": "", "cover": image_url(i.get("imageId"), 320) if i.get("imageId") else "",
                          "url": ""} for i in paged.get("items") or [] if i.get("apiPath")]
                if links:
                    rows.append({"title": title, "kind": "link", "items": links, "more": ""})
            elif mtype == "FEATURED_PROMOTIONS":
                promos = []
                for i in module.get("items") or []:
                    kind = _PROMO_KIND.get(i.get("type", ""))
                    if not kind or not i.get("artifactId"):
                        continue
                    promos.append({"kind": kind, "id": str(i["artifactId"]), "title": i.get("shortHeader") or i.get("header", ""),
                                   "subtitle": i.get("shortSubHeader") or i.get("header", ""),
                                   "cover": image_url(i.get("imageId"), 640, wide=True),
                                   "url": browse_url(kind, i["artifactId"])})
                if promos:
                    rows.append({"title": title, "kind": "promo", "items": promos, "more": ""})
    return rows


def parse_feed(data: dict) -> List[dict]:
    """Feed activities -> items (new albums of followed artists, monthly history mixes), newest first."""
    out = []
    for act in (data or {}).get("activities") or []:
        fa = act.get("followableActivity") or {}
        when = fa.get("occurredAt") or ""
        item = None
        if isinstance(fa.get("album"), dict):
            item = norm_album(fa["album"])
        elif isinstance(fa.get("historyMix"), dict):
            item = norm_mix(fa["historyMix"])
            when = when or fa["historyMix"].get("updated", "")
        if item:
            item.update(activity=fa.get("activityType", ""), date=when[:10], seen=bool(act.get("seen")))
            out.append(item)
    out.sort(key=lambda x: x.get("date", ""), reverse=True)
    return out


def parse_lyrics(data: dict) -> dict:
    """{'text': plain lyrics, 'synced': [[ms, line], ...]} (synced is empty when Tidal has no timed lyrics)."""
    synced = []
    for line in (data.get("subtitles") or "").splitlines():
        m = _LRC.match(line.strip())
        if m:
            synced.append([int((int(m.group(1)) * 60 + float(m.group(2))) * 1000), m.group(3)])
    return {"text": data.get("lyrics") or "", "synced": synced, "provider": data.get("lyricsProvider") or ""}


def quality_badge(info: dict) -> str:
    """Badge of what is actually played: '24-bit 96kHz', '16-bit 44.1kHz', 'AAC 320', 'AAC 96'."""
    depth, rate = info.get("bitDepth"), info.get("sampleRate")
    if depth and rate:
        khz = ("%.1f" % (rate / 1000)).rstrip("0").rstrip(".")
        return "%d-bit %skHz" % (depth, khz)
    return {"HIGH": "AAC 320", "LOW": "AAC 96"}.get(info.get("audioQuality", ""), info.get("audioQuality", ""))


def decode_manifest(info: dict) -> dict:
    """playbackinfo JSON -> {'url', 'mime', 'codec', 'dash'}. BTS manifests hold direct file links."""
    mime = info.get("manifestMimeType", "")
    raw = base64.b64decode(info.get("manifest") or b"")
    if mime == _DASH:
        return {"url": "", "mime": "", "codec": "", "dash": True, "encrypted": False}
    man = json.loads(raw.decode("utf-8")) if raw else {}
    urls = man.get("urls") or []
    return {"url": urls[0] if urls else "", "mime": man.get("mimeType", ""), "codec": man.get("codecs", ""),
            "dash": False, "encrypted": (man.get("encryptionType") or "NONE") != "NONE"}


# ---- sign-in -------------------------------------------------------------------------------------------------

def _run_refresh() -> bool:
    """`tiddl auth refresh` (tiddl writes the new token to its auth.json)."""
    exe = tidal.find_tiddl()
    if not exe:
        return False
    try:
        subprocess.run([exe, "auth", "refresh"], capture_output=True, timeout=30, env=tidal._env(),
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return False
    return True


class Auth:
    """The tiddl sign-in, read from auth.json (re-read on every refresh)."""

    def __init__(self, path: Optional[Path] = None, refresher: Optional[Callable[[], bool]] = None):
        self.path = Path(path) if path else tidal.app_path() / "auth.json"
        self._refresher = refresher or _run_refresh
        self.token = self.user_id = self.country = ""
        self.expires = 0.0
        self.load()

    def load(self) -> bool:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            data = {}
        self.token = str(data.get("token") or data.get("access_token") or "")
        self.user_id = str(data.get("user_id") or "")
        self.country = str(data.get("country_code") or "US")
        try:
            self.expires = float(data.get("expires_at") or 0)
        except (TypeError, ValueError):
            self.expires = 0.0
        return bool(self.token)

    @property
    def valid(self) -> bool:
        return bool(self.token)

    def expired(self, now: Optional[float] = None) -> bool:
        return bool(self.expires) and (now or time.time()) > self.expires - 60

    def refresh(self) -> bool:
        return bool(self._refresher()) and self.load()


# ---- client ----------------------------------------------------------------------------------------------------

class TidalApi:
    def __init__(self, auth: Optional[Auth] = None, base: str = API, base2: str = API2, locale: str = "de_DE",
                 opener: Callable = urllib.request.urlopen, cache_ttl: float = CACHE_TTL):
        self.auth = auth or Auth()
        self.base, self.base2, self.locale = base, base2, locale
        self._open = opener
        self._ttl = cache_ttl
        self._cache: Dict[str, Tuple[float, dict]] = {}
        self._lock = threading.Lock()
        self._gate = threading.Semaphore(MAX_PARALLEL)

    # -- low level
    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    def _url(self, path: str, params: Optional[dict], v2: bool = False) -> str:
        q = {"countryCode": self.auth.country, "locale": self.locale, "deviceType": "BROWSER"}
        q.update(params or {})
        return (self.base2 if v2 else self.base) + path + "?" + urllib.parse.urlencode(q)

    def _send(self, method: str, url: str, data: Optional[dict], headers: Optional[dict]):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", "Bearer " + self.auth.token)
        req.add_header("Accept", "application/json")
        if body is not None:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        with self._gate:
            with self._open(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                return raw, dict(resp.headers.items())

    def request(self, method: str, path: str, params: Optional[dict] = None, data: Optional[dict] = None,
                headers: Optional[dict] = None, v2: bool = False, cache: bool = True) -> Tuple[dict, dict]:
        """One API call -> (json, response headers). GETs are cached; 401 triggers one token refresh."""
        if not self.auth.valid and not self.auth.load():
            raise TidalError("Not signed in to Tidal.", 0)
        if self.auth.expired():
            self.auth.refresh()
        url = self._url(path, params, v2)
        key = method + " " + url
        if method == "GET" and cache:
            with self._lock:
                hit = self._cache.get(key)
            if hit and time.time() - hit[0] < self._ttl:
                return hit[1], {}
        for attempt in (1, 2):
            try:
                raw, head = self._send(method, url, data, headers)
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 401 and attempt == 1 and self.auth.refresh():
                    continue
                raise TidalError(_http_message(exc), exc.code) from None
            except (urllib.error.URLError, OSError, ValueError) as exc:
                raise TidalError("Tidal could not be reached: %s" % getattr(exc, "reason", exc), 0) from None
        try:
            result = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            raise TidalError("Tidal sent an unreadable answer.", 0) from None
        if method == "GET" and cache:
            with self._lock:
                self._cache[key] = (time.time(), result)
        elif method != "GET":
            self.clear_cache()            # library changed: lists must be read again
        return result, head

    def get(self, path: str, params: Optional[dict] = None, v2: bool = False, cache: bool = True) -> dict:
        return self.request("GET", path, params, v2=v2, cache=cache)[0]

    def _all(self, path: str, kind: str = "", limit: int = 0, params: Optional[dict] = None) -> List[dict]:
        """Read a paged list completely (or up to `limit` items) and normalize it."""
        out: List[dict] = []
        offset = 0
        while True:
            q = dict(params or {}, limit=PAGE_LIMIT, offset=offset)
            data = self.get(path, q)
            items = data.get("items") or []
            out += [x for x in (norm_item(i, kind) for i in items) if x]
            offset += len(items)
            total = int(data.get("totalNumberOfItems") or 0)
            if not items or offset >= total or (limit and len(out) >= limit):
                return out[:limit] if limit else out

    # -- pages
    def page(self, path: str) -> List[dict]:
        """'pages/home', 'pages/explore', 'pages/genre_pop', ... -> rows."""
        path = path if path.startswith("pages/") else "pages/" + path
        return parse_page(self.get(path))

    def home(self) -> List[dict]:
        return self.page("pages/home")

    def explore(self) -> List[dict]:
        return self.page("pages/explore")

    def my_mixes(self) -> List[dict]:
        rows = self.page("pages/my_collection_my_mixes")
        return [i for r in rows for i in r["items"] if i["kind"] == "mix"]

    def more(self, data_path: str) -> List[dict]:
        """All items behind a row's 'more' path (pages/data/<id>)."""
        return self._all(data_path)

    def feed(self) -> List[dict]:
        return parse_feed(self.get("feed/activities", {"userId": self.auth.user_id}, v2=True, cache=False))

    def search(self, query: str, limit: int = 25) -> dict:
        data = self.get("search", {"query": query, "limit": limit,
                                   "types": "ARTISTS,ALBUMS,TRACKS,PLAYLISTS,VIDEOS"}, cache=False)
        result = {}
        for key, kind in (("tracks", "track"), ("albums", "album"), ("artists", "artist"),
                          ("playlists", "playlist"), ("videos", "video")):
            result[key] = [x for x in (norm_item(i, kind) for i in (data.get(key) or {}).get("items") or []) if x]
        top = data.get("topHit") or {}
        hit = norm_item(top.get("value") or {}, (top.get("type") or "").lower().rstrip("s")) if top else None
        result["top"] = hit
        return result

    # -- details
    def album(self, album_id) -> dict:
        info = norm_album(self.get("albums/%s" % album_id))
        info["items"] = self._all("albums/%s/items" % album_id)
        return info

    def album_credits(self, album_id) -> List[dict]:
        """[{'title': track, 'credits': [{'role', 'names'}]}]"""
        data = self.get("albums/%s/items/credits" % album_id, {"limit": PAGE_LIMIT, "includeContributors": "true"})
        out = []
        for entry in data.get("items") or []:
            track = entry.get("item") or {}
            credits = [{"role": c.get("type", ""), "names": ", ".join(x.get("name", "") for x in c.get("contributors") or [])}
                       for c in entry.get("credits") or []]
            out.append({"title": track.get("title", ""), "credits": credits})
        return out

    def artist(self, artist_id) -> dict:
        info = norm_artist(self.get("artists/%s" % artist_id))
        info["top"] = self._all("artists/%s/toptracks" % artist_id, "track", limit=20)
        info["albums"] = self._all("artists/%s/albums" % artist_id, "album", limit=100)
        info["singles"] = self._all("artists/%s/albums" % artist_id, "album", limit=100,
                                    params={"filter": "EPSANDSINGLES"})
        for part, path, kind in (("videos", "videos", "video"), ("similar", "similar", "artist")):
            try:
                info[part] = self._all("artists/%s/%s" % (artist_id, path), kind, limit=30)
            except TidalError:     # some artists have no similar list (404)
                info[part] = []
        return info

    def playlist(self, uuid: str) -> dict:
        info = norm_playlist(self.get("playlists/%s" % uuid, cache=False), self.auth.user_id)
        info["items"] = self._all("playlists/%s/items" % uuid)
        return info

    def mix(self, mix_id: str) -> dict:
        items = self._all("mixes/%s/items" % mix_id)
        return {"kind": "mix", "id": mix_id, "title": "Mix", "subtitle": "", "cover": items[0]["cover"] if items else "",
                "items": items, "url": browse_url("mix", mix_id)}

    def track(self, track_id) -> dict:
        return norm_track(self.get("tracks/%s" % track_id))

    def video(self, video_id) -> dict:
        return norm_video(self.get("videos/%s" % video_id))

    def describe(self, url: str) -> dict:
        """What a Tidal link points to, for the download list and the HTML player page:
        {kind, id, title, artist, cover (320 px), items: [track dicts]}. Raises TidalError."""
        kind, _, item_id = tidal.resource_of(url).partition("/")
        if not kind or not item_id:
            raise TidalError("Not a Tidal link.")
        items: List[dict] = []
        if kind == "track":
            head = self.track(item_id)
            items = [head]
        elif kind == "album":
            head = norm_album(self.get("albums/%s" % item_id))
            items = [t for t in self._all("albums/%s/items" % item_id) if t.get("kind") == "track"]
        elif kind == "playlist":
            head = norm_playlist(self.get("playlists/%s" % item_id, cache=False), self.auth.user_id)
            items = [t for t in self._all("playlists/%s/items" % item_id) if t.get("kind") == "track"]
        elif kind == "mix":
            head = self.mix(item_id)
            items = [t for t in head.get("items") or [] if t.get("kind") == "track"]
        elif kind == "video":
            head = self.video(item_id)
        else:
            head = norm_artist(self.get("artists/%s" % item_id))
        return {"kind": kind, "id": item_id, "title": head.get("title", ""), "artist": head.get("subtitle", ""),
                "cover": resize_image(head.get("coverLarge") or head.get("cover") or "", 320), "items": items}

    def lyrics(self, track_id) -> dict:
        return parse_lyrics(self.get("tracks/%s/lyrics" % track_id))

    # -- library
    def favorites(self, kind: str) -> List[dict]:
        """kind: tracks | albums | artists | videos | playlists"""
        if kind not in ("tracks", "albums", "artists", "videos", "playlists"):
            raise ValueError(kind)
        return self._all("users/%s/favorites/%s" % (self.auth.user_id, kind), kind[:-1],
                         params={"order": "DATE", "orderDirection": "DESC"})

    def favorite_ids(self) -> Dict[str, List[str]]:
        """{'track': [...ids], 'album': [...], 'artist': [...], 'video': [...], 'playlist': [...]} for heart states."""
        data = self.get("users/%s/favorites/ids" % self.auth.user_id, cache=False)
        return {k.lower(): [str(x) for x in v] for k, v in data.items() if isinstance(v, list)}

    def user_playlists(self) -> List[dict]:
        """Own and favorited playlists, newest first."""
        out = []
        offset = 0
        while True:
            data = self.get("users/%s/playlistsAndFavoritePlaylists" % self.auth.user_id,
                            {"limit": 50, "offset": offset, "order": "DATE", "orderDirection": "DESC"}, cache=False)
            items = data.get("items") or []
            for entry in items:
                if isinstance(entry.get("playlist"), dict):
                    p = norm_playlist(entry["playlist"], self.auth.user_id)
                    p["mine"] = p["mine"] or entry.get("type") == "USER_CREATED"
                    out.append(p)
            offset += len(items)
            if not items or offset >= int(data.get("totalNumberOfItems") or 0):
                return out

    # -- playback
    def stream(self, track_id, quality: str = "LOSSLESS") -> dict:
        """Playable link for the internal player. Hi-res comes as MPEG-DASH, which the player cannot open
        directly: then LOSSLESS (FLAC 16-bit) is used and `downgraded` is set."""
        info = self.get("tracks/%s/playbackinfopostpaywall" % track_id,
                        {"audioquality": quality, "playbackmode": "STREAM", "assetpresentation": "FULL"}, cache=False)
        man = decode_manifest(info)
        downgraded = False
        if (man["dash"] or not man["url"]) and quality != "LOSSLESS":
            info = self.get("tracks/%s/playbackinfopostpaywall" % track_id,
                            {"audioquality": "LOSSLESS", "playbackmode": "STREAM", "assetpresentation": "FULL"}, cache=False)
            man = decode_manifest(info)
            downgraded = True
        if not man["url"] or man["encrypted"]:
            raise TidalError("This track cannot be played in Yeal (no direct stream).", 0)
        # Tidal may also answer a hi-res request with CD quality right away (depends on the sign-in's client).
        downgraded = downgraded or (quality.startswith("HI_RES") and not str(info.get("audioQuality", "")).startswith("HI_RES"))
        return {"url": man["url"], "mime": man["mime"], "codec": man["codec"], "quality": info.get("audioQuality", ""),
                "badge": quality_badge(info), "downgraded": downgraded,
                "bitDepth": info.get("bitDepth") or 0, "sampleRate": info.get("sampleRate") or 0}

    # -- writing (favorites, playlists)
    _FAV_FIELD = {"track": "trackIds", "album": "albumIds", "artist": "artistIds", "video": "videoIds",
                  "playlist": "uuids"}

    def add_favorite(self, kind: str, item_id) -> None:
        field = self._FAV_FIELD[kind]
        self.request("POST", "users/%s/favorites/%ss" % (self.auth.user_id, kind), data={field: str(item_id)})

    def remove_favorite(self, kind: str, item_id) -> None:
        self._FAV_FIELD[kind]   # KeyError for unknown kinds
        self.request("DELETE", "users/%s/favorites/%ss/%s" % (self.auth.user_id, kind, item_id))

    def _etag(self, uuid: str) -> str:
        _, head = self.request("GET", "playlists/%s" % uuid, cache=False)
        tag = next((v for k, v in head.items() if k.lower() == "etag"), "")
        if not tag:
            raise TidalError("Tidal did not send the playlist version (ETag).", 0)
        return tag

    def create_playlist(self, title: str, description: str = "") -> dict:
        data, _ = self.request("POST", "users/%s/playlists" % self.auth.user_id,
                               data={"title": title, "description": description})
        return norm_playlist(data, self.auth.user_id)

    def rename_playlist(self, uuid: str, title: str, description: Optional[str] = None) -> None:
        data = {"title": title}
        if description is not None:
            data["description"] = description
        self.request("POST", "playlists/%s" % uuid, data=data, headers={"If-None-Match": self._etag(uuid)})

    def delete_playlist(self, uuid: str) -> None:
        self.request("DELETE", "playlists/%s" % uuid, headers={"If-None-Match": self._etag(uuid)})

    def add_to_playlist(self, uuid: str, track_ids: List) -> None:
        if not track_ids:
            return
        self.request("POST", "playlists/%s/items" % uuid,
                     data={"trackIds": ",".join(str(t) for t in track_ids), "onArtifactNotFound": "SKIP",
                           "onDupes": "SKIP"}, headers={"If-None-Match": self._etag(uuid)})

    def remove_from_playlist(self, uuid: str, indices: List[int]) -> None:
        """Remove entries by their position (0-based) in the playlist."""
        if not indices:
            return
        self.request("DELETE", "playlists/%s/items/%s" % (uuid, ",".join(str(int(i)) for i in sorted(indices))),
                     headers={"If-None-Match": self._etag(uuid)})


def _http_message(exc: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(exc.read().decode("utf-8", "replace"))
        text = body.get("userMessage") or body.get("error") or ""
    except Exception:  # noqa: BLE001
        text = ""
    if exc.code in (401, 403):
        return "Tidal refused the request (%d). Sign in again under Settings > Tidal. %s" % (exc.code, text)
    if exc.code == 404:
        return "Not available on Tidal (404). %s" % text
    if exc.code == 412:
        return "The playlist was changed elsewhere; reload it and try again."
    if exc.code == 429:
        return "Tidal asks to slow down (429). Wait a moment and try again."
    return "Tidal error %d. %s" % (exc.code, text)
