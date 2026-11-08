# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Yeal: ONE small portable file. Only what the app really uses is packed:
# unused Qt modules / QML modules / Qt plugins / translations and unrelated Python packages
# (the central WinPython has hundreds) are removed.
#   YEAL_EMBED_TOOLS=1  -> also pack ffmpeg.exe + node.exe inside (big: ~100 MB more)
#   YEAL_SLIM_MEDIA=1   -> leave out Qt's bundled FFmpeg (about 8 MB smaller); the video preview in the frame
#                          extractor then uses the Windows media backend (plugins\multimedia\windowsmediaplugin.dll)
#   otherwise           -> they are looked up in "bin\" next to the exe (copied there by the .bat)
import os
import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH)
SRC = ROOT / "BIN" / "versions" / "v0.1" / "PyModul"
EMBED = os.environ.get("YEAL_EMBED_TOOLS") == "1"
SLIM_MEDIA = os.environ.get("YEAL_SLIM_MEDIA") == "1"
TC = Path(os.environ.get("TOOLS_CENTRAL", ROOT.parent / "Tools_Central"))
if not TC.is_dir():
    TC = Path(r"C:\Users\mail\AI_Coworker_Claude\Tools_Central")

# ---- Python packages that must never end up in the exe
EXCLUDES = [
    "tkinter", "_tkinter", "unittest", "doctest", "pydoc", "pdb", "lib2to3", "pip", "wheel", "test", "tests", "idlelib", "turtle", "curses",
    "numpy", "scipy", "pandas", "matplotlib", "PIL", "cv2", "IPython", "jupyter", "notebook", "pytest",
    "cryptography", "Cryptodome", "chardet", "sphinx", "docutils", "jedi", "black", "cython", "Cython", "numba", "sympy", "sqlalchemy",
    "PyQt5", "PyQt6", "PySide2", "shiboken2", "shiboken6.Shiboken_Qt6",
    # tools of the central WinPython that the app never imports (found in the exe's module list)
    "werkzeug", "flask", "watchdog", "pyreadline3", "_pyrepl", "pydoc_data",
    # PySide6 modules the app never imports
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras", "PySide6.QtQuick3D", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtSensors", "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtSerialPort", "PySide6.QtSerialBus", "PySide6.QtHelp",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets", "PySide6.QtTextToSpeech", "PySide6.QtVirtualKeyboard",
    "PySide6.QtWidgets", "PySide6.QtOpenGLWidgets", "PySide6.QtPrintSupport",
    "PySide6.QtXml", "PySide6.QtSvgWidgets", "PySide6.QtUiTools", "PySide6.QtStateMachine",
    "PySide6.QtHttpServer", "PySide6.QtSpatialAudio", "PySide6.QtMultimediaWidgets",
]

# ---- Qt files to drop (matched against the lower-case path inside the bundle)
DROP = re.compile("|".join([
    r"qt6?(webengine|webchannel|websockets|3d\w*|quick3d\w*|charts|datavisualization|graphs|pdf\w*|"
    r"sql|test|designer\w*|bluetooth|nfc|sensors|positioning|location|remoteobjects|scxml|serialport|"
    r"serialbus|help|texttospeech|virtualkeyboard|wayland\w*|openglwidgets|printsupport|"
    r"widgets|xml|uitools|statemachine|httpserver|spatialaudio|multimediawidgets|labs\w*)",
    r"qt6quickcontrols2(imagine|material|universal|fusion|fluentwinui3|windows|macos|ios)", r"opengl32sw", r"qtwebview_webengine", r"/translations/", r"\.qm$", r"/qtwebengine", r"/resources/",
    r"/qml/(qtquick3d|qt3d|qtwebengine|qtcharts|qtdatavisualization|qtgraphs|qtlocation|qtpositioning|"
    r"qtsensors|qttest|qtbluetooth|qtnfc|qtscxml|qtremoteobjects|qttexttospeech|qtwayland|qtwebchannel|"
    r"qtwebsockets|qt5compat|qtlabs\w*|qtquick/virtualkeyboard|qtquick/scene2d|qtquick/scene3d|"
    r"qtquick/localstorage|qtquick/nativestyle|qtquick/particles|qtquick/xmllistmodel|qtquick/tooling|"
    r"qtquick/pdf|qtquick/controls/(material|universal|imagine|fusion|fluentwinui3|windows|macos|ios|designer))",
    r"/plugins/(sqldrivers|printsupport|designer|qmltooling|position|sensors|texttospeech|"
    r"geometryloaders|renderers|sceneparsers|scxmldatasources|canbus|networkinformation|tls/qcertonly|"
    r"platforminputcontexts|virtualkeyboard|generic|egldeviceintegrations|wayland\w*|xcbglintegrations|"
    r"platformthemes|iconengines|styles)",
    r"imageformats/\w*(tiff|webp|gif|icns|ico|wbmp|tga|qpdf)",
    # Leaf Qt modules nothing in the app needs. Checked with the library dependencies of the Qt build: only their
    # own QML plugins (or 3D/Lottie modules that are not shipped) link against them. NOT droppable: Qt6QmlWorkerScript
    # and Qt6Concurrent (needed by Qt6Quick / Qt6Multimedia), Qt6OpenGL + QtOpenGL.pyd (needed by Qt6Quick / QtQuick).
    r"qt6(quicktest|quicktimeline\w*|quickvectorimage\w*|qmlxmllistmodel|qmllocalstorage|quickparticles|shadertools)",
    r"/plugins/platforms/(qdirect2d|qminimal|qoffscreen)",           # qwindows is the one that is used
    r"/qml/qt/labs/", r"/qml/qtquick/(timeline|vectorimage)", r"/qml/qtqml/(statemachine|xmllistmodel)",
    r"/quickimpl/qml/\+(fusion|imagine|material|universal)",          # alternative styles of the (unused) QML dialogs
    r"\.bak\d*$",                                                     # editor backups next to the QML files
] + ([r"/(avcodec|avformat|avutil|swscale|swresample)-\d+\.dll", r"/plugins/multimedia/ffmpegmediaplugin"] if SLIM_MEDIA else [])), re.IGNORECASE)


def keep(entry) -> bool:
    dest = "/" + str(entry[0]).replace("\\", "/").lower()
    if DROP.search(dest):
        return False
    # the PySide6 module .pyd/.so files of dropped modules
    name = dest.rsplit("/", 1)[-1]
    return not re.match(r"^(pyside6[./]?)?qt(webengine|3d|quick3d|charts|datavisualization|graphs|pdf|sql|test|"
                        r"designer|bluetooth|nfc|sensors|positioning|location|remoteobjects|scxml|serialport|"
                        r"serialbus|help|webchannel|websockets|texttospeech|virtualkeyboard|widgets|"
                        r"printsupport|xml|uitools|statemachine|httpserver|spatialaudio|multimediawidgets)", name) \
        if "pyside6" in dest and name.startswith("qt") else True


binaries = []
if EMBED:
    for exe, rel in (("ffmpeg.exe", ("Video Tools", "FFMPEG", "bin")), ("node.exe", ("Dependencies", "node", "bin"))):
        p = TC.joinpath(*rel, exe)
        if p.is_file():
            binaries.append((str(p), "bin"))

# Qt WebView backend for the embedded YouTube view (Windows: system WebView2). PyInstaller does NOT collect this
# plugin by itself. Without PySide6/plugins/webview/qtwebview_webview2.dll the exe shows the splash screen and
# then dies when the browser pane is created (about 1.6 s after start). It only needs Qt6Core/Gui/WebView + system DLLs.
import PySide6
WEBVIEW_PLUGIN = Path(PySide6.__file__).resolve().parent / "plugins" / "webview" / "qtwebview_webview2.dll"
if not WEBVIEW_PLUGIN.is_file():
    raise SystemExit("Build stopped: " + str(WEBVIEW_PLUGIN) + " not found (PySide6 install without QtWebView?).")
binaries.append((str(WEBVIEW_PLUGIN), "PySide6/plugins/webview"))

# ---- tiddl (the Tidal helper) runs from inside the exe: `Yeal.exe --tiddl ...` (main.py). It is a Python package with these
# dependencies; they are packed with their submodules and data (certifi: the CA bundle for https). Without tiddl in the build
# Python the exe is still built, but the Tidal helper then has to be installed separately (tiddl.exe next to Yeal.exe or on PATH).
import importlib.util
TIDDL_PACKAGES = ["tiddl", "aiofiles", "aiohttp", "aiohappyeyeballs", "aiosignal", "frozenlist", "multidict", "yarl", "propcache",
                  "m3u8", "mutagen", "pydantic", "pydantic_core", "annotated_types", "typing_inspection", "typing_extensions",
                  "requests", "requests_cache", "url_normalize", "cattrs", "attrs", "urllib3", "idna", "charset_normalizer",
                  "certifi", "typer", "click", "rich", "shellingham", "tomlkit", "platformdirs"]
tiddl_imports, tiddl_datas = [], []
if importlib.util.find_spec("tiddl") is None:
    print("WARNING: tiddl is not installed in the build Python: the exe will NOT contain the Tidal helper.")
else:
    for pkg in TIDDL_PACKAGES:
        if importlib.util.find_spec(pkg) is not None:
            tiddl_imports += collect_submodules(pkg)
            tiddl_datas += collect_data_files(pkg)

a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=[(str(SRC / "yeal" / "ui" / "qml"), "yeal/ui/qml"),
           (str(ROOT / "CHANGELOG.md"), ".")] + tiddl_datas,
    hiddenimports=collect_submodules("yt_dlp") + tiddl_imports + ["PySide6.QtMultimedia", "PySide6.QtQuickControls2",
                                                    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtNetwork"],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)
# Keep setuptools/pkg_resources when PyInstaller detects them. Its pyi_rth_pkgres runtime hook imports
# pkg_resources before Yeal starts; removing the module here produced an exe that built successfully but
# failed immediately with "No module named 'pkg_resources'".
a.binaries = [b for b in a.binaries if keep(b)]
if not any(str(b[0]).replace("\\", "/").lower().endswith("plugins/webview/qtwebview_webview2.dll") for b in a.binaries):
    raise SystemExit("Build stopped: the WebView2 plugin was filtered out of the bundle (check DROP / keep() in Yeal.spec).")
a.datas = [d for d in a.datas if keep(d)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Yeal",
    icon=str(ROOT / "docs" / "Logo.ico"),
    debug=False,
    strip=False,
    upx=False,          # UPX triggers antivirus false positives and slows start-up
    console=False,
    runtime_tmpdir=None,
)
