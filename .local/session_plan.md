# Autopilot Session Plan

## Goal
Add real-world operational datasets as examples and demonstrate exactly what actionable intelligence, artifacts, and reports OpsBrain generates.

## Discovery Summary
- **Skills**: Autopilot active
- **CLI**: git, uv, python, pytest, ruff, gh available
- **Project**: OpsBrain Multi-Agent Operations & Optimization Framework (Python 3.11+, Typer, SQLite WAL, HTML5/SVG UI)
- **Git**: Branch `main`, tracking `origin/main`

## Loaded Skills
- autopilot

## Tasks

### T001: Real-World Dataset Engineering
- **Blocked By**: []
- **Skill**: Direct / addyosmani-agent-skills-source-driven-development
- **MCP**: None
- **CLI**: uv
- **Done When**: Authentic operational datasets created in `examples/data/` (E-Commerce Checkout Outage, FinTech Payment Breach, Supply Chain Logistics).
- **Criticality**: blocking
- **Status**: completed

### T002: "What You Get" Demonstration Engine
- **Blocked By**: [T001]
- **Skill**: Direct
- **MCP**: None
- **CLI**: uv run python
- **Done When**: Executable `examples/real_data_pipeline_demo.py` processes real data and outputs complete 7-part intelligence package.
- **Criticality**: blocking
- **Status**: completed

### T003: Automated Test Verification
- **Blocked By**: [T001, T002]
- **Skill**: Direct / addyosmani-agent-skills-test-driven-development
- **MCP**: None
- **CLI**: uv run pytest
- **Done When**: Tests in `tests/integration/test_real_data_demo.py` pass cleanly alongside the existing tests (95/95 passing).
- **Criticality**: blocking
- **Status**: completed

### T004: Launcher & Documentation Integration
- **Blocked By**: [T002, T003]
- **Skill**: Direct
- **MCP**: None
- **CLI**: git, gh
- **Done When**: `run.bat realdata` added, `README.md` updated, code committed and pushed to GitHub.
- **Criticality**: non-blocking
- **Status**: completed
