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
        self.assertIsInstance(drives.drive_mask(), int)

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


if __name__ == "__main__":
    unittest.main()
