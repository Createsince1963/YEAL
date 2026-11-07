"""Tiny read-only web server on 127.0.0.1 for saved HTML pages (no Qt imports).

YouTube refuses to play embedded videos on pages opened from disk (file://) because no
HTTP referer is sent (player error 153). Serving the page over http://127.0.0.1 fixes that.
Only files of the given folder are served, directory listings are disabled.
"""
from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import quote

_servers: Dict[str, Tuple[ThreadingHTTPServer, int]] = {}
_lock = threading.Lock()


class _Handler(SimpleHTTPRequestHandler):
    def list_directory(self, path):  # noqa: D401 - no directory listings
        self.send_error(404)
        return None

    def log_message(self, *args) -> None:
        pass


def serve(folder: Path) -> int:
    """Start (or reuse) a server for `folder`; returns its port."""
    key = str(Path(folder).resolve())
    with _lock:
        if key in _servers:
            return _servers[key][1]
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Handler, directory=key))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        _servers[key] = (server, server.server_address[1])
        return _servers[key][1]


def page_url(page: Path, mode: str = "file") -> str:
    """URL for a saved page. file:// is independent; server mode enables online embeds."""
    page = Path(page).resolve()
    if mode != "server":
        return page.as_uri()
    port = serve(page.parent)
    return f"http://127.0.0.1:{port}/{quote(page.name)}"


def shutdown_all() -> None:
    with _lock:
        for server, _ in _servers.values():
            server.shutdown()
            server.server_close()
        _servers.clear()
