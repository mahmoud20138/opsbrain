"""OpsBrain CLI application — the main entry point.

Provides commands for:
- ``opsbrain run`` — run a full analysis pipeline
- ``opsbrain analyze`` — analyze an incident from a file
- ``opsbrain providers`` — list and test LLM providers
- ``opsbrain config`` — manage configuration
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console

from opsbrain import __version__

app = typer.Typer(
    name="opsbrain",
    help="OpsBrain - Multi-agent LLM-powered enterprise operations monitoring.",
    add_completion=False,
    no_args_is_help=True,
)

console = Console(highlight=False)


# ---------------------------------------------------------------------------
# Version callback
# ---------------------------------------------------------------------------

def _version_callback(value: bool) -> None:
    if value:
        console.print(f"opsbrain v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit.",
        callback=_version_callback, is_eager=True,
    ),
) -> None:
    """OpsBrain - Multi-agent LLM enterprise operations harness."""


# ---------------------------------------------------------------------------
# analyze command
# ---------------------------------------------------------------------------

@app.command()
def analyze(
    file: Path = typer.Argument(..., help="Path to incident data file (JSON)."),
    config: Path | None = typer.Option(None, "--config", "-c", help="Configuration file path."),
    provider: str | None = typer.Option(None, "--provider", "-p", help="Force a specific LLM provider."),
    mock: bool = typer.Option(False, "--mock", "-m", help="Run with offline MockLLMClient for testing."),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed output."),
) -> None:
    """Analyze an incident from a JSON file.

    Runs the full pipeline: Monitor -> RCA -> Solver -> Coordinator.
    """
    from opsbrain.cli.formatters import print_banner

    print_banner()

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    try:
        with open(file, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Error:[/red] Invalid JSON: {exc}")
        raise typer.Exit(1) from None

    console.print(f"[cyan]Analyzing incident from:[/cyan] {file}")
    asyncio.run(_run_analysis(data, config_path=config, provider_override=provider, mock=mock, verbose=verbose))


# ---------------------------------------------------------------------------
# providers command group
# ---------------------------------------------------------------------------

providers_app = typer.Typer(help="Manage LLM providers.")
app.add_typer(providers_app, name="providers")


@providers_app.command("list")
def providers_list(
    config: Path | None = typer.Option(None, "--config", "-c", help="Configuration file path."),
) -> None:
    """List all configured LLM providers and their status."""
    from opsbrain.cli.formatters import print_banner, print_providers_table
    from opsbrain.core.config import load_config
    from opsbrain.harness.registry import ProviderRegistry

    print_banner()

    cfg = load_config(config)
    registry = ProviderRegistry(cfg)
    providers = registry.list_available()
    print_providers_table(providers)


@providers_app.command("test")
def providers_test(
    config: Path | None = typer.Option(None, "--config", "-c", help="Configuration file path."),
) -> None:
    """Test connectivity to all configured providers."""
    from opsbrain.cli.formatters import print_banner
    from opsbrain.core.config import load_config
    from opsbrain.harness.registry import ProviderRegistry

    print_banner()

    cfg = load_config(config)
    registry = ProviderRegistry(cfg)

    console.print("[cyan]Testing provider connectivity...[/cyan]\n")
    results = asyncio.run(registry.health_check_all())

    for prov, healthy in results.items():
        status = "[green][+] Connected[/green]" if healthy else "[red][-] Failed[/red]"
        console.print(f"  {prov.value:15s} {status}")

    asyncio.run(registry.close_all())


# ---------------------------------------------------------------------------
# config command group
# ---------------------------------------------------------------------------

config_app = typer.Typer(help="Manage configuration.")
app.add_typer(config_app, name="config")


@config_app.command("init")
def config_init(
    output: Path = typer.Option(
        Path("configs/default.yaml"), "--output", "-o",
        help="Output path for the config file.",
    ),
) -> None:
    """Generate a default configuration file."""
    from opsbrain.core.config import generate_default_config

    output.parent.mkdir(parents=True, exist_ok=True)
    config_content = generate_default_config()
    output.write_text(config_content, encoding="utf-8")
    console.print(f"[green][+] Configuration written to:[/green] {output}")


@config_app.command("show")
def config_show(
    config: Path | None = typer.Option(None, "--config", "-c", help="Configuration file to display."),
) -> None:
    """Display the current configuration."""
    from opsbrain.core.config import load_config

    cfg = load_config(config)
    console.print_json(cfg.model_dump_json(indent=2))


# ---------------------------------------------------------------------------
# ui command
# ---------------------------------------------------------------------------

@app.command("ui")
def launch_ui(
    port: int = typer.Option(8080, "--port", "-p", help="Port to serve the UI on."),
    open_browser: bool = typer.Option(True, "--browser/--no-browser", help="Automatically open default browser."),
) -> None:
    """Launch the Enterprise Organizational Hierarchy & Frameworks Graph UI."""
    from opsbrain.cli.formatters import print_banner
    from opsbrain.cli.server import run_ui_server

    print_banner()
    console.print(f"[bold cyan]Launching OpsBrain Enterprise Graph UI on http://127.0.0.1:{port}[/bold cyan]")
    console.print("[dim]Press Ctrl+C to stop the server.[/dim]\n")

    try:
        run_ui_server(port=port, open_browser=open_browser)
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    except OSError as exc:
        console.print(f"[red]Error starting server on port {port}:[/red] {exc}")
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------

@app.command()
def run(
    pipeline: str = typer.Argument(
        "incident_response",
        help="Pipeline to run (incident_response, quick_triage, deep_analysis).",
    ),
    source: Path | None = typer.Option(None, "--source", "-s", help="Data source file (JSON)."),
    config: Path | None = typer.Option(None, "--config", "-c", help="Configuration file path."),
    provider: str | None = typer.Option(None, "--provider", "-p", help="Force a specific LLM provider."),
    mock: bool = typer.Option(False, "--mock", "-m", help="Run with offline MockLLMClient for testing."),
) -> None:
    """Run a named analysis pipeline."""
    from opsbrain.cli.formatters import print_banner

    print_banner()

    data: dict = {}
    if source:
        if not source.exists():
            console.print(f"[red]Error:[/red] Source file not found: {source}")
            raise typer.Exit(1)
        with open(source, encoding="utf-8") as f:
            data = json.load(f)

    console.print(f"[cyan]Running pipeline:[/cyan] {pipeline}")
    asyncio.run(_run_analysis(data, config_path=config, provider_override=provider, mock=mock))


# ---------------------------------------------------------------------------
# Core analysis runner
# ---------------------------------------------------------------------------

async def _run_analysis(
    data: dict,
    *,
    config_path: Path | None = None,
    provider_override: str | None = None,
    mock: bool = False,
    verbose: bool = False,
) -> None:
    """Run the full analysis pipeline on the given data."""
    from opsbrain.agents.base import AgentContext
    from opsbrain.agents.coordinator import CoordinatorAgent
    from opsbrain.agents.monitor import MonitorAgent
    from opsbrain.agents.rca import RCAAgent
    from opsbrain.agents.solver import SolverAgent
    from opsbrain.cli.formatters import (
        print_alert,
        print_rca_report,
        print_resolution_plan,
        print_solutions,
    )
    from opsbrain.core.config import load_config
    from opsbrain.core.events import EventBus
    from opsbrain.core.logging import setup_logging
    from opsbrain.core.types import Provider
    from opsbrain.harness.mock import MockLLMClient
    from opsbrain.harness.registry import ProviderRegistry

    # Load config
    cfg = load_config(config_path)
    setup_logging(cfg.log_level)

    registry: ProviderRegistry | None = None
    if mock:
        client = MockLLMClient()
        console.print("[yellow]Using offline MockLLMClient (--mock enabled)[/yellow]")
    else:
        # Get an LLM client
        registry = ProviderRegistry(cfg)
        prov = Provider(provider_override) if provider_override else cfg.routing.default_provider

        try:
            client = registry.get(prov)
        except Exception as exc:
            console.print(f"[red]Error:[/red] Cannot initialize provider '{prov.value}': {exc}")

            # Try fallback
            for fallback in cfg.routing.fallback_chain:
                if fallback != prov:
                    try:
                        client = registry.get(fallback)
                        console.print(f"[yellow]Using fallback provider:[/yellow] {fallback.value}")
                        break
                    except Exception:
                        continue
            else:
                console.print("[red]No providers available. Configure an API key or use --mock for offline demo mode.[/red]")
                return

    # Set up shared services
    event_bus = EventBus()

    # Create agents
    agent_kwargs = {"llm_client": client, "event_bus": event_bus}
    monitor = MonitorAgent(**agent_kwargs)
    rca = RCAAgent(**agent_kwargs)
    solver = SolverAgent(**agent_kwargs)
    coordinator = CoordinatorAgent(**agent_kwargs)

    context = AgentContext(data=data)
    prior_outputs: dict[str, dict] = {}

    # --- Stage 1: Monitor ---
    console.print("\n[bold cyan]=== Stage 1: Anomaly Detection ===[/bold cyan]")
    with console.status("[cyan]Monitor Agent analyzing...[/cyan]"):
        monitor_output = await monitor.process(context)
    prior_outputs["monitor"] = monitor_output.structured_data

    alerts = monitor_output.structured_data.get("alerts", [])
    if alerts:
        for alert in alerts:
            print_alert(alert)
    else:
        console.print("[green]No anomalies detected.[/green]")

    # --- Stage 2: Root Cause Analysis ---
    if alerts:
        console.print("\n[bold cyan]=== Stage 2: Root Cause Analysis ===[/bold cyan]")
        context.prior_outputs = prior_outputs
        context.data["alerts"] = alerts
        with console.status("[cyan]RCA Agent investigating...[/cyan]"):
            rca_output = await rca.process(context)
        prior_outputs["rca"] = rca_output.structured_data

        if rca_report := rca_output.structured_data.get("rca_report"):
            print_rca_report(rca_report)

        # --- Stage 3: Solution Generation ---
        console.print("\n[bold cyan]=== Stage 3: Solution Generation ===[/bold cyan]")
        context.prior_outputs = prior_outputs
        with console.status("[cyan]Solver Agent generating solutions...[/cyan]"):
            solver_output = await solver.process(context)
        prior_outputs["solver"] = solver_output.structured_data

        if solutions := solver_output.structured_data.get("solutions"):
            print_solutions(solutions)

        # --- Stage 4: Coordination ---
        console.print("\n[bold cyan]=== Stage 4: Cross-team Coordination ===[/bold cyan]")
        context.prior_outputs = prior_outputs
        with console.status("[cyan]Coordinator Agent planning...[/cyan]"):
            coord_output = await coordinator.process(context)
        prior_outputs["coordinator"] = coord_output.structured_data

        if plan := coord_output.structured_data.get("resolution_plan"):
            print_resolution_plan(plan)

    console.print("\n[bold green][+] Analysis complete.[/bold green]")

    # Cleanup
    if registry is not None:
        await registry.close_all()
    else:
        await client.close()
