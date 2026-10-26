"""The runtime monitor (YEAL_PERF=1): it prints a line with CPU / RAM / threads / GUI lag."""
import io
import os
import sys
import time
import unittest
from contextlib import redirect_stdout

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import _path  # noqa: F401

try:
    from PySide6.QtGui import QGuiApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class PerfMonitorTests(unittest.TestCase):
    def test_prints_a_line_and_measures_a_blocked_gui(self):
        from yeal.ui import perfmon
        app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        mon = perfmon.PerfMonitor(interval_ms=300)
        out = io.StringIO()
        with redirect_stdout(out):
            time.sleep(0.25)                      # the GUI thread is blocked for a quarter second ...
            end = time.time() + 0.8
            while time.time() < end:
                app.processEvents()
                time.sleep(0.01)
        mon.deleteLater()
        text = out.getvalue()
        self.assertIn("[perf]", text)
        self.assertIn("GUI lag", text)
        self.assertIn("threads=", text)

    def test_enabled_by_the_environment(self):
        from yeal.ui import perfmon
        old = os.environ.pop("YEAL_PERF", None)
        try:
            self.assertFalse(perfmon.enabled())
            os.environ["YEAL_PERF"] = "1"
            self.assertTrue(perfmon.enabled())
        finally:
            os.environ.pop("YEAL_PERF", None)
            if old is not None:
                os.environ["YEAL_PERF"] = old


if __name__ == "__main__":
    unittest.main()
