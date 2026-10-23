"""Plain data models shared by the engine, the queue and the UI (no Qt imports)."""
from __future__ import annotations

import time
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class JobState(str, Enum):
    QUEUED = "queued"
    FETCHING = "fetching"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"
    CANCELED = "canceled"

    @property
    def finished(self) -> bool:
        return self in (JobState.DONE, JobState.ERROR, JobState.CANCELED)

    @property
    def kind(self) -> str:
        """Coarse group used for filtering: queued | active | done | failed."""
        if self is JobState.QUEUED:
            return "queued"
        if self is JobState.DONE:
            return "done"
        if self in (JobState.ERROR, JobState.CANCELED):
            return "failed"
        return "active"


MODES = ("video", "audio")
COOKIE_BROWSERS = ("firefox", "edge", "chrome")
AUDIO_FORMATS = ("mp3", "m4a", "opus", "flac", "best")
QUALITIES = (0, 2160, 1440, 1080, 720, 480, 360)  # 0 = best available


@dataclass
class DownloadOptions:
    mode: str = "video"            # "video" | "audio"
    max_height: int = 1080         # 0 = best available
    audio_format: str = "mp3"      # one of AUDIO_FORMATS
    audio_bitrate: int = 320       # kbps target for lossy conversion (mp3 is always 320)
    embed_metadata: bool = True    # needs ffmpeg
    subtitles: bool = False
    sub_langs: List[str] = field(default_factory=lambda: ["de", "en"])
    playlist: bool = False
    save_description: bool = False  # description.html next to the file
    save_transcript: bool = False   # transcript.txt from subtitles
    online_player: bool = False     # the html page also embeds the online player (YouTube/Vimeo)
    split_chapters: bool = False    # also save every track in an album folder + playlist
    html_theme: str = "auto"        # "light" | "dark" = app theme when the job was created; "auto" = follow the browser
    rate_limit_kbps: int = 0       # 0 = unlimited
    proxy: str = ""                # http(s)/socks URL or ""
    profile: str = ""              # profile name, display only
    custom: dict = field(default_factory=dict)  # extra yt-dlp options (sanitized later)
    cookies_browser: str = ""      # "" | firefox | edge | chrome: read the login cookies of that browser
    gentle: bool = True            # polite request pattern: pauses, back-off (recommended)
    save_lyrics: bool = False      # song lyrics (.txt/.lrc) from LRCLIB, else the captions
    keep_whole: bool = True        # with split_chapters: also keep the full file (False = tracks only)
    live_minutes: int = 0          # live stream: record this many minutes (0 = until the stream ends)
    playlist_dir: bool = False     # playlist link: save in <download>/Playlists/<playlist name>/ + playlist page
    playlist_items: str = ""       # yt-dlp item spec of the chosen entries, e.g. "1,3,5-7" ("" = all)

    def normalized(self) -> "DownloadOptions":
        mode = self.mode if self.mode in MODES else "video"
        fmt = self.audio_format if self.audio_format in AUDIO_FORMATS else "mp3"
        try:
            height = int(self.max_height)
        except (TypeError, ValueError):
            height = 1080
        if height not in QUALITIES:
            height = 1080
        try:
            rate = max(0, int(self.rate_limit_kbps))
        except (TypeError, ValueError):
            rate = 0
        try:
            bitrate = int(self.audio_bitrate)
        except (TypeError, ValueError):
            bitrate = 320
        if bitrate not in (128, 192, 256, 320):
            bitrate = 320
        try:
            live = max(0, min(int(self.live_minutes), 24 * 60))
        except (TypeError, ValueError):
            live = 0
        items = ",".join(p for p in re.split(r"[,\s]+", str(self.playlist_items or "")) if re.fullmatch(r"\d+(-\d+)?", p))
        return DownloadOptions(mode, height, fmt, bitrate, bool(self.embed_metadata),
                               bool(self.subtitles), list(self.sub_langs or []),
                               bool(self.playlist), bool(self.save_description),
                               bool(self.save_transcript), bool(self.online_player), bool(self.split_chapters),
                               self.html_theme if self.html_theme in ("light", "dark") else "auto", rate, str(self.proxy or ""),
                               str(self.profile or ""), dict(self.custom or {}),
                               self.cookies_browser if self.cookies_browser in COOKIE_BROWSERS else "",
                               bool(self.gentle), bool(self.save_lyrics), bool(self.keep_whole),
                               live, bool(self.playlist_dir), items)


@dataclass
class DownloadJob:
    id: int
    url: str
    options: DownloadOptions
    state: JobState = JobState.QUEUED
    title: str = ""
    progress: float = 0.0          # 0..1, overall (playlist aware), covers all phases
    phase: str = ""                # human readable current step, e.g. "Converting audio"
    dl_progress: float = 0.0       # 0..1 download part only
    pp_progress: float = 0.0       # 0..1 creation part only (convert, merge, tags, cover)
    speed: str = ""
    eta: str = ""
    filename: str = ""
    error: str = ""              # plain-language reason + what to do
    error_detail: str = ""       # the technical line from yt-dlp
    playlist_index: int = 0
    playlist_count: int = 0
    thumbnail: str = ""            # https URL reported by yt-dlp
    uploader: str = ""
    duration: str = ""             # "3:45"
    size: str = ""                 # "123.4 MB"
    speed_bps: float = 0.0
    has_description: bool = False  # reported by yt-dlp
    has_transcript: bool = False
    saved_description: bool = False
    saved_transcript: bool = False
    note: str = ""                  # things that were skipped (subtitles, cover, quality), shown as a hint
    saved_lyrics: str = ""          # "" | "lyrics" | "captions" (what the text came from)
    tags_ask: bool = False          # one MP3 was just tagged automatically: the UI may ask whether to edit the tags
    created: float = field(default_factory=time.time)

    def reset(self) -> None:
        self.state = JobState.QUEUED
        self.progress = 0.0
        self.phase = ""
        self.dl_progress = self.pp_progress = 0.0
        self.speed = self.eta = self.error = self.error_detail = ""
        self.speed_bps = 0.0
        self.saved_description = self.saved_transcript = False
        self.saved_lyrics = ""
        self.tags_ask = False
        self.note = ""
        self.playlist_index = self.playlist_count = 0
