"""Ad/tracker blocking for the embedded YouTube view (no Qt imports).

A tiny local HTTP(S) proxy (127.0.0.1, random port) that refuses connections to known ad and tracker
domains and tunnels everything else untouched (HTTPS is never opened or decrypted - only the host name
of the CONNECT request is looked at). The web view is pointed at it with a Chromium flag.

Domain sources: a built-in list, plus an optional hosts-format file `blocklist.txt` in the data folder
(for example the StevenBlack list). Video streams (googlevideo.com) are never blocked.
"""
from __future__ import annotations

import select
import socket
import socketserver
import threading
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlsplit

BUILTIN = """
doubleclick.net googleadservices.com googlesyndication.com adservice.google.com
googletagservices.com google-analytics.com
adnxs.com adsrvr.org taboola.com outbrain.com criteo.com criteo.net scorecardresearch.com
quantserve.com moatads.com amazon-adsystem.com rubiconproject.com pubmatic.com openx.net
casalemedia.com advertising.com adform.net smartadserver.com 2mdn.net
""".split()

# never block these (video/image delivery, sign-in), even if a list names them
NEVER = ("googlevideo.com", "ytimg.com", "ggpht.com", "youtube.com", "google.com", "gstatic.com",
         "googleusercontent.com", "accounts.google.com")


def parse_hosts(text: str) -> set:
    out = set()
    for ln in text.splitlines():
        ln = ln.split("#", 1)[0].strip()
        if not ln:
            continue
        parts = ln.split()
        host = parts[-1].lower()
        if len(parts) <= 2 and "." in host and host not in ("localhost", "local", "broadcasthost") \
                and all(c.isalnum() or c in "-._" for c in host):
            out.add(host)
    return out


def load_domains(extra_file: Optional[Path] = None) -> frozenset:
    domains = set(BUILTIN)
    if extra_file and extra_file.is_file() and extra_file.stat().st_size < 60_000_000:
        try:
            domains |= parse_hosts(extra_file.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            pass
    return frozenset(d for d in domains if not any(d == n or d.endswith("." + n) for n in NEVER)
                     or d in BUILTIN)


def is_blocked(host: str, domains: Iterable[str]) -> bool:
    host = host.lower().rstrip(".")
    if any(host == n or host.endswith("." + n) for n in NEVER) and host not in domains:
        return False
    parts = host.split(".")
    return any(".".join(parts[i:]) in domains for i in range(len(parts) - 1))


def _pump(a: socket.socket, b: socket.socket) -> None:
    socks = [a, b]
    try:
        while True:
            ready, _, bad = select.select(socks, [], socks, 120)
            if bad or not ready:
                return
            for s in ready:
                data = s.recv(65536)
                if not data:
                    return
                (b if s is a else a).sendall(data)
    except OSError:
        return


class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        client = self.request
        client.settimeout(30)
        try:
            buf = b""
            while b"\r\n\r\n" not in buf and len(buf) < 65536:
                chunk = client.recv(8192)
                if not chunk:
                    return
                buf += chunk
            head, _, rest = buf.partition(b"\r\n\r\n")
            first = head.split(b"\r\n", 1)[0].decode("latin-1")
            method, target, _ = (first.split(" ") + ["", "", ""])[:3]
            domains = self.server.domains  # type: ignore[attr-defined]
            if method.upper() == "CONNECT":
                host, _, port = target.rpartition(":")
                if is_blocked(host, domains):
                    client.sendall(b"HTTP/1.1 403 Blocked\r\nContent-Length: 0\r\n\r\n")
                    return
                upstream = socket.create_connection((host, int(port or 443)), timeout=15)
                client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                if rest:
                    upstream.sendall(rest)
            else:
                parts = urlsplit(target)
                host = parts.hostname or ""
                if not host or parts.scheme != "http" or is_blocked(host, domains):
                    client.sendall(b"HTTP/1.1 403 Blocked\r\nContent-Length: 0\r\n\r\n")
                    return
                upstream = socket.create_connection((host, parts.port or 80), timeout=15)
                path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
                lines = [f"{method} {path} HTTP/1.1"] + [
                    ln.decode("latin-1") for ln in head.split(b"\r\n")[1:]
                    if not ln.lower().startswith((b"proxy-connection", b"connection"))]
                lines.append("Connection: close")
                upstream.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + rest)
            client.settimeout(None)
            _pump(client, upstream)
            upstream.close()
        except (OSError, ValueError):
            return


class FilterProxy(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, domains: frozenset):
        super().__init__(("127.0.0.1", 0), _Handler)
        self.domains = domains

    @property
    def port(self) -> int:
        return self.server_address[1]


def start(extra_file: Optional[Path] = None) -> FilterProxy:
    proxy = FilterProxy(load_domains(extra_file))
    threading.Thread(target=proxy.serve_forever, daemon=True, name="yeal-adblock").start()
    return proxy
