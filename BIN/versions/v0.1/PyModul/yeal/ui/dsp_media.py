"""Yeal's own audio engine, Qt side (desktop, optional):

    ffmpeg (decodes any file or stream, resamples, can jump to a position) -> core/dsp.py (32-bit float chain)
        -> QAudioSink (WASAPI on Windows) on the chosen output -> Windows / Bluetooth -> headphones

It looks like a QMediaPlayer to the players (same methods and signals for what they use), so TidalPlayer and LocalPlayer
only choose which one to create. ffmpeg runs as a normal process; a reader thread puts its output into a small queue, and
when the queue is full the thread stops reading - so ffmpeg waits when we are a few seconds ahead (a 2 hour mix never
fills the memory). A 15 ms timer in the Qt event loop moves the finished blocks through the chain into the sound card.
"""
from __future__ import annotations

import queue
import re
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices, QMediaPlayer

from ..core import dsp

PLAYING = QMediaPlayer.PlaybackState.PlayingState
PAUSED = QMediaPlayer.PlaybackState.PausedState
STOPPED = QMediaPlayer.PlaybackState.StoppedState
END = QMediaPlayer.MediaStatus.EndOfMedia
_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_RATES = (44100, 48000, 88200, 96000, 176400, 192000)
_CHUNK = 1 << 16
_QUEUE_CHUNKS = 160                                    # about 10 MB: roughly 30 s of float audio at 48 kHz


def usable(ffmpeg) -> bool:
    """The engine needs numpy and an ffmpeg that exists."""
    try:
        return dsp.available() and bool(ffmpeg) and Path(str(ffmpeg)).is_file()
    except OSError:
        return False


class _Feed:
    """One running ffmpeg: its audio arrives through `chunks` (None at the end), its messages in `log`."""
    def __init__(self, args):
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     creationflags=flags)
        self.chunks: "queue.Queue" = queue.Queue(maxsize=_QUEUE_CHUNKS)
        self.log: deque = deque(maxlen=60)
        self.duration_ms = 0
        self.stop = threading.Event()
        self.code: Optional[int] = None
        self._threads = [threading.Thread(target=self._read_audio, name="yeal-dsp-audio", daemon=True),
                         threading.Thread(target=self._read_log, name="yeal-dsp-log", daemon=True)]
        for t in self._threads:
            t.start()

    def _read_audio(self) -> None:
        try:
            while not self.stop.is_set():
                data = self.proc.stdout.read(_CHUNK)
                if not data:
                    break
                while not self.stop.is_set():
                    try:
                        self.chunks.put(data, timeout=0.1)           # a full queue: ffmpeg waits
                        break
                    except queue.Full:
                        continue
        except (OSError, ValueError):
            pass
        finally:
            self.code = self.proc.poll() if self.proc.poll() is not None else None
            while not self.stop.is_set():
                try:
                    self.chunks.put(None, timeout=0.1)
                    break
                except queue.Full:
                    continue

    def _read_log(self) -> None:
        try:
            for raw in iter(self.proc.stderr.readline, b""):
                line = raw.decode("utf-8", "replace").rstrip()
                self.log.append(line)
                if not self.duration_ms:
                    m = _DURATION.search(line)
                    if m:
                        self.duration_ms = int((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) * 1000)
        except (OSError, ValueError):
            pass

    def exit_code(self) -> int:
        try:
            return self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            return -1

    def close(self) -> None:
        self.stop.set()
        try:
            self.proc.kill()
        except OSError:
            pass
        for stream in (self.proc.stdout, self.proc.stderr):
            try:
                stream.close()
            except OSError:
                pass
        for t in self._threads:
            t.join(0.3)
        try:
            self.proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass


class DspMedia(QObject):
    positionChanged = Signal(int)
    durationChanged = Signal(int)
    playbackStateChanged = Signal(object)
    mediaStatusChanged = Signal(object)
    errorOccurred = Signal(object, str)
    levels = Signal(object)                    # [(bucket, level)] of the music that was just sent on (see tidal_backend.buffer_levels)

    def __init__(self, ffmpeg, parent=None):
        super().__init__(parent)
        self._ffmpeg = str(ffmpeg)
        self._cfg = dsp.DspConfig()
        self._chain = None
        self._volume = 0.8
        self._gain_db = 0.0
        self._device = None
        self._source = ""
        self._state = STOPPED
        self._start_ms = 0                     # where in the song the running ffmpeg began
        self._duration_ms = 0
        self._raw = bytearray()
        self._feed: Optional[_Feed] = None
        self._sink: Optional[QAudioSink] = None
        self._io = None
        self._rate = 48000
        self._eof = False                      # ffmpeg is finished: no more data is coming
        self._drained = False
        self._in_frames = 0                    # frames taken from ffmpeg since the start (song time of the next block)
        self._last_pos = -1
        self._last_emit = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(15)
        self._timer.timeout.connect(self._tick)

    # -- what the players set
    def setVolume(self, volume: float) -> None:
        """0..1 as the slider; the engine uses a quadratic curve (-40 dB at 10 %) so that quiet settings are usable."""
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._chain is not None:
            self._chain.volume = self._volume ** 2

    def setDevice(self, device) -> None:
        """Another output (Bluetooth headphones ...): the song goes on from the same place."""
        changed = device is not self._device
        self._device = device
        if changed and self._state != STOPPED:
            self.setPosition(self.position())

    def setConfig(self, cfg: dsp.DspConfig) -> None:
        self._cfg = cfg
        if self._state != STOPPED:
            self.setPosition(self.position())                 # the new filter starts at the place where we are

    def setReplayGain(self, gain_db: float) -> None:
        self._gain_db = float(gain_db or 0.0)
        if self._chain is not None:
            self._chain.set_replaygain(self._gain_db)

    def setSource(self, url: QUrl) -> None:
        self.stop()
        self._source = url.toLocalFile() if url.isLocalFile() else url.toString()
        self._start_ms = 0
        self._duration_ms = 0
        self._gain_db = 0.0

    # -- what the players ask
    def duration(self) -> int:
        return self._duration_ms

    def playbackState(self):
        return self._state

    def position(self) -> int:
        if self._state == STOPPED or self._sink is None:
            return self._start_ms
        played = self._sink.processedUSecs() / 1000.0
        lag = (self._chain.delay / self._rate * 1000.0) if self._chain is not None else 0.0
        return int(self._start_ms + max(0.0, played - lag))

    # -- transport
    def play(self) -> None:
        if self._state == PAUSED and self._sink is not None:
            self._sink.resume()
            self._set_state(PLAYING)
        elif self._state == STOPPED and self._source:
            self._start(self._start_ms)

    def pause(self) -> None:
        if self._state == PLAYING and self._sink is not None:
            self._sink.suspend()
            self._set_state(PAUSED)

    def stop(self) -> None:
        self._teardown()
        self._start_ms = 0
        self._set_state(STOPPED)

    def setPosition(self, ms: int) -> None:
        ms = max(0, int(ms))
        if self._state == STOPPED:
            self._start_ms = ms
            self.positionChanged.emit(ms)
            return
        was_paused = self._state == PAUSED
        self._start(ms)
        if was_paused:
            self.pause()

    # -- inside
    def _set_state(self, state) -> None:
        if state != self._state:
            self._state = state
            self.playbackStateChanged.emit(state)

    def _output_format(self):
        device = self._device or QMediaDevices.defaultAudioOutput()
        rate = int(device.preferredFormat().sampleRate() or 48000)
        rate = rate if rate in _RATES else 48000
        fmt = QAudioFormat()
        fmt.setSampleRate(rate)
        fmt.setChannelCount(2)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
        return device, fmt, rate

    def _teardown(self) -> None:
        self._timer.stop()
        feed, self._feed = self._feed, None
        if feed is not None:
            feed.close()
        sink, self._sink = self._sink, None
        if sink is not None:
            sink.stop()
            sink.deleteLater()
        self._io = None
        self._raw = bytearray()

    def _fail(self, text: str) -> None:
        self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, text[:200])
        self._teardown()
        self._set_state(STOPPED)

    def _start(self, pos_ms: int) -> None:
        self._teardown()
        device, fmt, rate = self._output_format()
        if not device.isFormatSupported(fmt):
            self._fail("The sound card does not take 32-bit float audio.")
            return
        self._rate = rate
        self._start_ms = pos_ms
        self._in_frames = 0
        self._eof = False
        self._drained = False
        self._last_pos = -1
        self._chain = dsp.Chain(self._cfg, rate)
        self._chain.volume = self._volume ** 2
        self._chain.set_replaygain(self._gain_db)
        args = [self._ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "info"]
        if pos_ms > 0:
            args += ["-ss", "%.3f" % (pos_ms / 1000.0)]
        args += ["-i", self._source, "-vn", "-sn", "-dn", "-map", "0:a:0", "-f", "f32le", "-ac", "2", "-ar", str(rate), "pipe:1"]
        try:
            self._feed = _Feed(args)
        except OSError:
            self._fail("ffmpeg could not be started.")
            return
        self._sink = QAudioSink(device, fmt, self)
        self._sink.setBufferSize(int(rate * 8 * 0.4))                  # 0.4 s: stable on Bluetooth, short enough to feel direct
        self._io = self._sink.start()
        self._set_state(PLAYING)
        self._timer.start()

    def _fill(self) -> None:
        """Take what the reader thread has ready (not more than a few blocks: the rest waits in the queue)."""
        feed = self._feed
        while feed is not None and not self._eof and len(self._raw) < dsp.BLOCK * 8 * 4:
            try:
                chunk = feed.chunks.get_nowait()
            except queue.Empty:
                break
            if chunk is None:
                self._eof = True
            else:
                self._raw += chunk

    def _pump(self) -> None:
        """Move what is ready through the chain into the sound card, as much as the card takes."""
        if self._sink is None or self._chain is None or self._io is None or self._state == STOPPED:
            return
        np = dsp.np
        need = dsp.BLOCK * 8                                              # one block: BLOCK frames x 2 channels x 4 bytes
        while self._sink.bytesFree() >= need:
            self._fill()
            if len(self._raw) >= need:
                block = np.frombuffer(bytes(self._raw[:need]), dtype=np.float32).reshape(-1, 2)
                del self._raw[:need]
            elif self._eof and len(self._raw) >= 8:                      # the last, shorter block
                usable_bytes = len(self._raw) // 8 * 8
                block = np.frombuffer(bytes(self._raw[:usable_bytes]), dtype=np.float32).reshape(-1, 2)
                self._raw = bytearray()
            elif self._eof and not self._drained:                        # everything is through: the tail of the filter
                self._drained = True
                tail = self._chain.flush()
                if len(tail):
                    self._io.write(tail.tobytes())
                break
            else:
                break
            self._send_levels(block)
            self._io.write(self._chain.process(block).tobytes())
            self._in_frames += len(block)

    def _send_levels(self, block) -> None:
        from .tidal_backend import buffer_levels
        np = dsp.np
        start_us = int(self._start_ms * 1000 + self._in_frames * 1_000_000 / self._rate)
        try:
            pairs = buffer_levels(memoryview(np.ascontiguousarray(block)).cast("B").cast("f"), 2, self._rate, start_us, 1.0)
        except (TypeError, ValueError):
            return
        if pairs:
            self.levels.emit(pairs)

    def _tick(self) -> None:
        feed = self._feed
        if self._state == STOPPED or self._sink is None or feed is None:
            return
        if feed.duration_ms and not self._duration_ms:
            self._duration_ms = feed.duration_ms
            self.durationChanged.emit(self._duration_ms)
        self._pump()
        if self._eof and self._in_frames == 0 and not self._raw:               # ffmpeg ended without any audio: it is an error
            code = feed.exit_code()
            if code != 0:
                lines = [l for l in feed.log if l.strip()]
                self._fail(lines[-1] if lines else "ffmpeg could not play this.")
                return
        now = time.monotonic()
        pos = self.position()
        if pos != self._last_pos and now - self._last_emit >= 0.04:
            self._last_pos, self._last_emit = pos, now
            self.positionChanged.emit(pos)
        if self._eof and self._drained and not self._raw and self._state == PLAYING:
            if self._sink.bytesFree() >= self._sink.bufferSize() - 64:       # the card has played everything
                self._teardown()
                self._start_ms = self._duration_ms or self._start_ms
                self._set_state(STOPPED)
                self.mediaStatusChanged.emit(END)
