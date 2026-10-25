"""Yeal's own player for DOWNLOADED files (0.9.1): the oval track player for the finished audio downloads, also the
source for streaming a song to a speaker in the network (Stream to box).

It is the TIDAL DIY player (queue, shuffle, repeat, volume, level, loudness profile) with local files as the source:
no API, no stream links. The whole file is scanned once (QAudioDecoder), so the loudness profile around the oval is
there from the first second. Sound does not overlap with the TIDAL players: starting one pauses the others
(Settings: single playback).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from ..core import tidal
from ..core.models import JobState
from .tidal_backend import LEVEL_BUCKET_US, TidalPlayer, pairs_of

AUDIO_EXT = (".mp3", ".flac", ".m4a", ".opus", ".ogg", ".wav", ".aac", ".wma")
MAX_FILES_PER_JOB = 500
_NUMBER = re.compile(r"^\d+\s*-\s*")


def split_name(stem: str, tidal_job: bool, uploader: str = "") -> tuple:
    """(title, artist) from a file name: 'NN - ' is dropped; Tidal files are named 'Artist - Title'."""
    name = _NUMBER.sub("", stem).strip()
    if tidal_job and " - " in name:
        artist, title = name.split(" - ", 1)
        return title.strip(), artist.strip()
    return name, uploader or ""


def library_items(jobs) -> List[dict]:
    """Queue items for every finished audio file of the download jobs (newest download first, files of an album or
    playlist in name order). A job that points at a folder brings the audio files in it."""
    items: List[dict] = []
    seen = set()
    for job in jobs or []:
        if job.state != JobState.DONE or not job.filename:
            continue
        path = Path(job.filename)
        files: List[Path] = []
        try:
            if path.is_file() and path.suffix.lower() in AUDIO_EXT:
                files = [path]
            elif path.is_dir():
                files = sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXT)[:MAX_FILES_PER_JOB]
        except OSError:
            continue
        is_tidal = tidal.is_tidal_url(job.url)
        for f in files:
            key = str(f)
            if key in seen:
                continue
            seen.add(key)
            title, artist = split_name(f.stem, is_tidal, job.uploader)
            items.append({"kind": "track", "id": key, "title": title, "subtitle": artist, "cover": job.thumbnail or "",
                          "duration": 0, "file": key, "jobId": int(job.id), "source": job.title or "", "url": ""})
    return items


class LocalOwner(QObject):
    """What the player needs from the app (the same hooks as TidalBackend, no API)."""
    _KEYS = {"tidal_volume": "local_volume"}      # the local player has its own volume

    def __init__(self, backend):
        super().__init__(backend)
        self._backend = backend
        self.api = None

    def settings_value(self, key: str, default: Any = None) -> Any:
        try:
            return self._backend.settings.get(self._KEYS.get(key, key), default)
        except Exception:  # noqa: BLE001
            return default

    def save_setting(self, key: str, value: Any) -> None:
        self._backend.setSetting(self._KEYS.get(key, key), value)

    def request_single_playback(self) -> None:
        """This player starts: the web players and the TIDAL DIY player are paused (Settings: single playback)."""
        if not self.settings_value("single_playback", True):
            return
        self._backend.tidalDiyPlaying.emit()
        tidal_backend = getattr(self._backend, "tidal", None)
        if tidal_backend is not None:
            tidal_backend.player.pause()

    def submit(self, fn) -> None:
        fn()


class LocalPlayer(TidalPlayer):
    libraryChanged = Signal()

    def __init__(self, backend):
        super().__init__(LocalOwner(backend))
        self._backend = backend
        self._library: List[dict] = []
        self._decoder = None
        self._scan_pairs: list = []
        self._scan_t = 0                  # microseconds decoded so far
        self._scan_path = ""

    # -- library of finished downloads
    @Property("QVariantList", notify=libraryChanged)
    def library(self):  # type: ignore[override]
        return self._library

    @Slot()
    def refreshLibrary(self) -> None:
        self._library = library_items(self._backend._model.jobs())
        self.libraryChanged.emit()

    @Slot(int)
    def playLibrary(self, index: int) -> None:
        if 0 <= index < len(self._library):
            self.playItems(self._library, index, self._library[index].get("source") or "Downloads")

    @Slot(int)
    def playJob(self, job_id: int) -> None:
        """Play a finished download (the first file of it) and let the rest of the library follow."""
        self.refreshLibrary()
        for i, item in enumerate(self._library):
            if item.get("jobId") == job_id:
                self.playLibrary(i)
                return
        self._owner._backend.toast.emit("This download has no audio file to play.")

    # -- playing a file
    def _play_current(self) -> None:
        track = self.queue.item(self.queue.current)
        if not track or not self._ensure():
            return
        path = Path(str(track.get("file") or ""))
        if not path.is_file():
            self.error.emit("The file is not there any more: %s" % path.name)
            return
        self._owner.request_single_playback()
        self._want = str(track.get("id", ""))
        self._levels.clear()
        self._profile.reset()
        self.profileChanged.emit()
        self._loading = False
        self._badge = path.suffix.lstrip(".").upper()
        self._badge_tip = str(path)
        self._lyrics = {"text": "", "synced": []}
        self.lyricsChanged.emit()
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._player.play()
        self.changed.emit()
        self._scan(str(path))

    # -- loudness profile of the whole file, scanned in the background of the event loop
    def _scan(self, path: str) -> None:
        self._stop_scan()
        try:
            from PySide6.QtMultimedia import QAudioDecoder
        except ImportError:
            return
        self._scan_pairs, self._scan_t, self._scan_path = [], 0, path
        dec = QAudioDecoder(self)
        dec.setSource(QUrl.fromLocalFile(path))
        dec.bufferReady.connect(self._on_scan_buffer)
        dec.finished.connect(self._on_scan_done)
        self._decoder = dec
        dec.start()

    def _stop_scan(self) -> None:
        dec, self._decoder = self._decoder, None
        if dec is not None:
            try:
                dec.bufferReady.disconnect(self._on_scan_buffer)
                dec.finished.disconnect(self._on_scan_done)
                dec.stop()
            except (RuntimeError, TypeError):
                pass
            dec.deleteLater()

    def _on_scan_buffer(self) -> None:
        dec = self._decoder
        while dec is not None and dec.bufferAvailable():
            buf = dec.read()
            self._scan_pairs += pairs_of(buf, self._scan_t)
            rate = max(1, buf.format().sampleRate())
            self._scan_t += int(buf.frameCount() * 1_000_000 / rate)

    def _on_scan_done(self) -> None:
        pairs, path = self._scan_pairs, self._scan_path
        self._stop_scan()
        current = self.queue.item(self.queue.current) or {}
        if not pairs or str(current.get("file") or "") != path:       # the song changed meanwhile
            return
        duration_ms = (pairs[-1][0] + 1) * LEVEL_BUCKET_US / 1000.0
        self._profile.reset()
        self._profile.add(pairs, duration_ms)
        self._profile.dirty = False
        self.profileChanged.emit()

    @Slot()
    def stop(self) -> None:
        self._stop_scan()
        super().stop()
