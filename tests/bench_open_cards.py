import os, sys, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"; os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["YEAL_DATA_DIR"] = r"C:\Users\mail\AppData\Local\Temp\yealcopy"
sys.path.insert(0, r"C:\Users\mail\AI_Coworker_Claude\APK YEAL\tests")
import _path
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
QQuickStyle.setStyle("Basic")
app = QGuiApplication(sys.argv)
from yeal import platforms
from yeal.ui.backend import Backend
ctx = platforms.detect()
b = Backend(ctx, check_updates=False)
engine = QQmlEngine()
engine.rootContext().setContextProperty("backend", b)
engine.rootContext().setContextProperty("jobModel", b.model)
engine.rootContext().setContextProperty("tidal", b.tidal)
QML = r"C:\Users\mail\AI_Coworker_Claude\APK YEAL\BIN\versions\v0.1\PyModul\yeal\ui\qml"
player = b.localPlayer
b.localPlayer.refreshLibrary()
songs = list(player.library)[:150]
player.queue.reset(songs, 0)
comp = QQmlComponent(engine)
comp.setData(b"import QtQuick\nItem { width: 1800; height: 1100\nLocalPlayerView { objectName: 'v'; anchors.fill: parent }\n}\n", QUrl.fromLocalFile(QML + r"\_ob.qml"))
root = comp.create(); assert root is not None, [e.toString() for e in comp.errors()]
win = QQuickWindow(); win.resize(1800, 1100); root.setParentItem(win.contentItem()); win.show()
view = root.childItems()[0]
for _ in range(30): app.processEvents()
def timed(label, key):
    t0 = time.perf_counter()
    view.setProperty("opened", {key: True})
    app.processEvents()
    first = (time.perf_counter() - t0) * 1000
    for _ in range(20): app.processEvents(); time.sleep(0.005)
    win.grabWindow()
    total = (time.perf_counter() - t0) * 1000
    print("%-10s first event pass %.0f ms (until painted %.0f ms)" % (label, first, total))
    view.setProperty("opened", {}); 
    for _ in range(40): app.processEvents(); time.sleep(0.005)
timed("queue", "queue"); timed("queue", "queue"); timed("library", "library"); timed("played", "played"); timed("sound", "sound")

print("--- canvases")
def walk(i):
    yield i
    for c in i.childItems():
        yield from walk(c)
cv = [i for i in walk(root) if i.metaObject().className().startswith("QQuickCanvas")]
print(len(cv), "canvases")
for c in cv:
    t0 = time.perf_counter()
    for _ in range(5):
        c.metaObject().invokeMethod(c, "requestPaint"); app.processEvents(); win.grabWindow()
    print("canvas %dx%d (parent %s): %.0f ms per paint+frame" % (c.width(), c.height(), c.parentItem().metaObject().className(), (time.perf_counter() - t0) / 5 * 1000))
t0 = time.perf_counter()
for _ in range(5): app.processEvents(); win.grabWindow()
print("idle frame (no paint): %.0f ms" % ((time.perf_counter() - t0) / 5 * 1000))
