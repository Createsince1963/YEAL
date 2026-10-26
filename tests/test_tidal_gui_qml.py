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
    "Sidebar": "Sidebar { anchors.fill: parent; rowNav: true; player: 'local' }",
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
    "LocalPlayerView": "LocalPlayerView { anchors.fill: parent }",
    "SunSound": "SunSound { width: 300; height: 400 }",
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

    def test_player_colour_and_orbit_settings(self):
        b = self.backend
        self.assertEqual(b.settings["tidal_player_color"], "green")
        for name in ("blue", "red", "yellow", "purple", "orange", "pink", "cyan", "white", "green"):
            b.setSetting("tidal_player_color", name)
            self.assertEqual(b.settings["tidal_player_color"], name)
        b.setSetting("tidal_player_color", "#12AbEf")                       # any #rrggbb, kept in lower case
        self.assertEqual(b.settings["tidal_player_color"], "#12abef")
        b.setSetting("tidal_player_color", "turquoise")                     # unknown: back to green
        self.assertEqual(b.settings["tidal_player_color"], "green")
        b.setSetting("tidal_player_color", "#12345")
        self.assertEqual(b.settings["tidal_player_color"], "green")
        self.assertIs(b.settings["local_orbit"], True)
        b.setSetting("local_orbit", False)
        self.assertIs(b.settings["local_orbit"], False)
        b.setSetting("local_orbit", True)

    def test_theme_knows_the_player_colours(self):
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { objectName: 'r'; property string blue: Theme.playerColor('blue'); "
                     b"property string hex: Theme.playerColor('#ABCDEF'); property string bad: Theme.playerColor('nope'); "
                     b"property int count: Theme.playerColors.length }\n", QUrl.fromLocalFile(str(QML_DIR / "_test_theme.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
        self.assertEqual(root.property("blue"), "#3d9bff")
        self.assertEqual(root.property("hex"), "#abcdef")
        self.assertEqual(root.property("bad"), "#1fcf8f")                   # unknown: the green
        self.assertEqual(root.property("count"), 9)
        root.deleteLater()

    def test_speaker_planet_shows_the_speakers_as_moons(self):
        import time
        b = self.backend
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { objectName: 'r'; width: 460; height: 200\n"
                     b"SunSpeaker { anchors.fill: parent; group: \"wlan\"; player: backend.localPlayerObject }\n}\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_moons.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))

        def moons(item, out):
            if item.objectName() == "moon":
                out.append(item)
            for child in item.childItems():
                moons(child, out)
            return out

        def settle():
            end = time.time() + 0.3
            while time.time() < end:
                self.app.processEvents()
                time.sleep(0.01)
        saved = list(b._stream_found)
        try:
            for count in (0, 1, 3, 8):
                b._stream_found = [{"id": "dev%d" % i, "name": "Speaker %d" % i, "host": "192.168.1.%d" % i} for i in range(count)]
                b.streamChanged.emit()
                settle()
                found = moons(root, [])
                self.assertEqual(len(found), count, count)
                # every moon sits inside the sky and no two moons lie on top of each other
                spots = [(m.x(), m.y()) for m in found]
                self.assertEqual(len(set(spots)), len(spots), spots)
                self.assertTrue(all(0 <= x <= 460 and -10 <= y <= 200 for x, y in spots), spots)
        finally:
            b._stream_found = saved
            b.streamChanged.emit()
        root.deleteLater()

    def test_bluetooth_planet_shows_the_outputs_of_this_pc(self):
        import time
        b = self.backend
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { objectName: 'r'; width: 420; height: 200\n"
                     b"SunSpeaker { anchors.fill: parent; mode: 'pc'; player: backend.tidal.playerObject }\n}\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_bt.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))

        def moons(item, out):
            if item.objectName() == "moon":
                out.append(item)
            for child in item.childItems():
                moons(child, out)
            return out
        end = time.time() + 0.3
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertEqual(len(moons(root, [])), len(b.audioOutputs))         # one moon for every output Windows lists
        root.deleteLater()

    def test_tidal_sun_view_has_the_bluetooth_planet_and_two_cards_share_the_right_column(self):
        import time
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { width: 1400; height: 900\nTidalSunView { objectName: 'v'; anchors.fill: parent }\n}\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_diysun.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
        view = root.findChild(QObject, "v")
        keys = [p["key"] for p in view.property("planets").toVariant()]
        self.assertIn("bluetooth", keys)
        self.assertEqual(len(keys), len(set(keys)))
        view.setProperty("opened", {"queue": True, "bluetooth": True})
        end = time.time() + 0.5
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)
        def card(item, name):
            if item.objectName() == name:
                return item
            for child in item.childItems():
                found = card(child, name)
                if found is not None:
                    return found
            return None
        queue, output = card(root, "card-queue"), card(root, "card-bluetooth")
        self.assertIsNotNone(queue)
        self.assertIsNotNone(output)
        self.assertEqual(queue.x(), output.x())                              # the same column ...
        self.assertLess(queue.y() + queue.height(), output.y())              # ... one above the other, not overlapping
        self.assertAlmostEqual(queue.height(), output.height(), delta=1)
        self.assertLessEqual(output.y() + output.height(), 900 - 10 + 1)
        view.setProperty("opened", {"queue": True})                          # alone it takes the whole column again
        end = time.time() + 0.5
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertGreater(queue.height(), 900 - 40)
        root.deleteLater()

    def test_card_opens_where_the_planet_stands_and_zooms_for_editing(self):
        import time
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { width: 1400; height: 900\nLocalPlayerView { objectName: 'v'; anchors.fill: parent }\n}\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_localsun.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
        view = root.findChild(QObject, "v")

        def pump():
            end = time.time() + 0.5
            while time.time() < end:
                self.app.processEvents()
                time.sleep(0.01)

        def card(item, name):
            if item.objectName() == name:
                return item
            for child in item.childItems():
                found = card(child, name)
                if found is not None:
                    return found
            return None
        view.setProperty("opened", {"library": True})
        pump()
        library = card(root, "card-library")
        self.assertLess(library.x(), 100)                                    # the library planet stands on the left: left column
        self.b_set_layout({"local.library": {"deg": 0, "r": 1}})
        pump()
        self.assertGreater(library.x(), 1000)                                # dragged to the right: the card follows it
        self.b_set_layout({})
        view.setProperty("opened", {"folders": True})
        pump()
        folders = card(root, "card-folders")
        small = folders.width()
        view.setProperty("zoomKey", "folders")
        pump()
        self.assertGreater(folders.width(), small * 2)                       # edit mode: the card grows ...
        view.setProperty("zoomKey", "")
        pump()
        self.assertAlmostEqual(folders.width(), small, delta=1)              # ... and is the normal size again
        root.deleteLater()

    def test_fans_show_the_next_and_the_last_played_songs(self):
        import time
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { width: 1400; height: 900\nLocalPlayerView { objectName: 'v'; anchors.fill: parent }\n}\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_fans.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
        view = root.findChild(QObject, "v")
        player = self.backend.localPlayer
        songs = [{"kind": "track", "id": "t%d" % i, "title": "Song %d" % i, "subtitle": "A", "file": "", "cover": "", "duration": 0, "url": ""}
                 for i in range(4)]
        player.queue.reset(songs, 0)
        player._history = list(reversed(songs[:3]))                         # what was played: newest first, the first one plays now
        player.historyChanged.emit()
        view.setProperty("nextOpen", True)
        view.setProperty("pastOpen", True)
        end = time.time() + 1.2
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertEqual([t["title"] for t in view.property("nextSongs")], ["Song 1", "Song 2", "Song 3"])
        self.assertEqual(len(view.property("pastSongs").toVariant()), 2)
        self.assertEqual(len(player.upcoming(2)), 2)
        root.deleteLater()

    def b_set_layout(self, layout):
        self.backend.setSetting("sun_layout", layout)

    def test_sun_settings_are_validated(self):
        b = self.backend
        b.setSetting("sun_scale", 9)
        self.assertEqual(b.settings["sun_scale"], 3.0)
        b.setSetting("sun_scale", 0.01)
        self.assertEqual(b.settings["sun_scale"], 0.5)
        b.setSetting("sun_scale", 1.234)
        self.assertEqual(b.settings["sun_scale"], 1.23)
        b.setSetting("sun_layout", {"local.queue": {"deg": 400, "r": 9}, "diy.search": {"deg": -30, "r": 0.1},
                                    "bad": "x", "x" * 50: {"deg": 1, "r": 1}, "local.library": {"deg": "a", "r": 1},
                                    "local.played": {"deg": 90.04, "r": 1.004}})
        layout = b.settings["sun_layout"]
        self.assertEqual(layout["local.queue"], {"deg": 40.0, "r": 3.0})           # the angle wraps round, the orbit is limited
        self.assertEqual(layout["diy.search"], {"deg": 330.0, "r": 0.4})
        self.assertEqual(layout["local.played"], {"deg": 90.0, "r": 1.0})
        self.assertEqual(set(layout), {"local.queue", "diy.search", "local.played"})   # junk and long names are dropped
        b.setSetting("sun_layout", {})
        b.setSetting("sun_scale", 1.0)

    def test_planets_can_be_moved_and_get_their_own_orbit(self):
        import time
        b = self.backend
        b.setSetting("sun_layout", {})
        b.setSetting("sun_scale", 1.0)
        b.setSetting("local_orbit", True)
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { width: 1400; height: 900\nLocalPlayerView { objectName: 'v'; anchors.fill: parent }\n}\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_orbit.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
        view = root.findChild(QObject, "v")

        def settle():
            end = time.time() + 0.5
            while time.time() < end:
                self.app.processEvents()
                time.sleep(0.01)

        def call(name, *args):
            QMetaObject.invokeMethod(view, name, Qt.DirectConnection, *[Q_ARG("QVariant", a) for a in args])
            self.app.processEvents()
        settle()
        cx, cy, rx, ry = (view.property(k) for k in ("cx", "cy", "rx", "ry"))
        # the default: every planet on the main orbit, one ring
        self.assertEqual(view.property("dragKey"), "")
        # drag the library planet to the right of the sun, a little outside the main orbit
        call("dragTo", "library", {"x": cx + rx * 1.5, "y": cy})
        self.assertEqual(view.property("dragKey"), "library")
        self.assertAlmostEqual(view.property("dragR"), 1.5, delta=0.01)
        self.assertAlmostEqual(view.property("dragDeg"), 0.0, delta=0.5)
        call("dropPlanet")
        self.assertEqual(view.property("dragKey"), "")
        self.assertEqual(b.settings["sun_layout"]["local.library"], {"deg": 0.0, "r": 1.5})
        # dragged close to the main orbit it snaps onto it, and close to a ring that is in use it snaps onto that one
        call("dragTo", "queue", {"x": cx - rx * 1.03, "y": cy})
        self.assertEqual(view.property("dragR"), 1.0)
        call("dragTo", "queue", {"x": cx - rx * 1.52, "y": cy})
        self.assertEqual(view.property("dragR"), 1.5)
        call("dropPlanet")
        self.assertEqual(b.settings["sun_layout"]["local.queue"]["r"], 1.5)
        # the orbit slider / wheel: larger and smaller, within the limits
        call("setOrbitScale", 2.0)
        self.assertEqual(b.settings["sun_scale"], 2.0)
        call("setOrbitScale", 50)
        self.assertEqual(b.settings["sun_scale"], 3.0)
        call("setOrbitScale", -1)
        self.assertEqual(b.settings["sun_scale"], 0.5)
        # back to the start
        call("resetOrbits")
        self.assertEqual(b.settings["sun_layout"], {})
        self.assertEqual(b.settings["sun_scale"], 1.0)
        root.deleteLater()

    def test_tidal_home_sun_mode_loads_the_sun_view(self):
        b = self.backend
        b.setSetting("tidal_sun", True)
        try:
            start = len(self.messages)
            comp = QQmlComponent(self.engine)
            comp.setData(b"import QtQuick\nItem { width: 1200; height: 800\nTidalHome { objectName: 'home'; anchors.fill: parent }\n}\n",
                         QUrl.fromLocalFile(str(QML_DIR / "_test_sunmode.qml")))
            root = comp.create()
            self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
            for _ in range(40):
                self.app.processEvents()
            home = root.findChild(QObject, "home")
            self.assertIs(home.property("sunMode"), True)
            bad = [m for m in self.messages[start:] if ".qml" in m and any(w in m for w in ERRORS)]
            self.assertEqual(bad, [])
            root.deleteLater()
        finally:
            b.setSetting("tidal_sun", False)

    def test_sun_view_makes_room_for_opened_planets(self):
        """Opening a planet moves the sun and its orbits so that the card does not cover it; folding brings it back."""
        import time
        comp = QQmlComponent(self.engine)
        comp.setData(b"import QtQuick\nItem { width: 1000; height: 800\nLocalPlayerView { objectName: 'v'; anchors.fill: parent }\n}\n",
                     QUrl.fromLocalFile(str(QML_DIR / "_test_sun.qml")))
        root = comp.create()
        self.assertIsNotNone(root, "\n".join(e.toString() for e in comp.errors()))
        view = root.findChild(QObject, "v")

        def settle():
            end = time.time() + 0.6
            while time.time() < end:
                self.app.processEvents()
                time.sleep(0.01)
        settle()
        centre = view.property("cx")
        self.assertAlmostEqual(centre, 500, delta=1)
        view.setProperty("opened", {"library": True})
        settle()
        self.assertGreater(view.property("cx"), 500 + 100)                  # the sun moved right of the library card
        view.setProperty("opened", {"library": True, "queue": True})
        settle()
        self.assertAlmostEqual(view.property("cx"), 500, delta=1)           # both sides: back in the middle, but narrower
        self.assertLess(view.property("availW"), 1000 - 2 * 260)
        view.setProperty("opened", {"played": True})
        settle()
        self.assertLess(view.property("cy"), 400 - 50)                       # the sun moved up for the played card
        self.assertGreaterEqual(view.property("availX0"), 10)
        self.backend.setSetting("local_orbit", False)                       # planets folded into the sun: cards are closed
        settle()
        self.assertAlmostEqual(view.property("cx"), 500, delta=1)
        self.assertAlmostEqual(view.property("cy"), 400, delta=1)
        self.backend.setSetting("local_orbit", True)
        root.deleteLater()

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
