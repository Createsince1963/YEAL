"""Self-updating yt-dlp (+ yt-dlp-ejs), like Seal keeps its bundled yt-dlp current.

YouTube changes constantly, so a yt-dlp that is a few months old stops working. Yeal keeps
its own copy in `<data_dir>/ytdlp/`, downloaded from PyPI (pure-Python wheels, sha256
verified) and put in front of `sys.path` before yt_dlp is first imported. That makes the
update independent of whatever Python (central WinPython, PyInstaller bundle, Android) runs Yeal.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import sys
import time
import urllib.request
import zipfile
from importlib import util as importlib_util
from pathlib import Path
from typing import Callable, Optional, Tuple

PYPI_JSON = "https://pypi.org/pypi/{}/json"
USER_AGENT = "Yeal-updater"
CHECK_INTERVAL_S = 3 * 24 * 3600
_PACKAGES = ("yt_dlp", "yt_dlp_ejs")


def local_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "ytdlp"


def activate(data_dir: Path) -> bool:
    """Prefer the downloaded yt-dlp. Must run before the first `import yt_dlp`."""
    d = local_dir(data_dir)
    if (d / "yt_dlp" / "version.py").is_file():
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))
        return True
    return False


def _version_from_file(path: Path) -> str:
    try:
        match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", path.read_text(encoding="utf-8"))
    except OSError:
        return ""
    return match.group(1) if match else ""


def installed_version(data_dir: Path) -> str:
    """Version that `import yt_dlp` will use (without importing it). '' if none."""
    local = local_dir(data_dir) / "yt_dlp" / "version.py"
    if local.is_file():
        return _version_from_file(local)
    try:
        spec = importlib_util.find_spec("yt_dlp")
    except (ImportError, ValueError):
        spec = None
    if spec and spec.origin:
        return _version_from_file(Path(spec.origin).parent / "version.py")
    return ""


def _norm(version: str) -> Tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", version))


def should_check(data_dir: Path, now: Optional[float] = None) -> bool:
    stamp = local_dir(data_dir) / "stamp.json"
    try:
        last = json.loads(stamp.read_text(encoding="utf-8")).get("checked", 0)
    except (OSError, ValueError):
        return True
    return (now or time.time()) - float(last) > CHECK_INTERVAL_S


def _open(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec - fixed https hosts
        return resp.read()


def _wheel(package: str, version: Optional[str] = None) -> Tuple[str, str, str]:
    """Return (version, url, sha256) of the pure-Python wheel."""
    data = json.loads(_open(PYPI_JSON.format(package)))
    version = version or data["info"]["version"]
    for f in data["releases"].get(version, []):
        if f["filename"].endswith("-py3-none-any.whl") and not f.get("yanked"):
            return version, f["url"], f["digests"]["sha256"]
    raise RuntimeError(f"No pure-Python wheel for {package} {version} on PyPI")


def _fetch_verified(url: str, sha256: str) -> bytes:
    blob = _open(url)
    if hashlib.sha256(blob).hexdigest() != sha256:
        raise RuntimeError("Checksum mismatch - download discarded")
    return blob


def _extract(blob: bytes, target: Path) -> None:
    root = target.resolve()
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for member in zf.infolist():
            top = member.filename.split("/", 1)[0]
            if member.is_dir() or ".data/" in member.filename or not (
                    top in _PACKAGES or top.endswith(".dist-info")):
                continue
            dest = (target / member.filename).resolve()
            if root not in dest.parents:        # zip-slip guard
                raise RuntimeError(f"Unsafe path in wheel: {member.filename}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(member))


def _ejs_pin(ytdlp_wheel: bytes) -> Optional[str]:
    with zipfile.ZipFile(io.BytesIO(ytdlp_wheel)) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        meta = zf.read(name).decode("utf-8", "replace")
    match = re.search(r"^Requires-Dist:\s*yt-dlp-ejs==([^;\s]+)", meta, re.MULTILINE)
    return match.group(1) if match else None


def update(data_dir: Path, force: bool = False,
           log: Callable[[str], None] = lambda msg: None) -> Tuple[str, bool]:
    """Install the latest yt-dlp. Returns (version, changed)."""
    data_dir = Path(data_dir)
    current = installed_version(data_dir)
    version, url, digest = _wheel("yt-dlp")
    if not force and current and _norm(current) >= _norm(version) and _ejs_available(data_dir):
        _write_stamp(data_dir, current)
        return current, False

    log(f"Downloading yt-dlp {version} ...")
    ytdlp_blob = _fetch_verified(url, digest)
    pin = _ejs_pin(ytdlp_blob)
    staging = data_dir / "ytdlp.new"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        _extract(ytdlp_blob, staging)
        ejs_version, ejs_url, ejs_digest = _wheel("yt-dlp-ejs", pin)
        log(f"Downloading yt-dlp-ejs {ejs_version} ...")
        _extract(_fetch_verified(ejs_url, ejs_digest), staging)
        if not (staging / "yt_dlp" / "version.py").is_file():
            raise RuntimeError("Downloaded wheel is incomplete")
        target, old = local_dir(data_dir), data_dir / "ytdlp.old"
        shutil.rmtree(old, ignore_errors=True)
        if target.exists():
            target.rename(old)
        staging.rename(target)
        shutil.rmtree(old, ignore_errors=True)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    _write_stamp(data_dir, version)
    activate(data_dir)
    return version, True


def _ejs_available(data_dir: Path) -> bool:
    """yt-dlp-ejs (the YouTube challenge solver) must be importable, locally or system-wide."""
    if (local_dir(data_dir) / "yt_dlp_ejs").is_dir():
        return True
    try:
        return importlib_util.find_spec("yt_dlp_ejs") is not None
    except (ImportError, ValueError):
        return False


def _write_stamp(data_dir: Path, version: str) -> None:
    d = local_dir(data_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / "stamp.json").write_text(json.dumps({"version": version, "checked": time.time()}),
                                  encoding="utf-8")


def restart_needed() -> bool:
    """True if yt_dlp was already imported in this process (old code still loaded)."""
    return "yt_dlp" in sys.modules
