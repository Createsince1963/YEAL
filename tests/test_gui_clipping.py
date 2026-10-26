"""No button is cut off: in narrow planet cards every Chip / AppButton / Button lies completely inside the card.
The rule for the GUI: rows of buttons are Flow items (they wrap), never plain Row items wider than the card."""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import _path  # noqa: F401

try:
    from PySide6.QtCore import QUrl, qInstallMessageHandler
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickItem, QQuickWindow
    from PySide6.QtQuickControls2 import QQuickStyle
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

from test_core import FakeYDL, make_ctx  # noqa: E402

QML_DIR = _path.PYMODUL / "yeal" / "ui" / "qml"
CARDS = ["SunSound", "SunSettings", "SunSpeaker"]
WIDTHS = [230, 270, 320]
BUTTONS = ("Chip", "AppButton", "Button", "TextBtn", "IconBtn")


def class_of(item) -> str:
    return item.metaObject().className().split("_QMLTYPE")[0].split("_QML_")[0]


def walk(item):
    for child in item.childItems():
        yield child
        yield from walk(child)


def clipped(card, width):
    """Buttons (visible ones) that reach out of the card on the left or right."""
    out = []
    for item in walk(card):
        if class_of(item) not in BUTTONS or not item.isVisible() or item.width() <= 0:
            continue
        pos = item.mapToItem(card, 0, 0)
        if pos.x() < -0.5 or pos.x() + item.width() > width + 0.5:
            out.append("%s at x=%.0f width=%.0f (card %d)" % (class_of(item), pos.x(), item.width(), width))
    return out


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class ClippingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from yeal.core.engine import Engine
        from yeal.ui.backend import Backend
        cls.messages = []
        qInstallMessageHandler(lambda mode, ctx, msg: cls.messages.append(msg))
        QQuickStyle.setStyle("Basic")
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        ctx = make_ctx(cls.tmp.name)
        cls.backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
        cls.backend.setSetting("audio_engine", "dsp")               # the Sound card shows all its filters
        cls.engine = QQmlEngine()
        cls.engine.rootContext().setContextProperty("backend", cls.backend)
        cls.engine.rootContext().setContextProperty("jobModel", cls.backend.model)
        if hasattr(cls.backend, "tidal"):
            cls.engine.rootContext().setContextProperty("tidal", cls.backend.tidal)

    @classmethod
    def tearDownClass(cls):
        cls.backend.shutdown()
        cls.tmp.cleanup()

    def test_no_button_is_cut_off(self):
        for name in CARDS:
            for width in WIDTHS:
                with self.subTest(card=name, width=width):
                    comp = QQmlComponent(self.engine)
                    comp.setData(("import QtQuick\nItem { width: 1200; height: 900\n%s { id: card; objectName: 'card'; width: %d; height: 700 }\n}\n"
                                  % (name, width)).encode(), QUrl.fromLocalFile(str(QML_DIR / ("_test_%s.qml" % name))))
                    root = comp.create()
                    self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
                    win = QQuickWindow()                       # positioners (Flow) lay out only inside a window
                    win.resize(1200, 900)
                    root.setParentItem(win.contentItem())
                    win.show()
                    for _ in range(40):
                        self.app.processEvents()
                    card = [c for c in root.childItems() if c.objectName() == "card"][0]
                    buttons = [i for i in walk(card) if class_of(i) in BUTTONS and i.isVisible()]
                    self.assertTrue(buttons, "no button found in %s" % name)
                    self.assertEqual(clipped(card, width), [])
                    win.close()
                    root.deleteLater()


if __name__ == "__main__":
    unittest.main()
