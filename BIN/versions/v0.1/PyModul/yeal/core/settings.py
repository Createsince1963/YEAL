"""Persistent user settings and download profiles (JSON, atomic writes, tolerant loading)."""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import List, Optional

from .models import AUDIO_FORMATS, COOKIE_BROWSERS, MODES, QUALITIES, DownloadOptions
from .tidal import TIDAL_ATMOS, TIDAL_QUALITIES, TIDAL_SINGLES, TIDAL_VIDEOS, TIDAL_VIDEO_QUALITIES

THEMES = ("system", "light", "dark")
HTML_OPEN_MODES = ("file", "server")
HTML_CREATE_MODES = ("server", "file", "both")
DL_BUTTON_STYLES = ("icon", "label", "off")   # header Download button: icon only / icon + text / hidden
DL_BUTTON_POSITIONS = ("left", "right")      # header Download button: next to the title or at the end of the bar
MAX_PROFILE_NAME = 40
MAX_STREAM_HOSTS = 10
TIDAL_DOCKS = ("left", "right", "float", "hidden")   # TIDAL DIY side areas: docked left/right, own window, hidden
TIDAL_PANES = ("playlists", "queue")
MAX_CUSTOM_COLORS = 5
PLAYER_COLORS = ("green", "blue", "red", "yellow", "purple", "orange", "pink", "cyan", "white")   # track player (QML: Theme.playerColor)


def default_profiles() -> List[dict]:
    def profile(name, mode, height, fmt="mp3"):
        return {"name": name, "mode": mode, "max_height": height, "audio_format": fmt,
                "embed_metadata": True, "subtitles": False, "playlist": False}
    return [
        profile("Video 4K", "video", 2160),
        profile("Video 1080p", "video", 1080),
        profile("Video 720p", "video", 720),
        profile("Video best", "video", 0),
        profile("Audio MP3", "audio", 0, "mp3"),
        profile("Audio original", "audio", 0, "best"),
    ]


def normalize_profile(raw: dict) -> dict:
    """Coerce an arbitrary dict into a valid profile (name is validated separately)."""
    raw = raw or {}
    mode = raw.get("mode") if raw.get("mode") in MODES else "video"
    try:
        height = int(raw.get("max_height", 1080))
    except (TypeError, ValueError):
        height = 1080
    fmt = raw.get("audio_format") if raw.get("audio_format") in AUDIO_FORMATS else "mp3"
    return {
        "name": str(raw.get("name", "")).strip()[:MAX_PROFILE_NAME],
        "mode": mode,
        "max_height": height if height in QUALITIES else 1080,
        "audio_format": fmt,
        "embed_metadata": bool(raw.get("embed_metadata", True)),
        "subtitles": bool(raw.get("subtitles", False)),
        "playlist": bool(raw.get("playlist", False)),
        "save_description": bool(raw.get("save_description", False)),
        "save_transcript": bool(raw.get("save_transcript", False)),
        "online_player": bool(raw.get("online_player", False)),
        "split_chapters": bool(raw.get("split_chapters", False)),
        "save_lyrics": bool(raw.get("save_lyrics", False)),
        "keep_whole": bool(raw.get("keep_whole", True)),
        "audio_bitrate": raw.get("audio_bitrate") if raw.get("audio_bitrate") in (128, 192, 256, 320) else 320,
    }


def _validate_sun_layout(raw) -> dict:
    """Places of the planets in the sun view: {'<view>.<planet>': {'deg': 0..360, 'r': 0.4..3}} - the angle on the orbit
    and the size of the orbit relative to the main orbit. Anything else is dropped; at most 40 planets are kept."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        if not isinstance(key, str) or not (0 < len(key) <= 40) or not isinstance(value, dict):
            continue
        try:
            deg, r = float(value.get("deg")), float(value.get("r"))
        except (TypeError, ValueError):
            continue
        if deg != deg or r != r:                     # NaN
            continue
        out[key] = {"deg": round(deg % 360.0, 1), "r": round(max(0.4, min(3.0, r)), 2)}
        if len(out) >= 40:
            break
    return out


MAX_QUEUE_LISTS = 30
MAX_LIST_ITEMS = 2000


def _validate_queue_lists(raw) -> list:
    """Saved queues: [{name, items: [{id, title, subtitle, file, cover}]}] - names unique, at most 30 lists of 2000 songs."""
    out, names = [], set()
    if not isinstance(raw, list):
        return out
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()[:60]
        if not name or name.lower() in names:
            continue
        items = []
        for it in entry.get("items") or []:
            if isinstance(it, dict) and it.get("file"):
                items.append({"kind": "track", "id": str(it.get("id") or it["file"])[:500], "title": str(it.get("title") or "")[:200],
                              "subtitle": str(it.get("subtitle") or "")[:200], "file": str(it["file"])[:500],
                              "cover": str(it.get("cover") or "")[:500], "duration": 0, "url": "", "source": name})
            if len(items) >= MAX_LIST_ITEMS:
                break
        if items:
            names.add(name.lower())
            out.append({"name": name, "items": items})
        if len(out) >= MAX_QUEUE_LISTS:
            break
    return out


def _clamp(value, low: int, high: int, default: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def _validate_tidal_layout(raw) -> dict:
    """TIDAL DIY layout: {'player': top|bottom, 'playlists'/'queue': {'dock', 'w', and for an own window 'x','y','h'}}.
    Unknown keys are dropped, sizes are clamped. Windows that ended up off-screen are moved back by the QML side,
    which knows the screens."""
    raw = raw if isinstance(raw, dict) else {}
    out = {"player": raw.get("player") if raw.get("player") in ("top", "bottom") else "bottom"}
    defaults = {"playlists": ("left", 220), "queue": ("right", 300)}
    for pane in TIDAL_PANES:
        src = raw.get(pane) if isinstance(raw.get(pane), dict) else {}
        dock, width = defaults[pane]
        pane_out = {"dock": src.get("dock") if src.get("dock") in TIDAL_DOCKS else dock,
                    "w": _clamp(src.get("w", width), 160, 900, width)}
        if pane_out["dock"] == "float":
            pane_out.update(x=_clamp(src.get("x", 100), -20000, 20000, 100), y=_clamp(src.get("y", 100), -20000, 20000, 100),
                            h=_clamp(src.get("h", 600), 200, 4000, 600))
        out[pane] = pane_out
    return out


@dataclass
class Settings:
    theme: str = "system"
    max_parallel: int = 2
    gentle_mode: bool = True          # pauses between requests/downloads, back-off on errors
    cookies_browser: str = ""         # reuse the YouTube login of firefox/edge/chrome for downloads
    ffmpeg_path: str = ""             # optional user-selected helper; empty = automatic lookup
    node_path: str = ""               # optional user-selected helper; empty = automatic lookup
    tidal_path: str = ""              # optional user-selected tiddl executable (Tidal helper); empty = automatic lookup
    tidal_quality: str = "high"       # Tidal: normal | high | max (needs a Tidal subscription)
    tidal_threads: int = 2            # Tidal: parallel track downloads (kept low on purpose)
    tidal_video_quality: str = "fhd"  # Tidal videos: sd | hd | fhd
    tidal_videos: str = "allow"       # videos inside albums/playlists/artists: none (skip) | allow (include) | only
    tidal_atmos: str = "none"         # Dolby Atmos versions: none (skip) | allow (include) | only
    tidal_singles: str = "none"       # artist links: none (albums only) | include (with singles/EPs) | only (singles/EPs)
    tidal_lyrics: bool = True         # embed lyrics into the files (tiddl metadata.lyrics)
    tidal_lrc: bool = False           # also write timed lyrics as .lrc files
    tidal_cover_embed: bool = True    # embed the cover into the files
    tidal_cover_file: bool = False    # save the album / playlist cover as an image file
    tidal_m3u: bool = False           # write an M3U playlist file for albums, playlists and mixes
    tidal_html: bool = False          # write Yeal's HTML player page into album / playlist folders
    tidal_no_skip: bool = False       # download again even when the file exists
    tidal_rewrite: bool = False       # rewrite the tags of files that already exist
    tidal_volume: int = 80            # TIDAL DIY player volume (0-100)
    tidal_tile_size: int = 140        # TIDAL DIY tile size in grids (px)
    tidal_opts_collapsed: bool = False   # workflow panel: the TIDAL options block is folded to one line
    tidal_player_style: str = "bar"      # TIDAL DIY player: bar (classic) | track (oval track player)
    local_volume: int = 80             # volume of the player for downloaded files
    audio_engine: str = "qt"           # qt: the Qt media player | dsp: Yeal's own engine (ffmpeg -> float32 chain -> sound card; needs numpy and ffmpeg)
    dsp: dict = field(default_factory=dict)          # settings of the own engine (equalizer, crossfeed ... see core/dsp.py validate_config)
    audio_buffer_ms: int = 600         # own engine: size of the sound card buffer (200..2000 ms); bigger rides out a busy GUI, smaller reacts faster (see ui/calibration.py)
    ui_refresh_hz: int = 20            # how often the player picture (oval, level band) is repainted (10..30)
    audio_output: str = ""             # the audio output of this computer the players use (Bluetooth headphones, speakers ...); "" = the system default
    sun_scale: float = 1.0             # sun views: size of the orbits (0.5 .. 3)
    sun_layout: dict = field(default_factory=dict)   # sun views: where the planets were dragged to (see _validate_sun_layout)
    tidal_sun: bool = False            # TIDAL DIY: the sun view (player as a sun with planets) instead of the pages
    glow_amp: int = 100                # glow around the inner lane of the player in percent (0 = none, 100 = normal, 300 = strong)
    outer_ring: str = "list"           # outer ring of the oval: list (progress through the playlist / album / folder / queue) | off
    custom_colors: List[str] = field(default_factory=list)   # colours the user made for the player (#rrggbb, at most 5)
    crossfade: int = 0                 # seamless change from song to song: 0 = off, otherwise 3..10 seconds of overlap
    level_amp: int = 100               # strength of the level band around the oval in percent (50..300)
    music_sources: List[dict] = field(default_factory=list)   # music folders of the user: [{id, name, path, kind}] (core/music_sources.py)
    queue_lists: List[dict] = field(default_factory=list)     # saved queues of the player for downloaded files: [{name, items: [...]}]
    library_source: str = ""           # player for downloaded files: "" = the downloads, else the id of a music source
    local_orbit: bool = True           # player for downloaded files: the planets (library, queue, played ...) are shown around the sun
    tidal_player_color: str = "green"  # track player colour: a name of PLAYER_COLORS or #rrggbb
    tidal_player_vis_mode: str = "song"  # track player band around the oval: song (loudness of the whole song) | flow (running level) | off
    tidal_layout: dict = field(default_factory=dict)   # TIDAL DIY areas: dock side / own window, sizes (see _validate_tidal_layout)
    panel_width: int = 400            # width of the tools panel next to the YouTube view
    panel_right: bool = False         # tools panel on the right instead of the left
    adblock_experimental: bool = False  # Windows browser view: block ad/tracker domains (experimental, needs restart)
    show_browser: bool = True         # Windows: embedded YouTube browser on the Downloads page
    auto_update: bool = True          # keep yt-dlp current (checked every few days)
    ask_mp3_tags: bool = True         # after an MP3 download: ask "edit the MP3 tags?" (the answer defaults to No)
    html_open_mode: str = "server"    # saved HTML pages: local Python HTTP server (online player) or file:// (independent)
    html_create: str = "both"         # which description pages are written: server | file | both (linked to each other)
    single_playback: bool = True      # saved HTML pages: the local player and the online player never play at the same time
    dl_button_style: str = "icon"     # direct Download button in the header button bar: icon | label | off
    dl_button_pos: str = "left"       # ... and where it sits in that bar: left | right
    stream_device: dict = field(default_factory=dict)   # chosen UPnP/DLNA renderer (Renderer.to_dict()); {} = none yet
    stream_hosts: List[str] = field(default_factory=list)  # manually added renderer addresses (IP, name or description URL)
    stream_volume: int = -1           # volume (0-100) set on the renderer before playing; -1 = leave the device as it is
    stream_scan_seconds: int = 4      # how long the network search waits for answers
    stream_port: int = 0              # port of Yeal's media server for the renderer; 0 = automatic (or fixed for the firewall)
    download_dir: str = ""            # empty -> platform default
    ask_drive_dialog: bool = True     # show the "download folder / external drive found" dialog (Don't ask again turns it off)
    rate_limit_kbps: int = 0          # 0 = unlimited
    proxy: str = ""
    custom_options: dict = field(default_factory=dict)
    profiles: List[dict] = field(default_factory=default_profiles)
    ui_collapsed: List[str] = field(default_factory=list)   # collapsed date groups of the download list
    drive_ignored: List[str] = field(default_factory=list)  # external drives the user said 'don't ask again'
    drive_folder: str = "Yeal"         # default folder name offered on an external drive
    list_group: str = "all"           # filter of the download list (all|active|queued|done|failed)
    active_profile: str = "Video 1080p"
    setup_complete: bool = True        # Backend changes this to False only for a new data folder
    window: dict = field(default_factory=dict)   # last window geometry: x, y, w, h, max
    profiles_version: int = 2         # 2 = "Video 4K" default profile exists

    # ---- validation -----------------------------------------------------
    def validate(self) -> "Settings":
        if self.theme not in THEMES:
            self.theme = "system"
        if self.cookies_browser not in COOKIE_BROWSERS:
            self.cookies_browser = ""
        self.ffmpeg_path = str(self.ffmpeg_path or "")[:1000]
        self.node_path = str(self.node_path or "")[:1000]
        self.tidal_path = str(self.tidal_path or "")[:1000]
        if self.tidal_quality == "low":                  # AAC 96 kbps is gone (older settings)
            self.tidal_quality = "normal"
        if self.tidal_quality not in TIDAL_QUALITIES:
            self.tidal_quality = "high"
        if self.tidal_video_quality not in TIDAL_VIDEO_QUALITIES:
            self.tidal_video_quality = "fhd"
        if self.tidal_videos not in TIDAL_VIDEOS:
            self.tidal_videos = "allow"
        try:
            self.tidal_threads = max(1, min(4, int(self.tidal_threads)))
        except (TypeError, ValueError):
            self.tidal_threads = 2
        if self.tidal_atmos not in TIDAL_ATMOS:
            self.tidal_atmos = "none"
        if self.tidal_singles not in TIDAL_SINGLES:
            self.tidal_singles = "none"
        for name in ("tidal_lyrics", "tidal_lrc", "tidal_cover_embed", "tidal_cover_file", "tidal_m3u", "tidal_html",
                     "tidal_no_skip", "tidal_rewrite"):
            setattr(self, name, bool(getattr(self, name)))
        self.tidal_volume = _clamp(self.tidal_volume, 0, 100, 80)
        self.tidal_tile_size = _clamp(self.tidal_tile_size, 90, 260, 140)
        self.local_volume = _clamp(self.local_volume, 0, 100, 80)
        self.audio_output = str(self.audio_output or "")[:200]
        self.audio_buffer_ms = _clamp(self.audio_buffer_ms, 200, 2000, 600)
        self.ui_refresh_hz = _clamp(self.ui_refresh_hz, 10, 30, 20)
        if self.audio_engine not in ("qt", "dsp"):
            self.audio_engine = "qt"
        from . import dsp as _dsp
        self.dsp = _dsp.validate_config(self.dsp)
        try:
            self.sun_scale = round(max(0.5, min(3.0, float(self.sun_scale))), 2)
        except (TypeError, ValueError):
            self.sun_scale = 1.0
        self.sun_layout = _validate_sun_layout(self.sun_layout)
        self.local_orbit = bool(self.local_orbit)
        from . import music_sources as _ms
        self.music_sources = _ms.validate_sources(self.music_sources)
        self.queue_lists = _validate_queue_lists(self.queue_lists)
        self.library_source = str(self.library_source or "")[:40]
        if self.library_source and not any(s["id"] == self.library_source for s in self.music_sources):
            self.library_source = ""
        try:
            self.glow_amp = max(0, min(300, int(self.glow_amp)))
        except (TypeError, ValueError):
            self.glow_amp = 100
        if self.outer_ring not in ("list", "off"):
            self.outer_ring = "list"
        seen: List[str] = []
        for c in (self.custom_colors if isinstance(self.custom_colors, list) else []):
            c = str(c).strip().lower()
            if re.fullmatch(r"#[0-9a-f]{6}", c) and c not in seen:
                seen.append(c)
        self.custom_colors = seen[:MAX_CUSTOM_COLORS]
        try:
            fade = int(self.crossfade)
        except (TypeError, ValueError):
            fade = 0
        self.crossfade = 0 if fade < 3 else min(10, fade)
        try:
            self.level_amp = max(50, min(300, int(self.level_amp)))
        except (TypeError, ValueError):
            self.level_amp = 100
        self.tidal_sun = bool(self.tidal_sun)
        color = str(self.tidal_player_color or "").strip().lower()
        self.tidal_player_color = color if color in PLAYER_COLORS or re.fullmatch(r"#[0-9a-f]{6}", color) else "green"
        self.tidal_layout = _validate_tidal_layout(self.tidal_layout)
        if self.tidal_player_style not in ("bar", "track"):
            self.tidal_player_style = "bar"
        if self.tidal_player_vis_mode not in ("song", "flow", "off"):
            self.tidal_player_vis_mode = "song"
        if self.html_open_mode not in HTML_OPEN_MODES:
            self.html_open_mode = "server"
        if self.html_create not in HTML_CREATE_MODES:
            self.html_create = "both"
        if self.dl_button_style not in DL_BUTTON_STYLES:
            self.dl_button_style = "icon"
        if self.dl_button_pos not in DL_BUTTON_POSITIONS:
            self.dl_button_pos = "left"
        self.max_parallel = max(1, min(4, int(self.max_parallel or 1)))
        self._validate_streaming()
        try:
            self.rate_limit_kbps = max(0, min(10_000_000, int(self.rate_limit_kbps)))
        except (TypeError, ValueError):
            self.rate_limit_kbps = 0
        self.ui_collapsed = [str(x)[:60] for x in self.ui_collapsed][:100] if isinstance(self.ui_collapsed, list) else []
        self.drive_ignored = [str(x)[:200] for x in self.drive_ignored][:50] if isinstance(self.drive_ignored, list) else []
        self.drive_folder = str(self.drive_folder or "Yeal")[:60]
        if self.list_group not in ("all", "active", "queued", "done", "failed"):
            self.list_group = "all"
        if not isinstance(self.custom_options, dict):
            self.custom_options = {}
        seen, clean = set(), []
        for raw in self.profiles if isinstance(self.profiles, list) else []:
            prof = normalize_profile(raw if isinstance(raw, dict) else {})
            if prof["name"] and prof["name"].lower() not in seen:
                seen.add(prof["name"].lower())
                clean.append(prof)
        self.profiles = clean or default_profiles()
        if self.active_profile not in self.profile_names():
            self.active_profile = self.profiles[0]["name"]
        return self

    def _validate_streaming(self) -> None:
        dev = self.stream_device if isinstance(self.stream_device, dict) else {}
        if not all(isinstance(dev.get(k), str) and dev.get(k) for k in ("id", "location", "control_url")):
            dev = {}
        self.stream_device = {k: str(v)[:500] for k, v in dev.items()} if dev else {}
        hosts = self.stream_hosts if isinstance(self.stream_hosts, list) else []
        self.stream_hosts = list(dict.fromkeys(str(h).strip()[:300] for h in hosts if str(h).strip()))[:MAX_STREAM_HOSTS]
        for key, lo, hi, default in (("stream_volume", -1, 100, -1), ("stream_scan_seconds", 2, 15, 4),
                                     ("stream_port", 0, 65535, 0)):
            try:
                setattr(self, key, max(lo, min(hi, int(getattr(self, key)))))
            except (TypeError, ValueError):
                setattr(self, key, default)
        if 0 < self.stream_port < 1024:
            self.stream_port = 0

    # ---- profiles -------------------------------------------------------
    def profile_names(self) -> List[str]:
        return [p["name"] for p in self.profiles]

    def get_profile(self, name: Optional[str] = None) -> dict:
        name = name or self.active_profile
        return next((p for p in self.profiles if p["name"] == name), self.profiles[0])

    def save_profile(self, old_name: str, raw: dict) -> str:
        """Create (old_name == '') or update/rename a profile. Returns '' or an error text."""
        prof = normalize_profile(raw)
        if not prof["name"]:
            return "Please enter a name."
        taken = {n.lower() for n in self.profile_names() if n != old_name}
        if prof["name"].lower() in taken:
            return "A profile with this name already exists."
        for i, existing in enumerate(self.profiles):
            if existing["name"] == old_name:
                self.profiles[i] = prof
                if self.active_profile == old_name:
                    self.active_profile = prof["name"]
                return ""
        self.profiles.append(prof)
        return ""

    def set_profile_flag(self, key: str, value: bool) -> bool:
        """Toggle an extra (save_description / save_transcript) on the active profile."""
        if key not in ("save_description", "save_transcript", "online_player", "split_chapters", "save_lyrics", "keep_whole"):
            return False
        self.get_profile()[key] = bool(value)
        return True

    def delete_profile(self, name: str) -> str:
        if len(self.profiles) <= 1:
            return "At least one profile is required."
        self.profiles = [p for p in self.profiles if p["name"] != name]
        if self.active_profile == name:
            self.active_profile = self.profiles[0]["name"]
        return ""

    def duplicate_profile(self, name: str) -> str:
        """Returns the name of the copy ('' if the source does not exist)."""
        src = next((p for p in self.profiles if p["name"] == name), None)
        if src is None:
            return ""
        base, n = f"{name} copy"[:MAX_PROFILE_NAME], 2
        new = base
        while new.lower() in {x.lower() for x in self.profile_names()}:
            new = f"{base[:MAX_PROFILE_NAME - 4]} {n}"
            n += 1
        self.profiles.append(dict(src, name=new))
        return new

    # ---- download options -----------------------------------------------
    def to_options(self, profile_name: Optional[str] = None) -> DownloadOptions:
        prof = self.get_profile(profile_name)
        return DownloadOptions(
            mode=prof["mode"], max_height=prof["max_height"], audio_format=prof["audio_format"],
            audio_bitrate=prof["audio_bitrate"],
            embed_metadata=prof["embed_metadata"], subtitles=prof["subtitles"],
            playlist=prof["playlist"], save_description=prof["save_description"],
            save_transcript=prof["save_transcript"], online_player=prof["online_player"],
            split_chapters=prof["split_chapters"], save_lyrics=prof["save_lyrics"],
            keep_whole=prof["keep_whole"],
            rate_limit_kbps=self.rate_limit_kbps, proxy=self.proxy,
            profile=prof["name"], custom=dict(self.custom_options),
            cookies_browser=self.cookies_browser, gentle=self.gentle_mode,
            html_create=self.html_create, single_playback=self.single_playback).normalized()

    # ---- persistence ----------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> "Settings":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls().validate()
        if not isinstance(raw, dict):
            return cls().validate()
        known = {f.name for f in fields(cls)}
        data = {k: v for k, v in raw.items() if k in known}
        if "profiles" not in raw and any(k in raw for k in ("mode", "max_height", "audio_format")):
            # settings written by Yeal < 0.3: keep the old defaults as a profile
            legacy = normalize_profile({
                "name": "My previous settings", "mode": raw.get("mode"),
                "max_height": raw.get("max_height", 1080), "audio_format": raw.get("audio_format"),
                "embed_metadata": raw.get("embed_metadata", True),
                "subtitles": raw.get("subtitles", False), "playlist": raw.get("playlist", False)})
            data["profiles"] = [legacy] + default_profiles()
            data["active_profile"] = legacy["name"]
        if int(raw.get("profiles_version", 1) or 1) < 2 and "profiles" in data:
            # settings from Yeal < 0.3.2: add the new default 4K profile once
            profs = data["profiles"] if isinstance(data["profiles"], list) else []
            if not any(isinstance(p, dict) and str(p.get("name", "")).lower() == "video 4k" for p in profs):
                data["profiles"] = [default_profiles()[0]] + profs
        data["profiles_version"] = 2
        try:
            st = cls(**data).validate()
        except (TypeError, ValueError, AttributeError):
            st = cls().validate()
        # Standing rule: Yeal always starts in the default view (workflow in the sidebar + YouTube browser).
        # The header button / Settings switch only hides the browser for the running session.
        st.show_browser = True
        return st

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        os.replace(tmp, path)
