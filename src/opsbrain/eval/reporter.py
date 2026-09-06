"""Benchmark and evaluation reporter.

Formats multi-agent benchmark runs into executive Markdown and JSON reports.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from opsbrain.eval.scorer import EvaluationScore
from opsbrain.orchestrator.engine import PipelineResult


class BenchmarkReport(BaseModel):
    """Aggregated report of benchmark runs."""

    title: str = "OpsBrain Benchmark Report"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_scenarios: int = 0
    passed_scenarios: int = 0
    average_score: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_seconds: float = 0.0
    scenario_results: dict[str, dict[str, Any]] = Field(default_factory=dict)


def generate_markdown_report(
    benchmark_data: dict[str, tuple[PipelineResult, EvaluationScore]],
    *,
    title: str = "OpsBrain Evaluation & Benchmark Report",
) -> str:
    """Generate a clean GitHub-flavored Markdown report of benchmark runs."""
    lines = [
        f"# {title}",
        f"*Generated at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        "",
        "## Summary",
        "",
        "| Scenario | Category | Overall Score | Anomaly | RCA | Solution | Coord | Risk | Status |",
        "|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    total_score = 0.0
    total_tokens = 0
    total_cost = 0.0
    total_duration = 0.0
    count = len(benchmark_data)

    for sc_id, (result, score) in benchmark_data.items():
        total_score += score.overall_score
        total_tokens += result.total_tokens
        total_cost += result.total_cost
        total_duration += result.duration_seconds

        passed = score.overall_score >= 7.0
        status_badge = "PASS" if passed else "FAIL"

        lines.append(
            f"| `{sc_id}` | `{result.pipeline_name}` | **{score.overall_score:.1f}/10** | "
            f"{score.anomaly_detection_score:.1f} | {score.root_cause_accuracy:.1f} | "
            f"{score.solution_actionability:.1f} | {score.coordination_completeness:.1f} | "
            f"{score.risk_awareness:.1f} | **{status_badge}** |"
        )

    avg_score = total_score / max(count, 1)
    lines.extend([
        "",
        "### Operational Efficiency Metrics",
        "",
        f"- **Average Quality Score**: `{avg_score:.2f} / 10.0`",
        f"- **Total Scenarios Evaluated**: `{count}`",
        f"- **Total Tokens Consumed**: `{total_tokens:,}`",
        f"- **Total Estimated Cost**: `${total_cost:.5f}`",
        f"- **Total Execution Latency**: `{total_duration:.2f}s`",
        "",
        "---",
        "",
        "## Scenario Details & Feedback",
        "",
    ])

    for sc_id, (result, score) in benchmark_data.items():
        lines.append(f"### Scenario: `{sc_id}`")
        lines.append(f"- **Incident Title**: {result.incident.title}")
        lines.append(f"- **Incident Status**: `{result.incident.status.value}`")
        lines.append(f"- **Duration**: `{result.duration_seconds:.2f}s` | **Tokens**: `{result.total_tokens:,}`")

        if score.feedback:
            lines.append("- **Qualitative Feedback**:")
            for fb in score.feedback:
                lines.append(f"  - {fb}")
        else:
            lines.append("- *No negative findings recorded; all criteria met.*")
        lines.append("")

    return "\n".join(lines)
