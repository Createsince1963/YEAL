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
TIDAL_QUALITY_LABELS = {   # shown in the download options (same steps as Tidal's own audio quality setting)
    "low": "Tidal Low (AAC 96 kbps)", "normal": "Tidal Normal (AAC 320 kbps)",
    "high": "Tidal High (FLAC 16-bit / 44.1 kHz)", "max": "Tidal Max (FLAC up to 24-bit / 192 kHz)"}
TIDAL_VIDEO_QUALITIES = ("sd", "hd", "fhd")           # tiddl --video-quality
TIDAL_VIDEOS = ("none", "allow", "only")              # tiddl --videos: skip / include / only videos inside albums, playlists, artists
TIDAL_ATMOS = ("none", "allow", "only")               # tiddl --dolby-atmos: skip / include / only Dolby Atmos versions
TIDAL_SINGLES = ("none", "include", "only")           # tiddl --singles: artist links without / with / only singles and EPs
AUDIO_EXTS = (".flac", ".m4a", ".mp4", ".mp3", ".aac")
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


def find_login_link(line: str) -> str:
    """The Tidal device-login link in one line of `tiddl auth login` output, else ''.
    Other links in the output (update notices with a GitHub address, docs) are ignored; the link may come without
    a scheme ('link.tidal.com/ABCDE')."""
    for m in re.finditer(r"(?:https?://)?([\w.-]*tidal\.com)(/[^\s'\"<>)]*)?", line or "", re.IGNORECASE):
        text = m.group(0).strip("'\".,;")
        host = m.group(1).lower()
        if host.startswith(("link.", "login.")) or "device" in text.lower():
            return text if text.lower().startswith("http") else "https://" + text
    return ""


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text or "")


def app_path() -> Path:
    """tiddl's data folder (same rule as tiddl: $TIDDL_PATH, else ~/.tiddl)."""
    env = os.environ.get("TIDDL_PATH")
    return Path(env) if env else Path.home() / ".tiddl"


def is_logged_in(path: Optional[Path] = None) -> bool:
    """tiddl keeps the login in auth.json; a non-empty token means someone is signed in."""
    for file in ([path] if path else [app_path() / "auth.json", app_path() / ".tiddl_config.json"]):
        try:
            data = json.loads(file.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and (data.get("token") or data.get("access_token")):
            return True
    return False


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
                  video_quality: str = "fhd", videos: str = "allow", atmos: str = "none", singles: str = "none",
                  no_skip: bool = False, rewrite: bool = False) -> List[str]:
    """`tiddl download -q <quality> -t <n> -vq <sd|hd|fhd> --videos <mode> --dolby-atmos <mode> [--singles <mode>]
    [--no-skip] [--rewrite-metadata] -p <dir> url <link>` (global options come before `url`).
    tiddl skips videos by default (`--videos none`), even a direct video link: a link to a single video is therefore
    always downloaded with `allow`; for albums/playlists/artists the user's choice applies. `--singles` only matters
    for artist links and is only passed there."""
    quality = quality if quality in TIDAL_QUALITIES else "high"
    video_quality = video_quality if video_quality in TIDAL_VIDEO_QUALITIES else "fhd"
    videos = videos if videos in TIDAL_VIDEOS else "allow"
    atmos = atmos if atmos in TIDAL_ATMOS else "none"
    singles = singles if singles in TIDAL_SINGLES else "none"
    if resource_of(url).startswith("video/") and videos == "none":
        videos = "allow"
    cmd = [exe, "download", "-q", quality, "-t", str(max(1, min(4, int(threads or 1)))),
           "-vq", video_quality, "--videos", videos, "--dolby-atmos", atmos]
    if resource_of(url).startswith("artist/"):
        cmd += ["--singles", singles]
    if no_skip:
        cmd.append("--no-skip")
    if rewrite:
        cmd.append("--rewrite-metadata")
    template = output_template(url)
    if template:
        cmd += ["-o", template]
    if base_dir:
        cmd += ["-p", str(base_dir), "--scan-path", str(base_dir)]
    return cmd + ["url", url]


def _env(home: Optional[Path] = None) -> dict:
    env = dict(os.environ)
    env.update(NO_COLOR="1", TERM="dumb", COLUMNS="200", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    if home is not None:
        env["TIDDL_PATH"] = str(home)
    return env


def _popen(cmd: List[str], home: Optional[Path] = None) -> subprocess.Popen:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            env=_env(home), creationflags=flags)


# ---- Yeal's own tiddl folder (0.9.1) -----------------------------------------------------------------------
# Downloads run with TIDDL_PATH=<Yeal data>/tiddl: the extras chosen in Yeal (lyrics, covers, M3U) go into a
# config.toml there, so the user's own tiddl setup (~/.tiddl/config.toml) is never changed. The sign-in stays in
# ~/.tiddl: its auth.json is copied in before a download and a token renewed by tiddl is copied back afterwards.

def config_toml(lyrics: bool = False, lrc: bool = False, cover_embed: bool = False, cover_file: bool = False,
                m3u: bool = False) -> str:
    """config.toml for tiddl 3.x with the extras chosen in Yeal (only keys tiddl knows)."""
    def b(v: bool) -> str:
        return "true" if v else "false"
    return ("# Written by Yeal for its Tidal downloads - changes are overwritten.\n"
            f"[metadata]\nenable = true\nlyrics = {b(lyrics)}\ncover = {b(cover_embed)}\n\n"
            f"[download]\nwrite_lrc_file = {b(lrc)}\n\n"
            f"[cover]\nsave = {b(cover_file)}\nallowed = [\"album\", \"playlist\"]\n\n"
            f"[m3u]\nsave = {b(m3u)}\nallowed = [\"album\", \"playlist\", \"mix\"]\n")


def _expires(path: Path) -> float:
    try:
        return float(json.loads(path.read_text(encoding="utf-8-sig")).get("expires_at") or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        return -1.0


def prepare_home(home: Path, extras: Optional[dict] = None, global_dir: Optional[Path] = None) -> Path:
    """Create Yeal's tiddl folder: config.toml with the extras, auth.json copied from the user's tiddl folder
    (only when that one is at least as new, so a token renewed in here is never replaced by an older one)."""
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    e = extras or {}
    (home / "config.toml").write_text(config_toml(bool(e.get("lyrics")), bool(e.get("lrc")), bool(e.get("cover_embed")),
                                                  bool(e.get("cover_file")), bool(e.get("m3u"))), encoding="utf-8")
    src = Path(global_dir or app_path()) / "auth.json"
    dst = home / "auth.json"
    if src.is_file() and _expires(src) >= _expires(dst):
        shutil.copyfile(src, dst)
    return home


def sync_auth_back(home: Path, global_dir: Optional[Path] = None) -> bool:
    """Copy a token that tiddl renewed inside Yeal's folder back to the user's tiddl folder (newer one wins)."""
    src = Path(home) / "auth.json"
    dst = Path(global_dir or app_path()) / "auth.json"
    if src.is_file() and _expires(src) > _expires(dst):
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            return True
        except OSError:
            return False
    return False


def new_audio_folders(base: Path, since: float) -> List[Path]:
    """Folders below `base` with audio files written since `since` (the result of one tiddl run), deepest first."""
    found = set()
    for path in Path(base).rglob("*"):
        try:
            if path.suffix.lower() in AUDIO_EXTS and path.is_file() and path.stat().st_mtime >= since - 2:
                found.add(path.parent)
        except OSError:
            continue
    return sorted(found, key=lambda p: (-len(p.parts), str(p)))


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", (text or "").lower())


def match_tracks(files: List[Path], tracks: List[dict]) -> List[Optional[dict]]:
    """The Tidal track of every downloaded file (same order as `files`), None where nothing fits.
    tiddl names files '<nn> - <title>' (album) or '<nn> - <artist> - <title>' (playlist); a file belongs to the longest
    title that its name ends with. With the same number of files and tracks and no match the order decides."""
    free = list(tracks or [])
    out: List[Optional[dict]] = []
    for f in files:
        stem = _norm(re.sub(r"^\d+\s*-\s*", "", f.stem))
        best = None
        for t in free:
            title = _norm(str(t.get("title") or ""))
            if title and stem.endswith(title) and (best is None or len(title) > len(_norm(str(best.get("title") or "")))):
                best = t
        if best is not None:
            free.remove(best)
        out.append(best)
    if len(files) == len(tracks or []) and not any(out):
        return list(tracks)
    return out


def write_html_pages(base: Path, since: float, source: str, theme: str = "auto", cover: str = "",
                     uploader: str = "", tracks: Optional[List[dict]] = None) -> List[Path]:
    """Yeal's player page (extras.write_playlist_page) in every album / playlist folder this run wrote to.
    Single songs (Singles / Videos folders) get none. `tracks` (Tidal track dicts of the link) give every row its own
    cover, artist and Tidal link / id, which the page shows while that title plays."""
    from . import extras
    pages = []
    for folder in new_audio_folders(base, since):
        if folder.name.lower() in ("singles", "videos") or folder == Path(base):
            continue
        files = sorted(p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXTS and p.is_file())
        found = match_tracks(files, tracks or [])
        items = []
        for i, f in enumerate(files):
            t = found[i] or {}
            thumb = str(t.get("cover") or "")
            if thumb.startswith("https://resources.tidal.com/"):
                thumb = re.sub(r"/\d+x\d+\.jpg$", "/320x320.jpg", thumb)
            items.append({"index": i + 1, "title": re.sub(r"^\d+\s*-\s*", "", f.stem), "file": f.name,
                          "thumb": thumb or cover, "artist": str(t.get("subtitle") or ""),
                          "id": str(t.get("id") or ""), "link": str(t.get("url") or "")})
        page = extras.write_playlist_page(folder, folder.name, uploader, source, items, "audio", theme)
        if page:
            pages.append(page)
    return pages


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
                 video_quality: str = "fhd", videos: str = "allow", atmos: str = "none", singles: str = "none",
                 no_skip: bool = False, rewrite: bool = False, home: Optional[Path] = None) -> tuple:
    """Run one tiddl download. `on_line(kind, text)` is called for every output line.
    `home`: Yeal's tiddl folder (TIDDL_PATH, see prepare_home); None = the user's own tiddl setup.
    Returns (exit code, all lines). The process is terminated when `cancel` is set."""
    proc = _popen(build_command(exe, url, quality, base_dir, threads, video_quality, videos, atmos, singles,
                                no_skip, rewrite), home)
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
            link = find_login_link(line)
            if link and not sent:
                sent = True
                self._on_link(link)
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
