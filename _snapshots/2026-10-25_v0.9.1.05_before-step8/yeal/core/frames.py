"""Split a video into still images with ffmpeg (every N seconds within a time range).
No Qt imports. Output goes to <download dir>/Frames/<video name>/."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

MAX_FRAMES = 5000
SHORTS_MAX_SECONDS = 180      # intervals below 1 s are only allowed for Shorts (<= 3 min)
VIDEO_EXT = (".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi")
FORMATS = ("jpg", "png")
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def parse_time(text: str) -> float:
    """'90', '1:30', '1:02:03' or '' (-> 0) to seconds. Raises ValueError."""
    text = (text or "").strip().replace(",", ".")
    if not text:
        return 0.0
    parts = text.split(":")
    if len(parts) > 3 or any(not re.fullmatch(r"\d+(\.\d+)?", p) for p in parts):
        raise ValueError("Use seconds or mm:ss, e.g. 90 or 1:30")
    total = 0.0
    for p in parts:
        total = total * 60 + float(p)
    return total


def frames_root(download_dir) -> Path:
    return Path(download_dir) / "Frames"


def target_dir(download_dir, video: Path) -> Path:
    """Own sub-folder per video; never reuses an existing folder."""
    name = _BAD.sub("_", video.stem).strip(" .")[:120] or "video"
    base = frames_root(download_dir)
    folder, n = base / name, 2
    while folder.exists():
        folder = base / f"{name} ({n})"
        n += 1
    return folder


def label(seconds: float) -> str:
    """HHhMMmSSs; with a decimal (HHhMMmSS.Ds) when the time is not a whole second."""
    s = int(seconds)
    tenth = int(round((seconds - s) * 10))
    if tenth >= 10:
        s, tenth = s + 1, 0
    frac = f".{tenth}" if tenth else ""
    return f"{s // 3600:02d}h{s % 3600 // 60:02d}m{s % 60:02d}{frac}s"


def extract(ffmpeg, video: Path, out_dir: Path, start: float, end: float, interval: float,
            fmt: str = "jpg") -> int:
    """Write one image every `interval` seconds from `start` to `end` (0 = until the end).
    Files are named <video>_<HHhMMmSSs>.<fmt>. Returns the number of images; raises ValueError / RuntimeError."""
    if fmt not in FORMATS:
        raise ValueError("Format must be jpg or png")
    if interval <= 0:
        raise ValueError("The interval must be greater than 0 seconds")
    if end and end <= start:
        raise ValueError("'To' must be later than 'From'")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not available")
    if not Path(video).is_file():
        raise RuntimeError("The video file was not found")
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(ffmpeg), "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(video)]
    if end:
        cmd += ["-t", f"{end - start:.3f}"]
    cmd += ["-vf", f"fps=1/{interval:g}", "-frames:v", str(MAX_FRAMES)]
    cmd += ["-q:v", "1"] if fmt == "jpg" else []   # best JPEG quality; PNG is lossless
    cmd.append(str(out_dir / f"frame_%05d.{fmt}"))
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          creationflags=flags)
    files = sorted(out_dir.glob(f"frame_*.{fmt}"))
    if proc.returncode != 0 and not files:
        raise RuntimeError((proc.stderr or "ffmpeg failed").strip().splitlines()[-1][:200])
    stem = _BAD.sub("_", Path(video).stem)[:80]
    for i, f in enumerate(files):
        f.rename(out_dir / f"{stem}_{label(start + i * interval)}.{fmt}")
    return len(files)


def probe_duration(ffmpeg, video: Path) -> float:
    """Duration in seconds (parsed from ffmpeg's banner); 0.0 if unknown."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    proc = subprocess.run([str(ffmpeg), "-nostdin", "-hide_banner", "-i", str(video)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          creationflags=flags)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr or "")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def filmstrip(ffmpeg, video: Path, out_dir: Path, count: int = 12, height: int = 90) -> tuple[float, list]:
    """Small preview images spread evenly over the video. Returns (duration, [image paths])."""
    duration = probe_duration(ffmpeg, video)
    if duration <= 0:
        raise RuntimeError("Could not read the video length")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("strip_*.jpg"):
        old.unlink()
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    files = []
    for i in range(count):
        t = duration * (i + 0.5) / count
        target = out_dir / f"strip_{i:02d}.jpg"
        subprocess.run([str(ffmpeg), "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}",
                        "-i", str(video), "-frames:v", "1", "-vf", f"scale=-2:{height}", "-q:v", "4", str(target)],
                       capture_output=True, creationflags=flags)
        if target.exists():
            files.append(target)
    if not files:
        raise RuntimeError("Could not create preview images")
    return duration, files


def list_videos(download_dir) -> list:
    """Video files in <download>/Video and the download folder itself, newest first.
    Returns [{path, title, size, mtime}]."""
    root = Path(download_dir)
    seen, out = set(), []
    for folder in (root / "Video", root):
        try:
            entries = list(folder.iterdir())
        except OSError:
            continue
        for p in entries:
            try:
                if p.is_file() and p.suffix.lower() in VIDEO_EXT and p not in seen:
                    seen.add(p)
                    st = p.stat()
                    out.append({"path": str(p), "title": p.stem, "size": st.st_size, "mtime": st.st_mtime})
            except OSError:
                pass
    return sorted(out, key=lambda d: d["mtime"], reverse=True)


def thumb_for(ffmpeg, video: Path, cache_dir: Path, height: int = 180) -> Optional[Path]:
    """Cached JPEG poster frame of a video (None on failure)."""
    import hashlib
    st = Path(video).stat()
    key = hashlib.md5(f"{video}|{st.st_mtime_ns}|{st.st_size}".encode("utf-8", "replace")).hexdigest()
    target = Path(cache_dir) / f"{key}.jpg"
    if target.exists():
        return target
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    for ss in ("1", "0"):   # very short clips have no frame at 1 s
        subprocess.run([str(ffmpeg), "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-ss", ss,
                        "-i", str(video), "-frames:v", "1", "-vf", f"scale=-2:{height}", "-q:v", "5", str(target)],
                       capture_output=True, creationflags=flags)
        if target.exists():
            return target
    return None
