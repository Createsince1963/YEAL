"""Seamless change from one song to the next (0.9.1.18): the song that ends is handed over to a Crossfader, which keeps
it playing and fades it out while the next song (a new media object of the player) fades in. Works with Qt's player
and with Yeal's own engine, because it only needs setVolume / stop on the objects."""
from __future__ import annotations

import math
import time
from typing import Callable, List, Optional

from PySide6.QtCore import QObject, QTimer

LEAD_MS = 5000          # the extra ring starts this long before the fade ...
TRAIL_MS = 5000         # ... and runs this long after it started
HANDOVER_MS = 1500      # the old song is handed over a little earlier: the stream of the next one has to be fetched


def phase_before(remaining_ms: float, fade_ms: float) -> float:
    """0..0.5 of the transition ring while the song is still running: 0 at LEAD_MS before the fade, 0.5 at its start."""
    if remaining_ms > fade_ms + LEAD_MS:
        return -1.0
    return max(0.0, min(0.5, 0.5 * (1.0 - (remaining_ms - fade_ms) / LEAD_MS)))


def phase_after(elapsed_ms: float) -> float:
    """0.5..1 of the transition ring after the fade started; -1 when the ring is over."""
    if elapsed_ms >= TRAIL_MS:
        return -1.0
    return 0.5 + 0.5 * max(0.0, elapsed_ms) / TRAIL_MS


class Crossfader(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._out: List[tuple] = []            # (object with the volume, object to stop, volume it had, other objects)
        self._in = None
        self._target: Callable[[], float] = lambda: 1.0
        self._t0 = 0.0
        self._dur = 1.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._step)

    @property
    def waiting(self) -> bool:
        return bool(self._out) and self._in is None and not self._timer.isActive()

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    def hold(self, volume_obj, media, volume: float, *extras) -> None:
        """Keep a song that is playing out of the player's way until the next one is ready. volume_obj has setVolume
        (Qt's audio output, or the own engine itself), media is stopped at the end, extras are deleted with it."""
        self._out.append((volume_obj, media, float(volume), extras))

    def begin(self, incoming, target: Callable[[], float], seconds: float) -> None:
        """The next song starts now: both volumes move over `seconds`."""
        self._in = incoming
        self._target = target
        self._dur = max(0.2, float(seconds))
        self._t0 = time.monotonic()
        if incoming is not None:
            incoming.setVolume(0.0)
        self._timer.start()

    def elapsed_ms(self) -> float:
        return (time.monotonic() - self._t0) * 1000.0 if self._t0 else 0.0

    def _step(self) -> None:
        p = (time.monotonic() - self._t0) / self._dur
        k = min(1.0, max(0.0, p)) * math.pi / 2
        for vobj, _media, vol, _extras in self._out:
            try:
                vobj.setVolume(vol * math.cos(k))
            except RuntimeError:
                pass
        if self._in is not None:
            try:
                self._in.setVolume(self._target() * math.sin(k))
            except RuntimeError:
                self._in = None
        if p >= 1.0:
            self.finish()

    def finish(self) -> None:
        """The change is over (or the next song never came): the old songs stop, the new one has its full volume."""
        self._timer.stop()
        incoming, self._in = self._in, None
        if incoming is not None:
            try:
                incoming.setVolume(self._target())
            except RuntimeError:
                pass
        self._drop()

    def cancel(self) -> None:
        self._timer.stop()
        self._t0 = 0.0
        self._in = None
        self._drop()

    def _drop(self) -> None:
        old, self._out = self._out, []
        for _vobj, media, _vol, extras in old:
            try:
                media.stop()
                media.deleteLater()
                for extra in extras:
                    if extra is not None and extra is not media:
                        extra.deleteLater()
            except RuntimeError:
                pass
