"""Audio performance & stability calibration (0.9.1.26).

It tests the real playback chain of Yeal's own engine - ffmpeg -> Python buffer -> filter chain -> sound card buffer
(QAudioSink) -> Windows -> Bluetooth / headphones - and not only the hardware:

 1. the audio output: name, formats it takes (sample rates, float32 / 32 / 16 bit), channels, Bluetooth hands-free warning;
 2. the smallest sound card buffer that plays without a dropout (underrun) while the GUI thread is busy like in the real
    player; the productive value is one step above it;
 3. how often the player picture can be repainted (GUI lag under load);
 4. (stress) many song changes, pause / continue / seek: threads, ffmpeg processes and memory must not grow, the GUI lag must
    stay small, no dropouts.
The result is a verdict list (PASS / WARN / FAIL), `audio_profile.json` (the values to use) and `audio_report.json` in the data
folder of Yeal. `--apply` writes the values into the settings (audio_buffer_ms, ui_refresh_hz); they stay changeable by hand.

    python -m yeal.ui.calibration --quick                 (about 1 minute)
    python -m yeal.ui.calibration --stress --apply        (about 4 minutes)
    python -m yeal.ui.calibration --stress --minutes 10   (long run: song changes for 10 minutes)
    python -m yeal.ui.calibration --list                  (only the outputs and their formats)

The sound is silent (volume 0): the sound card buffer runs all the same. psutil is optional (memory and process counts).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Callable, List, Optional

BUFFER_STEPS_MS = (200, 300, 400, 600, 1000, 1500)       # candidates for the sound card buffer
DEFAULT_BUFFER_MS = 600
GUI_LAG_WARN_MS, GUI_LAG_FAIL_MS = 100.0, 250.0
THREADS_PER_CHANGE_FAIL = 0.15
RSS_GROWTH_WARN_MB, RSS_GROWTH_FAIL_MB_MIN = 50.0, 5.0

try:
    import psutil
except ImportError:                    # optional
    psutil = None


# ---- 1. the outputs --------------------------------------------------------------------------------------------
def device_report(device) -> dict:
    """What one output takes. `device` is a QAudioDevice."""
    from PySide6.QtMultimedia import QAudioFormat
    fmt = device.preferredFormat()
    name = device.description()
    formats = [f.name for f in device.supportedSampleFormats()]
    rates = {}
    for rate in (44100, 48000, 96000, 192000):
        test = QAudioFormat()
        test.setSampleRate(rate)
        test.setChannelCount(2)
        test.setSampleFormat(QAudioFormat.SampleFormat.Float)
        rates[str(rate)] = bool(device.isFormatSupported(test))
    low = name.lower()
    return {"name": name, "id": bytes(device.id()).decode("utf-8", "replace"), "is_default": bool(device.isDefault()),
            "preferred_rate": fmt.sampleRate(), "preferred_channels": fmt.channelCount(),
            "preferred_format": fmt.sampleFormat().name, "sample_formats": formats,
            "min_rate": device.minimumSampleRate(), "max_rate": device.maximumSampleRate(),
            "min_channels": device.minimumChannelCount(), "max_channels": device.maximumChannelCount(),
            "float32_stereo_by_rate": rates,
            "hands_free": any(k in low for k in ("hands-free", "handsfree", "headset", "ag audio"))}


def list_devices() -> List[dict]:
    from PySide6.QtMultimedia import QMediaDevices
    return [device_report(d) for d in QMediaDevices.audioOutputs()]


def pick_device(name: str = ""):
    """The output named (part of the name) or the default output."""
    from PySide6.QtMultimedia import QMediaDevices
    if name:
        for d in QMediaDevices.audioOutputs():
            if name.lower() in d.description().lower():
                return d
    return QMediaDevices.defaultAudioOutput()


# ---- helpers -------------------------------------------------------------------------------------------------------
def _write_test_song(path: Path, seconds: int = 150) -> None:
    """Something like music: a few tones with a changing level plus a little noise (44.1 kHz stereo 16 bit)."""
    import random
    rng = random.Random(1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        step = 44100
        for s in range(seconds):
            frames = bytearray()
            level = 0.15 + 0.25 * abs(math.sin(s / 7.0))
            for i in range(step):
                t = (s * step + i) / 44100.0
                v = (math.sin(2 * math.pi * 110 * t) + 0.5 * math.sin(2 * math.pi * 440 * t) + 0.25 * math.sin(2 * math.pi * 1760 * t)) / 1.75
                v = level * v + 0.01 * (rng.random() - 0.5)
                frames += struct.pack("<hh", int(32767 * v), int(32767 * v * 0.93))
            w.writeframes(bytes(frames))


class _Load:
    """The busy GUI thread of the real player: paints, loads covers, scrolls lists. A short burst every 100 ms and a long stall every
    two seconds. It also measures the GUI lag (the delay of a 10 ms heartbeat)."""
    def __init__(self, enabled: bool):
        from PySide6.QtCore import QTimer
        self.enabled = enabled
        self.lag_max = 0.0
        self._last = time.perf_counter()
        self._n = 0
        self._beat = QTimer()
        self._beat.setInterval(10)
        self._beat.timeout.connect(self._on_beat)
        self._work = QTimer()
        self._work.setInterval(100)
        self._work.timeout.connect(self._on_work)

    def start(self) -> None:
        self._last = time.perf_counter()
        self.lag_max = 0.0
        self._beat.start()
        if self.enabled:
            self._work.start()

    def stop(self) -> None:
        self._beat.stop()
        self._work.stop()

    def _on_beat(self) -> None:
        now = time.perf_counter()
        self.lag_max = max(self.lag_max, (now - self._last) * 1000.0 - 10.0)
        self._last = now

    def _on_work(self) -> None:
        self._n += 1
        burst = 0.08 if self._n % 20 == 0 else 0.015          # 15 ms every 100 ms, 80 ms every two seconds
        end = time.perf_counter() + burst
        x = 0.0
        while time.perf_counter() < end:
            x += math.sqrt(12345.678)


def _pump(app, seconds: float, until: Optional[Callable[[], bool]] = None) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        if until and until():
            return True
        time.sleep(0.002)
    return bool(until and until())


def _snapshot() -> dict:
    snap = {"threads": threading.active_count(), "rss_mb": 0.0, "ffmpeg": -1}
    if psutil is not None:
        try:
            p = psutil.Process(os.getpid())
            snap["rss_mb"] = round(p.memory_info().rss / 1048576, 1)
            snap["ffmpeg"] = sum(1 for c in p.children(recursive=True) if "ffmpeg" in (c.name() or "").lower())
        except psutil.Error:
            pass
    return snap


# ---- 2. + 3. the buffer search and the repaint rate ---------------------------------------------------------------------
def test_buffer(app, media, song: Path, buffer_ms: int, seconds: float, loaded: bool) -> dict:
    from PySide6.QtCore import QUrl
    media.setBufferMs(buffer_ms)
    media.underruns = 0
    media.tick_peak_ms = 0.0
    load = _Load(loaded)
    media.setSource(QUrl.fromLocalFile(str(song)))
    media.play()
    load.start()
    _pump(app, 0.5)
    media.underruns = 0                                   # the start of a song is not counted
    _pump(app, seconds)
    load.stop()
    stats = media.stats()
    media.stop()
    return {"buffer_ms": buffer_ms, "underruns": stats["underruns"], "tick_peak_ms": stats["tick_peak_ms"],
            "gui_lag_max_ms": round(load.lag_max, 1), "queue_chunks": stats["queue_chunks"]}


def find_buffer(app, media, song: Path, seconds: float, progress) -> dict:
    results = []
    stable = None
    for ms in BUFFER_STEPS_MS:
        progress("buffer %4d ms ..." % ms)
        r = test_buffer(app, media, song, ms, seconds, loaded=True)
        results.append(r)
        progress("   underruns %d, longest tick %.1f ms, GUI lag %.0f ms" % (r["underruns"], r["tick_peak_ms"], r["gui_lag_max_ms"]))
        if r["underruns"] == 0 and stable is None:
            stable = ms
            break
    if stable is None:
        recommended = BUFFER_STEPS_MS[-1]
    else:
        i = BUFFER_STEPS_MS.index(stable)
        recommended = BUFFER_STEPS_MS[min(len(BUFFER_STEPS_MS) - 1, i + 1)]       # one step above the smallest stable one
    return {"results": results, "smallest_stable_ms": stable, "recommended_ms": max(recommended, DEFAULT_BUFFER_MS if stable is None else recommended)}


# ---- 4. the stress and leak test ----------------------------------------------------------------------------------------
def stress(app, media, song: Path, changes: int, minutes: float, progress) -> dict:
    from PySide6.QtCore import QUrl
    media.setBufferMs(DEFAULT_BUFFER_MS)
    media.underruns = 0
    media.tick_peak_ms = 0.0
    load = _Load(True)
    load.start()
    base = _snapshot()
    series = [dict(base, change=0)]
    n = 0
    t_end = time.time() + minutes * 60.0
    last_report = time.time()
    while n < changes or time.time() < t_end:
        n += 1
        media.setSource(QUrl.fromLocalFile(str(song)))
        media.play()
        _pump(app, 0.5)
        if n % 3 == 0:                                       # pause / continue / seek like a user
            media.pause()
            _pump(app, 0.15)
            media.play()
            media.setPosition(20000 + 1000 * (n % 30))
            _pump(app, 0.3)
        if n % 10 == 0 or time.time() - last_report > 30:
            last_report = time.time()
            snap = dict(_snapshot(), change=n)
            series.append(snap)
            progress("   %3d changes: threads %d, RSS %.1f MB, ffmpeg %d, underruns %d, GUI lag max %.0f ms" % (
                n, snap["threads"], snap["rss_mb"], snap["ffmpeg"], media.underruns, load.lag_max))
    media.stop()
    _pump(app, 1.0)
    load.stop()
    final = dict(_snapshot(), change=n)
    series.append(final)
    stats = media.stats()
    return {"changes": n, "seconds": None, "series": series, "base": base, "final": final, "underruns": stats["underruns"],
            "tick_peak_ms": stats["tick_peak_ms"], "gui_lag_max_ms": round(load.lag_max, 1)}


def judge(device: dict, buffer: Optional[dict], stress_result: Optional[dict], started: float) -> List[dict]:
    out: List[dict] = []

    def add(level, text):
        out.append({"level": level, "text": text})
    if device["hands_free"]:
        add("WARN", "This output looks like the Bluetooth hands-free / headset profile (%s): the sound is telephone quality. "
                    "Choose the stereo entry of the headphones in the Bluetooth planet." % device["name"])
    if not device["float32_stereo_by_rate"].get(str(device["preferred_rate"]), True):
        add("FAIL", "The output does not take 32-bit float at its own rate (%s Hz): the own engine cannot use it." % device["preferred_rate"])
    if buffer is not None:
        if buffer["smallest_stable_ms"] is None:
            add("FAIL", "Dropouts at every tested buffer size up to %d ms: the GUI thread is too busy for the sound." % BUFFER_STEPS_MS[-1])
        else:
            add("PASS", "No dropouts from a buffer of %d ms (recommended: %d ms)." % (buffer["smallest_stable_ms"], buffer["recommended_ms"]))
        worst = max((r["gui_lag_max_ms"] for r in buffer["results"]), default=0.0)
        add("PASS" if worst < GUI_LAG_WARN_MS else "WARN",
            "GUI lag with the synthetic load: %.0f ms at most (the load itself blocks up to 80 ms)." % worst)
    if stress_result is not None:
        s = stress_result
        grown = s["final"]["threads"] - s["base"]["threads"]
        per = grown / max(1, s["changes"])
        add("PASS" if per <= 0 else ("WARN" if per < THREADS_PER_CHANGE_FAIL else "FAIL"),
            "Threads after %d song changes: %+d (start %d, end %d)." % (s["changes"], grown, s["base"]["threads"], s["final"]["threads"]))
        if s["final"]["ffmpeg"] >= 0:
            add("PASS" if s["final"]["ffmpeg"] == 0 else "FAIL", "ffmpeg processes left after stopping: %d." % s["final"]["ffmpeg"])
            seconds = max(1.0, time.time() - started)
            growth = s["final"]["rss_mb"] - s["series"][1]["rss_mb"] if len(s["series"]) > 2 else s["final"]["rss_mb"] - s["base"]["rss_mb"]
            rate = growth / (seconds / 60.0)
            add("PASS" if growth < RSS_GROWTH_WARN_MB and rate < RSS_GROWTH_FAIL_MB_MIN else ("FAIL" if rate >= RSS_GROWTH_FAIL_MB_MIN else "WARN"),
                "Memory after the first changes: %+.1f MB (%.1f MB per minute)." % (growth, rate))
        else:
            add("WARN", "psutil is not installed: memory and ffmpeg processes were not measured (pip install psutil).")
        add("PASS" if s["underruns"] == 0 else "FAIL", "Dropouts during the stress test: %d." % s["underruns"])
        lag = s["gui_lag_max_ms"]
        add("PASS" if lag < GUI_LAG_WARN_MS * 2 else ("WARN" if lag < GUI_LAG_FAIL_MS * 2 else "FAIL"),
            "Largest GUI lag during the stress test: %.0f ms (the synthetic load blocks up to 80 ms)." % lag)
    return out


def profile_from(device: dict, buffer: Optional[dict], stress_result: Optional[dict]) -> dict:
    lag = max([r["gui_lag_max_ms"] for r in (buffer or {}).get("results", [])] + [(stress_result or {}).get("gui_lag_max_ms", 0.0)] or [0.0])
    hz = 20 if lag < 200 else 15
    return {"device_name": device["name"], "sample_rate": device["preferred_rate"], "channels": 2, "sample_format": "float32",
            "audio_buffer_ms": (buffer or {}).get("recommended_ms", DEFAULT_BUFFER_MS), "ui_refresh_hz": hz,
            "ffmpeg_readrate": 1.05, "underruns_during_test": (buffer or {}).get("results", [{}])[-1].get("underruns", 0)}


def run(ffmpeg, level: str = "quick", device_name: str = "", minutes: float = 0.0, progress: Callable[[str], None] = print,
        data_dir: Optional[Path] = None) -> dict:
    """Runs the calibration (needs a QGuiApplication). level: quick | stress."""
    from PySide6.QtGui import QGuiApplication
    from . import dsp_media
    from ..core import dsp
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    started = time.time()
    if not dsp_media.usable(ffmpeg):
        raise RuntimeError("The own engine needs numpy and ffmpeg (ffmpeg: %s)." % ffmpeg)
    qdev = pick_device(device_name)
    device = device_report(qdev)
    progress("Output: %s (%d Hz, %s)%s" % (device["name"], device["preferred_rate"], device["preferred_format"],
                                          "  - hands-free profile!" if device["hands_free"] else ""))
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    song = Path(tmp.name) / "calibration.wav"
    progress("Making the test song ...")
    _write_test_song(song, 150)
    media = dsp_media.DspMedia(ffmpeg)
    media.setDevice(qdev)
    media.setVolume(0.0)
    media.setConfig(dsp.config_from({"eq_on": True, "eq": [2, 1, 0, 0, 0, 0, 1, 2, 2, 3], "crossfeed": "light", "limiter": True}))
    try:
        buffer = find_buffer(app, media, song, 10.0 if level == "quick" else 30.0, progress)
        stress_result = None
        if level == "stress":
            progress("Stress test: song changes, pause, seek ...")
            stress_result = stress(app, media, song, 40, minutes, progress)
    finally:
        media.stop()
        media.deleteLater()
        _pump(app, 0.3)
        tmp.cleanup()
    verdicts = judge(device, buffer, stress_result, started)
    profile = profile_from(device, buffer, stress_result)
    report = {"level": level, "seconds": round(time.time() - started, 1), "device": device, "buffer": buffer, "stress": stress_result,
              "verdicts": verdicts, "profile": profile}
    if data_dir is not None:
        data_dir = Path(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "audio_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
        (data_dir / "audio_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def apply_profile(settings_path: Path, profile: dict) -> None:
    """Writes the measured values into the settings file (the app must not run: it would overwrite them when it closes)."""
    from ..core.settings import Settings
    s = Settings.load(settings_path)
    s.audio_buffer_ms = int(profile["audio_buffer_ms"])
    s.ui_refresh_hz = int(profile["ui_refresh_hz"])
    s.validate()
    s.save(settings_path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audio performance and stability calibration of Yeal")
    ap.add_argument("--quick", action="store_true", help="buffer search only (about 1 minute)")
    ap.add_argument("--stress", action="store_true", help="buffer search + song change stress and leak test")
    ap.add_argument("--minutes", type=float, default=0.0, help="stress test: keep changing songs for this many minutes")
    ap.add_argument("--device", default="", help="part of the name of the output (default: the system default)")
    ap.add_argument("--apply", action="store_true", help="write the measured values into the settings")
    ap.add_argument("--list", action="store_true", help="only list the outputs and their formats")
    args = ap.parse_args(argv)
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    if args.list:
        for d in list_devices():
            print(json.dumps(d, indent=2))
        return 0
    from .. import platforms
    ctx = platforms.detect()
    level = "stress" if args.stress or args.minutes else "quick"
    try:
        report = run(ctx.ffmpeg, level, args.device, args.minutes, print, ctx.data_dir)
    except RuntimeError as exc:
        print("Calibration not possible:", exc)
        return 2
    print()
    for v in report["verdicts"]:
        print("%-5s %s" % (v["level"], v["text"]))
    print("\nRecommended: audio_buffer_ms=%d, ui_refresh_hz=%d  (files: %s)" % (
        report["profile"]["audio_buffer_ms"], report["profile"]["ui_refresh_hz"], ctx.data_dir))
    if args.apply:
        apply_profile(ctx.settings_path, report["profile"])
        print("Written to the settings: %s" % ctx.settings_path)
    return 1 if any(v["level"] == "FAIL" for v in report["verdicts"]) else 0


if __name__ == "__main__":
    sys.exit(main())
