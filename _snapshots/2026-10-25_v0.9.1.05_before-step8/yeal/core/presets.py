"""Translate Yeal options + platform capabilities into yt-dlp option dicts."""
from __future__ import annotations

from typing import Dict, Tuple

from .models import DownloadOptions

# Options a user-supplied "custom options" JSON must never set: they run external
# programs, replace the post-processing chain or move output outside the download dir.
FORBIDDEN_KEYS = frozenset({
    "exec_cmd", "postprocessors", "external_downloader", "external_downloader_args",
    "postprocessor_args", "paths", "ffmpeg_location", "progress_hooks",
    "postprocessor_hooks", "load_info_filename", "cachedir", "plugin_dirs",
    "color", "usenetrc", "netrc_cmd", "cookiesfrombrowser",
})

_PROXY_SCHEMES = ("http", "https", "socks4", "socks4a", "socks5", "socks5h")


def normalize_proxy(value: str) -> str:
    """Return a clean proxy URL, or '' if empty. Raises ValueError for anything else."""
    from urllib.parse import urlsplit
    value = (value or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    if parts.scheme.lower() not in _PROXY_SCHEMES or not parts.hostname:
        raise ValueError("Use http://host:port, https://host:port or socks5://host:port")
    return value


def is_playlist_url(url: str) -> bool:
    """True for links that point at a playlist itself (not a single video inside one)."""
    from urllib.parse import parse_qs, urlsplit
    parts = urlsplit(url or "")
    query = parse_qs(parts.query)
    host = (parts.hostname or "").lower()
    if "youtube" in host or host == "youtu.be":
        if parts.path.rstrip("/") == "/playlist" and "list" in query:
            return True
        return False
    return any(seg in parts.path.lower() for seg in ("/playlist/", "/sets/", "/album/"))


def media_dir(base, mode: str):
    """Video and audio land in their own sub-folders of the download folder."""
    from pathlib import Path
    return Path(base) / ("Audio" if mode == "audio" else "Video")


DEFAULT_OUTTMPL = "%(title).150B [%(id)s].%(ext)s"
# Playlists: <download folder>/Playlists/<playlist name>/<n> - <title> [id].<ext>
PLAYLIST_OUTTMPL = "Playlists/%(playlist_title|Playlist).100B/%(playlist_index|0)03d - %(title).150B [%(id)s].%(ext)s"


def compress_items(indices) -> str:
    """[1,2,3,5,7,8] -> "1-3,5,7-8" (yt-dlp playlist_items spec)."""
    nums = sorted({int(i) for i in indices if int(i) > 0})
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return ",".join(out)


def sanitize_custom_options(raw: dict) -> Tuple[dict, list]:
    """Return (clean options, rejected keys)."""
    clean: Dict[str, object] = {}
    rejected = []
    for key, value in (raw or {}).items():
        if key in FORBIDDEN_KEYS or not isinstance(key, str):
            rejected.append(str(key))
            continue
        if key == "outtmpl":
            text = str(value)
            if ".." in text or text.startswith(("/", "\\")) or ":" in text.split("%(")[0]:
                rejected.append(key)
                continue
        clean[key] = value
    return clean, rejected


# audio targets whose container supports an embedded cover (yt-dlp EmbedThumbnail)
_THUMB_AUDIO = {"mp3", "m4a", "opus", "flac", "ogg", "vorbis"}


def _backoff(n: int) -> float:
    """Wait 2, 4, 8, ... seconds (max 60) between retries."""
    return float(min(2 ** (n + 1), 60))


def build_ydl_opts(options: DownloadOptions, ctx) -> dict:
    """Build the yt-dlp options. `ctx` is a platforms.PlatformInfo."""
    opt = options.normalized()
    can_merge = ctx.can_merge
    out: dict = {
        "outtmpl": DEFAULT_OUTTMPL,
        "paths": {"home": str(media_dir(ctx.download_dir, opt.mode)), "temp": str(ctx.temp_dir)},
        "noplaylist": not opt.playlist,
        # one unavailable video must not abort a whole playlist
        "ignoreerrors": "only_download" if opt.playlist else False,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "windowsfilenames": bool(ctx.is_windows),
        "retries": 5,
        "fragment_retries": 5,
        "continuedl": True,
    }
    if opt.gentle:
        # behave like a patient viewer, not a bulk tool: pause between requests, back off on errors
        out["sleep_interval_requests"] = 1
        out["retry_sleep_functions"] = {"http": _backoff, "fragment": _backoff,
                                         "extractor": _backoff, "file_access": _backoff}
        if opt.playlist:
            out["sleep_interval"] = 3
            out["max_sleep_interval"] = 8
    if opt.cookies_browser:
        out["cookiesfrombrowser"] = (opt.cookies_browser,)
    if ctx.ffmpeg:
        out["ffmpeg_location"] = str(ctx.ffmpeg)
    if opt.rate_limit_kbps:
        out["ratelimit"] = opt.rate_limit_kbps * 1024
    try:
        proxy = normalize_proxy(opt.proxy)
    except ValueError:
        proxy = ""
    if proxy:
        out["proxy"] = proxy
    if getattr(ctx, "js_runtime", None):
        out["js_runtimes"] = {"node": {"path": str(ctx.js_runtime)}}

    if opt.live_minutes > 0 and can_merge:     # live stream: stop after N minutes (ffmpeg cuts the recording)
        try:
            from yt_dlp.utils import download_range_func
            out["download_ranges"] = download_range_func(None, [(0, opt.live_minutes * 60)])
        except ImportError:
            pass

    if opt.playlist and opt.playlist_dir:
        out["outtmpl"] = PLAYLIST_OUTTMPL
        out["paths"]["home"] = str(ctx.download_dir)      # Playlists/ sits directly in the download folder
        if opt.playlist_items:
            out["playlist_items"] = opt.playlist_items

    pps = []
    if opt.mode == "audio":
        if can_merge:
            out["format"] = "bestaudio/best"
            # highest bitrate first (yt-dlp would otherwise weigh codec/container preferences before it)
            out["format_sort"] = ["abr", "asr", "acodec"]
            if opt.audio_format != "best":
                pp = {"key": "FFmpegExtractAudio", "preferredcodec": opt.audio_format}
                if opt.audio_format == "mp3":     # always try the maximum: 320 kbps
                    pp["preferredquality"] = "320"
                elif opt.audio_format != "flac":   # flac is lossless: no bitrate
                    pp["preferredquality"] = str(opt.audio_bitrate)
                pps.append(pp)
        else:  # no ffmpeg (e.g. Android v0.1): keep the native container
            out["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    else:
        sel = f"[height<={opt.max_height}]" if opt.max_height else ""
        if can_merge:
            out["format"] = f"bv*{sel}+ba/b{sel}/b"
            out["merge_output_format"] = "mp4"
        else:  # progressive single-file streams only
            out["format"] = f"b{sel}[ext=mp4]/b{sel}/b"

    if opt.subtitles or opt.save_transcript or opt.save_lyrics:
        out["writesubtitles"] = True
        out["writeautomaticsub"] = True
        out["subtitleslangs"] = list(opt.sub_langs) or ["en"]
        if opt.save_transcript:
            out["subtitlesformat"] = "vtt/best"
    if opt.subtitles:
        if can_merge and opt.mode == "video":
            pps.append({"key": "FFmpegEmbedSubtitle"})

    if opt.embed_metadata and can_merge:
        out["writethumbnail"] = True
        pps.insert(0, {"key": "FFmpegThumbnailsConvertor", "format": "jpg",
                       "when": "before_dl"})
        pps.append({"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True})  # track markers
        # EmbedThumbnail aborts the whole job for containers it cannot handle
        # (webm/opus "original" audio, wav, ...), so only add it when safe.
        if opt.mode == "video" or opt.audio_format in _THUMB_AUDIO:
            pps.append({"key": "EmbedThumbnail"})

    if opt.split_chapters and can_merge:
        # one file per chapter/track (needs chapters, e.g. a tracklist in the description)
        out["outtmpl"] = {"default": out["outtmpl"],
                          "chapter": "%(title).100B [%(id)s]/%(section_number)02d - %(section_title).100B.%(ext)s"}
        pps.append({"key": "FFmpegSplitChapters", "force_keyframes": False})

    if pps:
        out["postprocessors"] = pps

    clean, _ = sanitize_custom_options(opt.custom)
    out.update(clean)
    return out
