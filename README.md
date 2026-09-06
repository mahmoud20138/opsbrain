# 🧠 OpsBrain

**Multi-agent LLM-powered enterprise operations monitoring and process optimization framework.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## What is OpsBrain?

OpsBrain deploys **specialized LLM agents** to monitor enterprise operations, detect anomalies, diagnose root causes, generate solutions, and coordinate cross-team resolution — all through a **provider-agnostic harness** that works with any LLM.

```
Monitor Agent → detects anomaly in metrics/logs
    ↓
RCA Agent → traces root cause with evidence chain
    ↓
Solver Agent → proposes actionable solutions
    ↓
Coordinator Agent → assigns teams, drafts comms, tracks resolution
```

## Key Features

- 🔍 **Real-time Anomaly Detection** — Monitor metrics, logs, and workflows for operational issues
- 🔬 **Automated Root Cause Analysis** — Trace issues to their source with evidence-backed reasoning
- 💡 **Solution Generation** — Context-aware remediation plans grounded in runbooks and past incidents
- 🤝 **Cross-team Coordination** — Automated stakeholder communication and action item tracking
- 🔄 **Provider Agnostic** — OpenAI, Gemini, Claude, Ollama, and 100+ models via LiteLLM
- 📊 **Cost & Quality Tracking** — Per-agent telemetry, model comparison, and evaluation benchmarks
- 🛡️ **Built-in Guardrails** — PII detection, cost limits, safety filters, and circuit breakers

## Supported Providers

| Provider | Models | Status |
|:---------|:-------|:-------|
| **OpenAI** | GPT-4o, o3, o4-mini | ✅ Native |
| **Google Gemini** | Gemini 2.5 Pro/Flash | ✅ Native |
| **Anthropic** | Claude Opus, Sonnet | ✅ Native |
| **Ollama** | Llama, Mistral, Qwen | ✅ Native |
| **100+ others** | via LiteLLM | ✅ Fallback |

## Quick Start

### Installation

```bash
# Install with all LLM providers
pip install opsbrain[all-providers]

# Or install with specific providers
pip install opsbrain[openai,anthropic]

# Or minimal install (uses LiteLLM for any provider)
pip install opsbrain
```

### Configure

```bash
# Initialize configuration
opsbrain config init

# Set your API key(s)
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
# or
export GEMINI_API_KEY="..."
```

### Run

```bash
# Test provider connectivity
opsbrain providers list
opsbrain providers test

# Analyze an incident from a file
opsbrain analyze incident_data.json

# Run a full monitoring pipeline
opsbrain run incident_response --source metrics.json

# Start continuous monitoring
opsbrain monitor --source prometheus --interval 60
```

### Python API

```python
import asyncio
from opsbrain import OpsBrain

async def main():
    brain = OpsBrain.from_config("configs/default.yaml")

    # Analyze an incident
    result = await brain.analyze({
        "source": "payment-service",
        "metrics": {"error_rate": 0.15, "latency_p99": 2500},
        "logs": ["Connection pool exhausted", "Timeout waiting for connection"],
    })

    print(result.root_cause)
    print(result.solution)
    print(result.resolution_plan)

asyncio.run(main())
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  CLI / Python API                │
├─────────────────────────────────────────────────┤
│              Agent Orchestrator                  │
│  ┌──────┐ ┌─────┐ ┌──────┐ ┌───────────┐       │
│  │Monitor│ │ RCA │ │Solver│ │Coordinator│       │
│  └──┬───┘ └──┬──┘ └──┬───┘ └─────┬─────┘       │
├─────┴────────┴───────┴───────────┴──────────────┤
│              LLM Harness                         │
│  Router → Adapters → Guardrails → Telemetry     │
├─────────────────────────────────────────────────┤
│  OpenAI │ Gemini │ Claude │ Ollama │ LiteLLM    │
└─────────────────────────────────────────────────┘
```

## Example Use Cases

### IT System Outage
The Monitor Agent detects an API latency spike on the Payment Service. The RCA Agent traces it to database connection pool exhaustion caused by a memory leak in v3.2.1. The Solver Agent recommends a pod restart and rollback to v3.2.0. The Coordinator Agent pages the on-call SRE and creates an incident ticket.

### Supply Chain Disruption
The Monitor Agent flags shipping delay anomalies. The RCA Agent identifies port congestion from a weather event affecting Supplier X. The Solver Agent proposes rerouting through an alternative port and activating a backup supplier. The Coordinator Agent notifies procurement, logistics, and customer service teams.

## Development

```bash
# Clone the repository
git clone https://github.com/opsbrain/opsbrain.git
cd opsbrain

# Install in development mode
pip install -e ".[dev,all-providers]"

# Run tests
pytest

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/opsbrain/
```

## Real-World Enterprise Datasets & What You Can Get

OpsBrain includes authentic, multi-domain production datasets in [`examples/data/`](examples/data/) representing high-severity real-world operational incidents:

| Domain | Dataset File | Primary Incident Symptoms & Telemetry |
|:-------|:-------------|:--------------------------------------|
| **E-Commerce** | [`real_ecommerce_checkout_outage.json`](examples/data/real_ecommerce_checkout_outage.json) | Black Friday checkout crash: HikariPool database connections saturated (298/300), NGINX 34.8% HTTP 504 timeouts, Redis memory at 98.4% with key eviction storms. |
| **FinTech** | [`real_fintech_payment_clearing_delay.json`](examples/data/real_fintech_payment_clearing_delay.json) | Intraday Fedwire clearing window risk: Kafka consumer lag of 142,500 messages, AML sanctions queue depth 4,820, JVM GC pause times 4,850ms. |
| **Supply Chain** | [`real_supply_chain_port_disruption.json`](examples/data/real_supply_chain_port_disruption.json) & [`real_supply_chain_metrics.csv`](examples/data/real_supply_chain_metrics.csv) | Port of Long Beach congestion: dwell time spiked to 16.4 days (vs 3.2 baseline), 420 inbound TEU backlog, automotive semiconductor SKU-774 line-stoppage risk. |

### The 7 Deliverables You Get from OpsBrain

When you run an incident through OpsBrain's 5-stage agent pipeline (`Monitor` → `RCA` → `Solver` → `Coordinator` → `Evaluator`), you receive 7 actionable intelligence deliverables:

1. **Automated Anomaly Detection & Severity Triage**:
   - Zero-click ingestion of metrics, container logs, and alert payloads.
   - Blast radius analysis mapping impacted microservices and downstream dependencies.
2. **Formal Root Cause Analysis (RCA) with Evidence Chain**:
   - Unambiguous root cause identification grounded in log stack traces and telemetry.
   - Chronological causal timeline and contributing factor attribution.
3. **Ranked Actionable Remediation Plans & Rollback Guardrails**:
   - Step-by-step CLI commands (`kubectl`, `aws`, `curl`, SQL).
   - Estimated MTTR, risk assessment, and validated rollback execution commands.
4. **Cross-Team Coordination & Comms Pack**:
   - Department-specific action items with assignees, priority levels, and SLA deadlines.
   - Automated Slack broadcast drafts and executive briefings.
5. **Multi-Axis Pipeline Quality Scorecard**:
   - Quantitative rubric evaluation (0-100%) across 5 dimensions: Anomaly Detection, RCA Accuracy, Solution Actionability, Coordination Completeness, and Risk Awareness.
6. **Persisted State Machine Audit Trail & Telemetry**:
   - Immutable state lifecycle log (`DETECTED` → `ANALYZING` → `DIAGNOSED` → `RESOLVING` → `RESOLVED`).
   - Token usage and cost tracking per agent.
7. **Exportable Executive Post-Mortem Report**:
   - Automatic generation of production-ready post-mortem documentation in [`reports/`](reports/).

### Run the Real-World Demo

```bash
# Direct Python execution
python examples/real_data_pipeline_demo.py

# Or via Windows launcher
run.bat realdata
```

## Windows Quick Launcher (Batch Scripts)

For Windows environments, two launcher scripts are provided in the repository root:

- **`run.bat`** — Interactive terminal menu or direct command router:
  ```cmd
  run.bat                :: Open interactive menu (choose 1-9, R, U, C, 0)
  run.bat test           :: Run all 95 unit & integration tests
  run.bat lint           :: Run ruff code quality checks
  run.bat realdata       :: Run real-world data demo ("What You Can Get")
  run.bat demo           :: Run quickstart offline demonstration
  run.bat scenarios      :: Run all 4 enterprise operational scenarios
  run.bat providers      :: List LLM providers and status
  run.bat ui             :: Launch Organizational Graph UI in browser
  run.bat run incident_response --mock  :: Run CLI pipeline offline
  ```
- **`test.bat`** — One-click shortcut to run the entire test suite:
  ```cmd
  test.bat
  ```

## License

MIT — see [LICENSE](LICENSE) for details.

