"""TIDAL DIY (Yeal 0.9.1): Qt side of Yeal's own TIDAL view - page loading, library actions and the player.

QML sees one object, `tidal` (context property, set in main.py). API calls (core/tidal_api.py) run in worker
threads; results come back through queued signals, so workers never touch QML objects. Downloads go through the
normal Tidal job path of the main backend (Backend.addUrls -> tiddl).
"""
from __future__ import annotations

import math
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, List, Optional

from PySide6.QtCore import (Property, QAbstractListModel, QModelIndex, QObject, Qt, QTimer, QUrl, Signal,
                            Slot)
from PySide6.QtGui import QGuiApplication

from ..core import dsp, extras, tidal, tidal_api

LEVEL_BUCKET_US = 20000      # the level of the music is kept in 20 ms steps (matches the 30 Hz picture of the track player)


def buffer_levels(samples, channels: int, rate: int, start_us: int, scale: float) -> list:
    """[(bucket, level)] of one decoded audio buffer: 20 ms slices, level 0..1 from the RMS in dBFS (-48 dB = 0, 0 dB = 1).
    `samples` is a memoryview of the interleaved samples, `scale` the full-scale value of its type."""
    channels, rate = max(1, int(channels)), max(1, int(rate))
    per = max(1, int(rate * LEVEL_BUCKET_US / 1_000_000)) * channels
    out = []
    for a in range(0, len(samples), per):
        part = samples[a:a + per:7]               # every 7th sample is plenty for a level and keeps Python fast
        if not len(part):
            continue
        rms = math.sqrt(sum(float(x) * x for x in part) / len(part)) / scale
        db = 20.0 * math.log10(rms) if rms > 1e-5 else -100.0
        t = int(start_us) + int(a / channels / rate * 1_000_000)
        out.append((t // LEVEL_BUCKET_US, max(0.0, min(1.0, (db + 48.0) / 48.0))))
    return out


PROFILE_BINS = 240            # the loudness of a whole song in 240 steps (the band around the oval of the track player)


def pairs_of(buf, start_us=None) -> list:
    """[(bucket, level)] of a QAudioBuffer (see buffer_levels); [] for formats or buffers that cannot be read.
    start_us: where the buffer starts in the song when the buffer does not know it itself (a decoder)."""
    try:
        raw = buf.data()
        fmt = buf.format()
        code, scale = {"Int16": ("h", 32768.0), "Int32": ("i", 2147483648.0), "Float": ("f", 1.0)}.get(
            fmt.sampleFormat().name, (None, 1.0))
        if raw is None or code is None:
            return []
        return buffer_levels(memoryview(raw).cast("B").cast(code), fmt.channelCount(), fmt.sampleRate(),
                             int(buf.startTime()) if start_us is None else int(start_us), scale)
    except (TypeError, ValueError, AttributeError):
        return []


class SongProfile:
    """Loudness over the length of one song: PROFILE_BINS values 0..1, -1 where nothing was heard yet. It is filled
    while the song plays (or at once for a local file that is scanned) and drawn around the oval of the track player."""
    def __init__(self, bins: int = PROFILE_BINS):
        self.bins = bins
        self.reset()

    def reset(self) -> None:
        self._sum = [0.0] * self.bins
        self._count = [0] * self.bins
        self.dirty = False

    def add(self, pairs, duration_ms: float) -> bool:
        """Add (bucket, level) pairs of the 20 ms steps; duration_ms is the length of the song. True if something changed."""
        if not duration_ms or duration_ms <= 0:
            return False
        changed = False
        for bucket, level in pairs:
            i = int(bucket * LEVEL_BUCKET_US / 1000.0 / duration_ms * self.bins)
            if 0 <= i < self.bins:
                self._sum[i] += level
                self._count[i] += 1
                changed = True
        self.dirty = self.dirty or changed
        return changed

    def values(self) -> list:
        return [(s / c) if c else -1.0 for s, c in zip(self._sum, self._count)]


ROUTES = ("home", "explore", "feed", "mixes", "page", "more", "search", "album", "artist", "playlist", "mix",
          "favorites", "lyrics", "credits")


class QueueModel(QAbstractListModel):
    """The play queue. Rows can be moved (drag and drop), removed and inserted; `current` is the playing row."""
    _ROLES = ("kind", "itemId", "title", "subtitle", "cover", "duration", "quality", "url", "albumId", "artistId",
              "isCurrent")
    currentChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[dict] = []
        self._current = -1

    # -- Qt model
    def roleNames(self):
        return {Qt.UserRole + 1 + i: name.encode() for i, name in enumerate(self._ROLES)}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        name = self._ROLES[role - Qt.UserRole - 1] if Qt.UserRole < role <= Qt.UserRole + len(self._ROLES) else ""
        it = self._items[index.row()]
        if name == "isCurrent":
            return index.row() == self._current
        if name == "itemId":
            return it.get("id", "")
        return it.get(name, "" if name not in ("duration",) else 0)

    # -- state
    def items(self) -> List[dict]:
        return list(self._items)

    @property
    def current(self) -> int:
        return self._current

    def item(self, row: int) -> Optional[dict]:
        return self._items[row] if 0 <= row < len(self._items) else None

    def set_current(self, row: int) -> None:
        old, self._current = self._current, row if 0 <= row < len(self._items) else -1
        for r in {old, self._current}:
            if 0 <= r < len(self._items):
                idx = self.index(r)
                self.dataChanged.emit(idx, idx)
        self.currentChanged.emit()

    def reset(self, items: List[dict], current: int = 0) -> None:
        self.beginResetModel()
        self._items = [dict(i) for i in items if isinstance(i, dict) and i.get("kind") == "track"]
        self._current = current if 0 <= current < len(self._items) else (0 if self._items else -1)
        self.endResetModel()
        self.currentChanged.emit()

    def insert(self, row: int, items: List[dict]) -> None:
        items = [dict(i) for i in items if isinstance(i, dict) and i.get("kind") == "track"]
        if not items:
            return
        row = max(0, min(row, len(self._items)))
        self.beginInsertRows(QModelIndex(), row, row + len(items) - 1)
        self._items[row:row] = items
        if self._current >= row:
            self._current += len(items)
        self.endInsertRows()
        self.currentChanged.emit()

    def move(self, src: int, dst: int) -> bool:
        n = len(self._items)
        if not (0 <= src < n and 0 <= dst < n) or src == dst:
            return False
        # Qt wants the destination as "insert before" index in the old list
        if not self.beginMoveRows(QModelIndex(), src, src, QModelIndex(), dst + 1 if dst > src else dst):
            return False
        it = self._items.pop(src)
        self._items.insert(dst, it)
        cur = self._current
        if cur == src:
            cur = dst
        elif src < cur <= dst:
            cur -= 1
        elif dst <= cur < src:
            cur += 1
        self._current = cur
        self.endMoveRows()
        self.currentChanged.emit()
        return True

    def remove(self, row: int) -> bool:
        if not 0 <= row < len(self._items):
            return False
        self.beginRemoveRows(QModelIndex(), row, row)
        self._items.pop(row)
        if row < self._current:
            self._current -= 1
        elif row == self._current:
            self._current = min(self._current, len(self._items) - 1)
        self.endRemoveRows()
        self.currentChanged.emit()
        return True

    def replace_tail(self, items: List[dict]) -> None:
        """Replace everything after the current row (shuffle on / off)."""
        start = self._current + 1
        if start < len(self._items):
            self.beginRemoveRows(QModelIndex(), start, len(self._items) - 1)
            del self._items[start:]
            self.endRemoveRows()
        self.insert(start, items)


class TidalPlayer(QObject):
    """Internal player (QMediaPlayer + QAudioOutput, created on first use). The stream link is fetched right before
    playing because Tidal's links expire."""
    changed = Signal()            # state, current track, badge, shuffle/repeat
    positionChanged = Signal()
    lyricsChanged = Signal()
    levelChanged = Signal()       # level of the music (about 30 times a second while playing)
    profileChanged = Signal()     # the loudness profile of the song grew
    historyChanged = Signal()     # the list of played songs
    error = Signal(str)
    _streamReady = Signal(str, object, str)     # (track id, stream info or None, error)
    _lyricsReady = Signal(str, object)
    _groupReady = Signal(object, int)           # (tracks of dropped albums / playlists, row to insert at)

    def __init__(self, owner: "TidalBackend"):
        super().__init__(owner)
        self._owner = owner
        self.queue = QueueModel(self)
        self._player = None
        self._audio = None
        self._playing = False
        self._loading = False
        self._badge = ""
        self._badge_tip = ""
        self._source = ""            # "Played from: <playlist / album>"
        self._shuffle = False
        self._repeat = "off"         # off | all | one
        self._original: List[dict] = []   # order of the upcoming tracks before shuffling
        self._lyrics: dict = {"text": "", "synced": []}
        self._volume = int(owner.settings_value("tidal_volume", 80))
        self._want = ""              # track id whose stream is being fetched (late answers are ignored)
        self._now_source = ""        # "Played from" of titles dropped on the player
        self._abuf = None            # QAudioBufferOutput: decoded audio for the level
        self._engine_in_use = "qt"
        self._levels: dict = {}      # 20 ms bucket -> level 0..1
        self._level = 0.0
        self._last_buf = 0.0         # time of the last audio buffer (is the level real?)
        self._profile = SongProfile()
        self._history: list = []     # songs played in this session, newest first
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(33)
        self._tick_timer.timeout.connect(self._tick)
        self._streamReady.connect(self._on_stream)
        self._lyricsReady.connect(self._on_lyrics)
        self._groupReady.connect(self._on_group_ready)
        self.queue.currentChanged.connect(self.changed)

    # -- media objects
    def _ensure(self) -> bool:
        if self._player is not None:
            return True
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError:
            self.error.emit("Playback needs Qt Multimedia, which is missing in this installation.")
            return False
        media = self._make_dsp_media()
        if media is not None:                 # Yeal's own engine: ffmpeg -> float32 chain -> the chosen output
            self._engine_in_use = "dsp"
            self._audio = self._player = media
            media.setVolume(self._volume / 100.0)
            media.levels.connect(self._on_pairs)
            self._set_output_device()
        else:
            self._engine_in_use = "qt"
            self._audio = QAudioOutput(self)
            self._audio.setVolume(self._volume / 100.0)
            self._set_output_device()
            self._player = QMediaPlayer(self)
            self._player.setAudioOutput(self._audio)
        self._player.positionChanged.connect(lambda *_: self.positionChanged.emit())
        self._player.durationChanged.connect(lambda *_: self.positionChanged.emit())
        self._player.playbackStateChanged.connect(self._on_state)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.errorOccurred.connect(lambda _e, text: self.error.emit("Playback failed: " + text) if text else None)
        if self._engine_in_use == "qt":
            try:                          # the level of the music for the track player (Qt 6.8+); without it the level stays 0
                from PySide6.QtMultimedia import QAudioBufferOutput
                self._abuf = QAudioBufferOutput(self)
                self._player.setAudioBufferOutput(self._abuf)
                self._abuf.audioBufferReceived.connect(self._on_audio_buffer)
            except (ImportError, AttributeError):
                self._abuf = None
        return True

    # -- the engine: Qt's media player or Yeal's own (DspMedia)
    def _wanted_engine(self) -> str:
        pick = getattr(self._owner, "audio_engine", None)
        return pick() if callable(pick) else "qt"

    def _make_dsp_media(self):
        if self._wanted_engine() != "dsp":
            return None
        from . import dsp_media
        ffmpeg = getattr(self._owner, "ffmpeg_path", lambda: "")()
        if not dsp_media.usable(ffmpeg):
            self.error.emit("Yeal's own engine needs numpy and ffmpeg - playing with the standard engine.")
            return None
        media = dsp_media.DspMedia(ffmpeg, self)
        media.setConfig(dsp.config_from(getattr(self._owner, "dsp_config", lambda: {})()))
        return media

    @Slot()
    def applyDsp(self) -> None:
        """The filter settings changed: the running song goes on with the new filters."""
        if self._engine_in_use == "dsp" and self._player is not None:
            self._player.setConfig(dsp.config_from(getattr(self._owner, "dsp_config", lambda: {})()))

    @Slot()
    def applyEngine(self) -> None:
        """Another engine was chosen: playback stops; the next song starts with the new engine."""
        if self._player is None or self._wanted_engine() == self._engine_in_use:
            return
        self.stop()
        old, self._player, self._audio, self._abuf = self._player, None, None, None
        old.deleteLater()
        self.changed.emit()

    def _on_state(self, state) -> None:
        from PySide6.QtMultimedia import QMediaPlayer
        self._playing = state == QMediaPlayer.PlaybackState.PlayingState
        if self._playing:
            self._tick_timer.start()
        self.changed.emit()

    def _on_status(self, status) -> None:
        from PySide6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._advance(auto=True)

    def _set_output_device(self) -> None:
        """Play on the output chosen in the Speaker planet (Bluetooth headphones ...); the system default otherwise."""
        pick = getattr(self._owner, "audio_device", None)
        device = pick() if callable(pick) else None
        if device is not None and self._audio is not None:
            self._audio.setDevice(device)

    @Slot()
    def applyOutput(self) -> None:
        self._set_output_device()

    # -- properties
    @Property(bool, notify=changed)
    def playing(self) -> bool:  # type: ignore[override]
        return self._playing

    @Property(bool, notify=changed)
    def loading(self) -> bool:  # type: ignore[override]
        return self._loading

    @Property("QVariant", notify=changed)
    def current(self):  # type: ignore[override]
        return self.queue.item(self.queue.current) or {}

    @Property(int, notify=changed)
    def currentIndex(self) -> int:  # type: ignore[override]
        return self.queue.current

    @Property(QObject, constant=True)
    def queueModel(self):  # type: ignore[override]
        return self.queue

    @Property(str, notify=changed)
    def badge(self) -> str:  # type: ignore[override]
        return self._badge

    @Property(str, notify=changed)
    def badgeTip(self) -> str:  # type: ignore[override]
        return self._badge_tip

    @Property(str, notify=changed)
    def source(self) -> str:  # type: ignore[override]
        return self._source

    @Property(bool, notify=changed)
    def shuffle(self) -> bool:  # type: ignore[override]
        return self._shuffle

    @Property(str, notify=changed)
    def repeat(self) -> str:  # type: ignore[override]
        return self._repeat

    @Property(int, notify=changed)
    def volume(self) -> int:  # type: ignore[override]
        return self._volume

    @Property("QVariantList", notify=historyChanged)
    def history(self):  # type: ignore[override]
        return self._history

    def _note_played(self, track: dict) -> None:
        """A song starts: it goes to the top of the list of played songs (the same song twice in a row only once)."""
        if not track:
            return
        if self._history and self._history[0].get("id") == track.get("id"):
            return
        self._history = [dict(track)] + [t for t in self._history if t.get("id") != track.get("id")][:49]
        self.historyChanged.emit()

    @Slot(int)
    def playHistory(self, index: int) -> None:
        """Play a song of the list again; it becomes the queue (the rest of the list follows)."""
        if 0 <= index < len(self._history):
            self.playItems(self._history, index, "Played")

    @Property("QVariantList", notify=profileChanged)
    def profile(self):  # type: ignore[override]
        return self._profile.values()

    @Property(float, notify=levelChanged)
    def level(self) -> float:  # type: ignore[override]
        return self._level

    @Property(bool, notify=levelChanged)
    def levelLive(self) -> bool:  # type: ignore[override]
        """True while real audio data arrives (False: no level is known, the picture must not pretend one)."""
        return self._playing and time.monotonic() - self._last_buf < 1.5

    @Property(int, notify=positionChanged)
    def position(self) -> int:  # type: ignore[override]
        return int(self._player.position()) if self._player else 0

    @Property(int, notify=positionChanged)
    def duration(self) -> int:  # type: ignore[override]
        if self._player and self._player.duration() > 0:
            return int(self._player.duration())
        return int((self.queue.item(self.queue.current) or {}).get("duration", 0)) * 1000

    @Property("QVariant", notify=lyricsChanged)
    def lyrics(self):  # type: ignore[override]
        return self._lyrics

    # -- queue building
    @Slot("QVariantList", int, str)
    def playItems(self, items, index: int, source: str = "") -> None:
        """Replace the queue with `items` and play row `index` (the rest follows)."""
        tracks = [i for i in (items or []) if isinstance(i, dict) and i.get("kind") == "track"]
        if not tracks:
            return
        pick = items[index] if 0 <= index < len(items) else tracks[0]
        start = tracks.index(pick) if pick in tracks else 0
        self._source = source or ""
        self.queue.reset(tracks, start)
        self._original = []
        if self._shuffle:
            self._shuffle_tail()
        self._play_current()

    @Slot("QVariantList", str)
    def shuffleItems(self, items, source: str = "") -> None:
        tracks = [i for i in (items or []) if isinstance(i, dict) and i.get("kind") == "track"]
        if not tracks:
            return
        self._shuffle = True
        random.shuffle(tracks)
        self.playItems(tracks, 0, source)

    def _insert_tracks(self, tracks, row: int) -> None:
        tracks = [t for t in tracks or [] if isinstance(t, dict) and t.get("kind") == "track"]
        if not tracks:
            return
        empty = self.queue.rowCount() == 0
        at = self.queue.rowCount() if row < 0 or row > self.queue.rowCount() else row
        self.queue.insert(at, tracks)
        if empty:
            self.playIndex(0)

    PLAY_NOW = -2                    # "row" of _groupReady: play the titles at once instead of queueing them

    def _on_group_ready(self, tracks, row: int) -> None:
        if row == self.PLAY_NOW:
            if tracks:
                self.playItems(tracks, 0, self._now_source)
        else:
            self._insert_tracks(tracks, row)

    def _titles_of(self, items, row: int) -> None:
        """Albums, playlists and mixes bring their titles (fetched in the background); `row` is handed on."""
        api = self._owner.api

        def work():
            tracks = []
            for it in items:
                kind, item_id = it.get("kind"), str(it.get("id", ""))
                try:
                    if kind == "track":
                        tracks.append(it)
                    elif kind in ("album", "playlist", "mix"):
                        tracks += [t for t in getattr(api, kind)(item_id).get("items", []) if t.get("kind") == "track"]
                except tidal_api.TidalError:
                    continue
            self._groupReady.emit(tracks, row)
        self._owner.submit(work)

    @Slot("QVariantList", int)
    def enqueue(self, items, row: int = -1) -> None:
        """Put titles into the queue at `row` (-1 = at the end), e.g. dragged there. Albums, playlists and mixes bring
        their titles (fetched in the background); on an empty queue the first title starts."""
        items = [i for i in (items or []) if isinstance(i, dict)]
        if not any(i.get("kind") in ("album", "playlist", "mix") for i in items):
            self._insert_tracks(items, row)
            return
        self._titles_of(items, row)

    @Slot("QVariantList")
    def playNow(self, items) -> None:
        """Play dragged titles at once (dropped on the player): they replace the queue, the first one starts."""
        items = [i for i in (items or []) if isinstance(i, dict)]
        group = next((i for i in items if i.get("kind") in ("album", "playlist", "mix")), None)
        self._now_source = str((group or {}).get("title") or "")
        if group is None:
            tracks = [i for i in items if i.get("kind") == "track"]
            if tracks:
                self.playItems(tracks, 0, "")
            return
        self._titles_of(items, self.PLAY_NOW)

    @Slot("QVariantList")
    def queueNext(self, items) -> None:
        self.queue.insert(self.queue.current + 1, list(items or []))
        if self.queue.current < 0 and self.queue.rowCount():
            self.playIndex(0)

    @Slot("QVariantList")
    def queueAdd(self, items) -> None:
        empty = self.queue.rowCount() == 0
        self.queue.insert(self.queue.rowCount(), list(items or []))
        if empty and self.queue.rowCount():
            self.playIndex(0)

    @Slot(int, int)
    def move(self, src: int, dst: int) -> None:
        self.queue.move(src, dst)

    @Slot(int)
    def removeAt(self, row: int) -> None:
        playing_removed = row == self.queue.current
        self.queue.remove(row)
        if playing_removed:
            if self.queue.rowCount():
                self._play_current()
            else:
                self.stop()

    @Slot()
    def clearUpcoming(self) -> None:
        self.queue.replace_tail([])
        self._original = []

    # -- transport
    @Slot(int)
    def playIndex(self, row: int) -> None:
        if self.queue.item(row):
            self.queue.set_current(row)
            self._play_current()

    @Slot()
    def toggle(self) -> None:
        if not self._player or self.queue.current < 0:
            if self.queue.rowCount():
                self.playIndex(max(0, self.queue.current))
            return
        if self._playing:
            self._player.pause()
        else:
            self._player.play()

    @Slot()
    def pause(self) -> None:
        if self._player and self._playing:
            self._player.pause()

    @Slot()
    def stop(self) -> None:
        if self._player:
            self._player.stop()
        self._playing = False
        self.changed.emit()

    @Slot()
    def next(self) -> None:
        self._advance(auto=False)

    @Slot()
    def previous(self) -> None:
        if self._player and self._player.position() > 3000:
            self._player.setPosition(0)
            return
        if self.queue.current > 0:
            self.playIndex(self.queue.current - 1)
        elif self._player:
            self._player.setPosition(0)

    @Slot(int)
    def seek(self, ms: int) -> None:
        if self._player:
            self._player.setPosition(max(0, int(ms)))

    @Slot(int)
    def setVolume(self, value: int) -> None:
        self._volume = max(0, min(100, int(value)))
        if self._audio:
            self._audio.setVolume(self._volume / 100.0)
        self._owner.save_setting("tidal_volume", self._volume)
        self.changed.emit()

    @Slot()
    def toggleShuffle(self) -> None:
        self._shuffle = not self._shuffle
        if self._shuffle:
            self._shuffle_tail()
        elif self._original:
            # back to the order from before shuffling, for the tracks that are still upcoming (tracks added while
            # shuffling stay at the end)
            upcoming = self.queue.items()[self.queue.current + 1:]
            left = [t.get("id") for t in upcoming]
            restored = []
            for t in self._original:
                if t.get("id") in left:
                    left.remove(t.get("id"))
                    restored.append(t)
            added = [t for t in upcoming if t.get("id") in left]
            self.queue.replace_tail(restored + added)
            self._original = []
        self.changed.emit()

    @Slot()
    def cycleRepeat(self) -> None:
        self._repeat = {"off": "all", "all": "one", "one": "off"}[self._repeat]
        self.changed.emit()

    def _shuffle_tail(self) -> None:
        upcoming = self.queue.items()[self.queue.current + 1:]
        self._original = list(upcoming)
        random.shuffle(upcoming)
        self.queue.replace_tail(upcoming)

    def _advance(self, auto: bool) -> None:
        n = self.queue.rowCount()
        if not n:
            return
        cur = self.queue.current
        if auto and self._repeat == "one":
            self.playIndex(cur)
        elif cur + 1 < n:
            self.playIndex(cur + 1)
        elif self._repeat == "all" or not auto:
            if self._repeat == "all":
                self.playIndex(0)
            else:
                self.stop()
        else:
            self.stop()

    def _play_current(self) -> None:
        track = self.queue.item(self.queue.current)
        if not track or not self._ensure():
            return
        self._owner.request_single_playback()
        self._want = str(track.get("id", ""))
        self._levels.clear()
        self._profile.reset()
        self.profileChanged.emit()
        self._note_played(track)
        self._loading = True
        self._badge, self._badge_tip = "", ""
        self._lyrics = {"text": "", "synced": []}
        self.lyricsChanged.emit()
        self.changed.emit()
        want = self._want
        api = self._owner.api

        def work():
            try:
                info = api.stream(want, "HI_RES_LOSSLESS")
                self._streamReady.emit(want, info, "")
            except tidal_api.TidalError as exc:
                self._streamReady.emit(want, None, str(exc))
            try:
                self._lyricsReady.emit(want, api.lyrics(want))
            except tidal_api.TidalError:
                self._lyricsReady.emit(want, {"text": "", "synced": []})
        self._owner.submit(work)

    def _on_audio_buffer(self, buf) -> None:
        self._on_pairs(pairs_of(buf))

    def _on_pairs(self, pairs) -> None:
        """Levels of the music (from Qt's audio buffers, or from the blocks of Yeal's own engine)."""
        if not pairs:
            return
        for bucket, level in pairs:
            self._levels[bucket] = level
        self._profile.add(pairs, self.duration)
        if len(self._levels) > 240:
            for key in sorted(self._levels)[:-150]:
                del self._levels[key]
        self._last_buf = time.monotonic()

    def _tick(self) -> None:
        """The level at the playing position, with a quick rise and a soft fall."""
        target = 0.0
        if self._playing and self._player:
            bucket = int(self._player.position()) * 1000 // LEVEL_BUCKET_US
            known = [self._levels[k] for k in (bucket - 1, bucket, bucket + 1) if k in self._levels]
            target = max(known) if known else 0.0
        if self._profile.dirty:
            self._profile.dirty = False
            self.profileChanged.emit()
        new = max(target, self._level * 0.85)
        if new < 0.01:
            new = 0.0
        if new != self._level:
            self._level = new
            self.levelChanged.emit()
        if not self._playing and new == 0.0:
            self._tick_timer.stop()

    def _on_stream(self, track_id: str, info, err: str) -> None:
        if track_id != self._want:
            return
        self._loading = False
        if not info:
            self.changed.emit()
            self.error.emit(err or "This track cannot be played.")
            return
        self._badge = info.get("badge", "")
        self._badge_tip = ("Played in CD quality; Tidal does not send Hi-Res for playing with this sign-in. "
                           "Downloads still use the quality chosen in TIDAL options.") if info.get("downgraded") else \
            "Quality that is playing now"
        self._player.setSource(QUrl(info["url"]))
        if self._engine_in_use == "dsp":                       # Tidal's own loudness value of the song (for ReplayGain)
            self._player.setReplayGain(info.get("replayGain") or 0.0)
        self._player.play()
        self.changed.emit()

    def _on_lyrics(self, track_id: str, data) -> None:
        if track_id == self._want:
            self._lyrics = data or {"text": "", "synced": []}
            self.lyricsChanged.emit()


class TidalBackend(QObject):
    pageLoaded = Signal(str, str, "QVariant")     # (request id, route, data)
    pageFailed = Signal(str, str, str)            # (request id, route, message)
    playlistsChanged = Signal()
    dragPayloadChanged = Signal()
    favoritesChanged = Signal()
    signedInChanged = Signal()
    _done = Signal(str, str, object, str)         # worker -> GUI thread: (request id, route, data, error)
    _sideDone = Signal(str, object)               # worker -> GUI thread: (what, data)

    def __init__(self, backend, api: Optional[tidal_api.TidalApi] = None, parent: Optional[QObject] = None):
        super().__init__(parent or backend)
        self._backend = backend
        self._api = api
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="yeal-tidal")
        self._playlists: List[dict] = []
        self._fav: dict = {}
        self._done.connect(self._on_done)
        self._sideDone.connect(self._on_side)
        self._drag: list = []
        self.player = TidalPlayer(self)
        self.player.error.connect(self.toast)
        backend.tidalChanged.connect(self._on_login_changed)

    # -- helpers used by the player and tests
    @property
    def api(self) -> tidal_api.TidalApi:
        if self._api is None:
            self._api = tidal_api.TidalApi()
        return self._api

    def submit(self, fn) -> None:
        self._pool.submit(fn)

    def settings_value(self, key: str, default: Any = None) -> Any:
        try:
            return self._backend.settings.get(key, default)
        except Exception:  # noqa: BLE001
            return default

    def save_setting(self, key: str, value: Any) -> None:
        self._backend.setSetting(key, value)

    def audio_device(self):
        return self._backend.audio_device()

    def audio_engine(self) -> str:
        return self._backend.audio_engine()

    def dsp_config(self) -> dict:
        return self._backend.dsp_config()

    def ffmpeg_path(self) -> str:
        return self._backend.ffmpeg_path()

    def request_single_playback(self) -> None:
        """The own player starts: the embedded web players are paused (Settings: single playback)."""
        self._backend.tidalDiyPlaying.emit()
        local = getattr(self._backend, "localPlayer", None)      # ... and the player for downloaded files
        if local is not None:
            local.pause()

    def toast(self, message: str) -> None:
        if message:
            self._backend.toast.emit(message)

    def shutdown(self) -> None:
        self.player.stop()
        self._pool.shutdown(wait=False, cancel_futures=True)

    # -- sign-in
    @Property(bool, notify=signedInChanged)
    def signedIn(self) -> bool:  # type: ignore[override]
        return tidal.is_logged_in()

    def _on_login_changed(self) -> None:
        if self._api is not None:
            self._api.auth.load()
            self._api.clear_cache()
        self.signedInChanged.emit()
        if tidal.is_logged_in():
            self.refreshLibrary()

    # -- loading pages
    @Slot(str, str, result=str)
    def load(self, route: str, arg: str = "") -> str:
        """Start loading a page; the answer comes as pageLoaded(id, route, data) or pageFailed(id, route, message)."""
        rid = uuid.uuid4().hex[:10]
        if route not in ROUTES:
            QTimer.singleShot(0, lambda: self.pageFailed.emit(rid, route, "Unknown page"))
            return rid

        def work():
            try:
                self._done.emit(rid, route, self._fetch(route, arg), "")
            except tidal_api.TidalError as exc:
                self._done.emit(rid, route, None, str(exc))
            except Exception as exc:  # noqa: BLE001 - never let a worker die silently
                self._done.emit(rid, route, None, "Unexpected error: %s" % exc)
        self.submit(work)
        return rid

    def _fetch(self, route: str, arg: str):
        api = self.api
        if route == "home":
            return api.home()
        if route == "explore":
            return api.explore()
        if route == "page":
            return api.page(arg)
        if route == "more":
            return api.more(arg)
        if route == "feed":
            return api.feed()
        if route == "mixes":
            return api.my_mixes()
        if route == "search":
            return api.search(arg)
        if route == "album":
            return api.album(arg)
        if route == "artist":
            return api.artist(arg)
        if route == "playlist":
            return api.playlist(arg)
        if route == "mix":
            return api.mix(arg)
        if route == "favorites":
            return api.user_playlists() if arg == "playlists" else api.favorites(arg)
        if route == "lyrics":
            return api.lyrics(arg)
        if route == "credits":
            return api.album_credits(arg)
        raise tidal_api.TidalError("Unknown page")

    def _on_done(self, rid: str, route: str, data, err: str) -> None:
        if err:
            self.pageFailed.emit(rid, route, err)
        else:
            self.pageLoaded.emit(rid, route, data)

    # -- library: playlists and favorites
    @Property("QVariantList", notify=playlistsChanged)
    def playlists(self):  # type: ignore[override]
        return self._playlists

    @Property("QVariantList", notify=playlistsChanged)
    def myPlaylists(self):  # type: ignore[override]
        return [p for p in self._playlists if p.get("mine")]

    @Slot()
    def refreshLibrary(self) -> None:
        if not tidal.is_logged_in():
            return

        def work():
            try:
                self._sideDone.emit("playlists", self.api.user_playlists())
            except tidal_api.TidalError as exc:
                self._sideDone.emit("error", "Tidal playlists: %s" % exc)
            try:
                self._sideDone.emit("favorites", self.api.favorite_ids())
            except tidal_api.TidalError:
                pass
        self.submit(work)

    def _on_side(self, what: str, data) -> None:
        if what == "playlists":
            self._playlists = list(data or [])
            self.playlistsChanged.emit()
        elif what == "favorites":
            self._fav = {k: set(v) for k, v in (data or {}).items()}
            self.favoritesChanged.emit()
        elif what == "error":
            self.toast(str(data))
        elif what == "toast":
            self.toast(str(data))
        elif what == "reload":
            self.refreshLibrary()

    @Slot(str, str, result=bool)
    def isFavorite(self, kind: str, item_id: str) -> bool:
        return str(item_id) in self._fav.get(kind, set())

    @Slot(str, str)
    def toggleFavorite(self, kind: str, item_id: str) -> None:
        item_id = str(item_id)
        was = self.isFavorite(kind, item_id)
        bucket = self._fav.setdefault(kind, set())
        (bucket.discard if was else bucket.add)(item_id)      # show the new state at once
        self.favoritesChanged.emit()

        def work():
            try:
                (self.api.remove_favorite if was else self.api.add_favorite)(kind, item_id)
                self._sideDone.emit("toast", "Removed from your collection." if was else "Added to your collection.")
                if kind == "playlist":
                    self._sideDone.emit("reload", None)
            except (tidal_api.TidalError, KeyError) as exc:
                self._sideDone.emit("error", "Favorite not changed: %s" % exc)
                self._sideDone.emit("reload", None)
        self.submit(work)

    def _write(self, action, done: str, reload: bool = True) -> None:
        def work():
            try:
                action()
                self._sideDone.emit("toast", done)
            except tidal_api.TidalError as exc:
                self._sideDone.emit("error", str(exc))
            if reload:
                self._sideDone.emit("reload", None)
        self.submit(work)

    @Slot(str, "QVariantList")
    def createPlaylist(self, title: str, track_ids=None) -> None:
        title = (title or "").strip()[:100]
        if not title:
            self.toast("Enter a name for the playlist.")
            return
        ids = [str(t) for t in (track_ids or [])]

        def action():
            new = self.api.create_playlist(title)
            if ids:
                self.api.add_to_playlist(new["id"], ids)
        self._write(action, "Playlist \"%s\" created." % title)

    @Slot(str, str)
    def renamePlaylist(self, uuid_: str, title: str) -> None:
        title = (title or "").strip()[:100]
        if title:
            self._write(lambda: self.api.rename_playlist(uuid_, title), "Playlist renamed.")

    @Slot(str)
    def deletePlaylist(self, uuid_: str) -> None:
        self._write(lambda: self.api.delete_playlist(uuid_), "Playlist deleted.")

    @Slot(str, "QVariantList")
    def addToPlaylist(self, uuid_: str, track_ids) -> None:
        ids = [str(t) for t in (track_ids or [])]
        if ids:
            self._write(lambda: self.api.add_to_playlist(uuid_, ids),
                        "%d title(s) added to the playlist." % len(ids))

    @Slot(str, "QVariantList")
    def removeFromPlaylist(self, uuid_: str, indices) -> None:
        rows = [int(i) for i in (indices or [])]
        if rows:
            self._write(lambda: self.api.remove_from_playlist(uuid_, rows),
                        "%d title(s) removed from the playlist." % len(rows))

    @Slot(str)
    def saveQueueAsPlaylist(self, title: str) -> None:
        self.createPlaylist(title, [t.get("id") for t in self.player.queue.items()])

    # -- downloads, links, link lists
    @Slot("QVariantList", result=int)
    def download(self, urls) -> int:
        links = [str(u) for u in (urls or []) if tidal.is_tidal_url(str(u))]
        if not links:
            return 0
        return self._backend.addUrls("\n".join(links))

    @Slot(str)
    def copyLink(self, url: str) -> None:
        QGuiApplication.clipboard().setText(url or "")
        self.toast("Link copied.")

    @Slot(str, str)
    def saveLinklist(self, kind: str, item_id: str) -> None:
        """Playlist / album / mix -> HTML page with Tidal links (no download): <download folder>/Tidal/Linklisten."""
        folder = Path(self._backend.settings.get("download_dir") or ".") / "Tidal" / "Linklisten"

        def work():
            try:
                info = {"playlist": self.api.playlist, "album": self.api.album, "mix": self.api.mix}[kind](item_id)
            except (tidal_api.TidalError, KeyError) as exc:
                self._sideDone.emit("error", "Link list not saved: %s" % exc)
                return
            page = extras.write_tidal_linklist(folder, info)
            self._sideDone.emit("toast", "Link list saved: %s" % page if page else "Link list could not be written.")
        self.submit(work)

    @Slot("QVariantList")
    def saveLinklists(self, items) -> None:
        for it in items or []:
            if isinstance(it, dict) and it.get("kind") in ("playlist", "album", "mix"):
                self.saveLinklist(it["kind"], str(it.get("id", "")))

    # -- drag and drop inside the view: what is being dragged (the drop target on the queue needs the real titles)
    @Property("QVariantList", notify=dragPayloadChanged)
    def dragPayload(self):  # type: ignore[override]
        return self._drag

    @Slot("QVariantList")
    def setDragPayload(self, items) -> None:
        self._drag = [dict(i) for i in (items or []) if isinstance(i, dict) and i.get("kind")]
        self.dragPayloadChanged.emit()

    @Property(QObject, constant=True)
    def playerObject(self):  # type: ignore[override]
        return self.player
