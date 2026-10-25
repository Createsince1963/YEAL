"""Streaming to UPnP/DLNA renderers: discovery description, media server, SOAP control, settings, Qt bridge.
A fake renderer (plain HTTP on 127.0.0.1) stands in for the speaker; nothing leaves the machine."""
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote_plus

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import _path  # noqa: F401
from yeal.core import streaming  # noqa: E402
from yeal.core.settings import Settings  # noqa: E402

DESC = """<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0"><device>
<deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
<friendlyName>{name}</friendlyName><manufacturer>KEF</manufacturer><modelName>LS50 Wireless II</modelName>
<UDN>uuid:fake-1234</UDN>
<serviceList>
<service><serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType><controlURL>/avt</controlURL></service>
<service><serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType><controlURL>/rc</controlURL></service>
</serviceList></device></root>"""

SERVER_DESC = DESC.replace("MediaRenderer", "MediaServer")


class FakeRenderer:
    """Speaks just enough UPnP: description, AVTransport and RenderingControl. `fetch` = like a real speaker, it
    downloads the media URL when Play arrives."""

    def __init__(self, name="Fake KEF", fetch=True, fault=False, desc=DESC):
        self.name, self.fetch, self.fault, self.desc = name, fetch, fault, desc
        self.actions, self.bodies, self.fetched = [], [], b""
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                data = outer.desc.format(name=outer.name).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"])).decode()
                action = self.headers["SOAPACTION"].strip('"').split("#")[1]
                outer.actions.append(action)
                outer.bodies.append(body)
                if outer.fault:
                    resp = ('<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><s:Fault><detail>'
                            '<UPnPError xmlns="urn:schemas-upnp-org:control-1-0"><errorCode>714</errorCode>'
                            '<errorDescription>Illegal MIME-type</errorDescription></UPnPError></detail></s:Fault>'
                            '</s:Body></s:Envelope>').encode()
                    self.send_response(500)
                else:
                    extra = "<CurrentTransportState>PLAYING</CurrentTransportState>" if action == "GetTransportInfo" else ""
                    resp = ('<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
                            f'<u:{action}Response xmlns:u="x">{extra}</u:{action}Response></s:Body></s:Envelope>').encode()
                    self.send_response(200)
                if action == "Play" and outer.fetch and not outer.fault:
                    latest = next(b for b in reversed(outer.bodies) if "<CurrentURI>" in b)     # the URI set last
                    url = latest.split("<CurrentURI>")[1].split("</CurrentURI>")[0]
                    threading.Thread(target=outer._download, args=(url.replace("&amp;", "&"),), daemon=True).start()
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.location = f"http://127.0.0.1:{self.httpd.server_address[1]}/desc.xml"

    def _download(self, url):
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                self.fetched = r.read()
        except OSError:
            pass

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class StreamingCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.song = Path(self.tmp.name) / "Song & Co.mp3"
        self.song.write_bytes(bytes(range(256)) * 40)       # 10240 bytes

    def fake(self, **kw):
        f = FakeRenderer(**kw)
        self.addCleanup(f.close)
        return f

    def test_describe_reads_a_renderer(self):
        r = streaming.describe(self.fake(name="KEF LS50").location)
        self.assertEqual((r.name, r.manufacturer, r.model), ("KEF LS50", "KEF", "LS50 Wireless II"))
        self.assertTrue(r.control_url.endswith("/avt") and r.rc_url.endswith("/rc"))
        self.assertEqual(r.id, "uuid:fake-1234")
        back = streaming.Renderer.from_dict(r.to_dict())
        self.assertEqual(back, r)
        self.assertIsNone(streaming.Renderer.from_dict({"id": "x"}))

    def test_describe_ignores_other_devices_and_bad_input(self):
        self.assertIsNone(streaming.describe(self.fake(desc=SERVER_DESC).location))     # a media server, not a renderer
        self.assertIsNone(streaming.describe("ftp://127.0.0.1/x"))
        self.assertIsNone(streaming.describe("http://8.8.8.8/desc.xml"))                # not a local-network address
        self.assertIsNone(streaming.describe("http://127.0.0.1:1/none"))               # nothing listens

    def test_discover_with_a_direct_description_url(self):
        f = self.fake()
        found = streaming.discover(1.0, hosts=[f.location])
        self.assertEqual([r.name for r in found], ["Fake KEF"])

    def test_xml_with_entities_is_refused(self):
        evil = b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "y">]><a>&x;</a>'
        with self.assertRaises(streaming.StreamError):
            streaming._safe_xml(evil)

    def test_check_host(self):
        for ok in ("192.168.1.50", "kef-ls50", "http://192.168.1.50:50001/desc.xml"):
            self.assertEqual(streaming.check_host(ok), "", ok)
        for bad in ("", "  ", "a b", "ftp://x", "http://", "x;rm -rf"):
            self.assertNotEqual(streaming.check_host(bad), "", bad)

    def test_stream_plays_and_the_speaker_gets_the_file(self):
        f = self.fake()
        r = streaming.describe(f.location)
        s = streaming.Streamer()
        self.addCleanup(s.shutdown)
        warning = s.stream(r, self.song, "Song & Co", volume=25, wait_for_fetch=5)
        self.assertEqual(warning, "")
        self.assertEqual(f.actions, ["SetVolume", "Stop", "SetAVTransportURI", "Play"])
        self.assertIn("<DesiredVolume>25</DesiredVolume>", f.bodies[0])
        uri_call = f.bodies[2]
        self.assertIn("http://127.0.0.1:", uri_call)
        self.assertIn("&lt;dc:title&gt;Song &amp;amp; Co&lt;/dc:title&gt;", uri_call)     # title is escaped twice (DIDL in SOAP)
        self.assertIn("audio/mpeg", uri_call)
        deadline = time.time() + 3
        while not f.fetched and time.time() < deadline:
            time.sleep(0.05)
        self.assertEqual(f.fetched, self.song.read_bytes())
        self.assertEqual(r.state(), "PLAYING")
        s.stop()
        self.assertIn("Stop", f.actions[-1])

    def test_warning_when_the_speaker_never_fetches(self):
        f = self.fake(fetch=False)
        s = streaming.Streamer()
        self.addCleanup(s.shutdown)
        warning = s.stream(streaming.describe(f.location), self.song, "x", wait_for_fetch=0.4)
        self.assertIn("did not fetch", warning)

    def test_speaker_error_is_reported_in_words(self):
        f = self.fake(fault=True)
        s = streaming.Streamer()
        self.addCleanup(s.shutdown)
        with self.assertRaises(streaming.StreamError) as cm:
            s.stream(streaming.describe(f.location), self.song, "x", wait_for_fetch=0.2)
        self.assertIn("Illegal MIME-type", str(cm.exception))

    def test_unreachable_speaker(self):
        dead = streaming.Renderer("id", "Gone", "http://127.0.0.1:1/d", "127.0.0.1", "http://127.0.0.1:1/avt")
        with self.assertRaises(streaming.StreamError) as cm:
            dead.pause()
        self.assertIn("not reachable", str(cm.exception))

    def test_media_server_range_head_and_unknown_tokens(self):
        server = streaming.MediaServer()
        self.addCleanup(server.stop)
        port = server.start()
        path = server.add(self.song)
        url = f"http://127.0.0.1:{port}{path}"
        data = self.song.read_bytes()

        def get(u, method="GET", rng=None):
            req = urllib.request.Request(u, method=method, headers={"Range": rng} if rng else {})
            return urllib.request.urlopen(req, timeout=3)

        with get(url) as r:
            self.assertEqual((r.status, r.headers["Content-Type"], r.headers["Accept-Ranges"]), (200, "audio/mpeg", "bytes"))
            self.assertEqual(r.headers["transferMode.dlna.org"], "Streaming")
            self.assertEqual(r.read(), data)
        with get(url, rng="bytes=100-199") as r:
            self.assertEqual(r.status, 206)
            self.assertEqual(r.headers["Content-Range"], f"bytes 100-199/{len(data)}")
            self.assertEqual(r.read(), data[100:200])
        with get(url, rng="bytes=-50") as r:
            self.assertEqual(r.read(), data[-50:])
        with get(url, rng=f"bytes={len(data) - 10}-") as r:
            self.assertEqual(r.read(), data[-10:])
        with get(url, method="HEAD") as r:
            self.assertEqual((r.status, r.headers["Content-Length"], r.read()), (200, str(len(data)), b""))
        with self.assertRaises(urllib.error.HTTPError) as cm:
            get(url, rng="bytes=99999-")
        self.assertEqual(cm.exception.code, 416)
        for bad in ("/m/AAAAAAAAAAAAAAAAAAAA.mp3", "/", "/m/../../etc/passwd", f"/{self.song.name}"):
            with self.assertRaises(urllib.error.HTTPError, msg=bad) as cm:
                get(f"http://127.0.0.1:{port}{urllib.parse.quote(bad)}")
            self.assertEqual(cm.exception.code, 404, bad)
        self.assertGreaterEqual(server.hits(path), 5)
        server.clear()                                            # a finished stream is no longer served
        with self.assertRaises(urllib.error.HTTPError):
            get(url)

    def test_busy_port_is_explained(self):
        a = streaming.MediaServer()
        self.addCleanup(a.stop)
        port = a.start()
        b = streaming.MediaServer(port)
        with self.assertRaises(streaming.StreamError) as cm:
            b.start()
        self.assertIn("another port", str(cm.exception))

    def test_mime_types(self):
        self.assertEqual(streaming.mime_for(Path("a.M4A")), "audio/mp4")
        self.assertEqual(streaming.mime_for(Path("a.flac")), "audio/flac")
        self.assertTrue(streaming.is_video(Path("a.mkv")))
        self.assertFalse(streaming.is_video(Path("a.mp3")))
        self.assertEqual(streaming.mime_for(Path("a.unknownext")), "application/octet-stream")

    def test_private_clients_only(self):
        self.assertTrue(streaming._private_client("192.168.1.20"))
        self.assertTrue(streaming._private_client("10.0.0.2"))
        self.assertTrue(streaming._private_client("::ffff:192.168.1.20"))
        self.assertFalse(streaming._private_client("8.8.8.8"))
        self.assertFalse(streaming._private_client("not-an-ip"))

    def test_local_addresses_are_usable(self):
        for ip in streaming.local_ipv4_addresses():
            self.assertNotEqual(ip, "127.0.0.1")
        self.assertEqual(streaming.local_ip_for("127.0.0.1"), "127.0.0.1")

    def test_settings_validation(self):
        s = Settings(stream_device={"id": "x"}, stream_hosts=["a", "a", " ", 5] + ["h%d" % i for i in range(20)],
                     stream_volume=500, stream_scan_seconds=0, stream_port=80)
        s.validate()
        self.assertEqual(s.stream_device, {})                          # incomplete device data is dropped
        self.assertLessEqual(len(s.stream_hosts), 10)
        self.assertEqual(s.stream_hosts[:2], ["a", "5"])
        self.assertEqual((s.stream_volume, s.stream_scan_seconds, s.stream_port), (100, 2, 0))   # ports < 1024 -> automatic
        ok = {"id": "u", "name": "n", "location": "http://h/d", "control_url": "http://h/a"}
        s2 = Settings(stream_device=ok, stream_volume="x", stream_port=50000).validate()
        self.assertEqual(s2.stream_device["id"], "u")
        self.assertEqual((s2.stream_volume, s2.stream_port), (-1, 50000))
        path = Path(self.tmp.name) / "settings.json"
        s2.save(path)
        self.assertEqual(Settings.load(path).stream_device["control_url"], "http://h/a")


try:
    from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class StreamingBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QQuickStyle.setStyle("Basic")
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv)

    def make_backend(self):
        from test_core import FakeYDL, make_ctx
        from yeal.core.engine import Engine
        from yeal.ui.backend import Backend
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ctx = make_ctx(tmp.name)
        backend = Backend(ctx, engine=Engine(ctx, ydl_class=FakeYDL), check_updates=False)
        self.addCleanup(backend.shutdown)
        return backend, Path(tmp.name)

    def pump(self, cond, timeout=6.0):
        end = time.time() + timeout
        while time.time() < end:
            self.app.processEvents()
            if cond():
                return True
            time.sleep(0.01)
        return False

    def add_done_job(self, backend, folder):
        """A finished audio job whose file exists, without running a download."""
        from yeal.core.models import DownloadJob, JobState
        from yeal.core.presets import media_dir
        job = DownloadJob(id=7, url="https://example.com/v", options=backend._settings.to_options("Audio MP3"))
        job.title, job.state = "Test Song", JobState.DONE
        audio = media_dir(folder / "dl", "audio")
        audio.mkdir(parents=True, exist_ok=True)
        (audio / "Test Song.mp3").write_bytes(b"ID3" + b"\0" * 5000)
        job.filename = str(audio / "Test Song.mp3")
        backend._jobChanged.emit(job)
        self.pump(lambda: backend.model.get(7) is not None)
        return job

    def test_scan_select_stream_stop_with_the_fake_speaker(self):
        backend, folder = self.make_backend()
        self.add_done_job(backend, folder)
        fake = FakeRenderer("Fake LS50")
        self.addCleanup(fake.close)
        choices = []
        backend.streamChoice.connect(choices.append)

        backend.streamJob(7, "")                                   # nothing chosen yet -> the dialog must open
        self.assertEqual(choices, [7])

        self.assertEqual(backend.addStreamHost("bad host!"), "Enter an IP address (e.g. 192.168.1.50), a device name, or the full description URL.")
        self.assertEqual(backend.addStreamHost(fake.location), "")      # manual description URL + search
        self.assertTrue(self.pump(lambda: not backend.streamScanning and backend.streamDevices))
        dev = backend.streamDevices[0]
        self.assertEqual((dev["name"], dev["online"], dev["selected"]), ("Fake LS50", True, False))
        self.assertIn(fake.location, backend.settings["stream_hosts"])

        backend.streamJob(7, dev["id"])                            # choose + play
        self.assertTrue(self.pump(lambda: backend.streamPlaying and not backend.streamBusy))
        self.assertIn("Playing on Fake LS50", backend.streamStatus)
        self.assertTrue(backend.streamDevices[0]["selected"])
        self.assertEqual(backend.settings["stream_device"]["name"], "Fake LS50")
        self.assertTrue(self.pump(lambda: fake.fetched.startswith(b"ID3")))
        self.assertEqual(fake.actions[-2:], ["SetAVTransportURI", "Play"])

        backend.pauseStream()
        self.assertTrue(self.pump(lambda: not backend.streamBusy and "Pause" in fake.actions))
        backend.resumeStream()
        self.assertTrue(self.pump(lambda: not backend.streamBusy and fake.actions[-1] == "Play"))
        backend.setStreamVolume(40)
        self.assertTrue(self.pump(lambda: "SetVolume" in fake.actions))
        backend.stopStream()
        self.assertTrue(self.pump(lambda: not backend.streamPlaying and not backend.streamBusy))
        self.assertEqual(fake.actions[-1], "Stop")

        # the saved device is used directly next time (no dialog)
        choices.clear()
        backend.streamJob(7, "")
        self.assertTrue(self.pump(lambda: backend.streamPlaying))
        self.assertEqual(choices, [])
        backend.clearStreamDevice()
        self.assertEqual(backend.settings["stream_device"], {})

    def test_unknown_job_and_scan_without_devices(self):
        backend, _ = self.make_backend()
        toasts = []
        backend.toast.connect(toasts.append)
        backend.streamJob(999, "")
        self.assertIn("finished single file", toasts[-1])
        backend.removeStreamHost("nothing")
        backend.setSetting("stream_volume", 33)
        backend.setSetting("stream_port", 80)                                 # privileged ports fall back to automatic
        self.assertEqual((backend.settings["stream_volume"], backend.settings["stream_port"]), (33, 0))

    def test_qml_button_menu_and_dialog_load(self):
        """The real DownloadRow (button) and StreamDialog load with the real backend and react to a click."""
        qml_dir = _path.PYMODUL / "yeal" / "ui" / "qml"
        harness = b"""
import QtQuick
import QtQuick.Controls.Basic
ApplicationWindow {
    id: root
    visible: true; width: 900; height: 700
    property alias row: rowItem
    property alias dlg: dlg
    StreamDialog { id: dlg }
    DownloadRow {
        id: rowItem
        width: 800
        jobId: 7; title: "Test Song"; url: "https://example.com/v"; filename: "x.mp3"; jobState: "done"; progress: 1
        speed: ""; eta: ""; error: ""; playlistText: ""; thumbnail: ""; uploader: ""; duration: ""; size: ""
        profile: "Audio MP3"; mode: "audio"; extrasText: ""; phase: ""; hasPage: false; dlProgress: 1; ppProgress: 1
        convLabel: ""; note: ""; errorDetail: ""; section: "Today"
        onStreamRequested: (id, t) => dlg.openFor(id, t)
    }
}
"""
        backend, folder = self.make_backend()
        self.add_done_job(backend, folder)
        engine = QQmlApplicationEngine()
        self.addCleanup(engine.deleteLater)
        engine.rootContext().setContextProperty("backend", backend)
        engine.loadData(harness, QUrl.fromLocalFile(str(qml_dir / "Harness.qml")))
        self.assertTrue(engine.rootObjects())
        root = engine.rootObjects()[0]
        button = root.findChild(QObject, "streamButton")
        self.assertIsNotNone(button, "the Stream to box button is missing in the row")
        self.assertTrue(button.property("visible"))
        self.assertEqual(button.property("text"), "Stream to box")
        dlg = root.findChild(QObject, "streamDialog")
        choices = []
        backend.streamChoice.connect(choices.append)
        button.clicked.emit()                                      # no device saved: the app asks for one
        self.assertEqual(choices, [7])
        QMetaObject.invokeMethod(dlg, "openFor", Q_ARG("QVariant", 7), Q_ARG("QVariant", "Test Song"))
        self.pump(lambda: dlg.property("opened"))
        self.assertTrue(dlg.property("opened"))
        self.assertTrue(self.pump(lambda: backend.streamScanning is False and backend.streamStatus != ""))   # opening started a search
        QMetaObject.invokeMethod(dlg, "close")


if __name__ == "__main__":
    unittest.main()
