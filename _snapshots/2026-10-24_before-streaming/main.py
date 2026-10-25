"""Yeal entry point. Must be named main.py for pyside6-android-deploy."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

_LOG = None   # keeps the log file (and the Qt message handler's target) alive


def _setup_diagnostics(data_dir: Path) -> None:
    """The windowed exe has no console (sys.stdout / sys.stderr are None), so startup errors vanished silently.
    In the frozen exe (or with YEAL_LOG=1) write Python errors, native crashes (faulthandler) and Qt/QML messages
    to <data_dir>/yeal.log; the previous run is kept as yeal.prev.log."""
    global _LOG
    import os
    if not (getattr(sys, "frozen", False) or os.environ.get("YEAL_LOG")):
        return
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        log = data_dir / "yeal.log"
        if log.exists():
            os.replace(log, data_dir / "yeal.prev.log")
        _LOG = open(log, "w", buffering=1, encoding="utf-8", errors="replace")
    except OSError:
        return
    if sys.stdout is None:
        sys.stdout = _LOG
    if sys.stderr is None:
        sys.stderr = _LOG
    import faulthandler
    faulthandler.enable(file=_LOG, all_threads=True)
    os.environ.setdefault("QT_LOGGING_RULES", "qt.webview*=true")
    from PySide6.QtCore import qInstallMessageHandler

    def _handler(_mode, _context, message):
        try:
            _LOG.write("[qt] %s\n" % message)
        except Exception:  # noqa: BLE001
            pass

    qInstallMessageHandler(_handler)
    print("Yeal log started; frozen=%s python=%s" % (getattr(sys, "frozen", False), sys.version.split()[0]), flush=True)


def main() -> int:
    from PySide6.QtCore import QCoreApplication, QUrl
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    from yeal import __version__, platforms
    from yeal.ui.backend import Backend

    QCoreApplication.setOrganizationName("Yeal")
    QCoreApplication.setApplicationName("Yeal")
    QCoreApplication.setApplicationVersion(__version__)
    QQuickStyle.setStyle("Basic")

    ctx = platforms.detect()
    _setup_diagnostics(ctx.data_dir)
    if ctx.name == "windows":   # embedded YouTube browser: system WebView2, profile kept in the data folder
        import os
        marker = ctx.data_dir / "wipe_browser_profile"
        if marker.exists():   # requested in Settings > Admin: forget the browser sign-in
            import shutil
            shutil.rmtree(ctx.data_dir / "webview2", ignore_errors=True)
            marker.unlink(missing_ok=True)
        os.environ.setdefault("QT_WEBVIEW_PLUGIN", "webview2")
        os.environ.setdefault("WEBVIEW2_USER_DATA_FOLDER", str(ctx.data_dir / "webview2"))
        try:   # ad/tracker blocking for the browser view: local filter proxy, set via a Chromium flag
            from yeal.core import adblock
            from yeal.core.settings import Settings
            if Settings.load(ctx.settings_path).adblock_experimental and not os.environ.get("YEAL_NO_ADBLOCK"):
                proxy = adblock.start(ctx.data_dir / "blocklist.txt")
                os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
                    f"--proxy-server=http://127.0.0.1:{proxy.port}")
        except Exception:  # noqa: BLE001 - never block the start because of the filter
            pass
        try:
            from PySide6.QtWebView import QtWebView
            QtWebView.initialize()   # must run before the QGuiApplication exists
        except Exception as exc:  # noqa: BLE001 - the app works without the browser pane
            print("QtWebView.initialize failed:", exc, flush=True)
        if getattr(sys, "frozen", False):
            import PySide6
            plugin = Path(PySide6.__file__).resolve().parent / "plugins" / "webview" / "qtwebview_webview2.dll"
            print("WebView2 plugin present:", plugin.is_file(), plugin, flush=True)
    app = QGuiApplication(sys.argv)
    # System UI font: Segoe UI Variable on Windows, Roboto on Android (Qt default elsewhere).
    family = "Roboto" if ctx.is_mobile else ("Segoe UI Variable Text" if ctx.name == "windows" else "")
    if family:
        font = app.font()
        font.setFamilies([family, font.family()])
        app.setFont(font)
    app.setWindowIcon(QIcon(str(HERE / "yeal" / "ui" / "qml" / "assets" / "icon.png")))
    backend = Backend(ctx)

    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("backend", backend)
    context.setContextProperty("jobModel", backend.model)
    engine.load(QUrl.fromLocalFile(str(HERE / "yeal" / "ui" / "qml" / "Main.qml")))
    if not engine.rootObjects():
        print("QML load failed: no root object (see [qt] lines above)", flush=True)
        return 1

    code = app.exec()
    backend.shutdown()
    return code


if __name__ == "__main__":
    sys.exit(main())
