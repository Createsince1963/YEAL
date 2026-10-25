"""Settings page layout (collapsible groups) and the "ask about the download folder" switch."""
import os
import re
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import _path  # noqa: F401

from yeal.core.settings import Settings  # noqa: E402

QML_DIR = _path.PYMODUL / "yeal" / "ui" / "qml"


class SettingsLayoutTest(unittest.TestCase):
    def test_every_group_is_collapsible_and_starts_collapsed(self):
        text = (QML_DIR / "SettingsPage.qml").read_text(encoding="utf-8")
        blocks = re.split(r"\n        SettingsGroup \{\n", text)[1:]
        self.assertGreaterEqual(len(blocks), 9)
        for block in blocks:
            head = block.split("\n            Layout.fillWidth: true")[0]
            title = re.search(r'title: qsTr\("(.*?)"\)', head).group(1)
            self.assertIn("collapsible: true", head, title)
            self.assertIn("collapsed: true", head, title)

    def test_settings_are_grouped_by_function(self):
        text = (QML_DIR / "SettingsPage.qml").read_text(encoding="utf-8")
        blocks = re.split(r"\n        SettingsGroup \{\n", text)[1:]
        titles = [re.search(r'title: qsTr\("(.*?)"\)', b).group(1) for b in blocks]
        self.assertEqual(titles, ["Appearance & browser", "Downloads", "Output", "Login & network", "Streaming",
                                  "Tidal", "Download engine", "Advanced", "Info"])

    def test_module_licenses_are_shown_without_a_show_button(self):
        text = (QML_DIR / "SettingsPage.qml").read_text(encoding="utf-8")
        start = text.index('label: qsTr("Module licenses")')
        block = text[start:start + 900]
        self.assertNotIn("licensesRow", text)
        self.assertNotIn('qsTr("Show")', block)
        self.assertIn("backend.thirdPartyLicenses", block)

    def test_ask_drive_dialog_defaults_to_on(self):
        self.assertTrue(Settings().ask_drive_dialog)


try:
    from PySide6.QtGui import QGuiApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class DriveQuestionTest(unittest.TestCase):
    def test_dont_ask_again_silences_the_drive_dialog(self):
        from test_core import FakeYDL, make_ctx
        from yeal.core.engine import Engine
        from yeal.ui.backend import Backend

        app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = make_ctx(tmp)
            backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
            offered = []
            backend.externalDrive.connect(offered.append)
            drive = {"root": "Z:\\", "label": "stick", "free": 1, "total": 2, "id": "z-1"}

            backend._drive_offered = set()
            backend._on_drives([drive])
            self.assertEqual(len(offered), 1)                       # asked once ...

            backend.setSetting("ask_drive_dialog", False)
            self.assertFalse(backend.settings["ask_drive_dialog"])
            backend._drive_offered = set()
            backend._on_drives([dict(drive, id="z-2")])
            self.assertEqual(len(offered), 1)                       # ... and not again

            backend.setSetting("ask_drive_dialog", True)            # Settings > Downloads switches it back on
            backend._on_drives([dict(drive, id="z-3")])
            self.assertEqual(len(offered), 2)
            del app


if __name__ == "__main__":
    unittest.main()
