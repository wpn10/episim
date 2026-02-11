# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

EpiSim — three-agent pipeline that transforms epidemic modeling research papers (PDF/arxiv) into validated, interactive Streamlit simulators. Built on Opus 4.6 (1M context, extended thinking, 128K output) for the "Built with Opus 4.6" hackathon (Feb 10–16, 2026), PS2 — Break the Barriers.

## Commands

```bash
pip install -e .                                          # install package
python -m episim.core.orchestrator --paper <path_or_url>  # run full pipeline
cd output/{paper_name} && streamlit run app.py             # launch generated simulator
pytest tests/                                              # all tests
pytest tests/test_sir_basic.py -v                          # single test
```

## Architecture

Pipeline: `Paper Loader → Context Builder → Reader Agent → Builder Agent → Validator → (Debugger loop) → Output`

- **`episim/core/model_spec.py`** — Central schema. `EpidemicModel` (Pydantic v2) is the contract between all agents. Also defines `ValidationReport`, `MetricResult`, `GeneratedFiles`. All agent I/O uses these schemas via Anthropic `tool_use`.
- **`episim/core/paper_loader.py`** — PDF/arxiv → raw text via PyMuPDF.
- **`episim/core/context_builder.py`** — Assembles paper text + `episim/knowledge/*.md` into XML-tagged context string.
- **`episim/agents/reader.py`** — Opus 4.6 + extended thinking (32K budget). Extracts `EpidemicModel` from paper. Returns `(model, thinking_text)`.
- **`episim/agents/builder.py`** — Opus 4.6 + 128K output. Generates `model.py`, `solver.py`, `app.py`, `config.json`, `requirements.txt` in one API call.
- **`episim/agents/validator.py`** — Mostly Python (not LLM). Generates `_validate.py`, runs via subprocess, compares metrics within 5% tolerance.
- **`episim/agents/debugger.py`** — Opus 4.6 + extended thinking. Triggered only on validation failure. Returns patched files. Max 3 retries.
- **`episim/core/orchestrator.py`** — Wires pipeline + CLI (`argparse`).

## Generated Code Contracts

All generated simulators in `output/{paper}/` must follow these interfaces so the Validator works generically:

- **model.py**: `COMPARTMENTS: list[str]` + `def derivatives(t, y, params) -> list[float]` — `y` order matches `COMPARTMENTS`
- **solver.py**: `def run_simulation(params, y0, t_span, num_points=1000) -> dict[str, ndarray]` — keys = `"t"` + compartment names
- **config.json**: `{"parameters": {...}, "initial_conditions": {...}, "population": N, "simulation_days": D, "compartments": [...]}`

## Key Patterns

- All agents use raw `anthropic` SDK, not Agent SDK. One prompt → one response per agent.
- Structured output via `tool_use` with Pydantic-generated JSON schemas (`model.model_json_schema()`).
- Generated code runs in subprocess (never `exec()`).
- Knowledge base (`episim/knowledge/`) is static reference material (base_models.md, parameters.md, solver_guide.md).
- `output/` is gitignored. Each generated simulator is self-contained.

## Design Docs

- `docs/hld.md` — Full high-level design with component specs, API config, interface contracts, build order
- `docs/tasks.md` — 12-chapter implementation breakdown with dependencies
