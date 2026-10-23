"""yt-dlp wrapper: runs one job, reports progress, supports cancellation."""
from __future__ import annotations

import glob
import re
import threading
from pathlib import Path
from typing import Callable, Optional

from . import album, extras, lyrics, mp3tags
from .models import DownloadJob, JobState
from .presets import build_ydl_opts

from . import updater


class Cancelled(Exception):
    """Raised from progress hooks to stop a download."""


_cancel_exc = None


def _cancel_exception():
    """Cancelled that is also a yt-dlp DownloadCancelled, so yt-dlp passes it through untouched.
    Built lazily: yt_dlp must not be imported before updater.activate() ran."""
    global _cancel_exc
    if _cancel_exc is None:
        try:
            from yt_dlp.utils import DownloadCancelled
            _cancel_exc = type("YtdlpCancelled", (Cancelled, DownloadCancelled), {})
        except Exception:  # yt-dlp missing (tests with a fake class)
            _cancel_exc = Cancelled
    return _cancel_exc


def apply_fallback(exc: BaseException, opts: dict, done: set) -> str:
    """An optional part failed (subtitles, cover image, the chosen quality): switch it off in `opts`
    and return a short note so the download can continue with what is available. '' = no fallback."""
    text = str(exc).lower()
    pps = opts.get("postprocessors") or []

    def drop(*keys):
        opts["postprocessors"] = [p for p in pps if p.get("key") not in keys]

    if "subs" not in done and ("subtitle" in text or "caption" in text):
        opts.update(writesubtitles=False, writeautomaticsub=False)
        opts.pop("subtitleslangs", None)
        drop("FFmpegEmbedSubtitle")
        done.add("subs")
        return "Subtitles were not available - downloaded without them."
    if "cover" not in done and ("thumbnail" in text or "cover" in text or "embedthumbnail" in text):
        opts["writethumbnail"] = False
        drop("EmbedThumbnail", "FFmpegThumbnailsConvertor")
        done.add("cover")
        return "The cover image was not available - downloaded without it."
    if "quality" not in done and ("requested format is not available" in text or "format is not available" in text):
        opts["format"] = "bestaudio/best" if "audio" in str(opts.get("format", "")) else "bv*+ba/b"
        done.add("quality")
        return "The chosen quality was not available - the best available one was used."
    return ""


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def fmt_speed(bps: Optional[float]) -> str:
    if not bps:
        return ""
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if bps < 1024 or unit == "GB/s":
            return f"{bps:.1f} {unit}" if unit != "B/s" else f"{bps:.0f} {unit}"
        bps /= 1024
    return ""


def fmt_eta(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_size(num: Optional[float]) -> str:
    if not num:
        return ""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024
    return ""


def fmt_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return ""
    return fmt_eta(seconds)


def final_path(info: Optional[dict]) -> str:
    """Path of the finished file (after merging/conversion) from a yt-dlp info dict."""
    if not isinstance(info, dict):
        return ""
    for item in info.get("requested_downloads") or []:
        if item.get("filepath"):
            return str(item["filepath"])
    if info.get("filepath"):
        return str(info["filepath"])
    for entry in info.get("entries") or []:
        path = final_path(entry)
        if path:
            return path
    return ""


def clean_error(exc: BaseException) -> str:
    text = _ANSI.sub("", str(exc)).strip()
    text = re.sub(r"^(ERROR:\s*)+", "", text)
    line = text.splitlines()[0][:300] if text else exc.__class__.__name__
    low = line.lower()
    if "not a bot" in low or "429" in low or "too many requests" in low:
        line += "  - YouTube asks for a pause: wait a few minutes, keep 'Gentle mode' on, update yt-dlp, or sign in (Settings)."
    elif "[youtube" in low:  # YouTube breaks often; a fresh yt-dlp is the usual cure
        line += "  (Settings -> Update yt-dlp)"
    return line


# (keywords in the lower-cased error text, why it stopped, what the user can do) - first match wins
_REASONS = [
    (("not a bot", "429", "too many requests", "rate-limit", "rate limit"),
     "YouTube asks for a pause (too many requests / bot check, HTTP 429).",
     "Wait a few minutes (the queue pauses itself), keep Gentle mode on, or use your browser login (Settings)."),
    (("private video", "this video is private"),
     "The video is private.", "Only the owner can open it. Sign in with an account that has access."),
    (("sign in to confirm your age", "age-restricted", "age restricted", "confirm your age"),
     "The video is age-restricted.", "Use your browser login for downloads (Settings > Use browser login)."),
    (("members-only", "members only", "join this channel", "premium"),
     "The video is for channel members or Premium.", "Use the browser login of an account with access (Settings)."),
    (("not available in your country", "geo", "blocked it in your country", "uploader has not made this video available"),
     "The video is not available in your country.", "A VPN or proxy in another country may help (Settings > Proxy)."),
    (("video unavailable", "has been removed", "no longer available", "account associated with this video has been terminated",
      "copyright"),
     "The video is unavailable or was removed.", "Check the link in the browser view."),
    (("live event will begin", "premieres in", "this live event"),
     "The live stream or premiere has not started yet.", "Try again when it is running or finished."),
    (("unsupported url", "is not a valid url", "no video formats found"),
     "Yeal could not find a video at this link.", "Open the page in the browser view and use the address of the video itself."),
    (("timed out", "connection reset", "connection refused", "getaddrinfo", "name or service not known",
      "temporary failure in name resolution", "network is unreachable", "ssl", "urlopen error", "remote end closed"),
     "The connection to the server failed.", "Check your internet connection (or proxy) and press Retry."),
    (("ffmpeg", "ffprobe"),
     "ffmpeg is missing or failed (needed to merge or convert).", "Check Settings > Download engine, then press Retry."),
    (("no space left", "disk full"),
     "The disk is full.", "Free some space or choose another download folder (Settings)."),
    (("permission denied", "access is denied", "file name too long", "invalid argument"),
     "The file could not be written.", "Choose another download folder (Settings) or shorten the title."),
    (("[youtube", "signature", "nsig", "player response", "po token"),
     "YouTube changed something the downloader relies on.", "Settings > Update yt-dlp, then press Retry."),
]


def friendly_error(exc: BaseException) -> str:
    """Why a download stopped and what to do, in plain words. The technical line is in `clean_error`."""
    text = _ANSI.sub("", str(exc)).lower()
    for keys, why, tip in _REASONS:
        if any(k in text for k in keys):
            return f"Stopped automatically: {why}\n{tip}"
    return "Stopped automatically: " + clean_error(exc)


PHASES = {
    "FFmpegExtractAudio": "Converting audio",
    "FFmpegMerger": "Merging video and audio",
    "FFmpegVideoConvertor": "Converting video",
    "FFmpegThumbnailsConvertor": "Preparing cover",
    "EmbedThumbnail": "Embedding cover",
    "FFmpegMetadata": "Writing tags",
    "FFmpegEmbedSubtitle": "Embedding subtitles",
    "FFmpegFixupM4a": "Fixing container",
    "FFmpegFixupM3u8": "Fixing container",
    "FFmpegSplitChapters": "Splitting into tracks",
    "MoveFiles": "Saving file",
}


HEAVY = ("FFmpegExtractAudio", "FFmpegMerger", "FFmpegVideoConvertor", "FFmpegSplitChapters")


def pp_weight(name: str) -> int:
    """Share of one post-processing step in the creation bar (conversion/merging dominates)."""
    return 8 if name in HEAVY else 1


def expected_audio_bytes(duration_s: float, fmt: str, bitrate: int) -> float:
    """Rough size of the converted audio file; used to turn file growth into a percentage."""
    per_s = 90000 if fmt == "flac" else max(bitrate, 64) * 125
    return max(duration_s, 1.0) * per_s


def default_ydl_class():
    from yt_dlp import YoutubeDL
    return YoutubeDL


class Engine:
    """`ydl_class` is injectable so the engine can be tested without network."""

    def __init__(self, ctx, ydl_class=None):
        self.ctx = ctx
        self._ydl_class = ydl_class

    def _lyrics_for(self, job: DownloadJob, item: dict, path: str, notify: Callable[[DownloadJob], None]) -> Optional[dict]:
        """Find the song text (LRCLIB, else the captions), save .txt/.lrc/.srt and tag the audio file."""
        job.phase = "Looking up lyrics"
        notify(job)
        artist, title = lyrics.guess_track(item)
        found = lyrics.fetch(artist, title, float(item.get("duration") or 0))
        if found:
            found["source"] = "lrclib"
        else:
            sub = extras.pick_subtitle(item, job.options.sub_langs)
            text = extras.subtitle_to_text(Path(sub).read_text(encoding="utf-8", errors="replace")) if sub else ""
            if text:
                found = {"plain": text, "synced": "", "artist": artist, "title": title, "source": "captions"}
        if not found:
            return None
        lyrics.write_lyrics(path, found)
        if job.options.mode == "audio":
            lyrics.embed(self.ctx.ffmpeg, path, found["plain"])
        elif found.get("synced"):
            lyrics.write_srt(path, found, float(item.get("duration") or 0))   # video players show it as subtitles
        job.saved_lyrics = "lyrics" if found["source"] == "lrclib" else "captions"
        return found

    def _tag_mp3(self, job: DownloadJob, info: Optional[dict]) -> None:
        """Audio jobs: fill the MP3 tags from the description (genre, mood, keywords ...). When exactly one
        file was tagged the job asks the UI whether the user wants to edit them."""
        if job.options.mode != "audio" or not job.options.embed_metadata:
            return
        tagged = []
        for item in (info or {}).get("entries") or [info or {}]:
            path = final_path(item) if isinstance(item, dict) else ""
            if path.lower().endswith(".mp3") and mp3tags.auto_fill(path, item):
                tagged.append(path)
        job.tags_ask = len(tagged) == 1

    def _playlist_page(self, job: DownloadJob, info: dict) -> None:
        """Write the playlist HTML page into the playlist folder; the job then points at that folder."""
        items, folder = [], None
        for n, entry in enumerate([e for e in info.get("entries") or [] if isinstance(e, dict)], 1):
            path = final_path(entry)
            exists = bool(path) and Path(path).is_file()
            if exists and folder is None:
                folder = Path(path).parent
            page = Path(path).with_suffix("").name + ".html" if exists else ""
            if page and not (Path(path).parent / page).is_file():
                page = ""
            items.append({"index": int(entry.get("playlist_index") or n), "title": entry.get("title") or "",
                          "duration": fmt_duration(entry.get("duration")),
                          "file": Path(path).name if exists else "", "page": page})
        if folder is None:
            return
        written = extras.write_playlist_page(folder, str(info.get("title") or folder.name),
                                             str(info.get("uploader") or info.get("channel") or ""),
                                             str(info.get("webpage_url") or job.url), items,
                                             job.options.mode, job.options.html_theme)
        if written:
            job.filename = str(folder)

    def run(self, job: DownloadJob, cancel: threading.Event,
            notify: Callable[[DownloadJob], None]) -> None:
        self.ctx.ensure_dirs()
        updater.activate(self.ctx.data_dir)
        ydl_class = self._ydl_class or default_ydl_class()
        cancelled = _cancel_exception()
        job.state = JobState.FETCHING
        job.phase = "Preparing"
        job.progress = 0.01
        notify(job)

        opts = build_ydl_opts(job.options, self.ctx)

        duration_s = [0.0]
        dl_done = [False]    # post-processing steps that run before the download do not count
        planned = [pp_weight(str(pp.get("key"))) for pp in opts.get("postprocessors") or []]
        if job.options.mode == "video" and self.ctx.can_merge:
            planned.append(pp_weight("FFmpegMerger"))
        pp_total = max(1, sum(planned) + 1)       # +1: final move
        pp_weights_done = [0]
        stop_watch = [None]
        streams_done = [0]   # finished streams of the current item (video + audio = 2)

        # Progress of one item over all phases: preparing 0-3 %, download 3-85 %, post-processing 85-100 %.
        def overall(frac: float) -> float:
            if job.playlist_count > 1:
                return min(((job.playlist_index - 1) + frac) / job.playlist_count, 0.999)
            return min(frac, 0.999)

        def on_progress(d: dict) -> None:
            if cancel.is_set():
                raise cancelled()
            info = d.get("info_dict") or {}
            if info.get("title"):
                job.title = info["title"]
            thumb = info.get("thumbnail")
            if isinstance(thumb, str) and thumb.startswith("https://"):
                job.thumbnail = thumb
            job.uploader = info.get("uploader") or info.get("channel") or job.uploader
            job.duration = fmt_duration(info.get("duration")) or job.duration
            duration_s[0] = float(info.get("duration") or duration_s[0] or 0)
            job.has_description = job.has_description or extras.has_description(info)
            job.has_transcript = job.has_transcript or extras.has_transcript(info)
            job.playlist_index = int(info.get("playlist_autonumber") or info.get("playlist_index") or job.playlist_index or 0)
            job.playlist_count = int(info.get("n_entries") or job.playlist_count or 0)
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                done = d.get("downloaded_bytes") or 0
                job.state = JobState.DOWNLOADING
                n_streams = max(1, len(info.get("requested_formats") or []))
                part = (streams_done[0] + (done / total if total else 0.0)) / n_streams
                dl_done[0] = False
                job.phase = "Downloading"
                job.dl_progress = min(part, 1.0)
                job.progress = overall(0.03 + 0.82 * min(part, 1.0))
                job.speed = fmt_speed(d.get("speed"))
                job.speed_bps = float(d.get("speed") or 0.0)
                job.eta = fmt_eta(d.get("eta"))
                job.size = fmt_size(total) or job.size
            elif status == "finished":
                job.filename = d.get("filename") or job.filename
                n_streams = max(1, len(info.get("requested_formats") or []))
                streams_done[0] += 1
                if streams_done[0] < n_streams:     # next stream of the same item follows
                    job.state = JobState.DOWNLOADING
                    job.dl_progress = streams_done[0] / n_streams
                    job.progress = overall(0.03 + 0.82 * streams_done[0] / n_streams)
                else:
                    streams_done[0] = 0
                    dl_done[0] = True
                    pp_weights_done[0] = 0
                    job.dl_progress = 1.0
                    job.pp_progress = 0.0
                    job.state = JobState.PROCESSING
                    job.phase = "Processing"
                    job.progress = overall(0.85)
                job.speed = job.eta = ""
                job.speed_bps = 0.0
                job.size = fmt_size(d.get("total_bytes") or d.get("downloaded_bytes")) or job.size
            notify(job)

        def set_pp(frac: float) -> None:
            job.pp_progress = min(max(frac, 0.0), 0.99)
            job.progress = overall(0.85 + 0.15 * job.pp_progress)

        def start_watch(source: Path, base_weight: int, weight: int) -> None:
            """ffmpeg reports no progress: follow the growing `<name>.temp.<ext>` file instead."""
            stop = threading.Event()
            stop_watch[0] = stop
            expected = expected_audio_bytes(duration_s[0], job.options.audio_format, job.options.audio_bitrate)
            pattern = glob.escape(source.stem) + ".temp.*"

            def run() -> None:
                while not stop.wait(0.4):
                    try:
                        sizes = [p.stat().st_size for p in source.parent.glob(pattern)]
                    except OSError:
                        continue
                    if sizes:
                        set_pp((base_weight + weight * min(max(sizes) / expected, 0.98)) / pp_total)
                        notify(job)
            threading.Thread(target=run, daemon=True).start()

        def on_postprocess(d: dict) -> None:
            if cancel.is_set():
                raise cancelled()
            info = d.get("info_dict") or {}
            if d.get("status") == "finished" and info.get("filepath"):
                job.filename = info["filepath"]
            name = d.get("postprocessor") or ""
            if not dl_done[0]:
                return
            job.state = JobState.PROCESSING
            if d.get("status") == "started":
                job.phase = PHASES.get(name, "Processing")
                if name == "FFmpegExtractAudio" and duration_s[0] and job.filename:
                    start_watch(Path(job.filename), pp_weights_done[0], pp_weight(name))
            elif d.get("status") == "finished":
                if stop_watch[0] is not None:
                    stop_watch[0].set()
                pp_weights_done[0] = min(pp_weights_done[0] + pp_weight(name), pp_total - 1)
            set_pp(pp_weights_done[0] / pp_total)
            notify(job)

        opts["progress_hooks"] = [on_progress]
        opts["postprocessor_hooks"] = [on_postprocess]
        try:
            fallbacks: set = set()
            while True:
                try:
                    with ydl_class(opts) as ydl:
                        info = ydl.extract_info(job.url, download=True)
                    break
                except Cancelled:
                    raise
                except Exception as exc:  # noqa: BLE001
                    note = "" if cancel.is_set() else apply_fallback(exc, opts, fallbacks)
                    if not note:
                        raise
                    job.note = (job.note + "\n" if job.note else "") + note   # continue with what is available
                    job.phase = "Retrying without the missing part"
                    notify(job)
            if info and not job.title:
                job.title = info.get("title") or ""
            job.filename = final_path(info) or job.filename
            if (job.options.save_description or job.options.save_transcript
                    or job.options.online_player or job.options.save_lyrics):
                for item in (info or {}).get("entries") or [info or {}]:
                    path = final_path(item)
                    if not path:
                        continue
                    found = self._lyrics_for(job, item, path, notify) if job.options.save_lyrics else None
                    desc, trans = extras.write_extras(
                        item, path, job.options.save_description, job.options.save_transcript,
                        job.options.sub_langs, job.options.subtitles, job.options.mode,
                        job.options.online_player, job.options.html_theme, found)
                    job.saved_description = job.saved_description or desc
                    job.saved_transcript = job.saved_transcript or trans
            self._tag_mp3(job, info)     # after the lyrics step, which rewrites the tags with ffmpeg
            if job.options.playlist_dir and info and info.get("entries"):
                self._playlist_page(job, info)
            if job.options.split_chapters and info and not info.get("entries"):
                job.phase = "Creating album"
                notify(job)
                folder = album.find_album_dir(Path(job.filename).parent, str(info.get("id") or "")) \
                    if job.filename else None
                if folder:
                    album.finish(self.ctx.ffmpeg, folder, info.get("title") or folder.name,
                                 info.get("artist") or info.get("uploader") or info.get("channel") or "",
                                 info.get("chapters") or [])
                    if not job.options.keep_whole and job.filename and Path(job.filename).is_file():
                        try:   # tracks only: remove the full file, the job now points at the album folder
                            Path(job.filename).unlink()
                            job.filename = str(folder)
                        except OSError:
                            pass
            if cancel.is_set():
                raise cancelled()
            job.state = JobState.DONE
            job.phase = ""
            job.dl_progress = job.pp_progress = 1.0
            job.progress = 1.0
            job.speed = job.eta = ""
            job.speed_bps = 0.0
        except Cancelled:
            job.state = JobState.CANCELED
            job.speed = job.eta = ""
            job.speed_bps = 0.0
        except Exception as exc:  # noqa: BLE001 - surface any yt-dlp failure to the UI
            if cancel.is_set():
                job.state = JobState.CANCELED
            else:
                job.state = JobState.ERROR
                job.error = friendly_error(exc)
                job.error_detail = clean_error(exc)
        finally:
            if stop_watch[0] is not None:
                stop_watch[0].set()
        notify(job)
