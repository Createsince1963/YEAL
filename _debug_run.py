"""Debug launcher for Yeal (no change to the app code): starts main.py, brings the window to the front and
saves screenshots of every screen at set times to _to_delete/shot_<ms>_screen<N>.png.
Env: YEAL_SHOTS = comma separated milliseconds after start (default 3000,6000,9000,14000,18000)."""
import faulthandler
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYMOD = ROOT / "BIN" / "versions" / "v0.1" / "PyModul"
sys.path.insert(0, str(PYMOD))
faulthandler.enable()
faulthandler.dump_traceback_later(60, repeat=True)
SHOTS = ROOT / "_to_delete"
TIMES = [int(x) for x in os.environ.get("YEAL_SHOTS", "3000,6000,9000,14000,18000").split(",")]

from PySide6.QtCore import QTimer, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

import yeal.ui.backend as backend_mod  # noqa: E402

_orig_init = backend_mod.Backend.__init__


def _patched_init(self, *a, **k):
    _orig_init(self, *a, **k)

    def front():
        for w in QGuiApplication.topLevelWindows():
            if w.isVisible():
                try:
                    if w.windowStates() & Qt.WindowMinimized:
                        w.showNormal()
                    w.setFlag(Qt.WindowStaysOnTopHint, True)
                    w.raise_()
                    w.requestActivate()
                except Exception:  # noqa: BLE001
                    pass

    def grab(ms):
        try:
            for i, screen in enumerate(QGuiApplication.screens()):
                screen.grabWindow(0).save(str(SHOTS / ("shot_%05d_screen%d.png" % (ms, i))))
        except Exception as exc:  # noqa: BLE001
            print("SHOT FAILED", exc, flush=True)

    for ms in TIMES:
        QTimer.singleShot(ms - 500, front)
        QTimer.singleShot(ms, lambda m=ms: grab(m))
    QTimer.singleShot(max(TIMES) + 1500, QGuiApplication.quit)


backend_mod.Backend.__init__ = _patched_init
backend_mod.Backend._poll_drives = lambda self: None     # no drive dialog in test runs
sys.argv = [str(PYMOD / "main.py"), "--selftest"]
runpy.run_path(str(PYMOD / "main.py"), run_name="__main__")
