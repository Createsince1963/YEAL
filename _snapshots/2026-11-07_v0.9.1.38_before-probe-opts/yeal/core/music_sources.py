"""Music folders of the user (0.9.1.19): any folder on this PC or in the network can be added as a source for the player
for downloaded files. The "Folders" planet shows every source as a moon; choosing a moon fills the library with its songs,
and a source (or an album folder in it) can be dragged into the queue.

Pure functions, no Qt: validation of the setting, kind of a folder (local / network) and the scan for audio files.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

AUDIO_EXT = (".mp3", ".flac", ".m4a", ".opus", ".ogg", ".wav", ".aac", ".wma")
MAX_SOURCES = 12
MAX_FILES = 3000
_NUMBER = re.compile(r"^\d+\s*-\s*")


def is_network_path(path: str) -> bool:
    """A UNC path (\\\\server\\share, //server/share) or, on Windows, a drive that is a network share."""
    text = str(path or "").strip()
    if text.startswith("\\\\") or text.startswith("//"):
        return True
    if sys.platform == "win32" and len(text) >= 2 and text[1] == ":":
        try:
            import ctypes
            return ctypes.windll.kernel32.GetDriveTypeW(text[:2] + "\\") == 4      # DRIVE_REMOTE
        except Exception:  # noqa: BLE001
            return False
    return False


def source_id(path: str) -> str:
    return "src-" + hashlib.sha1(os.path.normcase(os.path.normpath(path)).encode("utf-8")).hexdigest()[:8]


def validate_sources(raw) -> List[dict]:
    """[{id, name, path, kind: local | network}] - bad entries are dropped, duplicates (same path) are dropped, at most
    MAX_SOURCES are kept."""
    out: List[dict] = []
    seen = set()
    if not isinstance(raw, (list, tuple)):
        return out
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "").strip()[:500]
        if not path:
            continue
        key = os.path.normcase(os.path.normpath(path))
        if key in seen:
            continue
        seen.add(key)
        name = str(entry.get("name") or "").strip()[:60] or Path(path.rstrip("\\/")).name or path
        out.append({"id": str(entry.get("id") or source_id(path))[:40], "name": name, "path": path,
                    "kind": "network" if is_network_path(path) else "local"})
        if len(out) >= MAX_SOURCES:
            break
    return out


def split_name(stem: str) -> tuple:
    """(title, artist) from a file name: 'NN - ' is dropped, 'Artist - Title' is split."""
    name = _NUMBER.sub("", stem).strip()
    if " - " in name:
        artist, title = name.split(" - ", 1)
        return title.strip(), artist.strip()
    return name, ""


def scan_folder(path: str, limit: int = MAX_FILES, cancel=None) -> List[dict]:
    """Queue items of all audio files in a folder (sub folders included), in name order. `cancel` is an optional
    callable; when it returns true the scan stops (a network folder can be slow)."""
    root = Path(path)
    files: List[Path] = []
    try:
        if root.is_file():
            files = [root] if root.suffix.lower() in AUDIO_EXT else []
        else:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames.sort()
                for name in sorted(filenames):
                    if name.lower().endswith(AUDIO_EXT):
                        files.append(Path(dirpath) / name)
                        if len(files) >= limit:
                            break
                if len(files) >= limit or (cancel and cancel()):
                    break
    except OSError:
        pass
    items: List[dict] = []
    for f in files:
        title, artist = split_name(f.stem)
        items.append({"kind": "track", "id": str(f), "title": title, "subtitle": artist, "cover": "", "duration": 0,
                      "file": str(f), "jobId": 0, "source": f.parent.name, "url": ""})
    return items


def check_folder(path: str) -> Optional[str]:
    """None when the folder can be used, otherwise a short reason."""
    try:
        p = Path(path)
        if not p.exists():
            return "The folder does not exist (or the network share is not reachable)."
        if not p.is_dir():
            return "This is not a folder."
        next(iter(p.iterdir()), None)
    except OSError as exc:
        return f"The folder cannot be read: {exc.strerror or exc}"
    return None
