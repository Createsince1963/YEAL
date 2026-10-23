"""Look at the audio streams a link offers, before a download starts (no Qt imports).

Used to offer a higher-quality target (AAC/M4A, original stream, FLAC) instead of the
MP3 default when the source is better than a typical 128-160 kbps stream.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

MP3_MIN_KBPS = 320                   # MP3 is only ever made at 320 kbps, otherwise no download
HIGH_ABR = 120                       # kbps; at or above this the choice dialog is shown
LOSSLESS = ("flac", "alac", "wav", "pcm", "aiff")


def best_audio(info: dict) -> dict:
    """Describe the best audio-only stream of an extract_info() result."""
    best: dict = {}
    for f in (info or {}).get("formats") or []:
        if (f.get("vcodec") or "none") != "none" or (f.get("acodec") or "none") == "none":
            continue
        abr = float(f.get("abr") or f.get("tbr") or 0)
        lossless = any(k in (f.get("acodec") or "").lower() for k in LOSSLESS)
        score = (lossless, abr)
        if not best or score > best["score"]:
            best = {"score": score, "abr": int(round(abr)), "codec": (f.get("acodec") or "").split(".")[0],
                    "ext": f.get("ext") or "", "lossless": lossless}
    if not best and info:   # single-format sites: use the top level values
        abr = float(info.get("abr") or info.get("tbr") or 0)
        codec = (info.get("acodec") or "").split(".")[0]
        lossless = any(k in codec.lower() for k in LOSSLESS)
        if abr or lossless:
            best = {"score": (lossless, abr), "abr": int(round(abr)), "codec": codec,
                    "ext": info.get("ext") or "", "lossless": lossless}
    best.pop("score", None)
    return best


def is_high_quality(best: dict) -> bool:
    return bool(best) and (best.get("lossless") or best.get("abr", 0) >= HIGH_ABR)


def choices(best: dict) -> list:
    """Offered targets, default first: MP3 (always 320 kbps), AAC, then the exact formats.

    Every entry: id, format, bitrate, title, detail. MP3 is never offered below 320 kbps:
    if it cannot be made at 320 there is no MP3 entry and no download in that format.
    """
    abr = int(best.get("abr") or 0)
    codec = (best.get("codec") or "audio").upper()
    out = [{"id": "mp3", "format": "mp3", "bitrate": MP3_MIN_KBPS,
            "title": "MP3 (%d kbps)" % MP3_MIN_KBPS,
            "detail": "Works everywhere. Always %d kbps (never lower), converted from the %s source. A lossy copy of a lossy file: it cannot sound better than the source." % (MP3_MIN_KBPS, codec)},
           {"id": "m4a", "format": "m4a", "bitrate": 320,
            "title": "AAC (M4A)",
            "detail": "Better sound than MP3 at the same size. Plays on phones, Apple devices and most players."},
           {"id": "best", "format": "best", "bitrate": 0,
            "title": "Original (%s, %s kbps)" % (codec, abr) if abr else "Original (%s)" % codec,
            "detail": "The unchanged source stream, no conversion, best possible quality."}]
    if best.get("lossless"):
        out.append({"id": "flac", "format": "flac", "bitrate": 0, "title": "FLAC (lossless)",
                    "detail": "Keeps the full quality of the %s source. Large file." % codec})
    return out


def probe_playlist(url: str, ydl_class, opts: dict) -> dict:
    """List the entries of a playlist without downloading. Returns
    {"title", "uploader", "entries": [{index, id, title, duration, url, available}]} or {} on failure."""
    o = dict(opts)
    for key in ("postprocessors", "progress_hooks", "postprocessor_hooks", "merge_output_format", "outtmpl",
                "playlist_items", "download_ranges"):
        o.pop(key, None)
    o.update({"skip_download": True, "noplaylist": False, "extract_flat": "in_playlist",
              "ignoreerrors": True, "writethumbnail": False, "writesubtitles": False, "writeautomaticsub": False})
    try:
        with ydl_class(o) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:  # noqa: BLE001 - a failed probe: the whole playlist is downloaded as before
        return {}
    if not isinstance(info, dict) or not info.get("entries"):
        return {}
    entries = []
    for n, e in enumerate([e for e in info["entries"] if isinstance(e, dict)], 1):
        title = str(e.get("title") or e.get("id") or "")
        entries.append({"index": n, "id": str(e.get("id") or ""), "title": title,
                        "duration": int(e.get("duration") or 0),
                        "url": str(e.get("url") or e.get("webpage_url") or ""),
                        "available": not title.startswith(("[Private video]", "[Deleted video]"))})
    if not entries:
        return {}
    return {"title": str(info.get("title") or "Playlist"),
            "uploader": str(info.get("uploader") or info.get("channel") or ""), "entries": entries}


def probe(url: str, ydl_class, opts: dict) -> dict:
    """Fetch metadata only. Returns {"title", "thumbnail", "best": {...}} or {} on any failure."""
    o = dict(opts)
    for key in ("postprocessors", "progress_hooks", "postprocessor_hooks", "merge_output_format"):
        o.pop(key, None)
    o.update({"skip_download": True, "noplaylist": True, "format": "bestaudio/best",
              "writethumbnail": False, "writesubtitles": False, "writeautomaticsub": False})
    try:
        with ydl_class(o) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:  # noqa: BLE001 - a failed probe just means "no choice dialog"
        return {}
    if not isinstance(info, dict):
        return {}
    if info.get("entries"):    # playlist/channel: no per-item dialog
        return {}
    thumb = info.get("thumbnail")
    return {"title": info.get("title") or url,
            "thumbnail": thumb if isinstance(thumb, str) and thumb.startswith("https://") else "",
            "chapters": len(info.get("chapters") or []),
            "live": bool(info.get("is_live")) or info.get("live_status") == "is_live",
            "best": best_audio(info)}
