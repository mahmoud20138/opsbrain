"""Rich console formatters for OpsBrain CLI output."""

from __future__ import annotations

from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console(highlight=False)

# Severity -> Rich colour mapping
_SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "cyan",
    "info": "dim",
}


def print_banner() -> None:
    """Print the OpsBrain ASCII banner."""
    banner = Text.from_markup(
        "[bold cyan]"
        "+=======================================+\n"
        "|          [*] O P S B R A I N          |\n"
        "|   Multi-Agent Enterprise Operations   |\n"
        "+=======================================+"
        "[/bold cyan]"
    )
    console.print(banner)
    console.print()


def print_providers_table(providers: list[dict[str, Any]]) -> None:
    """Print a table of available providers."""
    table = Table(
        title="LLM Providers",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Provider", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Reason", style="dim")

    for p in providers:
        status = "[+] Ready" if p["available"] else "[-] Unavailable"
        style = "green" if p["available"] else "red"
        table.add_row(p["provider"], Text(status, style=style), p.get("reason", ""))

    console.print(table)


def print_alert(alert: dict[str, Any]) -> None:
    """Print a single alert with severity-coloured panel."""
    severity = alert.get("severity", "medium")
    color = _SEVERITY_COLORS.get(severity, "white")

    content_parts = [f"[bold]{alert.get('description', '')}[/bold]"]
    if alert.get("affected_systems"):
        content_parts.append(f"\n[dim]Systems:[/dim] {', '.join(alert['affected_systems'])}")
    if alert.get("evidence"):
        content_parts.append("\n[dim]Evidence:[/dim]")
        for e in alert["evidence"]:
            content_parts.append(f"\n  - {e}")

    panel = Panel(
        "\n".join(content_parts),
        title=f"[!] {alert.get('title', 'Alert')}",
        subtitle=f"Severity: {severity.upper()}",
        border_style=color,
        box=box.HEAVY,
    )
    console.print(panel)


def print_rca_report(report: dict[str, Any]) -> None:
    """Print an RCA report."""
    panel_content = [
        f"[bold]Root Cause:[/bold] {report.get('root_cause', 'Unknown')}",
        f"[bold]Confidence:[/bold] {report.get('confidence', 0):.0%}",
    ]

    if report.get("evidence_chain"):
        panel_content.append("\n[bold]Evidence Chain:[/bold]")
        for i, ev in enumerate(report["evidence_chain"], 1):
            panel_content.append(f"  {i}. {ev}")

    if report.get("contributing_factors"):
        panel_content.append("\n[bold]Contributing Factors:[/bold]")
        for f in report["contributing_factors"]:
            panel_content.append(f"  - {f}")

    panel = Panel(
        "\n".join(panel_content),
        title="[RCA] Root Cause Analysis",
        border_style="blue",
        box=box.ROUNDED,
    )
    console.print(panel)


def print_solutions(solutions: list[dict[str, Any]]) -> None:
    """Print a list of solutions."""
    for i, sol in enumerate(solutions, 1):
        risk_color = _SEVERITY_COLORS.get(sol.get("risk_level", "medium"), "white")
        content_parts = []

        if sol.get("steps"):
            for j, step in enumerate(sol["steps"], 1):
                content_parts.append(f"  {j}. {step}")

        if sol.get("estimated_time_minutes"):
            content_parts.append(f"\n[dim]Estimated Time:[/dim] {sol['estimated_time_minutes']} minutes")
        if sol.get("rollback_plan"):
            content_parts.append(f"[dim]Rollback:[/dim] {sol['rollback_plan']}")

        panel = Panel(
            "\n".join(content_parts),
            title=f"[SOL] Solution {i}: {sol.get('title', 'Untitled')}",
            subtitle=f"Risk: {sol.get('risk_level', 'medium').upper()} | Confidence: {sol.get('confidence', 0):.0%}",
            border_style=risk_color,
            box=box.ROUNDED,
        )
        console.print(panel)


def print_resolution_plan(plan: dict[str, Any]) -> None:
    """Print a resolution plan with action items."""
    # Summary
    if plan.get("summary"):
        console.print(Panel(
            plan["summary"],
            title="[PLAN] Resolution Plan",
            border_style="green",
            box=box.ROUNDED,
        ))

    # Action items table
    if plan.get("action_items"):
        table = Table(
            title="Action Items",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold green",
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Action", style="white")
        table.add_column("Assignee", style="cyan")
        table.add_column("Team", style="blue")
        table.add_column("Priority", justify="center")
        table.add_column("Due By", style="dim")

        for i, item in enumerate(plan["action_items"], 1):
            priority = item.get("priority", "medium")
            p_color = _SEVERITY_COLORS.get(priority, "white")
            table.add_row(
                str(i),
                item.get("description", ""),
                item.get("assignee", ""),
                item.get("team", ""),
                Text(priority.upper(), style=p_color),
                item.get("due_by", ""),
            )

        console.print(table)

    # Communication draft
    if plan.get("communication_draft"):
        console.print(Panel(
            plan["communication_draft"],
            title="[MSG] Stakeholder Communication Draft",
            border_style="dim",
            box=box.SIMPLE,
        ))


def print_telemetry_summary(summary: dict[str, Any]) -> None:
    """Print telemetry/usage summary."""
    table = Table(
        title="[STATS] Usage Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Requests", str(summary.get("total_requests", 0)))
    table.add_row("Total Tokens", f"{summary.get('total_tokens', 0):,}")
    table.add_row("Total Cost", f"${summary.get('total_cost_usd', 0):.6f}")
    table.add_row("Avg Latency", f"{summary.get('average_latency_ms', 0):.0f}ms")
    table.add_row("Error Rate", f"{summary.get('error_rate', 0):.1%}")

    console.print(table)

    if summary.get("cost_by_provider"):
        ptable = Table(title="Cost by Provider", box=box.SIMPLE)
        ptable.add_column("Provider", style="cyan")
        ptable.add_column("Cost", justify="right")
        for prov, cost in summary["cost_by_provider"].items():
            ptable.add_row(prov, f"${cost:.6f}")
        console.print(ptable)
