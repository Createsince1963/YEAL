"""Windows (and Linux/macOS) desktop platform."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from . import PlatformInfo


def app_dir() -> Path:
    if getattr(sys, "frozen", False):          # PyInstaller / pyside6-deploy build
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]  # .../PyModul


def _tools_central(start: Path) -> Optional[Path]:
    for parent in (start, *start.parents):
        if parent.name.lower() == "tools_central":
            return parent
    return None


def _central(base: Path) -> Optional[Path]:
    """Tools_Central: an ancestor, $TOOLS_CENTRAL, or a sibling of the workspace folder."""
    found = _tools_central(base)
    if found:
        return found
    env = os.environ.get("TOOLS_CENTRAL")
    if env and Path(env).is_dir():
        return Path(env)
    for parent in base.parents:
        if (parent / "Tools_Central").is_dir():
            return parent / "Tools_Central"
    return None


def find_ffmpeg(base: Optional[Path] = None) -> Optional[Path]:
    """Lookup order: YEAL_FFMPEG, bundled bin/, Tools_Central video tools, PATH."""
    base = base or app_dir()
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    candidates = []
    env = os.environ.get("YEAL_FFMPEG")
    if env:
        candidates.append(Path(env))
    candidates.append(base / "bin" / exe)
    bundle = getattr(sys, "_MEIPASS", None)      # single-file exe: tools are packed inside
    if bundle:
        candidates.append(Path(bundle) / "bin" / exe)
    central = _central(base)
    if central:
        candidates.append(central / "Video Tools" / "FFMPEG" / "bin" / exe)
    for c in candidates:
        if c.is_file():
            return c
    found = shutil.which("ffmpeg")
    return Path(found) if found else None


def find_node(base: Optional[Path] = None) -> Optional[Path]:
    """JS runtime for YouTube (yt-dlp needs Node >= 22 or Deno). Lookup like ffmpeg."""
    base = base or app_dir()
    exe = "node.exe" if os.name == "nt" else "node"
    candidates = []
    env = os.environ.get("YEAL_NODE")
    if env:
        candidates.append(Path(env))
    candidates.append(base / "bin" / exe)
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        candidates.append(Path(bundle) / "bin" / exe)
    central = _central(base)
    if central:
        candidates.append(central / "Dependencies" / "node" / "bin" / exe)
    for c in candidates:
        if c.is_file():
            return c
    found = shutil.which("node")
    return Path(found) if found else None


def detect() -> PlatformInfo:
    base = app_dir()
    if sys.platform.startswith("win"):
        name = "windows"
    elif sys.platform == "darwin":
        name = "macos"
    else:
        name = "linux"

    env_data = os.environ.get("YEAL_DATA_DIR")
    if env_data:
        data = Path(env_data)
    elif (base / "portable.flag").exists():
        data = base / "data"
    elif name == "windows":
        data = Path(os.environ.get("APPDATA", Path.home())) / "Yeal"
    else:
        data = Path.home() / ".local" / "share" / "yeal"

    download = Path(os.environ.get("YEAL_DOWNLOAD_DIR", Path.home() / "Downloads" / "Yeal"))
    return PlatformInfo(name, False, data, download, find_ffmpeg(base), find_node(base))


def open_path(path: Path) -> bool:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except OSError:
        return False


def find_vlc() -> Optional[Path]:
    """VLC from the usual install folders or PATH (None if not installed)."""
    import shutil
    candidates = []
    for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if base:
            candidates.append(Path(base) / "VideoLAN" / "VLC" / "vlc.exe")
    candidates.append(Path("/usr/bin/vlc"))
    candidates.append(Path("/Applications/VLC.app/Contents/MacOS/VLC"))
    for c in candidates:
        if c.is_file():
            return c
    found = shutil.which("vlc")
    return Path(found) if found else None


def open_in_vlc(path: Path, fullscreen: bool = True) -> bool:
    vlc = find_vlc()
    if vlc is None:
        return False
    cmd = [str(vlc)] + (["--fullscreen"] if fullscreen else []) + ["--play-and-exit", str(path)]
    try:
        subprocess.Popen(cmd)
        return True
    except OSError:
        return False


def reveal_path(path: Path) -> bool:
    try:
        if sys.platform.startswith("win") and path.exists():
            # Explorer needs /select,"<path>" as ONE raw string: a list argument gets quoted as a
            # whole by subprocess ("/select,C:\a b") and Explorer then opens Documents instead.
            subprocess.Popen(f'explorer /select,"{os.path.normpath(str(path))}"')
            return True
    except OSError:
        pass
    return open_path(path if path.is_dir() else path.parent)
