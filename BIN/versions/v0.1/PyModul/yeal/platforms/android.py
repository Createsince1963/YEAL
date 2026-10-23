"""Android platform (pyside6-android-deploy / python-for-android).

v0.1 limits, on purpose:
* no ffmpeg -> progressive single-file video and native-container audio only
* downloads go to the Download location Qt reports for the app (scoped storage)
* no share-intent / foreground service yet (see docs/ANDROID.md)
"""
from __future__ import annotations

import os
from pathlib import Path

from . import PlatformInfo


def detect() -> PlatformInfo:
    from PySide6.QtCore import QStandardPaths  # imported lazily: not needed in tests

    def loc(kind) -> Path:
        text = QStandardPaths.writableLocation(kind)
        return Path(text) if text else Path(os.environ.get("HOME", "/data/local/tmp"))

    data = loc(QStandardPaths.StandardLocation.AppDataLocation)
    download = loc(QStandardPaths.StandardLocation.DownloadLocation) / "Yeal"
    return PlatformInfo("android", True, data, download, ffmpeg=None)
