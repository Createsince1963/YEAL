"""Runtime monitor for finding a slow player (0.9.1.25). Switched on with the environment variable YEAL_PERF=1 (Run_Yeal_Debug.bat
can set it); it prints one line every two seconds to the console:

    CPU  RAM  threads  ffmpeg processes  GUI lag (largest delay of a 50 ms timer in the last interval)

How to read it: RAM rising without end = buffers / cache / leak; threads or ffmpeg processes rising with every song = workers or
processes that are not stopped; CPU rising with every song change = signals or timers connected twice; high GUI lag with moderate
CPU = the GUI thread is blocked (the sound stutters when the lag gets near the 0.6 s buffer of the own engine).
psutil is optional (pip install psutil); without it only the GUI lag and the thread count are shown.
"""
from __future__ import annotations

import os
import threading
import time

from PySide6.QtCore import QObject, QTimer

try:
    import psutil
except ImportError:                       # optional
    psutil = None


def enabled() -> bool:
    return os.environ.get("YEAL_PERF", "") not in ("", "0")


class PerfMonitor(QObject):
    def __init__(self, parent=None, interval_ms: int = 2000):
        super().__init__(parent)
        self._proc = psutil.Process(os.getpid()) if psutil else None
        if self._proc:
            self._proc.cpu_percent(None)
        self.extra = None                 # optional callable -> dict with more numbers (dropouts, longest chain tick of the own engine)
        self._last = time.monotonic()
        self._lag = 0.0
        self._beat = QTimer(self)
        self._beat.setInterval(50)
        self._beat.timeout.connect(self._on_beat)
        self._beat.start()
        self._report = QTimer(self)
        self._report.setInterval(interval_ms)
        self._report.timeout.connect(self._print)
        self._report.start()

    def _on_beat(self) -> None:
        now = time.monotonic()
        self._lag = max(self._lag, (now - self._last) * 1000.0 - 50.0)
        self._last = now

    def _print(self) -> None:
        parts = []
        if self._proc is not None:
            try:
                children = sum(1 for c in self._proc.children(recursive=True) if "ffmpeg" in (c.name() or "").lower())
                parts.append("CPU=%5.1f%%" % self._proc.cpu_percent(None))
                parts.append("RAM=%7.1f MB" % (self._proc.memory_info().rss / 1048576))
                parts.append("ffmpeg=%d" % children)
            except psutil.Error:
                pass
        parts.append("threads=%3d" % threading.active_count())
        parts.append("GUI lag=%5.0f ms" % max(0.0, self._lag))
        if self.extra is not None:
            try:
                parts += ["%s=%s" % (k, v) for k, v in (self.extra() or {}).items()]
            except Exception:  # noqa: BLE001 - a monitor never breaks the player
                pass
        self._lag = 0.0
        print("[perf] " + " | ".join(parts), flush=True)
