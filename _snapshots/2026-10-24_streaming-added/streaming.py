"""Stream finished downloads to UPnP/DLNA renderers in the local network (no Qt imports, standard library only).

Typical targets: KEF LS50 Wireless (I and II), KEF LSX, smart TVs, AV receivers, Sonos and other DLNA boxes.

How it works
- Discovery: SSDP M-SEARCH (UDP multicast, sent from every local IPv4 address) finds "MediaRenderer" devices; the device
  description XML gives name, model and the control URLs. Addresses can also be added by hand.
- Serving: the speaker does not receive the file, it fetches it. A small HTTP server (own port, only registered files,
  random token in the URL, only clients from private/local networks, Range requests supported) hands the file out.
- Control: SOAP calls (SetAVTransportURI, Play, Pause, Stop, SetVolume) to the renderer.
"""
from __future__ import annotations

import ipaddress
import mimetypes
import re
import secrets
import select
import socket
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from xml.sax.saxutils import escape

SSDP_ADDR = ("239.255.255.250", 1900)
RENDERER_ST = "urn:schemas-upnp-org:device:MediaRenderer:1"
AVT = "urn:schemas-upnp-org:service:AVTransport:1"
RCS = "urn:schemas-upnp-org:service:RenderingControl:1"
MAX_XML_BYTES = 1_000_000
HTTP_TIMEOUT = 4.0
DLNA_FLAGS = "01700000000000000000000000000000"   # streaming transfer, byte seek, connection stalling

_MIME = {
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac", ".wav": "audio/wav",
    ".ogg": "audio/ogg", ".opus": "audio/ogg", ".mp4": "video/mp4", ".m4v": "video/mp4",
    ".mkv": "video/x-matroska", ".webm": "video/webm", ".mov": "video/quicktime",
}


class StreamError(Exception):
    """A problem that can be shown to the user as is."""


@dataclass
class Renderer:
    id: str                 # UDN (uuid:...), or the description URL when the device has none
    name: str
    location: str           # URL of the device description
    host: str
    control_url: str        # AVTransport
    rc_url: str = ""        # RenderingControl (volume); '' = not available
    manufacturer: str = ""
    model: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> Optional["Renderer"]:
        try:
            return cls(id=str(raw["id"])[:200], name=str(raw.get("name") or raw["id"])[:120],
                       location=str(raw["location"])[:500], host=str(raw.get("host", ""))[:100],
                       control_url=str(raw["control_url"])[:500], rc_url=str(raw.get("rc_url", ""))[:500],
                       manufacturer=str(raw.get("manufacturer", ""))[:80], model=str(raw.get("model", ""))[:80])
        except (KeyError, TypeError, AttributeError):
            return None

    # ---- SOAP -----------------------------------------------------------
    def _soap(self, url: str, service: str, action: str, args: Iterable[Tuple[str, object]]) -> Dict[str, str]:
        body = "".join(f"<{k}>{escape(str(v))}</{k}>" for k, v in args)
        envelope = ('<?xml version="1.0" encoding="utf-8"?>'
                    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
                    's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
                    f'<u:{action} xmlns:u="{service}">{body}</u:{action}></s:Body></s:Envelope>')
        req = urllib.request.Request(url, data=envelope.encode("utf-8"), method="POST", headers={
            "Content-Type": 'text/xml; charset="utf-8"', "SOAPACTION": f'"{service}#{action}"'})
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                data = resp.read(MAX_XML_BYTES)
        except urllib.error.HTTPError as exc:
            raise StreamError(_soap_fault(exc.read(MAX_XML_BYTES)) or f"{self.name}: HTTP {exc.code}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise StreamError(f"{self.name} is not reachable ({getattr(exc, 'reason', exc)}).") from exc
        return _soap_values(data)

    def _avt(self, action: str, **args) -> Dict[str, str]:
        return self._soap(self.control_url, AVT, action, [("InstanceID", 0)] + list(args.items()))

    # ---- transport ------------------------------------------------------
    def play_url(self, url: str, title: str, mime: str, video: bool = False) -> None:
        try:
            self._avt("Stop")        # a stopped renderer accepts a new URI more reliably; errors are irrelevant
        except StreamError:
            pass
        self._avt("SetAVTransportURI", CurrentURI=url, CurrentURIMetaData=didl(url, title, mime, video))
        self._avt("Play", Speed=1)

    def pause(self) -> None:
        self._avt("Pause")

    def resume(self) -> None:
        self._avt("Play", Speed=1)

    def stop(self) -> None:
        self._avt("Stop")

    def state(self) -> str:
        """PLAYING | PAUSED_PLAYBACK | STOPPED | TRANSITIONING | NO_MEDIA_PRESENT | ''"""
        return self._avt("GetTransportInfo").get("CurrentTransportState", "")

    # ---- volume ---------------------------------------------------------
    def set_volume(self, percent: int) -> None:
        if not self.rc_url:
            raise StreamError(f"{self.name} has no volume control over the network.")
        self._soap(self.rc_url, RCS, "SetVolume", [("InstanceID", 0), ("Channel", "Master"),
                                                   ("DesiredVolume", max(0, min(100, int(percent))))])

    def get_volume(self) -> int:
        if not self.rc_url:
            return -1
        vals = self._soap(self.rc_url, RCS, "GetVolume", [("InstanceID", 0), ("Channel", "Master")])
        try:
            return int(vals.get("CurrentVolume", -1))
        except ValueError:
            return -1


# ---- XML helpers ---------------------------------------------------------
def _safe_xml(data: bytes) -> ET.Element:
    """Parse XML from the network; documents with a DTD/entities are refused (entity expansion attacks)."""
    if b"<!DOCTYPE" in data[:2000].upper() or b"<!ENTITY" in data.upper():
        raise StreamError("Unexpected XML from the device.")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise StreamError("The device sent invalid XML.") from exc


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _soap_values(data: bytes) -> Dict[str, str]:
    root = _safe_xml(data)
    out: Dict[str, str] = {}
    for el in root.iter():
        if len(el) == 0 and el.text is not None and _local(el.tag) not in ("Envelope", "Body"):
            out[_local(el.tag)] = el.text
    return out


def _soap_fault(data: bytes) -> str:
    try:
        vals = _soap_values(data)
    except StreamError:
        return ""
    code, desc = vals.get("errorCode", ""), vals.get("errorDescription", "")
    return f"The device refused the request ({desc or 'error'} {code})".strip() if (code or desc) else ""


def didl(url: str, title: str, mime: str, video: bool = False) -> str:
    kind = "object.item.videoItem" if video else "object.item.audioItem.musicTrack"
    proto = f"http-get:*:{mime}:DLNA.ORG_OP=01;DLNA.ORG_CI=0;DLNA.ORG_FLAGS={DLNA_FLAGS}"
    return ('<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">'
            f'<item id="0" parentID="-1" restricted="1"><dc:title>{escape(title or "Yeal")}</dc:title>'
            f'<upnp:class>{kind}</upnp:class><res protocolInfo="{escape(proto, {chr(34): "&quot;"})}">{escape(url)}</res>'
            '</item></DIDL-Lite>')


def mime_for(path: Path) -> str:
    ext = Path(path).suffix.lower()
    return _MIME.get(ext) or mimetypes.guess_type(str(path))[0] or "application/octet-stream"


def is_video(path: Path) -> bool:
    return mime_for(path).startswith("video/")


# ---- discovery -----------------------------------------------------------
def local_ipv4_addresses() -> List[str]:
    """Own IPv4 addresses (default route first); loopback and link-local addresses are left out."""
    found: List[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))      # no packet is sent; only selects the outgoing interface
            found.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.append(info[4][0])
    except OSError:
        pass
    out: List[str] = []
    for ip in found:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if addr.is_loopback or addr.is_link_local or addr.is_unspecified or ip in out:
            continue
        out.append(ip)
    return out


def local_ip_for(host: str) -> str:
    """The own address that the given LAN host will see (used in the media URL)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((host, 9))
            return s.getsockname()[0]
    except OSError:
        ips = local_ipv4_addresses()
        if ips:
            return ips[0]
        raise StreamError("This PC has no network address (is Wi-Fi/LAN connected?).")


def _msearch(st: str) -> bytes:
    return ("M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 2\r\n"
            f"ST: {st}\r\n\r\n").encode("ascii")


def _ssdp_locations(timeout: float, unicast: Iterable[str] = ()) -> List[str]:
    socks: List[socket.socket] = []
    for ip in local_ipv4_addresses() or ["0.0.0.0"]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            s.bind((ip, 0))
            s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ip))
            s.setblocking(False)
            socks.append(s)
        except OSError:
            continue
    if not socks:
        return []
    msg = _msearch(RENDERER_ST)
    targets = [SSDP_ADDR] + [(h, 1900) for h in unicast]
    for _ in range(2):                                    # UDP is lossy: send twice
        for s in socks:
            for t in targets:
                try:
                    s.sendto(msg, t)
                except OSError:
                    pass
        time.sleep(0.15)
    locations: List[str] = []
    end = time.time() + timeout
    try:
        while True:
            left = end - time.time()
            if left <= 0:
                break
            ready, _, _ = select.select(socks, [], [], left)
            for s in ready:
                try:
                    data, _addr = s.recvfrom(4096)
                except OSError:
                    continue
                m = re.search(rb"(?im)^location:\s*(\S+)", data)
                if m:
                    loc = m.group(1).decode("ascii", "ignore")
                    if loc.startswith("http") and loc not in locations:
                        locations.append(loc)
    finally:
        for s in socks:
            s.close()
    return locations


def describe(location: str) -> Optional[Renderer]:
    """Read a device description. None when it is not a renderer with AVTransport."""
    parsed = urlparse(location)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    try:
        addr = ipaddress.ip_address(parsed.hostname)
        if not (addr.is_private or addr.is_link_local):
            return None                                   # only devices of the local network
    except ValueError:
        pass
    try:
        with urllib.request.urlopen(location, timeout=HTTP_TIMEOUT) as resp:
            data = resp.read(MAX_XML_BYTES)
        root = _safe_xml(data)
    except (urllib.error.URLError, OSError, StreamError):
        return None
    base = location
    for el in root.iter():
        if _local(el.tag) == "URLBase" and (el.text or "").strip():
            base = el.text.strip()
    for dev in root.iter():
        if _local(dev.tag) != "device":
            continue
        kids = {_local(k.tag): (k.text or "").strip() for k in dev if len(k) == 0}
        if "MediaRenderer" not in kids.get("deviceType", ""):
            continue
        avt = rcs = ""
        for svc in dev.iter():
            if _local(svc.tag) != "service":
                continue
            f = {_local(k.tag): (k.text or "").strip() for k in svc}
            if f.get("serviceType", "").startswith("urn:schemas-upnp-org:service:AVTransport"):
                avt = urljoin(base, f.get("controlURL", ""))
            elif f.get("serviceType", "").startswith("urn:schemas-upnp-org:service:RenderingControl"):
                rcs = urljoin(base, f.get("controlURL", ""))
        if not avt:
            continue
        return Renderer(id=kids.get("UDN") or location, name=kids.get("friendlyName") or parsed.hostname,
                        location=location, host=parsed.hostname, control_url=avt, rc_url=rcs,
                        manufacturer=kids.get("manufacturer", ""), model=kids.get("modelName", ""))
    return None


def discover(timeout: float = 4.0, hosts: Iterable[str] = (),
             on_found: Optional[Callable[[Renderer], None]] = None) -> List[Renderer]:
    """Find renderers: multicast search plus unicast search / direct description URLs for manual `hosts`."""
    hosts = [h.strip() for h in hosts if h and h.strip()]
    urls = [h for h in hosts if h.lower().startswith("http")]
    plain = [h for h in hosts if not h.lower().startswith("http")]
    locations = _ssdp_locations(max(1.0, float(timeout)), plain) + urls
    result: List[Renderer] = []
    seen = set()
    for loc in dict.fromkeys(locations):
        r = describe(loc)
        if r is None or r.id in seen:
            continue
        seen.add(r.id)
        result.append(r)
        if on_found:
            on_found(r)
    result.sort(key=lambda r: r.name.lower())
    return result


def check_host(text: str) -> str:
    """Validate a manually entered address: an IPv4 address, a host name or a description URL. '' = ok, else the reason."""
    text = (text or "").strip()
    if not text:
        return "Please enter an address."
    if text.lower().startswith("http"):
        p = urlparse(text)
        return "" if p.scheme in ("http", "https") and p.hostname else "That is not a valid URL."
    if re.fullmatch(r"[A-Za-z0-9._-]{1,100}", text):
        return ""
    return "Enter an IP address (e.g. 192.168.1.50), a device name, or the full description URL."


# ---- media server ---------------------------------------------------------
def _private_client(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return False
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_private or addr.is_loopback or addr.is_link_local


class _MediaHandler(BaseHTTPRequestHandler):
    server_version = "Yeal"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args) -> None:
        pass

    def _entry(self):
        if not _private_client(self.client_address[0]):
            self.send_error(403)
            return None
        m = re.fullmatch(r"/m/([A-Za-z0-9_-]{16,64})(\.[A-Za-z0-9]{1,5})?", self.path.split("?", 1)[0])
        entry = self.server.media.get(m.group(1)) if m else None      # type: ignore[attr-defined]
        if entry is None or not entry["path"].is_file():
            self.send_error(404)
            return None
        return entry

    def _serve(self, head: bool) -> None:
        entry = self._entry()
        if entry is None:
            return
        path: Path = entry["path"]
        size = path.stat().st_size
        start, end, status = 0, size - 1, 200
        rng = self.headers.get("Range", "")
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng.strip())
        if m and (m.group(1) or m.group(2)) and size > 0:
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start = max(0, size - int(m.group(2)))
            end = min(end, size - 1)
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            status = 206
        length = end - start + 1 if size else 0
        self.send_response(status)
        self.send_header("Content-Type", entry["mime"])
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("transferMode.dlna.org", "Streaming")
        self.send_header("contentFeatures.dlna.org",
                         f"DLNA.ORG_OP=01;DLNA.ORG_CI=0;DLNA.ORG_FLAGS={DLNA_FLAGS}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        entry["hits"] += 1
        if head or not length:
            return
        try:
            with open(path, "rb") as fh:
                fh.seek(start)
                left = length
                while left > 0:
                    chunk = fh.read(min(65536, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, OSError):
            self.close_connection = True      # the renderer closed the connection (seek, next track): normal

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        self._serve(False)

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve(True)


class MediaServer:
    """HTTP server for the files that are currently streamed. Only registered files are served."""

    def __init__(self, port: int = 0):
        self.port = int(port or 0)
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._media: Dict[str, dict] = {}
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def start(self) -> int:
        with self._lock:
            if self._httpd is None:
                try:
                    httpd = ThreadingHTTPServer(("0.0.0.0", self.port), _MediaHandler)
                except OSError as exc:
                    raise StreamError(f"Streaming port {self.port or 'auto'} cannot be opened: "
                                      f"{exc.strerror or exc}. Choose another port in Settings.") from exc
                httpd.daemon_threads = True
                httpd.media = self._media          # type: ignore[attr-defined]
                threading.Thread(target=httpd.serve_forever, name="yeal-media", daemon=True).start()
                self._httpd = httpd
            return self._httpd.server_address[1]

    def add(self, path: Path) -> str:
        """Register a file; returns the URL path part ('/m/<token>.ext')."""
        path = Path(path)
        if not path.is_file():
            raise StreamError("The file was not found.")
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._media[token] = {"path": path, "mime": mime_for(path), "hits": 0}
        ext = path.suffix.lower() if re.fullmatch(r"\.[A-Za-z0-9]{1,5}", path.suffix) else ""
        return f"/m/{token}{ext}"

    def hits(self, url_path: str) -> int:
        m = re.match(r"/m/([A-Za-z0-9_-]+)", url_path)
        return self._media.get(m.group(1), {}).get("hits", 0) if m else 0

    def clear(self) -> None:
        with self._lock:
            self._media.clear()

    def stop(self) -> None:
        with self._lock:
            if self._httpd is not None:
                self._httpd.shutdown()
                self._httpd.server_close()
                self._httpd = None
            self._media.clear()


class Streamer:
    """Serves a file and tells a renderer to play it."""

    def __init__(self) -> None:
        self.server = MediaServer()
        self.renderer: Optional[Renderer] = None

    def set_port(self, port: int) -> None:
        port = int(port or 0)
        if port != self.server.port:
            self.server.stop()
            self.server.port = port

    def stream(self, renderer: Renderer, path: Path, title: str, volume: int = -1,
               wait_for_fetch: float = 6.0) -> str:
        """Start playing. Returns '' or a warning (e.g. the device never fetched the file: firewall)."""
        port = self.server.start()
        self.server.clear()
        url_path = self.server.add(path)
        url = f"http://{local_ip_for(renderer.host)}:{port}{url_path}"
        if volume >= 0 and renderer.rc_url:
            try:
                renderer.set_volume(volume)
            except StreamError:
                pass                         # volume is a convenience, never a reason to fail
        renderer.play_url(url, title, mime_for(path), is_video(path))
        self.renderer = renderer
        end = time.time() + wait_for_fetch
        while time.time() < end:
            if self.server.hits(url_path) > 0:
                return ""
            time.sleep(0.2)
        return (f"{renderer.name} did not fetch the file. Allow Yeal in the Windows firewall for private networks "
                f"(or set a fixed port in Settings and open it) and check that the PC and the device are in the same network.")

    def stop(self) -> None:
        r, self.renderer = self.renderer, None
        if r is not None:
            try:
                r.stop()
            except StreamError:
                pass
        self.server.clear()

    def shutdown(self) -> None:
        self.stop()
        self.server.stop()
