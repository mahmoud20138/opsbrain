"""Unit tests for the OpsBrain Organizational Hierarchy UI & Web Server."""

from __future__ import annotations

import http.client
import socketserver
import threading
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from opsbrain.cli.app import app
from opsbrain.cli.server import UIRequestHandler

runner = CliRunner()


def test_ui_assets_exist():
    """Verify all mandatory frontend assets exist on disk."""
    ui_dir = Path(__file__).resolve().parent.parent.parent / "ui"
    assert ui_dir.exists(), "ui/ directory must exist"

    expected_files = [
        ui_dir / "index.html",
        ui_dir / "css" / "app.css",
        ui_dir / "js" / "app.js",
        ui_dir / "js" / "data" / "models.js",
        ui_dir / "js" / "graph" / "engine.js",
        ui_dir / "js" / "components" / "inspector.js",
        ui_dir / "js" / "components" / "frameworks.js",
    ]

    for f in expected_files:
        assert f.exists(), f"Asset {f.name} must exist"
        assert f.stat().st_size > 50, f"Asset {f.name} should not be empty"


def test_models_have_all_industries():
    """Verify models.js contains all 5 industry schemas."""
    models_file = Path(__file__).resolve().parent.parent.parent / "ui" / "js" / "data" / "models.js"
    content = models_file.read_text(encoding="utf-8")

    expected_industries = [
        "tech_saas",
        "manufacturing_supply_chain",
        "healthcare_networks",
        "financial_services",
        "retail_ecommerce",
    ]

    for ind in expected_industries:
        assert ind in content, f"Industry {ind} must be defined in models.js"


def test_ui_request_handler_serves_files():
    """Verify UIRequestHandler starts on a random port and serves index.html."""
    # Find a free port by binding to 0
    with socketserver.TCPServer(("127.0.0.1", 0), UIRequestHandler) as httpd:
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.1)

        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3.0)
            conn.request("GET", "/index.html")
            resp = conn.getresponse()
            assert resp.status == 200
            body = resp.read().decode("utf-8")
            assert "OpsBrain" in body
            assert "Enterprise Organizational" in body
            conn.close()
        finally:
            httpd.shutdown()
            httpd.server_close()


def test_cli_ui_help():
    """Verify `opsbrain ui --help` outputs valid help text."""
    result = runner.invoke(app, ["ui", "--help"])
    assert result.exit_code == 0
    assert "Enterprise Organizational Hierarchy" in result.output
    assert "--port" in result.output
