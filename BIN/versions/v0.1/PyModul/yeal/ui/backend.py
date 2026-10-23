"""Qt bridge: exposes the download queue and settings to QML."""
from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any, List

from PySide6.QtCore import (Property, QAbstractListModel, QModelIndex, QObject,
                            QSortFilterProxyModel, Qt, QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import QGuiApplication

from .. import __version__, platforms
from ..core.engine import Engine, fmt_size
from ..core.models import DownloadJob, JobState
from ..core.presets import compress_items, is_playlist_url, media_dir, normalize_proxy, sanitize_custom_options
from ..core.queue import DownloadQueue
from ..core import frames as framelib
from ..core import audioprobe, history, localserve, mp3tags, updater, vault as vaultlib
from ..core.presets import build_ydl_opts
from ..core.settings import HTML_OPEN_MODES, THEMES, Settings

def _extras_text(job: DownloadJob) -> str:
    """Short status of the optional description / transcript files."""
    parts = []
    for label, want, have, saved in (
            ("Description", job.options.save_description, job.has_description, job.saved_description),
            ("Transcript", job.options.save_transcript, job.has_transcript, job.saved_transcript)):
        if saved:
            parts.append(f"{label} saved")
        elif want and job.state.finished and job.state.value == "done":
            parts.append(f"No {label.lower()} available")
        elif have and not want:
            parts.append(f"{label} available")
    return "  ·  ".join(parts)


def _fmt_rate(bps: float) -> str:
    from ..core.engine import fmt_speed
    return fmt_speed(bps)


def _webview_importable() -> bool:
    try:
        import PySide6.QtWebView  # noqa: F401
        return True
    except ImportError:
        return False


_URL = re.compile(r"https?://\S+", re.IGNORECASE)


class JobModel(QAbstractListModel):
    """Newest job first. Rows are plain DownloadJob snapshots."""

    _ROLES = ["jobId", "url", "title", "jobState", "progress", "speed", "eta",
              "error", "filename", "playlistText", "thumbnail", "uploader", "duration",
              "size", "profile", "kind", "mode", "extrasText", "phase", "hasPage", "dlProgress", "ppProgress", "convLabel", "note", "errorDetail", "section"]

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._jobs: List[DownloadJob] = []
        self._role_ids = {Qt.ItemDataRole.UserRole + 1 + i: name.encode()
                          for i, name in enumerate(self._ROLES)}

    def roleNames(self):  # noqa: N802 (Qt API)
        return self._role_ids

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._jobs)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._jobs)):
            return None
        job = self._jobs[index.row()]
        name = self._role_ids.get(role)
        if name is None:
            return None
        key = name.decode()
        if key == "section":
            return history.section_label(job.created)
        if key == "errorDetail":
            return job.error_detail
        if key == "jobId":
            return job.id
        if key == "jobState":
            return job.state.value
        if key == "title":
            return job.title or job.url
        if key == "extrasText":
            return _extras_text(job)
        if key == "dlProgress":
            return job.dl_progress
        if key == "ppProgress":
            return job.pp_progress
        if key == "convLabel":
            fmt = job.options.audio_format
            if job.options.mode == "audio":
                return "Creating " + fmt.upper() if fmt != "best" else "Finishing file"
            return "Creating video file"
        if key == "hasPage":
            return bool(job.saved_description and job.state.value == "done")
        if key == "kind":
            return job.state.kind
        if key == "profile":
            return job.options.profile
        if key == "mode":
            return job.options.mode
        if key == "playlistText":
            return (f"{job.playlist_index}/{job.playlist_count}"
                    if job.playlist_count > 1 else "")
        return getattr(job, key)

    def upsert(self, job: DownloadJob) -> None:
        for row, existing in enumerate(self._jobs):
            if existing.id == job.id:
                self._jobs[row] = job
                idx = self.index(row)
                self.dataChanged.emit(idx, idx)
                return
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._jobs.insert(0, job)
        self.endInsertRows()

    def remove(self, job_id: int) -> None:
        for row, existing in enumerate(self._jobs):
            if existing.id == job_id:
                self.beginRemoveRows(QModelIndex(), row, row)
                del self._jobs[row]
                self.endRemoveRows()
                return

    def get(self, job_id: int) -> DownloadJob | None:
        return next((j for j in self._jobs if j.id == job_id), None)

    def jobs(self) -> List[DownloadJob]:
        return list(self._jobs)


class JobFilterModel(QSortFilterProxyModel):
    """Filters the job list by group (all|active|queued|done|failed) and a search text."""

    def __init__(self, source: JobModel, parent: QObject | None = None):
        super().__init__(parent)
        self._group = "all"
        self._text = ""
        self._collapsed: set = set()
        self.setSourceModel(source)
        self.setDynamicSortFilter(True)

    def _set(self, group: str | None = None, text: str | None = None) -> None:
        self.beginFilterChange()
        if group is not None:
            self._group = group
        if text is not None:
            self._text = text.strip().lower()
        self.endFilterChange()

    @Slot(str)
    def setGroup(self, group: str) -> None:
        if group in ("all", "active", "queued", "done", "failed"):
            self._set(group=group)

    @Slot(str)
    def setSearch(self, text: str) -> None:
        self._set(text=text)

    def set_collapsed(self, names) -> None:
        self.beginFilterChange()
        self._collapsed = set(names)
        self.endFilterChange()

    def _basic(self, job) -> bool:
        if self._group != "all" and job.state.kind != self._group:
            return False
        if self._text:
            return self._text in f"{job.title} {job.url} {job.uploader}".lower()
        return True

    def filterAcceptsRow(self, row: int, parent: QModelIndex) -> bool:  # noqa: N802
        jobs = self.sourceModel()._jobs
        job = jobs[row]
        if not self._basic(job):
            return False
        if self._collapsed:
            section = history.section_label(job.created)
            if section in self._collapsed:
                # a collapsed group keeps one (hidden) row so that its header stays visible
                return not any(history.section_label(j.created) == section and self._basic(j) for j in jobs[:row])
        return True


class Backend(QObject):
    # Emitted from worker threads; Qt queues them onto the GUI thread.
    _jobChanged = Signal(object)
    _jobRemoved = Signal(int)
    _updateFinished = Signal(str, str)   # (version, message); message '' = nothing to report
    settingsChanged = Signal()
    ytdlpChanged = Signal()
    statsChanged = Signal()
    framesChanged = Signal()
    filmstripReady = Signal(str, float, list, str)   # (video path, duration s, [image urls], error); duration 0 = failed
    framesDone = Signal(int, str, str)   # (image count, folder, error) - the dialog shows the result
    libraryThumb = Signal(str, str)   # (video path, thumbnail url)
    _framesFinished = Signal(int, str, str)   # (count, folder, error)
    _audioProbed = Signal(str, object)        # (url, probe result) from the worker thread
    vaultChanged = Signal()                   # locked/unlocked/entries changed
    tracklistFound = Signal(str, int)         # (url, tracks): the description has a tracklist -> suggest an album
    externalDrive = Signal(dict)              # {root,label,free,total,id,folder} -> offer it as download target
    _drivesFound = Signal(list)
    _tracklistProbed = Signal(str, int)
    duplicateFound = Signal(dict)             # {url, title, date, mode, jobId} -> ask: download again?
    playlistChoice = Signal(dict)             # {url, title, uploader, entries}: pick the items of a playlist
    _playlistProbed = Signal(str, object)
    liveChoice = Signal(dict)                 # {url, title, thumbnail}: the link is a live stream -> ask record/duration
    audioChoice = Signal(dict)                # {url, title, thumbnail, best, choices} -> dialog
    tagsPrompt = Signal(dict)                 # {jobId, title}: an MP3 was tagged automatically -> ask: edit the tags?
    toast = Signal(str)

    def __init__(self, ctx: platforms.PlatformInfo, engine: Engine | None = None,
                 parent: QObject | None = None, check_updates: bool = True):
        super().__init__(parent)
        self._ctx = ctx
        ctx.ensure_dirs()
        self._settings = Settings.load(ctx.settings_path)
        self._default_download_dir = ctx.download_dir
        self._apply_download_dir()
        self._model = JobModel(self)
        self._filtered = JobFilterModel(self._model, self)
        self._jobChanged.connect(self._model.upsert)
        self._jobRemoved.connect(self._model.remove)
        for sig in (self._model.rowsInserted, self._model.rowsRemoved, self._model.dataChanged):
            sig.connect(lambda *_: self.statsChanged.emit())
        self._updateFinished.connect(self._on_update_finished)
        self._framesFinished.connect(self._on_frames_finished)
        self._audioProbed.connect(self._on_audio_probed)
        self._playlistProbed.connect(self._on_playlist_probed)
        self._playlist_totals: dict = {}      # url -> number of listed entries (to tell "all" from a pick)
        self._probe_options: dict = {}   # url -> DownloadOptions waiting for the user's choice
        self._probe = audioprobe.probe   # injectable for tests
        # embedded browser: Windows only, needs QtWebView (WebView2 plugin shipped with PySide6)
        self._browser_ok = ctx.name == "windows" and _webview_importable()
        self._frames_busy = False
        self._updating = False
        self._engine = engine or Engine(ctx)
        self._queue = DownloadQueue(
            self._engine.run, self._settings.max_parallel,
            on_change=self._jobChanged.emit, on_remove=self._jobRemoved.emit)
        self._tracklist_seen: dict = {}      # url -> track count (0 = none), checked once per url
        self._drive_mask = None
        self._drive_offered: set = set()      # offered in this session (asked once per drive and start)
        self._drive_busy = False
        self._drivesFound.connect(self._on_drives)
        self._tracklistProbed.connect(self._on_tracklist)
        if not ctx.is_mobile:
            self._drive_timer = QTimer(self)
            self._drive_timer.setInterval(4000)
            self._drive_timer.timeout.connect(self._poll_drives)
            self._drive_timer.start()
            QTimer.singleShot(2500, self._poll_drives)
        self._history_path = ctx.data_dir / "history.json"
        self._dup_pending: dict = {}      # url -> options waiting for the user's answer
        self._history_timer = QTimer(self)
        self._history_timer.setSingleShot(True)
        self._history_timer.setInterval(1200)
        self._history_timer.timeout.connect(self._save_history)
        self._jobChanged.connect(lambda job: job.state.finished and self._history_timer.start())
        self._tags_asked: set = set()     # job ids that already got the "edit the MP3 tags?" question
        self._jobChanged.connect(self._ask_tags)
        self._jobRemoved.connect(lambda _id: self._history_timer.start())
        self._filtered.setGroup(self._settings.list_group)
        self._filtered.set_collapsed(self._settings.ui_collapsed)
        self._queue.restore(history.load(self._history_path))     # finished downloads of earlier sessions
        updater.activate(self._ctx.data_dir)
        if check_updates and self._settings.auto_update and updater.should_check(self._ctx.data_dir):
            self._start_update(silent=True)

    # ---- properties -----------------------------------------------------
    @Property(QObject, constant=True)
    def model(self) -> QObject:  # type: ignore[override]
        return self._model

    @Property(QObject, constant=True)
    def filteredModel(self) -> QObject:  # type: ignore[override]
        return self._filtered

    @Property("QVariantMap", notify=statsChanged)
    def stats(self) -> dict:  # type: ignore[override]
        counts = {"all": 0, "active": 0, "queued": 0, "done": 0, "failed": 0}
        speed = 0.0
        running = []
        for job in self._model.jobs():
            counts["all"] += 1
            counts[job.state.kind] += 1
            speed += job.speed_bps
            if job.state.kind in ("active", "queued"):
                running.append(job.progress)
        counts["progress"] = sum(running) / len(running) if running else -1.0
        counts["speed"] = _fmt_rate(speed) if speed else ""
        return counts

    @Property("QVariantMap", notify=settingsChanged)
    def settings(self) -> dict:  # type: ignore[override]
        data = asdict(self._settings)
        data["custom_options"] = json.dumps(self._settings.custom_options, indent=2) \
            if self._settings.custom_options else ""
        data["download_dir"] = str(self._ctx.download_dir)
        data["profile_names"] = self._settings.profile_names()
        data["active_mode"] = self._settings.get_profile()["mode"]
        return data

    @Property(bool, notify=framesChanged)
    def framesBusy(self) -> bool:  # type: ignore[override]
        return self._frames_busy

    @Property(str, notify=ytdlpChanged)
    def ytdlpVersion(self) -> str:  # type: ignore[override]
        return updater.installed_version(self._ctx.data_dir) or "-"

    @Property(bool, notify=ytdlpChanged)
    def ytdlpBusy(self) -> bool:  # type: ignore[override]
        return self._updating

    jsRuntimeAvailable = Property(bool, lambda self: self._ctx.js_runtime is not None, constant=True)
    platformName = Property(str, lambda self: self._ctx.name, constant=True)
    isMobile = Property(bool, lambda self: self._ctx.is_mobile, constant=True)
    ffmpegAvailable = Property(bool, lambda self: self._ctx.can_merge, constant=True)
    appVersion = Property(str, lambda self: __version__, constant=True)
    browserAvailable = Property(bool, lambda self: self._browser_ok, constant=True)

    # ---- slots ----------------------------------------------------------
    @Slot(str, result=int)
    def addUrls(self, text: str) -> int:
        urls = list(dict.fromkeys(_URL.findall(text or "")))
        for url in urls:
            options = self._settings.to_options()
            options.html_theme = self._effective_theme()
            if is_playlist_url(url):   # a playlist link: the entries are listed, the user picks
                options.playlist = True
                options.playlist_dir = True
            if self._ask_duplicate(url, options):
                continue
            self._start(url, options, single=len(urls) == 1)
        if not urls and (text or "").strip():
            self.toast.emit("No valid http(s) link found.")
        return len(urls)

    def _start(self, url: str, options, single: bool) -> None:
        if options.playlist and options.playlist_dir and is_playlist_url(url):
            self._check_playlist(url, options)          # list the entries, the user picks
        elif single and not options.playlist:
            self._check_audio_quality(url, options)   # live stream? better audio target? ask first
        else:
            self._queue.add(url, options)

    def _ask_duplicate(self, url: str, options) -> bool:
        """True when the link is already running/finished and the user must decide (or it is skipped)."""
        key = history.video_key(url)
        jobs = self._model.jobs()
        for j in jobs:
            if not j.state.finished and history.video_key(j.url) == key and j.options.mode == options.mode:
                self.toast.emit("This link is already in the list.")
                return True
        if options.playlist:
            return False
        prev = history.find_done(jobs, url, options.mode)
        if prev is None:
            return False
        import datetime as _dt
        self._dup_pending[url] = options
        self.duplicateFound.emit({"url": url, "title": prev.title or url, "jobId": prev.id, "mode": options.mode,
                                  "date": _dt.datetime.fromtimestamp(prev.created).strftime("%d.%m.%Y %H:%M")})
        return True

    @Slot(str, bool)
    def confirmDuplicate(self, url: str, again: bool) -> None:
        options = self._dup_pending.pop(url, None)
        if options is not None and again:
            self._start(url, options, single=True)

    def _save_history(self) -> None:
        try:
            history.save(self._history_path, self._model.jobs())
        except OSError:
            pass

    @Slot(str)
    def toggleSection(self, name: str) -> None:
        names = list(self._settings.ui_collapsed)
        if name in names:
            names.remove(name)
        else:
            names.append(name)
        self._settings.ui_collapsed = names
        self._filtered.set_collapsed(names)
        self._save()

    @Slot(str, int, result=int)
    def sectionCount(self, name: str, _refresh: int = 0) -> int:
        return sum(1 for j in self._model.jobs() if history.section_label(j.created) == name)

    @Slot(str)
    def clearSection(self, name: str) -> None:
        for j in self._model.jobs():
            if j.state.finished and history.section_label(j.created) == name:
                self._queue.remove(j.id)

    @Slot(str)
    def setListGroup(self, group: str) -> None:
        if group in ("all", "active", "queued", "done", "failed"):
            self._settings.list_group = group
            self._filtered.setGroup(group)
            self._save()

    def _effective_theme(self) -> str:
        """'light' or 'dark': the theme the app shows now (used for the saved HTML page)."""
        if self._settings.theme in ("light", "dark"):
            return self._settings.theme
        return "dark" if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark else "light"

    def _check_audio_quality(self, url: str, options) -> None:
        """Probe the link in the background; the job is created after the (optional) choice."""
        self.toast.emit("Checking link…")
        self._probe_options[url] = options
        opts = build_ydl_opts(options, self._ctx)

        def work() -> None:
            try:
                from ..core.engine import default_ydl_class
                result = self._probe(url, self._engine._ydl_class or default_ydl_class(), opts)
            except Exception:  # noqa: BLE001
                result = {}
            self._audioProbed.emit(url, result)
        threading.Thread(target=work, daemon=True).start()

    @Slot(str, object)
    def _on_audio_probed(self, url: str, result: Any) -> None:
        options = self._probe_options.get(url)
        if options is None:
            return
        best = (result or {}).get("best") or {}
        if (result or {}).get("live"):      # a running live stream: record it? for how long?
            self.liveChoice.emit({"url": url, "title": result.get("title", url),
                                  "thumbnail": result.get("thumbnail", "")})
            return
        wants_audio_choice = (options.mode == "audio" and options.audio_format == "mp3" and self._ctx.can_merge)
        if wants_audio_choice and audioprobe.is_high_quality(best):
            self.audioChoice.emit({"url": url, "title": result.get("title", url),
                                   "thumbnail": result.get("thumbnail", ""),
                                   "abr": int(best.get("abr") or 0), "codec": best.get("codec", ""),
                                   "choices": audioprobe.choices(best)})
        else:
            del self._probe_options[url]
            self._queue.add(url, options)

    def _check_playlist(self, url: str, options) -> None:
        """Read the playlist's entries in the background; the job is created after the user's pick."""
        self.toast.emit("Reading playlist…")
        self._probe_options[url] = options
        opts = build_ydl_opts(options, self._ctx)

        def work() -> None:
            try:
                from ..core.engine import default_ydl_class
                result = audioprobe.probe_playlist(url, self._engine._ydl_class or default_ydl_class(), opts)
            except Exception:  # noqa: BLE001
                result = {}
            self._playlistProbed.emit(url, result)
        threading.Thread(target=work, name="yeal-playlist", daemon=True).start()

    @Slot(str, object)
    def _on_playlist_probed(self, url: str, result: Any) -> None:
        options = self._probe_options.get(url)
        if options is None:
            return
        if (result or {}).get("entries"):
            self._playlist_totals[url] = len(result["entries"])
            self.playlistChoice.emit(dict(result, url=url))
        else:                                   # could not list it: download the whole playlist as before
            del self._probe_options[url]
            self._queue.add(url, options)

    @Slot(str, "QVariantList")
    def confirmPlaylist(self, url: str, indices: list) -> None:
        """Answer of the playlist dialog: the 1-based positions to download ([] = cancel)."""
        options = self._probe_options.pop(url, None)
        if options is None:
            return
        picked = sorted({int(i) for i in (indices or [])})
        total = int(self._playlist_totals.pop(url, 0))
        if not picked:
            return
        options.playlist = True
        options.playlist_dir = True
        # all items = no item filter (also catches entries that appear later)
        options.playlist_items = "" if total and len(picked) == total else compress_items(picked)
        self._queue.add(url, options.normalized())

    @Slot(str, int)
    def confirmLive(self, url: str, minutes: int) -> None:
        """Answer of the live-stream dialog. minutes < 0 = don't record; 0 = until the stream ends."""
        options = self._probe_options.pop(url, None)
        if options is None or minutes < 0:
            return
        options.live_minutes = minutes
        self._queue.add(url, options.normalized())

    @Slot(str, str, int)
    def confirmAudio(self, url: str, fmt: str, bitrate: int) -> None:
        """Dialog answer. fmt '' = cancel (nothing is downloaded)."""
        options = self._probe_options.pop(url, None)
        if options is None or not fmt:
            return
        if fmt == "mp3":
            if 0 < bitrate < audioprobe.MP3_MIN_KBPS:     # MP3 only at 320 kbps, otherwise no download
                self.toast.emit("MP3 needs at least %d kbps: not downloaded." % audioprobe.MP3_MIN_KBPS)
                return
            bitrate = audioprobe.MP3_MIN_KBPS
        options.audio_format = fmt
        options.audio_bitrate = bitrate or options.audio_bitrate
        self._queue.add(url, options.normalized())

    @Slot(str, result="QStringList")
    def extractLinks(self, text: str) -> list:
        return list(dict.fromkeys(m.rstrip(".,;)") for m in _URL.findall(text or "")))

    @Slot(result=str)
    def clipboardText(self) -> str:
        return QGuiApplication.clipboard().text()

    @Slot(str)
    def notify(self, message: str) -> None:
        self.toast.emit(message)

    @Slot(result=int)
    def addFromClipboard(self) -> int:
        return self.addUrls(QGuiApplication.clipboard().text())

    @Slot(int)
    def cancel(self, job_id: int) -> None:
        self._queue.cancel(job_id)

    @Slot(int)
    def retry(self, job_id: int) -> None:
        self._queue.retry(job_id)

    @Slot(int)
    def remove(self, job_id: int) -> None:
        self._queue.remove(job_id)

    @Slot()
    def clearFinished(self) -> None:
        self._queue.clear_finished()

    # ---- admin vault (stored in the user's data folder, never next to the program) -------------
    def _vault(self):
        if getattr(self, "_vault_obj", None) is None:
            try:
                self._vault_obj = vaultlib.Vault(self._ctx.data_dir / "vault.json")
            except vaultlib.Unavailable:
                self._vault_obj = False
        return self._vault_obj or None

    @Property(bool, constant=True)
    def vaultAvailable(self) -> bool:
        return self._vault() is not None

    @Property(bool, notify=vaultChanged)
    def vaultUnlocked(self) -> bool:
        v = self._vault()
        return bool(v and v.unlocked)

    @Property(bool, notify=vaultChanged)
    def vaultDefaultPassword(self) -> bool:
        v = self._vault()
        return bool(v and v.uses_default_password())

    @Slot(str, result=str)
    def vaultUnlock(self, password: str) -> str:
        """Returns '' on success, else an error text."""
        v = self._vault()
        if v is None:
            return "Not available on this system."
        if v.wait_seconds() > 0:
            return "Too many attempts. Wait %d s." % v.wait_seconds()
        if not v.unlock(password):
            return "Wrong password."
        self._vault_timer().start()
        self.vaultChanged.emit()
        return ""

    def _vault_timer(self):
        if getattr(self, "_vault_t", None) is None:
            from PySide6.QtCore import QTimer
            self._vault_t = QTimer(self)
            self._vault_t.setSingleShot(True)
            self._vault_t.setInterval(5 * 60 * 1000)      # auto-lock after 5 minutes
            self._vault_t.timeout.connect(self.vaultLock)
        return self._vault_t

    @Slot()
    def vaultLock(self) -> None:
        v = self._vault()
        if v:
            v.lock()
            self.vaultChanged.emit()

    @Slot(result="QVariantList")
    def vaultEntries(self):
        v = self._vault()
        return v.entries() if v and v.unlocked else []

    @Slot("QVariantMap", result=str)
    def vaultSave(self, entry) -> str:
        v = self._vault()
        try:
            v.save_entry(dict(entry))
        except (ValueError, PermissionError) as exc:
            return str(exc)
        self._vault_timer().start()
        self.vaultChanged.emit()
        return ""

    @Slot(str)
    def vaultDelete(self, entry_id: str) -> None:
        v = self._vault()
        if v and v.unlocked:
            v.delete_entry(entry_id)
            self.vaultChanged.emit()

    @Slot(str, bool)
    def vaultCopy(self, entry_id: str, user: bool) -> None:
        """Copy the user name or the password; the clipboard is cleared after 30 s."""
        v = self._vault()
        if not (v and v.unlocked):
            return
        if user:
            text = next((e.get("user", "") for e in v.entries() if e["id"] == entry_id), "")
        else:
            text = v.password_of(entry_id)
        clip = QGuiApplication.clipboard()
        clip.setText(text)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(30_000, lambda: clip.text() == text and clip.clear())
        self.toast.emit("Copied (clipboard is cleared in 30 s)")

    @Slot(str, str, result=str)
    def vaultChangePassword(self, old: str, new: str) -> str:
        v = self._vault()
        err = v.change_password(old, new) if v else "Not available."
        self.vaultChanged.emit()
        return err

    @Slot(result=bool)
    def wipeLogins(self) -> bool:
        """Delete the vault now and the browser sign-in (YouTube profile) at the next start."""
        try:
            (self._ctx.data_dir / "vault.json").unlink(missing_ok=True)
            self._vault_obj = None
            (self._ctx.data_dir / "wipe_browser_profile").write_text("1")
        except OSError:
            return False
        self.vaultChanged.emit()
        return True

    @Slot()
    def updateYtDlp(self) -> None:
        self._start_update(silent=False)

    @Slot(int)
    def openFile(self, job_id: int) -> None:
        """Open the finished file with the default app."""
        target = self._job_file(job_id)
        if target is None or not platforms.open_path(target):
            self._open_download_dir(job_id)

    @Slot(int)
    def openFileInVlc(self, job_id: int) -> None:
        """Play the finished file in VLC, fullscreen."""
        target = self._job_file(job_id)
        if target is None:
            return
        if not platforms.open_in_vlc(target, True):
            self.toast.emit("VLC was not found. Install VLC or use 'Open file'.")

    @Property(bool, constant=True)
    def vlcAvailable(self) -> bool:
        return platforms.vlc_available()

    def _job_page(self, job_id: int) -> Path | None:
        target = self._job_file(job_id)
        if target is None:
            return None
        if target.is_dir():      # a playlist: <folder>/<folder name>.html
            page = target / (target.name + ".html")
        else:
            page = target.with_suffix("").with_name(target.with_suffix("").name + ".html")
        return page if page.is_file() else None

    @Slot(int)
    def openPage(self, job_id: int) -> None:
        """Open saved HTML directly or through the optional local server, as configured."""
        page = self._job_page(job_id)
        if page is None:
            self.toast.emit("No HTML page saved for this download.")
            return
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(localserve.page_url(page, self._settings.html_open_mode)))

    @Slot(int)
    def showInFolder(self, job_id: int) -> None:
        target = self._job_file(job_id)
        if target is None or not platforms.reveal_path(target):
            self._open_download_dir(job_id)

    @Slot()
    def openDownloadFolder(self) -> None:
        """Open the download folder chosen in Settings (created if missing)."""
        self._open_download_dir(None)

    def _open_download_dir(self, job_id: int | None) -> None:
        root = Path(self._ctx.download_dir)
        folder = root
        job = self._model.get(job_id) if job_id is not None else None
        if job is not None and media_dir(root, job.options.mode).is_dir():
            folder = media_dir(root, job.options.mode)
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        if not platforms.open_path(folder):
            self.toast.emit(str(folder))

    @Slot(str)
    def copyText(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text or "")

    @Slot(str, result=str)
    def setDownloadDir(self, value: str) -> str:
        """Accepts a file:// URL (from FolderDialog) or a path; '' restores the default.
        Returns an error message, or '' on success."""
        value = (value or "").strip()
        if value:
            path = Path(QUrl(value).toLocalFile() if value.startswith("file:") else value)
        else:
            path = self._default_download_dir
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".yeal_write_test"
            probe.write_text("x", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            return f"Folder is not writable: {exc.strerror or exc}"
        self._ctx.download_dir = path
        self._settings.download_dir = "" if not value else str(path)
        self._save()
        return ""

    @Slot(str)
    def checkTracklist(self, url: str) -> None:
        """Look (in the background) whether the video has a tracklist; emits tracklistFound if so."""
        url = (url or "").strip()
        if not url.startswith(("http://", "https://")) or is_playlist_url(url):
            return
        if url in self._tracklist_seen:
            n = self._tracklist_seen[url]
            if n >= 2:
                self.tracklistFound.emit(url, n)
            return
        self._tracklist_seen[url] = 0
        opts = build_ydl_opts(self._settings.to_options(), self._ctx)

        def work() -> None:
            try:
                from ..core.engine import default_ydl_class
                result = self._probe(url, self._engine._ydl_class or default_ydl_class(), opts)
            except Exception:  # noqa: BLE001
                result = {}
            self._tracklistProbed.emit(url, int((result or {}).get("chapters") or 0))
        threading.Thread(target=work, name="yeal-tracklist", daemon=True).start()

    def _on_tracklist(self, url: str, count: int) -> None:
        self._tracklist_seen[url] = count
        if count >= 2:
            self.tracklistFound.emit(url, count)

    def _poll_drives(self) -> None:
        mask = platforms.drives.drive_mask()
        if mask == self._drive_mask or self._drive_busy:
            return
        self._drive_mask = mask
        self._drive_busy = True

        def work() -> None:
            try:
                found = platforms.drives.external_drives()
            except Exception:  # noqa: BLE001
                found = []
            self._drivesFound.emit(found)
        threading.Thread(target=work, name="yeal-drives", daemon=True).start()

    def _on_drives(self, found: list) -> None:
        self._drive_busy = False
        current = str(self._ctx.download_dir).lower()
        for d in found:
            if d["id"] in self._drive_offered or d["id"] in self._settings.drive_ignored:
                continue
            if current.startswith(d["root"].lower().rstrip("\\/")):
                continue     # already downloading to this drive
            self._drive_offered.add(d["id"])
            self.externalDrive.emit(dict(d, folder=self._settings.drive_folder))   # the dialog queues them

    @Slot(str, str, result=str)
    def useExternalDrive(self, root: str, name: str) -> str:
        """Create <root>/<name> and download there from now on. Returns an error text or ''."""
        folder = platforms.drives.clean_folder_name(name)
        err = self.setDownloadDir(str(Path(root) / folder))
        if not err:
            self._settings.drive_folder = folder
            self._save()
            self.toast.emit("Downloads now go to %s" % (Path(root) / folder))
        return err

    @Slot(result=str)
    def userDownloadsDir(self) -> str:
        """The Windows user Downloads folder (top entry of the drive dropdown)."""
        return str(platforms.drives.user_downloads_dir())

    @Slot(result=str)
    def useDownloadsFolder(self) -> str:
        """Download straight into the user's Downloads folder. Returns an error text or ''."""
        path = platforms.drives.user_downloads_dir()
        err = self.setDownloadDir(str(path))
        if not err:
            self.toast.emit("Downloads now go to %s" % path)
        return err

    @Slot(str)
    def ignoreExternalDrive(self, drive_id: str) -> None:
        if drive_id and drive_id not in self._settings.drive_ignored:
            self._settings.drive_ignored.append(drive_id)
            self._save()

    @Slot(int, result=str)
    def jobVideoPath(self, job_id: int) -> str:
        """Path of a finished job's video ('' if missing)."""
        path = self._job_file(job_id)
        return str(path) if path and path.is_file() else ""

    @Slot(str, result=str)
    def videoUrl(self, path: str) -> str:
        """file:// URL of a video for the preview player ('' if missing)."""
        return QUrl.fromLocalFile(path).toString() if path and Path(path).is_file() else ""

    @Slot(result="QVariantList")
    def libraryVideos(self) -> list:
        """Videos in the download folder for the extractor's tile browser. Thumbnails that are
        not cached yet are created in a worker thread and announced via libraryThumb."""
        items = framelib.list_videos(self._ctx.download_dir)
        cache = Path(self._ctx.temp_dir) / "thumbs"
        pending, out = [], []
        for it in items:
            p = Path(it["path"])
            thumb = ""
            if self._ctx.ffmpeg:
                try:
                    import hashlib
                    st = p.stat()
                    key = hashlib.md5(f"{p}|{st.st_mtime_ns}|{st.st_size}".encode("utf-8", "replace")).hexdigest()
                    cached = cache / f"{key}.jpg"
                    if cached.exists():
                        thumb = QUrl.fromLocalFile(str(cached)).toString()
                    else:
                        pending.append(p)
                except OSError:
                    pass
            out.append({"path": it["path"], "title": it["title"], "size": fmt_size(it["size"]), "thumb": thumb})
        if pending:
            ffmpeg = self._ctx.ffmpeg

            def work() -> None:
                for p in pending:
                    try:
                        img = framelib.thumb_for(ffmpeg, p, cache)
                    except Exception:
                        img = None
                    if img:
                        self.libraryThumb.emit(str(p), QUrl.fromLocalFile(str(img)).toString())

            threading.Thread(target=work, name="yeal-thumbs", daemon=True).start()
        return out

    @Slot(str)
    def openFolder(self, folder: str) -> None:
        """Open a folder (e.g. the image folder shown in the extractor)."""
        if folder and not platforms.open_path(Path(folder)):
            self.toast.emit(folder)

    @Slot(str, result="QVariantMap")
    def addExternalVideo(self, url: str) -> dict:
        """A video dropped from any folder (file:// URL or path). Returns a tile dict, or {} if it is
        not a usable video file. Output folders are unaffected: images always go to <downloads>/Frames."""
        p = Path(QUrl(url).toLocalFile() if url.startswith("file:") else url)
        if not p.is_file() or p.suffix.lower() not in framelib.VIDEO_EXT:
            return {}
        thumb = ""
        if self._ctx.ffmpeg:
            cache = Path(self._ctx.temp_dir) / "thumbs"
            ffmpeg = self._ctx.ffmpeg

            def work() -> None:
                try:
                    img = framelib.thumb_for(ffmpeg, p, cache)
                except Exception:
                    img = None
                if img:
                    self.libraryThumb.emit(str(p), QUrl.fromLocalFile(str(img)).toString())

            threading.Thread(target=work, name="yeal-thumb", daemon=True).start()
        try:
            size = fmt_size(p.stat().st_size)
        except OSError:
            size = ""
        return {"path": str(p), "title": p.stem, "size": size, "thumb": thumb}

    @Slot(str)
    def loadFilmstrip(self, path: str) -> None:
        """Create preview thumbnails in a worker thread; result arrives via filmstripReady."""
        video = Path(path) if path else None
        if video is None or not video.is_file():
            self.filmstripReady.emit(path, 0.0, [], "The video file was not found.")
            return
        if not self._ctx.ffmpeg:
            self.filmstripReady.emit(path, 0.0, [], "ffmpeg was not found.")
            return
        out_dir = Path(self._ctx.temp_dir) / "filmstrip"

        def work() -> None:
            try:
                duration, files = framelib.filmstrip(self._ctx.ffmpeg, video, out_dir)
                urls = [QUrl.fromLocalFile(str(f)).toString() for f in files]
                self.filmstripReady.emit(path, float(duration), urls, "")
            except Exception as exc:  # any failure must reach the dialog, never kill the thread silently
                self.filmstripReady.emit(path, 0.0, [], str(exc) or exc.__class__.__name__)

        threading.Thread(target=work, name="yeal-filmstrip", daemon=True).start()

    @Slot(str, str, str, str, str, result=str)
    def extractFrames(self, path: str, start: str, end: str, interval: str, fmt: str) -> str:
        """Split a video into images (own folder per video under <downloads>/Frames).
        Intervals below 1 s are only accepted for Shorts. Returns an error text, or '' when started."""
        if self._frames_busy:
            return "Another frame extraction is still running."
        if not self._ctx.ffmpeg:
            return "ffmpeg is required for this function."
        video = Path(path) if path else None
        if video is None or not video.is_file():
            return "The video file was not found."
        try:
            t0, t1, step = framelib.parse_time(start), framelib.parse_time(end), framelib.parse_time(interval)
        except ValueError as exc:
            return str(exc)
        if step < 0.1:
            return "The shortest interval is 0.1 seconds."
        if t1 and t1 <= t0:
            return "'To' must be later than 'From'."
        out_dir = framelib.target_dir(self._ctx.download_dir, video)
        self._frames_busy = True
        self.framesChanged.emit()

        def work() -> None:
            try:
                if step < 1 and framelib.probe_duration(self._ctx.ffmpeg, video) > framelib.SHORTS_MAX_SECONDS:
                    raise ValueError("An interval below 1 second is only available for Shorts (up to 3 minutes).")
                count = framelib.extract(self._ctx.ffmpeg, video, out_dir, t0, t1, step, fmt)
                self._framesFinished.emit(count, str(out_dir), "")
            except (ValueError, RuntimeError, OSError) as exc:
                self._framesFinished.emit(0, str(out_dir), str(exc))

        threading.Thread(target=work, name="yeal-frames", daemon=True).start()
        return ""

    @Slot(int, str, str)
    def _on_frames_finished(self, count: int, folder: str, error: str) -> None:
        self._frames_busy = False
        self.framesChanged.emit()
        self.framesDone.emit(count, folder, error)
        if error:
            self.toast.emit("Frames failed: " + error)
        elif count == 0:
            self.toast.emit("No images were created - check the time range.")
        else:
            self.toast.emit(f"{count} images saved")

    @Slot(str, "QVariant")
    def setSetting(self, key: str, value: Any) -> None:
        if key not in ("theme", "max_parallel", "auto_update", "rate_limit_kbps", "show_browser", "gentle_mode", "panel_width", "panel_right", "adblock_experimental", "ask_mp3_tags", "html_open_mode"):
            return
        current = getattr(self._settings, key)
        try:
            value = type(current)(value)
        except (TypeError, ValueError):
            return
        if key == "theme" and value not in THEMES:
            return
        if key == "html_open_mode" and value not in HTML_OPEN_MODES:
            return
        setattr(self._settings, key, value)
        self._settings.validate()
        if key == "html_open_mode" and self._settings.html_open_mode == "file":
            localserve.shutdown_all()
        self._queue.set_max_parallel(self._settings.max_parallel)
        self._save()

    @Slot(str)
    def setCookiesBrowser(self, name: str) -> None:
        """'' = off. Uses the login cookies of that browser for downloads (age limit, members, Premium)."""
        self._settings.cookies_browser = name
        self._settings.validate()
        self._save()

    @Slot(int, int, int, int, bool)
    def saveWindow(self, x: int, y: int, w: int, h: int, maximized: bool) -> None:
        """Remember the window geometry (normal size even while maximized)."""
        self._settings.window = {"x": x, "y": y, "w": w, "h": h, "max": maximized}
        self._save()

    @Slot(str, result=str)
    def setProxy(self, value: str) -> str:
        """Returns an error message, or '' on success ('' value clears the proxy)."""
        try:
            self._settings.proxy = normalize_proxy(value)
        except ValueError as exc:
            return str(exc)
        self._save()
        return ""

    # ---- profiles -------------------------------------------------------
    @Slot(str, bool)
    def setProfileFlag(self, key: str, value: bool) -> None:
        """Quick toggle for description/transcript on the active profile."""
        if self._settings.set_profile_flag(key, value):
            self._save()

    @Slot(str)
    def setAlbumMode(self, mode: str) -> None:
        """Album handling of the active profile: whole | split (tracks only) | both."""
        if mode not in ("whole", "split", "both"):
            return
        a = self._settings.set_profile_flag("split_chapters", mode != "whole")
        b = self._settings.set_profile_flag("keep_whole", mode != "split")
        if a and b:
            self._save()

    @Slot(str)
    def setFormatMode(self, mode: str) -> None:
        """Quick Video/Audio switch: activates the matching default profile."""
        prefs = {"video": ("Video 1080p",), "audio": ("Audio MP3",)}.get(mode)
        cur = self._settings.get_profile()
        if prefs is None or (cur["mode"] == mode and (mode == "video" or cur["audio_format"] == "mp3")):
            return
        names = [p["name"] for p in self._settings.profiles if p["mode"] == mode]
        if not names:
            self.toast.emit("No %s profile yet - create one under Profiles." % mode)
            return
        self._settings.active_profile = prefs[0] if prefs[0] in names else names[0]
        self._save()

    @Slot(str)
    def setActiveProfile(self, name: str) -> None:
        if name in self._settings.profile_names():
            self._settings.active_profile = name
            self._save()

    @Slot(str, "QVariantMap", result=str)
    def saveProfile(self, old_name: str, data: dict) -> str:
        """Create (old_name '') or update a profile. Returns an error text or ''."""
        err = self._settings.save_profile(old_name, dict(data))
        if not err:
            self._save()
        return err

    @Slot(str, result=str)
    def deleteProfile(self, name: str) -> str:
        err = self._settings.delete_profile(name)
        if not err:
            self._save()
        return err

    @Slot(str, result=str)
    def duplicateProfile(self, name: str) -> str:
        new = self._settings.duplicate_profile(name)
        if new:
            self._save()
        return new

    @Slot(str)
    def openLink(self, url: str) -> None:
        if url.startswith(("http://", "https://")):
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(url))

    @Slot(str, result=str)
    def setCustomOptions(self, text: str) -> str:
        """Returns an error message, or '' on success."""
        text = (text or "").strip()
        if not text:
            self._settings.custom_options = {}
            self._save()
            return ""
        try:
            raw = json.loads(text)
        except ValueError as exc:
            return f"Invalid JSON: {exc}"
        if not isinstance(raw, dict):
            return "Expected a JSON object, e.g. {\"ratelimit\": 500000}"
        clean, rejected = sanitize_custom_options(raw)
        if rejected:
            return "Not allowed: " + ", ".join(sorted(rejected))
        self._settings.custom_options = clean
        self._save()
        return ""

    def _start_update(self, silent: bool) -> None:
        if self._updating:
            return
        self._updating = True
        self.ytdlpChanged.emit()

        def work() -> None:
            try:
                version, changed = updater.update(self._ctx.data_dir)
                if changed:
                    note = f"yt-dlp updated to {version}"
                    if updater.restart_needed():
                        note += " - restart Yeal to use it"
                    self._updateFinished.emit(version, note)
                else:
                    self._updateFinished.emit(version, "" if silent else f"yt-dlp {version} is up to date")
            except Exception as exc:  # noqa: BLE001 - network/PyPI problems must never crash the app
                self._updateFinished.emit("", "" if silent else f"yt-dlp update failed: {str(exc)[:160]}")

        threading.Thread(target=work, name="yeal-update", daemon=True).start()

    @Slot(str, str)
    def _on_update_finished(self, version: str, message: str) -> None:
        self._updating = False
        self.ytdlpChanged.emit()
        if message:
            self.toast.emit(message)

    def shutdown(self) -> None:
        self._save_history()
        self._queue.shutdown()
        localserve.shutdown_all()

    # ---- MP3 tags ---------------------------------------------------------
    mp3TagsAvailable = Property(bool, lambda self: mp3tags.AVAILABLE, constant=True)

    @Slot(object)
    def _ask_tags(self, job: DownloadJob) -> None:
        """A single MP3 was just tagged automatically: offer to edit the tags (once per job, if enabled)."""
        if (job.state is JobState.DONE and job.tags_ask and self._settings.ask_mp3_tags
                and job.id not in self._tags_asked):
            self._tags_asked.add(job.id)
            self.tagsPrompt.emit({"jobId": job.id, "title": job.title or job.url})

    def _mp3_of(self, job_id: int) -> Path | None:
        path = self._job_file(job_id)
        return path if path is not None and path.suffix.lower() == ".mp3" and path.is_file() else None

    @Slot(int, result="QVariantMap")
    def tagsRead(self, job_id: int) -> dict:
        """Current tags of a finished MP3 job; {"error": text} when they cannot be read."""
        path = self._mp3_of(job_id)
        if not mp3tags.AVAILABLE:
            return {"error": "MP3 tag support (mutagen) is not installed."}
        if path is None:
            return {"error": "The MP3 file was not found."}
        try:
            return asdict(mp3tags.read_tags(path))
        except (OSError, mp3tags.MutagenError):
            return {"error": "The tags of this file could not be read."}

    @Slot(int, "QVariantMap", result=str)
    def tagsSave(self, job_id: int, data: dict) -> str:
        """Write the edited fields into the MP3. Returns '' when saved, else the reason."""
        path = self._mp3_of(job_id)
        if not mp3tags.AVAILABLE:
            return "MP3 tag support (mutagen) is not installed."
        if path is None:
            return "The MP3 file was not found."
        try:
            mp3tags.write_tags(path, mp3tags.from_dict(data, mp3tags.read_tags(path)))
        except (OSError, mp3tags.MutagenError):
            return "The tags could not be saved (is the file open in a player or write-protected?)."
        self.toast.emit("MP3 tags saved")
        return ""

    # ---- internals ------------------------------------------------------
    def _job_file(self, job_id: int) -> Path | None:
        """Finished file of a job; falls back to the newest file in the download folder
        whose name starts with the job title (for entries saved by older versions)."""
        job = self._model.get(job_id)
        if job is None:
            return None
        if job.filename and Path(job.filename).exists():
            return Path(job.filename)
        stem = "".join(c for c in (job.title or "") if c not in '<>:"/\\|?*')[:30].strip().lower()
        if len(stem) >= 8:
            hits = []
            root = Path(self._ctx.download_dir)
            for folder in (media_dir(root, job.options.mode), root):
                try:
                    hits += [p for p in folder.iterdir()
                             if p.is_file() and p.name.lower().startswith(stem)
                             and p.suffix not in (".part", ".ytdl", ".html", ".txt")]
                except OSError:
                    pass
            if hits:
                return max(hits, key=lambda p: p.stat().st_mtime)
        return None

    def _apply_download_dir(self) -> None:
        if self._settings.download_dir:
            self._ctx.download_dir = Path(self._settings.download_dir)

    def _save(self) -> None:
        try:
            self._settings.save(self._ctx.settings_path)
        except OSError:
            self.toast.emit("Could not save settings.")
        self.settingsChanged.emit()
