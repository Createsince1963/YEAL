"""TIDAL DIY (0.9.1): every QML file of the own TIDAL view loads without QML errors (offscreen, real Backend)."""
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
    from PySide6.QtQuickControls2 import QQuickStyle
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

from test_core import FakeYDL, make_ctx  # noqa: E402

QML_DIR = _path.PYMODUL / "yeal" / "ui" / "qml"
# Each entry: QML snippet placed in a 1200x800 item. Components that need properties get them here.
COMPONENTS = {
    "TidalHome": "TidalHome { anchors.fill: parent }",
    "Sidebar": "Sidebar { anchors.fill: parent; rowNav: true; player: 'tidaldiy' }",
    "AppMenu": "AppMenu { AppMenuItem { text: 'Tidal Max (FLAC up to 24-bit / 192 kHz)' } }",
    "TidalOptions": "TidalOptions { width: 400 }",
    "WorkflowPanel": "WorkflowPanel { anchors.fill: parent; inSidebar: true; tidalPlayer: true }",
    "SettingsPage": "SettingsPage { anchors.fill: parent; Component.onCompleted: showTidal() }",
}
ERRORS = ("ReferenceError", "TypeError", "is not defined", "Unable to assign", "Cannot ", "Error")


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class TidalGuiQmlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from yeal.core.engine import Engine
        from yeal.ui.backend import Backend
        cls.messages = []
        qInstallMessageHandler(lambda mode, ctx, msg: cls.messages.append(msg))
        QQuickStyle.setStyle("Basic")
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        cls.tmp = tempfile.TemporaryDirectory()
        ctx = make_ctx(cls.tmp.name)
        cls.backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
        cls.engine = QQmlEngine()
        cls.engine.rootContext().setContextProperty("backend", cls.backend)
        cls.engine.rootContext().setContextProperty("jobModel", cls.backend.model)
        if hasattr(cls.backend, "tidal"):
            cls.engine.rootContext().setContextProperty("tidal", cls.backend.tidal)

    @classmethod
    def tearDownClass(cls):
        cls.backend.shutdown()
        cls.tmp.cleanup()

    def test_components_load(self):
        for name, snippet in COMPONENTS.items():
            with self.subTest(component=name):
                start = len(self.messages)
                comp = QQmlComponent(self.engine)
                comp.setData(("import QtQuick\nItem { width: 1200; height: 800\n%s\n}\n" % snippet).encode(),
                             QUrl.fromLocalFile(str(QML_DIR / ("_test_%s.qml" % name))))
                obj = comp.create()
                errors = [e.toString() for e in comp.errors()]
                self.assertIsNotNone(obj, "\n".join(errors))
                for _ in range(20):
                    self.app.processEvents()
                bad = [m for m in self.messages[start:] if ".qml" in m and any(w in m for w in ERRORS)]
                self.assertEqual(bad, [])
                obj.deleteLater()

    def test_tidal_option_settings(self):
        """The chips write through backend.setSetting; bad values are refused, sizes clamped."""
        b = self.backend
        for key, good, bad in (("tidal_atmos", "only", "maybe"), ("tidal_singles", "include", "all"),
                               ("tidal_videos", "none", "some")):
            b.setSetting(key, good)
            self.assertEqual(b.settings[key], good)
            b.setSetting(key, bad)
            self.assertEqual(b.settings[key], good)
        for key in ("tidal_lyrics", "tidal_lrc", "tidal_cover_embed", "tidal_cover_file", "tidal_m3u", "tidal_html",
                    "tidal_no_skip", "tidal_rewrite"):
            b.setSetting(key, True)
            self.assertIs(b.settings[key], True)
            b.setSetting(key, False)
            self.assertIs(b.settings[key], False)
        b.setSetting("tidal_volume", 500)
        self.assertEqual(b.settings["tidal_volume"], 100)
        cfg = b._tidal_config()
        self.assertEqual(cfg["atmos"], "only")
        self.assertEqual(cfg["extras"]["m3u"], False)

    def test_menu_fits_widest_entry(self):
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { width: 1200; height: 800\n"
                     b"property real itemW: menu.itemAt(0) ? menu.itemAt(0).implicitWidth : 0\n"
                     b"AppMenu { id: menu\n"
                     b"AppMenuItem { text: 'Tidal Max (FLAC up to 24-bit / 192 kHz) and a very long tail' } } }\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_menu.qml")))
        obj = comp.create()
        self.assertIsNotNone(obj, "\n".join(e.toString() for e in comp.errors()))
        self.assertGreater(obj.property("itemW"), 200)
        obj.deleteLater()


if __name__ == "__main__":
    unittest.main()
