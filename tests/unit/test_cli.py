"""Unit tests for the OpsBrain Typer CLI commands."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from opsbrain.cli.app import app
from opsbrain.harness.mock import MockLLMClient

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "opsbrain v" in result.output


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "OpsBrain" in result.output
    assert "analyze" in result.output
    assert "providers" in result.output
    assert "config" in result.output


def test_cli_config_init_and_show(tmp_path):
    cfg_file = tmp_path / "custom_config.yaml"
    init_res = runner.invoke(app, ["config", "init", "-o", str(cfg_file)])
    assert init_res.exit_code == 0
    assert cfg_file.exists()

    show_res = runner.invoke(app, ["config", "show", "-c", str(cfg_file)])
    assert show_res.exit_code == 0
    assert "log_level" in show_res.output


def test_cli_providers_list():
    result = runner.invoke(app, ["providers", "list"])
    assert result.exit_code == 0
    assert "LLM Providers" in result.output


def test_cli_analyze_file(tmp_path):
    incident_file = tmp_path / "incident.json"
    incident_file.write_text(json.dumps({
        "source": "api-gateway",
        "metrics": {"error_rate": 0.20},
        "logs": ["Connection refused"],
    }), encoding="utf-8")

    mock_client = MockLLMClient(response_content="""{
        "anomalies_detected": true,
        "alerts": [{"title": "Gateway Crash", "severity": "critical", "affected_systems": ["api"]}],
        "root_cause": "Network partition",
        "solutions": [{"title": "Reboot", "steps": ["reboot"]}],
        "summary": "Investigated",
        "action_items": []
    }""")

    with patch("opsbrain.harness.registry.ProviderRegistry.get", return_value=mock_client):
        result = runner.invoke(app, ["analyze", str(incident_file)])
        assert result.exit_code == 0
        assert "Analysis complete" in result.output


def test_cli_run_mock():
    result = runner.invoke(app, ["run", "incident_response", "--mock"])
    assert result.exit_code == 0
    assert "MockLLMClient" in result.output
    assert "Analysis complete" in result.output


def test_cli_analyze_mock(tmp_path):
    incident_file = tmp_path / "incident.json"
    incident_file.write_text(json.dumps({"source": "demo-db", "metrics": {}}), encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(incident_file), "--mock"])
    assert result.exit_code == 0
    assert "MockLLMClient" in result.output
    assert "Analysis complete" in result.output

