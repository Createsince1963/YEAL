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

from PyInstaller.utils.hooks import collect_submodules

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

a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=[(str(SRC / "yeal" / "ui" / "qml"), "yeal/ui/qml")],
    hiddenimports=collect_submodules("yt_dlp") + ["PySide6.QtMultimedia", "PySide6.QtQuickControls2",
                                                    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtNetwork"],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)
# setuptools / pkg_resources / distutils cannot be excluded by name (a PyInstaller hook aliases them and
# fails on the central WinPython) - they are removed after the analysis instead.
_UNNEEDED = ("setuptools", "pkg_resources", "_distutils_hack", "distutils")
a.pure = [m for m in a.pure if not m[0].split(".")[0] in _UNNEEDED]
a.datas = [d for d in a.datas if not str(d[0]).replace("\\", "/").split("/")[0] in _UNNEEDED]
a.binaries = [b for b in a.binaries if keep(b)]
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
