"""Platform layer: everything that differs between Windows desktop and Android."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PlatformInfo:
    name: str                       # "windows" | "linux" | "macos" | "android"
    is_mobile: bool
    data_dir: Path                  # settings + temp live here
    download_dir: Path
    ffmpeg: Optional[Path] = None   # None -> no merging / audio conversion
    js_runtime: Optional[Path] = None  # node.exe; YouTube needs a JS runtime (yt-dlp EJS)

    @property
    def is_windows(self) -> bool:
        return self.name == "windows"

    @property
    def can_merge(self) -> bool:
        return self.ffmpeg is not None

    @property
    def temp_dir(self) -> Path:
        return self.data_dir / "tmp"

    @property
    def settings_path(self) -> Path:
        return self.data_dir / "settings.json"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.download_dir, self.temp_dir):
            d.mkdir(parents=True, exist_ok=True)


def is_android() -> bool:
    return (sys.platform == "android" or "ANDROID_ARGUMENT" in os.environ
            or "ANDROID_STORAGE" in os.environ and "ANDROID_ROOT" in os.environ)


def detect() -> PlatformInfo:
    if is_android():
        from . import android
        return android.detect()
    from . import desktop
    return desktop.detect()


def open_path(path: Path) -> bool:
    """Open a file/folder with the system handler. Returns False if unsupported."""
    if is_android():
        return False
    from . import desktop
    return desktop.open_path(path)


from . import drives  # noqa: E402,F401


def vlc_available() -> bool:
    if is_android():
        return False
    from . import desktop
    return desktop.find_vlc() is not None


def open_in_vlc(path: Path, fullscreen: bool = True) -> bool:
    if is_android():
        return False
    from . import desktop
    return desktop.open_in_vlc(path, fullscreen)


def reveal_path(path: Path) -> bool:
    """Show a file selected in the file manager (or just open its folder)."""
    if is_android():
        return False
    from . import desktop
    return desktop.reveal_path(path)
