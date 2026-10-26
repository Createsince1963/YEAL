"""Measurement of the player: frame cost of the sun view with a moving level, and thread / memory / process growth over many
song changes with Yeal's own engine. Run: python bench.py [gui|changes|both]"""
import gc
import math
import os
import struct
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
sys.path.insert(0, r"C:\Users\mail\AI_Coworker_Claude\APK YEAL\tests")
import _path  # noqa
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickWindow, QQuickItem
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQuick import QQuickView

from test_core import FakeYDL, make_ctx
from yeal.core.engine import Engine
from yeal.ui.backend import Backend
from yeal.platforms import desktop

try:
    import psutil
    PROC = psutil.Process(os.getpid())
except ImportError:
    PROC = None

QML_DIR = Path(r"C:\Users\mail\AI_Coworker_Claude\APK YEAL\BIN\versions\v0.1\PyModul\yeal\ui\qml")
mode = sys.argv[1] if len(sys.argv) > 1 else "both"

QQuickStyle.setStyle("Basic")
app = QGuiApplication.instance() or QGuiApplication(sys.argv)
tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
ctx = make_ctx(tmp.name)
ctx.ffmpeg = desktop.find_ffmpeg()
backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
player = backend.localPlayer


def write_wav(path, seconds=20):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
        frames = bytearray()
        for i in range(44100 * seconds):
            v = int(32767 * 0.5 * math.sin(2 * math.pi * 440 * i / 44100))
            frames += struct.pack("<hh", v, v)
        w.writeframes(bytes(frames))


def pump(sec):
    end = time.time() + sec
    while time.time() < end:
        app.processEvents()
        time.sleep(0.002)


def stats(tag):
    ff = 0
    if PROC:
        ff = sum(1 for c in PROC.children(recursive=True) if "ffmpeg" in (c.name() or "").lower())
    print("%-22s threads=%3d  rss=%7.1f MB  ffmpeg=%d  pyobjs=%d" % (
        tag, threading.active_count(), (PROC.memory_info().rss / 1048576) if PROC else 0, ff, len(gc.get_objects())))


if mode in ("gui", "both"):
    from PySide6.QtQml import QQmlEngine
    engine = QQmlEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("jobModel", backend.model)
    engine.rootContext().setContextProperty("tidal", backend.tidal)
    for w, h in ((1000, 700), (1920, 1000)):
        win = QQuickWindow()
        win.resize(w, h)
        comp = QQmlComponent(engine)
        comp.setData(b"import QtQuick\nItem { width: %d; height: %d\nLocalPlayerView { anchors.fill: parent }\n}\n" % (w, h),
                     QUrl.fromLocalFile(str(QML_DIR / "_bench.qml")))
        root = comp.create()
        assert root is not None, [e.toString() for e in comp.errors()]
        root.setParentItem(win.contentItem())
        win.show()
        pump(1.0)
        # a level change like the 30 Hz tick: the Canvases repaint, the window is rendered
        frames = 90
        t0 = time.perf_counter()
        for i in range(frames):
            player._level = 0.3 + 0.5 * abs(math.sin(i / 5))
            player.levelChanged.emit()
            app.processEvents()
            win.grabWindow()
        dt = (time.perf_counter() - t0) / frames * 1000
        print("sun view %dx%d: %.1f ms per level tick incl. render (budget 33 ms at 30 Hz)" % (w, h, dt))
        # the same without the big sky canvas repaint: only levelChanged
        root.deleteLater()
        win.close()
        pump(0.3)

if mode in ("changes", "both"):
    wav = Path(tmp.name) / "s.wav"
    write_wav(wav)
    item = {"kind": "track", "id": str(wav), "title": "S", "subtitle": "", "file": str(wav), "cover": "", "duration": 0, "url": ""}
    backend.setSetting("audio_engine", "dsp")
    player.setVolume(0)
    stats("start")
    for n in range(1, 31):
        player.playItems([dict(item, id=str(wav) + str(n))], 0, "x")
        pump(0.5)
        if n % 10 == 0:
            gc.collect()
            stats("after %d changes" % n)
    player.stop()
    pump(1.0)
    gc.collect()
    stats("stopped")

backend.shutdown()
