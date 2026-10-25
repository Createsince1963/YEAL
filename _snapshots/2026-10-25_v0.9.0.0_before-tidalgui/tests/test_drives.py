import unittest

import _path  # noqa: F401
from yeal.platforms import drives
from yeal.core.settings import Settings


class DriveTests(unittest.TestCase):
    def test_folder_name(self):
        self.assertEqual(drives.clean_folder_name(" My/Media: "), "My_Media_")
        self.assertEqual(drives.clean_folder_name("..  "), "Yeal")
        self.assertEqual(drives.clean_folder_name(""), "Yeal")

    def test_scan_does_not_crash(self):
        self.assertIsInstance(drives.external_drives(), list)
        self.assertIsInstance(drives.drive_mask(), (int, tuple))     # Windows: (letter mask, serials)
        found, pending = drives.scan_drives()
        self.assertIsInstance(found, list)
        self.assertIsInstance(pending, bool)

    def test_downloads_dir(self):
        p = drives.user_downloads_dir()
        self.assertEqual(p.name.lower(), "downloads")

    def test_no_pseudo_drives(self):
        for d in drives.external_drives():
            self.assertGreaterEqual(d["total"], drives.MIN_DRIVE_BYTES)

    def test_settings_validation(self):
        s = Settings(drive_ignored="x", drive_folder="")
        s.validate()
        self.assertEqual(s.drive_ignored, [])
        self.assertEqual(s.drive_folder, "Yeal")

    def test_small_usb_stick_is_not_hidden(self):
        self.assertLessEqual(drives.MIN_DRIVE_BYTES, 128 << 20)      # a 256 MB stick is a valid target
        self.assertGreater(drives.MIN_DRIVE_BYTES, 16 << 20)         # the 16 MB driver pseudo drive is not

    def test_header_download_button_settings(self):
        s = Settings(dl_button_style="weird", dl_button_pos="top")
        s.validate()
        self.assertEqual((s.dl_button_style, s.dl_button_pos), ("icon", "left"))
        s = Settings(dl_button_style="label", dl_button_pos="right")
        s.validate()
        self.assertEqual((s.dl_button_style, s.dl_button_pos), ("label", "right"))


if __name__ == "__main__":
    unittest.main()
