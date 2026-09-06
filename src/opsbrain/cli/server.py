"""Lightweight embedded HTTP server for the OpsBrain Organizational Hierarchy UI."""

from __future__ import annotations

import functools
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path
from typing import ClassVar

import structlog

logger = structlog.get_logger(__name__)


class UIRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler that serves the ui/ directory."""

    # Set base directory to the ui/ folder
    ui_dir: ClassVar[Path] = Path(__file__).resolve().parent.parent.parent.parent / "ui"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.ui_dir), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        logger.debug("ui_server.request", message=format % args)


def run_ui_server(port: int = 8080, open_browser: bool = True) -> None:
    """Start the UI server on the given port and optionally open a browser."""
    ui_path = UIRequestHandler.ui_dir
    if not ui_path.exists() or not (ui_path / "index.html").exists():
        raise FileNotFoundError(f"UI directory or index.html not found at: {ui_path}")

    handler = functools.partial(UIRequestHandler)

    # Allow socket address reuse
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        url = f"http://127.0.0.1:{port}"
        logger.info("ui_server.started", url=url, path=str(ui_path))

        if open_browser:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("ui_server.stopping")
        finally:
            httpd.server_close()
