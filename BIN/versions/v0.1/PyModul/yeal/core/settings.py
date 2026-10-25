"""Persistent user settings and download profiles (JSON, atomic writes, tolerant loading)."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import List, Optional

from .models import AUDIO_FORMATS, COOKIE_BROWSERS, MODES, QUALITIES, DownloadOptions
from .tidal import TIDAL_QUALITIES

THEMES = ("system", "light", "dark")
HTML_OPEN_MODES = ("file", "server")
HTML_CREATE_MODES = ("server", "file", "both")
DL_BUTTON_STYLES = ("icon", "label", "off")   # header Download button: icon only / icon + text / hidden
DL_BUTTON_POSITIONS = ("left", "right")      # header Download button: next to the title or at the end of the bar
MAX_PROFILE_NAME = 40
MAX_STREAM_HOSTS = 10


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


@dataclass
class Settings:
    theme: str = "system"
    max_parallel: int = 2
    gentle_mode: bool = True          # pauses between requests/downloads, back-off on errors
    cookies_browser: str = ""         # reuse the YouTube login of firefox/edge/chrome for downloads
    ffmpeg_path: str = ""             # optional user-selected helper; empty = automatic lookup
    node_path: str = ""               # optional user-selected helper; empty = automatic lookup
    tidal_path: str = ""              # optional user-selected tiddl executable (Tidal helper); empty = automatic lookup
    tidal_quality: str = "high"       # Tidal: low | normal | high | max (needs a Tidal subscription)
    tidal_threads: int = 2            # Tidal: parallel track downloads (kept low on purpose)
    panel_width: int = 400            # width of the tools panel next to the YouTube view
    panel_right: bool = False         # tools panel on the right instead of the left
    adblock_experimental: bool = False  # Windows browser view: block ad/tracker domains (experimental, needs restart)
    show_browser: bool = True         # Windows: embedded YouTube browser on the Downloads page
    auto_update: bool = True          # keep yt-dlp current (checked every few days)
    ask_mp3_tags: bool = True         # after an MP3 download: ask "edit the MP3 tags?" (the answer defaults to No)
    html_open_mode: str = "server"    # saved HTML pages: local Python HTTP server (online player) or file:// (independent)
    html_create: str = "both"         # which description pages are written: server | file | both (linked to each other)
    dl_button_style: str = "icon"     # direct Download button in the header button bar: icon | label | off
    dl_button_pos: str = "left"       # ... and where it sits in that bar: left | right
    stream_device: dict = field(default_factory=dict)   # chosen UPnP/DLNA renderer (Renderer.to_dict()); {} = none yet
    stream_hosts: List[str] = field(default_factory=list)  # manually added renderer addresses (IP, name or description URL)
    stream_volume: int = -1           # volume (0-100) set on the renderer before playing; -1 = leave the device as it is
    stream_scan_seconds: int = 4      # how long the network search waits for answers
    stream_port: int = 0              # port of Yeal's media server for the renderer; 0 = automatic (or fixed for the firewall)
    download_dir: str = ""            # empty -> platform default
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
        if self.tidal_quality not in TIDAL_QUALITIES:
            self.tidal_quality = "high"
        try:
            self.tidal_threads = max(1, min(4, int(self.tidal_threads)))
        except (TypeError, ValueError):
            self.tidal_threads = 2
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
            html_create=self.html_create).normalized()

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
