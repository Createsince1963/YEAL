"""TIDAL DIY (0.9.1): every QML file of the own TIDAL view loads without QML errors (offscreen, real Backend)."""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import _path  # noqa: F401

try:
    from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt, QUrl, qInstallMessageHandler
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
    "TidalDragSource": "TidalDragSource { item: ({ url: 'https://tidal.com/browse/album/1' }) }",
    "TidalTile": "TidalTile { item: ({ kind: 'album', id: '1', title: 'A', subtitle: 'B', url: 'https://tidal.com/browse/album/1' }) }",
    "TidalTrackRow": "TidalTrackRow { width: 600; item: ({ kind: 'track', id: '1', title: 'T', subtitle: 'S', album: 'A', duration: 60, url: 'https://tidal.com/browse/track/1' }) }",
    "TidalPlaylists": "TidalPlaylists { width: 220; height: 400 }",
    "TidalQueue": "TidalQueue { width: 300; height: 400 }",
    "TidalPlayerBar": "TidalPlayerBar { width: 1000 }",
    "TidalTrackPlayer": "TidalTrackPlayer { width: 700; height: 300 }",
    "TidalTrackPanel": "TidalTrackPanel { width: 480; height: 300 }",
    "TidalQueueDrop": "ListView { id: lv; width: 200; height: 200; TidalQueueDrop { anchors.fill: parent; list: lv } }",
    "TidalDock": "TidalDock { width: 300; height: 300; title: 'Test'; Text { text: 'content' } }",
    "TidalDockFloating": "TidalDock { width: 300; height: 300; title: 'Test'; side: 'float'; Text { text: 'content' } }",
    "WorkflowPanel": "WorkflowPanel { anchors.fill: parent; inSidebar: true; tidalPlayer: true }",
    "SettingsPage": "SettingsPage { anchors.fill: parent; Component.onCompleted: showTidal() }",
}
ERRORS = ("ReferenceError", "TypeError", "is not defined", "Unable to assign", "Cannot ", "Error")


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class TidalGuiQmlTest(unittest.TestCase):
    maxDiff = None
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

    def test_player_style_and_vis_settings(self):
        b = self.backend
        b.setSetting("tidal_player_style", "track")
        self.assertEqual(b.settings["tidal_player_style"], "track")
        b.setSetting("tidal_player_style", "wide")                      # not a style: falls back to the classic bar
        self.assertEqual(b.settings["tidal_player_style"], "bar")
        self.assertEqual(b.settings["tidal_player_vis_mode"], "song")           # the default: loudness of the whole song
        for mode in ("flow", "off", "song"):
            b.setSetting("tidal_player_vis_mode", mode)
            self.assertEqual(b.settings["tidal_player_vis_mode"], mode)
        b.setSetting("tidal_player_vis_mode", "spectrum")                        # not a mode: back to the default
        self.assertEqual(b.settings["tidal_player_vis_mode"], "song")

    def test_layout_changes_are_saved_and_reset(self):
        """Docking, detaching, hiding and the player position end up validated in the tidal_layout setting."""
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { width: 1200; height: 800\nTidalHome { objectName: 'home'; anchors.fill: parent }\n}\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_layout.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
        home = root.findChild(QObject, "home")
        self.assertIsNotNone(home)

        def call(name, *args):
            QMetaObject.invokeMethod(home, name, Qt.DirectConnection, *[Q_ARG("QVariant", a) for a in args])
            for _ in range(10):
                self.app.processEvents()

        def layout():
            return self.backend.settings["tidal_layout"]

        call("resetLayout")
        call("setSide", "queue", "left")
        self.assertEqual(layout()["queue"]["dock"], "left")
        self.assertEqual(home.property("_order"), "playlists,queue,c")     # both areas left of the page
        call("setSide", "playlists", "right")
        self.assertEqual(home.property("_order"), "queue,c,playlists")
        call("setSide", "queue", "float")
        self.assertEqual(layout()["queue"]["dock"], "float")
        self.assertIn("x", layout()["queue"])
        call("togglePane", "queue")                                          # hide ...
        self.assertEqual(layout()["queue"]["dock"], "hidden")
        call("togglePane", "queue")                                          # ... and back to where it was
        self.assertEqual(layout()["queue"]["dock"], "float")
        call("setPlayerTop", True)
        self.assertEqual(layout()["player"], "top")
        call("resetLayout")
        self.assertEqual(layout()["queue"]["dock"], "right")
        self.assertEqual(layout()["playlists"]["dock"], "left")
        self.assertEqual(layout()["player"], "bottom")
        root.deleteLater()

    def test_tidal_options_tiles_open_one_group_and_fold(self):
        """Two-column tiles: one group open at a time, the overview line follows the settings, folding is remembered."""
        js = lambda v: v.toVariant() if hasattr(v, 'toVariant') else v
        b = self.backend
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { width: 420; height: 600\nTidalOptions { objectName: 'opts'; width: 400 }\n}\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_opts.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
        opts = root.findChild(QObject, "opts")
        b.setSetting("tidal_quality", "high")
        b.setSetting("tidal_videos", "none")
        for _ in range(5):
            self.app.processEvents()
        keys = [g["key"] for g in js(opts.property("shown"))]
        self.assertEqual(keys, ["tidal_quality", "tidal_videos", "tidal_atmos", "tidal_singles", "_extras"])  # no video quality without videos
        b.setSetting("tidal_videos", "allow")
        for _ in range(5):
            self.app.processEvents()
        self.assertIn("tidal_video_quality", [g["key"] for g in js(opts.property("shown"))])
        self.assertIsNone(js(opts.property("openGroup")))
        opts.setProperty("openKey", "_extras")
        self.assertEqual(js(opts.property("openGroup"))["key"], "_extras")
        opts.setProperty("openKey", "tidal_atmos")
        self.assertEqual(js(opts.property("openGroup"))["key"], "tidal_atmos")
        self.assertIn("High (FLAC)", opts.property("overview"))
        b.setSetting("tidal_opts_collapsed", True)
        self.assertIs(b.settings["tidal_opts_collapsed"], True)
        b.setSetting("tidal_opts_collapsed", False)
        self.assertIs(b.settings["tidal_opts_collapsed"], False)
        root.deleteLater()

    def test_table_header_and_rows_stay_left_aligned_when_a_column_is_resized(self):
        """The header cells sit exactly over the cells of the rows (also after dragging a column edge)."""
        from PySide6.QtCore import QPointF
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { width: 1100; height: 500\nTidalTrackList { objectName: 'list'; anchors.fill: parent; "
                     b"items: [{kind: 'track', id: '1', title: 'One', subtitle: 'Artist A', album: 'Album A', duration: 100, quality: 'HiFi'},"
                     b"{kind: 'track', id: '2', title: 'Two', subtitle: 'Artist B', album: 'Album B', duration: 120, quality: 'MAX'}] }\n}\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_cols.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
        lst = root.findChild(QObject, "list")
        for _ in range(30):
            self.app.processEvents()

        def named(item, name, out):          # delegates of a ListView are only in the visual tree
            if item.objectName() == name:
                out.append(item)
            for child in item.childItems():
                named(child, name, out)
            return out

        def x_of(name, which=0):
            items = named(root, name, [])
            self.assertGreater(len(items), which, name)
            return items[which].mapToItem(root, QPointF(0, 0)).x()

        for artist_w, album_w in ((170, 190), (260, 190), (260, 120), (100, 300)):
            lst.setProperty("artistW", artist_w)
            lst.setProperty("albumW", album_w)
            for _ in range(10):
                self.app.processEvents()
            for row in (0, 1):
                self.assertAlmostEqual(x_of("artistCell"), x_of("artistText", row), delta=1.0, msg=(artist_w, album_w))
                self.assertAlmostEqual(x_of("albumCell"), x_of("albumText", row), delta=1.0, msg=(artist_w, album_w))
        root.deleteLater()

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
