"""Audio outputs of this computer (Bluetooth headphones, speakers, HDMI): kinds, the list for the Speaker planet, the choice
and the switch of the players."""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import _path  # noqa: F401
from yeal.core import audiodev  # noqa: E402

try:
    from PySide6.QtGui import QGuiApplication
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

from test_core import FakeYDL, make_ctx  # noqa: E402


class KindTests(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(audiodev.output_kind("Kopfhörer (Papa's Kopfhörer)"), "headphones")
        self.assertEqual(audiodev.output_kind("Headset (WH-1000XM4 Hands-Free)"), "headphones")
        self.assertEqual(audiodev.output_kind("Speakers (AirPods Pro)"), "headphones")
        self.assertEqual(audiodev.output_kind("ASUS XG32VQR (NVIDIA High Definition Audio)"), "monitor")
        self.assertEqual(audiodev.output_kind("Lautsprecher/Kopfhörer (Realtek High Definition Audio)"), "headphones")
        self.assertEqual(audiodev.output_kind("Lautsprecher (USB Audio)"), "speaker")
        self.assertEqual(audiodev.output_kind(""), "speaker")

    def test_list_marks_the_choice_or_the_default(self):
        devices = [{"id": "a", "description": "Speakers", "isDefault": False},
                   {"id": "b", "description": "Kopfhörer (BT)", "isDefault": True},
                   {"id": "c", "description": "HDMI", "isDefault": False}]
        out = audiodev.describe_outputs(devices)
        self.assertEqual([o["selected"] for o in out], [False, True, False])           # nothing chosen: the default
        out = audiodev.describe_outputs(devices, "c")
        self.assertEqual([o["selected"] for o in out], [False, False, True])           # the choice
        out = audiodev.describe_outputs(devices, "gone")                               # a device that is not there any more
        self.assertEqual([o["selected"] for o in out], [False, True, False])           # back to the default
        self.assertEqual(out[1]["kind"], "headphones")
        self.assertEqual(audiodev.describe_outputs([]), [])


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class BackendOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from yeal.core.engine import Engine
        from yeal.ui.backend import Backend
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        ctx = make_ctx(cls.tmp.name)
        cls.backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)

    @classmethod
    def tearDownClass(cls):
        cls.backend.shutdown()
        cls.tmp.cleanup()

    def test_outputs_are_listed_with_exactly_one_selected(self):
        outputs = self.backend.audioOutputs
        if not outputs:
            self.skipTest("no audio output on this machine")
        self.assertEqual(sum(1 for o in outputs if o["selected"]), 1)
        self.assertTrue(all(o["name"] and o["kind"] in ("headphones", "monitor", "speaker") for o in outputs))

    def test_choice_is_saved_and_the_players_follow(self):
        b = self.backend
        outputs = b.audioOutputs
        if len(outputs) < 1:
            self.skipTest("no audio output on this machine")
        seen = []
        b.audioOutputsChanged.connect(lambda: seen.append(1))
        applied = []
        original = (b.tidal.player.applyOutput, b.localPlayer.applyOutput)
        b.tidal.player.applyOutput = lambda: applied.append("tidal")
        b.localPlayer.applyOutput = lambda: applied.append("local")
        try:
            target = outputs[-1]["id"]
            b.selectAudioOutput(target)
            self.assertEqual(b.settings["audio_output"], target)
            self.assertEqual([o["id"] for o in b.audioOutputs if o["selected"]], [target])
            self.assertEqual(sorted(applied), ["local", "tidal"])
            self.assertTrue(seen)
            device = b.audio_device()
            self.assertIsNotNone(device)
            self.assertEqual(bytes(device.id()).decode("latin1"), target)
            b.selectAudioOutput("not-a-device")                          # a device that does not exist: the system default
            fallback = b.audio_device()
            self.assertTrue(fallback is None or fallback.isDefault())
            b.selectAudioOutput("")                                       # back to the default
            self.assertEqual(b.settings["audio_output"], "")
        finally:
            b.tidal.player.applyOutput, b.localPlayer.applyOutput = original

    def test_real_players_accept_the_output_switch(self):
        p = self.backend.localPlayer
        self.assertTrue(p._ensure())
        p.applyOutput()                                                   # must not raise
        self.backend.tidal.player.applyOutput()


if __name__ == "__main__":
    unittest.main()
