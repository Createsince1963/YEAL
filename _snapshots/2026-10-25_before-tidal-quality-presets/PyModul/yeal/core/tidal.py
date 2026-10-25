"""Tidal support (Yeal 0.9.0.0): runs the `tiddl` command line tool as a separate process.

tiddl (https://github.com/oskvr37/tiddl, Apache-2.0) is NOT bundled and NOT imported: Yeal only starts it
like it starts ffmpeg, so Tidal changes (tokens, stream formats) are fixed by updating tiddl alone.

Tidal can only be used with an active, paid Tidal subscription. Every user signs in with their own Tidal
account (device login in the browser); Yeal never sees or stores the Tidal password or token - tiddl keeps
its own login in `~/.tiddl/auth.json` (or `%TIDDL_PATH%`).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, List, Optional
from urllib.parse import urlparse

TIDAL_QUALITIES = ("low", "normal", "high", "max")   # tiddl: m4a 96 / m4a 320 / FLAC 16-bit / FLAC up to 24-bit
TIDAL_VIDEO_QUALITIES = ("sd", "hd", "fhd")           # tiddl --video-quality
TIDAL_VIDEOS = ("none", "allow", "only")              # tiddl --videos: skip / include / only videos inside albums, playlists, artists
TIDAL_HOSTS = ("tidal.com", "www.tidal.com", "listen.tidal.com", "embed.tidal.com")
_RESOURCE = re.compile(r"/(?:browse/)?(track|album|playlist|artist|mix|video)/([0-9A-Za-z-]+)", re.IGNORECASE)
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")
# Folder layout below <download folder>\Tidal\ (tiddl --output template, one per kind of link).
# Single songs -> Singles, playlists and mixes -> Playlists\<name>, videos -> Videos, albums and artists -> Albums.
OUTPUT_TEMPLATES = {
    "track": "Singles/{item.artist} - {item.title}",
    "video": "Videos/{item.artist} - {item.title}",
    "playlist": "Playlists/{playlist.title}/{playlist.index:02d} - {item.artist} - {item.title}",
    "mix": "Playlists/Mix {mix_id}/{item.artist} - {item.title}",
    "album": "Albums/{album.artist}/{album.title}/{item.number:02d} - {item.title}",
    "artist": "Albums/{album.artist}/{album.title}/{item.number:02d} - {item.title}",
}
INSTALL_HINT = "Install tiddl once with:  pip install tiddl   (needs Python), then choose it under Settings > Tidal."

NOTICE = ("Tidal needs an active Tidal subscription. Sign in with your own Tidal account; the downloads are meant "
          "for personal use and are subject to Tidal's terms of use. Yeal does not work without a subscription.")


def is_tidal_url(url: str) -> bool:
    """True for a Tidal track / album / playlist / artist / mix / video link."""
    try:
        parts = urlparse((url or "").strip())
    except ValueError:
        return False
    return (parts.scheme in ("http", "https") and (parts.hostname or "").lower() in TIDAL_HOSTS
            and bool(_RESOURCE.search(parts.path)))


def resource_of(url: str) -> str:
    """'album/123' style id used for display and for tiddl."""
    m = _RESOURCE.search(urlparse((url or "").strip()).path)
    return f"{m.group(1).lower()}/{m.group(2)}" if m else ""


def output_template(url: str) -> str:
    """tiddl output template (sub folder + file name) for a Tidal link: Singles / Playlists / Videos / Albums."""
    kind = resource_of(url).split("/")[0]
    return OUTPUT_TEMPLATES.get(kind, "")


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text or "")


def app_path() -> Path:
    """tiddl's data folder (same rule as tiddl: $TIDDL_PATH, else ~/.tiddl)."""
    env = os.environ.get("TIDDL_PATH")
    return Path(env) if env else Path.home() / ".tiddl"


def is_logged_in(path: Optional[Path] = None) -> bool:
    """tiddl keeps the login in auth.json; a non-empty token means someone is signed in."""
    try:
        data = json.loads((path or app_path() / "auth.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and bool(data.get("token"))


def find_tiddl(configured: str = "") -> str:
    """Path of the tiddl executable: the user's choice, else PATH, else next to the running Python."""
    if configured:
        p = Path(configured)
        return str(p) if p.is_file() else ""
    found = shutil.which("tiddl")
    if found:
        return found
    names = ("tiddl.exe", "tiddl") if os.name == "nt" else ("tiddl",)
    base = Path(sys.executable).resolve().parent
    for folder in (base, base / "Scripts", base / "bin"):
        for name in names:
            if (folder / name).is_file():
                return str(folder / name)
    return ""


def build_command(exe: str, url: str, quality: str = "high", base_dir: str = "", threads: int = 2,
                  video_quality: str = "fhd", videos: str = "allow") -> List[str]:
    """`tiddl download -q <quality> -t <n> -vq <sd|hd|fhd> --videos <mode> -p <dir> url <link>` (global options come before `url`).
    tiddl skips videos by default (`--videos none`), even a direct video link: a link to a single video is therefore
    always downloaded with `allow`; for albums/playlists/artists the user's choice applies."""
    quality = quality if quality in TIDAL_QUALITIES else "high"
    video_quality = video_quality if video_quality in TIDAL_VIDEO_QUALITIES else "fhd"
    videos = videos if videos in TIDAL_VIDEOS else "allow"
    if resource_of(url).startswith("video/") and videos == "none":
        videos = "allow"
    cmd = [exe, "download", "-q", quality, "-t", str(max(1, min(4, int(threads or 1)))),
           "-vq", video_quality, "--videos", videos]
    template = output_template(url)
    if template:
        cmd += ["-o", template]
    if base_dir:
        cmd += ["-p", str(base_dir), "--scan-path", str(base_dir)]
    return cmd + ["url", url]


def _env() -> dict:
    env = dict(os.environ)
    env.update(NO_COLOR="1", TERM="dumb", COLUMNS="200", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    return env


def _popen(cmd: List[str]) -> subprocess.Popen:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            env=_env(), creationflags=flags)


def iter_lines(stream) -> "iter":
    """Yield text lines; a carriage return (progress bar redraw) also ends a line."""
    buf = b""
    while True:
        chunk = stream.read1(512) if hasattr(stream, "read1") else stream.read(512)
        if not chunk:
            break
        buf += chunk
        while True:
            m = re.search(rb"[\r\n]", buf)
            if not m:
                break
            line, buf = buf[:m.start()], buf[m.end():]
            text = strip_ansi(line.decode("utf-8", "replace")).strip()
            if text:
                yield text
    text = strip_ansi(buf.decode("utf-8", "replace")).strip()
    if text:
        yield text


def classify(line: str) -> str:
    """'done' (one item finished), 'error', 'skip' or 'info'."""
    low = line.lower()
    if "not logged in" in low or "auth token is missing" in low or "token is missing" in low:
        return "login"
    if low.startswith("downloaded"):
        return "done"
    if "error" in low or "failed" in low or "traceback" in low:
        return "error"
    if "skipp" in low or "already exist" in low:
        return "skip"
    return "info"


def friendly_error(lines: List[str], code: int) -> str:
    text = " ".join(lines[-6:]).lower()
    if any(classify(x) == "login" for x in lines[-10:]):
        return "Not signed in to Tidal. Open Settings > Tidal and sign in with your Tidal account."
    if "401" in text or "403" in text or "expired" in text or "token" in text:
        return "Tidal refused the request (login expired?). Sign out and in again under Settings > Tidal, or update tiddl."
    if "subscription" in text or "not available" in text or "region" in text or "country" in text:
        return "Tidal does not offer this content for your account or country (a subscription is required)."
    if "ffmpeg" in text:
        return "ffmpeg was not found - Tidal downloads need it. See Settings > Download engine."
    last = lines[-1] if lines else ""
    return (f"tiddl stopped with code {code}. " + last[:200]).strip()


def run_download(exe: str, url: str, quality: str, base_dir: str, threads: int,
                 cancel: threading.Event, on_line: Callable[[str, str], None],
                 video_quality: str = "fhd", videos: str = "allow") -> tuple:
    """Run one tiddl download. `on_line(kind, text)` is called for every output line.
    Returns (exit code, all lines). The process is terminated when `cancel` is set."""
    proc = _popen(build_command(exe, url, quality, base_dir, threads, video_quality, videos))
    lines: List[str] = []

    def watch() -> None:
        cancel.wait()
        if proc.poll() is None:
            proc.terminate()

    threading.Thread(target=watch, daemon=True).start()
    try:
        for line in iter_lines(proc.stdout):
            lines.append(line)
            on_line(classify(line), line)
        code = proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill()
    return code, lines


class LoginFlow:
    """`tiddl auth login --no-browser`: reads the Tidal device-login link from its output, then waits until the
    user has finished in the browser. `on_link(url)` fires once, `on_done(ok, message)` at the end."""

    def __init__(self, exe: str, on_link: Callable[[str], None], on_done: Callable[[bool, str], None]):
        self._exe, self._on_link, self._on_done = exe, on_link, on_done
        self._proc: Optional[subprocess.Popen] = None

    def start(self) -> None:
        threading.Thread(target=self._run, name="yeal-tidal-login", daemon=True).start()

    def cancel(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()

    def _run(self) -> None:
        try:
            self._proc = _popen([self._exe, "auth", "login", "--no-browser"])
        except OSError as exc:
            self._on_done(False, f"tiddl could not be started: {exc}")
            return
        sent = False
        for line in iter_lines(self._proc.stdout):
            m = re.search(r"https?://\S+", line) or re.search(r"'([^']*link\.tidal\.com[^']*)'", line)
            if m and not sent:
                sent = True
                link = m.group(0).strip("'\".,")
                self._on_link(link if link.startswith("http") else "https://" + link)
        self._proc.wait()
        ok = is_logged_in()
        self._on_done(ok, "Signed in to Tidal." if ok else "Tidal sign-in was not completed.")


def logout(exe: str) -> bool:
    """`tiddl auth logout --force`; True when no login remains."""
    try:
        subprocess.run([exe, "auth", "logout", "--force"], capture_output=True, timeout=20, env=_env(),
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return False
    return not is_logged_in()
