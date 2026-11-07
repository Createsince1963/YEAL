"""The sound check of Settings (0.9.1.27): starts the calibration (ui/calibration.py) as a separate process, so the player and the GUI
stay free, shows its progress lines and the PASS / WARN / FAIL list, and applies the recommended values on request.

The child is `main.py --calibrate --json ...` (in the exe: `Yeal.exe --calibrate --json ...`); it prints `PROGRESS <text>` lines,
then `RESULT <json>` (or `ERROR <text>`). Music is paused while it runs: the test needs the output and the CPU for itself.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Property, QObject, QProcess, Signal, Slot


def child_command(level: str, minutes: float = 0.0, device: str = "") -> tuple:
    """(program, arguments) of the calibration process."""
    args = ["--calibrate", "--json", "--stress" if level == "stress" else "--quick"]
    if minutes:
        args += ["--minutes", str(minutes)]
    if device:
        args += ["--device", device]
    if getattr(sys, "frozen", False):
        return sys.executable, args
    return sys.executable, [str(Path(__file__).resolve().parents[2] / "main.py")] + args


class CalibrationRunner(QObject):
    changed = Signal()

    def __init__(self, backend):
        super().__init__(backend)
        self._backend = backend
        self._proc = None
        self._running = False
        self._status = ""
        self._log = []
        self._report = {}
        self._buffer = ""
        self._canceled = False

    # -- what the page shows
    @Property(bool, notify=changed)
    def running(self):  # type: ignore[override]
        return self._running

    @Property(str, notify=changed)
    def status(self):  # type: ignore[override]
        return self._status

    @Property("QVariantList", notify=changed)
    def log(self):  # type: ignore[override]
        return self._log[-6:]

    @Property("QVariantList", notify=changed)
    def verdicts(self):  # type: ignore[override]
        return list(self._report.get("verdicts") or [])

    @Property("QVariantMap", notify=changed)
    def profile(self):  # type: ignore[override]
        return dict(self._report.get("profile") or {})

    @Property(bool, notify=changed)
    def hasResult(self):  # type: ignore[override]
        return bool(self._report)

    # -- control
    @Slot(str)
    def start(self, level: str = "quick") -> None:
        if self._running:
            return
        for player in (self._backend.tidal.player, self._backend.localPlayer):   # the test needs the output and the CPU
            try:
                player.pause()
            except Exception:  # noqa: BLE001
                pass
        program, args = child_command("stress" if level == "stress" else "quick")
        self._report, self._log, self._buffer, self._canceled = {}, [], "", False
        self._status = "Starting ..."
        self._running = True
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_output)
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(self._on_error)
        self._proc = proc
        proc.start(program, args)
        self.changed.emit()

    @Slot()
    def cancel(self) -> None:
        if self._proc is not None and self._running:
            self._canceled = True
            self._proc.kill()

    @Slot()
    def apply(self) -> None:
        """Use the recommended values (they stay changeable in the settings)."""
        prof = self._report.get("profile") or {}
        if not prof:
            return
        self._backend.setSetting("audio_buffer_ms", int(prof.get("audio_buffer_ms", 600)))
        self._backend.setSetting("ui_refresh_hz", int(prof.get("ui_refresh_hz", 20)))
        self._status = "Applied: sound buffer %d ms, repaint %d Hz. A running song takes the new buffer at its next start." % (
            int(prof.get("audio_buffer_ms", 600)), int(prof.get("ui_refresh_hz", 20)))
        self.changed.emit()

    # -- the child
    def _on_output(self) -> None:
        self._buffer += bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._handle(line.strip())
        self.changed.emit()

    def _handle(self, line: str) -> None:
        if line.startswith("PROGRESS "):
            self._status = line[9:]
            self._log.append(line[9:])
        elif line.startswith("RESULT "):
            try:
                self._report = json.loads(line[7:])
            except ValueError:
                self._status = "The result could not be read."
        elif line.startswith("ERROR "):
            self._status = line[6:]

    def _on_finished(self, code, _status) -> None:
        self._on_output()
        self._running = False
        if self._canceled:
            self._status = "Canceled."
        elif self._report:
            self._status = "Ready: %d tests. Recommended sound buffer %d ms, repaint %d Hz." % (
                len(self._report.get("verdicts") or []), int(self._report["profile"]["audio_buffer_ms"]),
                int(self._report["profile"]["ui_refresh_hz"]))
        elif self._status in ("", "Starting ..."):
            self._status = "The sound check could not run."
        self._proc = None
        self.changed.emit()

    def _on_error(self, _error) -> None:
        if self._proc is not None and self._proc.state() == QProcess.ProcessState.NotRunning and not self._report:
            self._status = "The sound check could not be started."
            self._running = False
            self.changed.emit()
