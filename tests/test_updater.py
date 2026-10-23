import hashlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

import _path  # noqa: F401
from yeal.core import updater


def make_wheel(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    return buf.getvalue()


def ytdlp_wheel(version="9999.1.0", ejs="0.1", extra=None):
    files = {
        "yt_dlp/__init__.py": "",
        "yt_dlp/version.py": f"__version__ = '{version}'\n",
        f"yt_dlp-{version}.dist-info/METADATA":
            f"Name: yt-dlp\nVersion: {version}\nRequires-Dist: yt-dlp-ejs=={ejs}; extra == 'default'\n",
        f"yt_dlp-{version}.data/data/share/man/yt-dlp.1": "man page",
    }
    files.update(extra or {})
    return make_wheel(files)


class FakePyPI:
    """Replaces updater._open: serves PyPI JSON and wheel files from memory."""

    def __init__(self, ytdlp_blob, ejs_blob, version="9999.1.0", ejs="0.1", corrupt=False):
        self.blobs = {"https://files/ytdlp.whl": ytdlp_blob, "https://files/ejs.whl": ejs_blob}
        self.version, self.ejs, self.corrupt = version, ejs, corrupt
        self.requests = []

    def _release(self, url, blob):
        digest = hashlib.sha256(blob).hexdigest()
        if self.corrupt:
            digest = "0" * 64
        return [{"filename": "pkg-1-py3-none-any.whl", "url": url, "digests": {"sha256": digest}}]

    def __call__(self, url):
        self.requests.append(url)
        if url.endswith("/yt-dlp/json"):
            return json.dumps({"info": {"version": self.version}, "releases": {
                self.version: self._release("https://files/ytdlp.whl", self.blobs["https://files/ytdlp.whl"])}}).encode()
        if url.endswith("/yt-dlp-ejs/json"):
            return json.dumps({"info": {"version": "9.9"}, "releases": {
                self.ejs: self._release("https://files/ejs.whl", self.blobs["https://files/ejs.whl"])}}).encode()
        return self.blobs[url]


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name)
        # hermetic: pretend no system-wide yt-dlp / yt-dlp-ejs is installed
        self.orig_find_spec = updater.importlib_util.find_spec
        updater.importlib_util.find_spec = lambda name, *a, **k: None
        self.orig_open, self.orig_path = updater._open, list(sys.path)
        self.addCleanup(self.restore)
        self.ejs = make_wheel({"yt_dlp_ejs/__init__.py": "", "yt_dlp_ejs/solver.js": "//js",
                               "yt_dlp_ejs-0.1.dist-info/METADATA": "Name: yt-dlp-ejs\n"})

    def restore(self):
        updater._open = self.orig_open
        updater.importlib_util.find_spec = self.orig_find_spec
        sys.path[:] = self.orig_path

    def test_install_activate_and_skip_when_current(self):
        fake = FakePyPI(ytdlp_wheel(), self.ejs)
        updater._open = fake
        version, changed = updater.update(self.data)
        self.assertEqual((version, changed), ("9999.1.0", True))
        d = updater.local_dir(self.data)
        self.assertTrue((d / "yt_dlp" / "version.py").is_file())
        self.assertTrue((d / "yt_dlp_ejs" / "solver.js").is_file())
        self.assertFalse(any(".data" in str(p) for p in d.rglob("*")))     # data files skipped
        self.assertEqual(updater.installed_version(self.data), "9999.1.0")
        self.assertIn(str(d), sys.path)
        self.assertFalse((self.data / "ytdlp.new").exists())
        self.assertFalse(updater.should_check(self.data))                  # stamp is fresh
        self.assertTrue(updater.should_check(self.data, now=time.time() + 4 * 86400))
        requests_before = len(fake.requests)
        self.assertEqual(updater.update(self.data), ("9999.1.0", False))   # already current
        self.assertEqual(len(fake.requests), requests_before + 1)          # only the JSON lookup

    def test_replaces_older_local_copy(self):
        updater._open = FakePyPI(ytdlp_wheel("2025.1.1"), self.ejs, version="2025.1.1")
        updater.update(self.data)
        updater._open = FakePyPI(ytdlp_wheel("2026.2.2"), self.ejs, version="2026.2.2")
        self.assertEqual(updater.update(self.data), ("2026.2.2", True))
        self.assertEqual(updater.installed_version(self.data), "2026.2.2")
        self.assertFalse((self.data / "ytdlp.old").exists())

    def test_checksum_mismatch_leaves_nothing_behind(self):
        updater._open = FakePyPI(ytdlp_wheel(), self.ejs, corrupt=True)
        with self.assertRaises(RuntimeError):
            updater.update(self.data)
        self.assertFalse(updater.local_dir(self.data).exists())
        self.assertFalse((self.data / "ytdlp.new").exists())

    def test_zip_slip_is_rejected(self):
        evil = ytdlp_wheel(extra={"yt_dlp/../../evil.txt": "pwned"})
        updater._open = FakePyPI(evil, self.ejs)
        with self.assertRaises(RuntimeError):
            updater.update(self.data)
        self.assertFalse((self.data.parent / "evil.txt").exists())
        self.assertFalse(updater.local_dir(self.data).exists())

    def test_failed_update_keeps_working_install(self):
        updater._open = FakePyPI(ytdlp_wheel("2025.1.1"), self.ejs, version="2025.1.1")
        updater.update(self.data)

        def offline(url):
            raise OSError("no network")
        updater._open = offline
        with self.assertRaises(OSError):
            updater.update(self.data)
        self.assertEqual(updater.installed_version(self.data), "2025.1.1")

    def test_version_compare(self):
        self.assertGreater(updater._norm("2026.10.21"), updater._norm("2025.9.26"))
        self.assertEqual(updater._norm("2026.01.05"), (2026, 1, 5))


@unittest.skipUnless(os.environ.get("YEAL_NET_TESTS") == "1", "set YEAL_NET_TESTS=1 for the real PyPI test")
class RealPyPITest(unittest.TestCase):
    def test_real_update_gives_importable_ytdlp(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            version, changed = updater.update(Path(d), force=True)
            self.assertTrue(changed)
            code = ("import sys; sys.path.insert(0, sys.argv[1]); import yt_dlp, yt_dlp_ejs; "
                    "print(yt_dlp.version.__version__, yt_dlp.__file__.startswith(sys.argv[1]))")
            out = subprocess.run([sys.executable, "-I", "-c", code, str(updater.local_dir(Path(d)))],
                                 capture_output=True, text=True, check=True).stdout.split()
            self.assertEqual(out, [version, "True"])


if __name__ == "__main__":
    unittest.main()
