"""Song lyrics lookup (no Qt imports).

Primary source: LRCLIB (https://lrclib.net) - free, no key, plain and time-synced lyrics.
Fallback (done by the caller): the video's own subtitles/captions as text.
Network answers are untrusted data: https only, size cap, only text fields are used.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Optional

API = "https://lrclib.net/api/"
MAX_BYTES = 2_000_000
DURATION_TOLERANCE = 6          # seconds between the video and the matched song
USER_AGENT = "Yeal (https://github.com/yeal-app) lyrics lookup"

_NOISE = re.compile(r"\s*[\(\[][^)\]]*(official|video|audio|lyrics?|lyric video|hd|hq|4k|remaster\w*|visuali[sz]er|mv)"
                    r"[^)\]]*[\)\]]", re.I)


def clean_title(text: str) -> str:
    return re.sub(r"\s{2,}", " ", _NOISE.sub("", text or "")).strip(" -|")


def guess_track(info: dict) -> tuple[str, str]:
    """(artist, title) from YouTube Music style tags, else from an 'Artist - Title' video title."""
    artist = (info.get("artist") or "").split(",")[0].strip()
    track = (info.get("track") or "").strip()
    if artist and track:
        return artist, clean_title(track)
    title = clean_title(info.get("title") or "")
    for sep in (" - ", " – ", " — ", " | "):
        if sep in title:
            a, t = title.split(sep, 1)
            return (artist or a.strip()), clean_title(t)
    uploader = re.sub(r"\s*-\s*Topic$", "", info.get("uploader") or info.get("channel") or "", flags=re.I)
    return (artist or uploader.strip()), title


def _get(url: str, opener: Optional[Callable] = None):
    if not url.startswith("https://"):
        raise ValueError("https only")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with (opener or urllib.request.urlopen)(req, timeout=15) as resp:
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("answer too large")
    return json.loads(data.decode("utf-8", "replace"))


def _pick(results: list, duration: float) -> dict:
    best, best_diff = {}, None
    for r in results or []:
        if not isinstance(r, dict) or r.get("instrumental"):
            continue
        if not (r.get("plainLyrics") or r.get("syncedLyrics")):
            continue
        try:
            diff = abs(float(r.get("duration") or 0) - duration) if duration else 0.0
        except (TypeError, ValueError):
            continue
        if duration and diff > DURATION_TOLERANCE:
            continue
        if best_diff is None or diff < best_diff or (diff == best_diff and r.get("syncedLyrics") and not best.get("syncedLyrics")):
            best, best_diff = r, diff
    return best


def fetch(artist: str, title: str, duration: float = 0, opener: Optional[Callable] = None) -> dict:
    """Returns {"plain": str, "synced": str, "artist": str, "title": str} or {} when nothing fits."""
    if not title:
        return {}
    q = {"track_name": title}
    if artist:
        q["artist_name"] = artist
    try:
        results = _get(API + "search?" + urllib.parse.urlencode(q), opener)
        if not results and artist:      # artist tag often wrong on uploads: try the title alone
            results = _get(API + "search?" + urllib.parse.urlencode({"q": f"{artist} {title}"}), opener)
    except Exception:  # noqa: BLE001 - offline / blocked / bad answer: caller falls back to captions
        return {}
    hit = _pick(results if isinstance(results, list) else [], float(duration or 0))
    if not hit:
        return {}
    plain = str(hit.get("plainLyrics") or "")
    synced = str(hit.get("syncedLyrics") or "")
    if not plain and synced:
        plain = "\n".join(re.sub(r"^\[[^\]]*\]\s*", "", ln) for ln in synced.splitlines())
    return {"plain": plain.strip(), "synced": synced.strip(),
            "artist": str(hit.get("artistName") or ""), "title": str(hit.get("trackName") or "")}


def write_lyrics(media_path: str, found: dict) -> bool:
    """Save `<name>.txt` (plain) and `<name>.lrc` (synced, players use it automatically)."""
    if not found or not found.get("plain"):
        return False
    base = Path(media_path).with_suffix("")
    try:
        header = f"{found.get('artist', '')} - {found.get('title', '')}".strip(" -")
        base.with_name(base.name + ".txt").write_text((header + "\n\n" if header else "") + found["plain"] + "\n",
                                                      encoding="utf-8")
        if found.get("synced"):
            base.with_name(base.name + ".lrc").write_text(found["synced"] + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


_LRC = re.compile(r"^\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]\s*(.*)$")


def parse_lrc(synced: str) -> list:
    """[(seconds, text)] sorted; lines without a timestamp are ignored."""
    out = []
    for ln in (synced or "").splitlines():
        m = _LRC.match(ln.strip())
        if m:
            frac = float("0." + m.group(3)) if m.group(3) else 0.0
            out.append((int(m.group(1)) * 60 + int(m.group(2)) + frac, m.group(4).strip()))
    return sorted(out)


def lrc_to_srt(synced: str, total: float = 0) -> str:
    """Subtitle file for video players (VLC, Windows Media Player, TVs) that do not read .lrc."""
    def ts(sec: float) -> str:
        ms = int(round(sec * 1000))
        return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)
    rows = [r for r in parse_lrc(synced) if r[1]]
    blocks = []
    for i, (t, text) in enumerate(rows):
        end = rows[i + 1][0] if i + 1 < len(rows) else (total or t + 5)
        blocks.append("%d\n%s --> %s\n%s\n" % (i + 1, ts(t), ts(max(end - 0.05, t + 0.5)), text))
    return "\n".join(blocks)


def write_srt(media_path: str, found: dict, total: float = 0) -> bool:
    srt = lrc_to_srt(found.get("synced", ""), total) if found else ""
    if not srt:
        return False
    base = Path(media_path).with_suffix("")
    try:
        base.with_name(base.name + ".srt").write_text(srt, encoding="utf-8")
    except OSError:
        return False
    return True


def embed(ffmpeg, media_path: str, plain: str) -> bool:
    """Write the lyrics into the file's tags (ID3 USLT / MP4 lyrics) - phone and desktop players show them."""
    import os, subprocess, tempfile
    path = Path(media_path)
    if not ffmpeg or not plain or path.suffix.lower() not in (".mp3", ".m4a"):
        return False
    tmp = Path(tempfile.mkstemp(suffix=path.suffix, dir=str(path.parent))[1])
    try:
        cmd = [str(ffmpeg), "-y", "-v", "error", "-i", str(path), "-map", "0", "-c", "copy",
               "-map_metadata", "0", "-metadata", "lyrics=" + plain]
        if path.suffix.lower() == ".mp3":
            cmd += ["-id3v2_version", "3"]
        cmd.append(str(tmp))
        if subprocess.run(cmd, capture_output=True, timeout=120).returncode != 0 or tmp.stat().st_size == 0:
            return False
        os.replace(tmp, path)
        return True
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        if tmp.exists():
            tmp.unlink()
