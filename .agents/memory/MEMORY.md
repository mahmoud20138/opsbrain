# Autopilot Memory

## Operational Knowledge
- **Project**: OpsBrain Multi-Agent Enterprise Operations & Optimization Framework.
- **Git Repo**: `https://github.com/mahmoud20138/opsbrain` (Branch: `main`).
- **Test Suite**: 95 tests across unit, integration, UI server, and real-world pipelines (`uv run pytest`).
- **Real-World Datasets**:
  - `examples/data/real_ecommerce_checkout_outage.json` (HikariPool connection pool exhaustion, NGINX 504 timeouts, Redis eviction storms).
  - `examples/data/real_fintech_payment_clearing_delay.json` (Kafka lag 142k, AML hold queues, Fedwire SLA breach risk).
  - `examples/data/real_supply_chain_port_disruption.json` & `real_supply_chain_metrics.csv` (Port of Long Beach dwell times, auto semiconductor SKU-774 line-stoppage risk).
- **Execution & Deliverables**:
  - `examples/real_data_pipeline_demo.py` & `run.bat realdata` executes full 5-stage agent pipeline (`Monitor` -> `RCA` -> `Solver` -> `Coordinator` -> `Evaluator`) and outputs:
    1. Automated Anomaly Detection & Severity Triage
    2. Formal RCA with Causal Evidence Chains
    3. Ranked Actionable Remediation Plans & Rollback Guardrails
    4. Cross-Team Action Items & Stakeholder Broadcasts
    5. Multi-Axis Pipeline Quality Scorecard (Score >= 9.3/10.0)
    6. Persisted State Machine Audit Trail & Telemetry
    7. Executive Incident Post-Mortem Markdown Report (`reports/`)
- **Windows Gotchas**:
  - Background processes holding `.venv/Scripts/opsbrain.exe` lock will cause `uv run` package rebuild errors; stop processes before rebuild.
  - In `run.bat`, loop `%1` shift into `!EXTRA_ARGS!` for clean argument passthrough.
