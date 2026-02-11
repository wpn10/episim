"""Builder Agent — converts EpidemicModel into a complete Streamlit simulator."""

from __future__ import annotations

import json
from pathlib import Path

import anthropic

from episim.core.model_spec import EpidemicModel, GeneratedFiles

BUILDER_SYSTEM_PROMPT = """You are an expert Python engineer specializing in scientific computing and interactive web applications. Your task is to generate a complete, self-contained epidemic simulator from a model specification.

You will receive an EpidemicModel JSON spec. Generate five files that together form a runnable Streamlit app.

## File Contracts

### model.py
- Define `COMPARTMENTS: list[str]` matching the spec's compartments list (exact order).
- Define `def derivatives(t, y, params) -> list[float]` implementing the ODE system.
- The function must unpack `y` in the same order as COMPARTMENTS.
- Access parameters via `params['name']` dict lookups.
- Use only basic math (no imports needed inside the function).

### solver.py
- `from scipy.integrate import solve_ivp`
- `import numpy as np`
- `from model import COMPARTMENTS, derivatives`
- Define `def run_simulation(params: dict, y0: list[float], t_span: tuple, num_points: int = 1000) -> dict`:
  - Uses `method="RK45"` with `max_step=1.0` for stability
  - Uses `rtol=1e-8, atol=1e-8`
  - Returns `{"t": ndarray, "S": ndarray, "I": ndarray, ...}` with keys = "t" + COMPARTMENTS

### app.py
- A Streamlit application.
- `import streamlit as st`
- `import plotly.graph_objects as go`
- `import json` to load config.json
- Import `run_simulation` from solver and `COMPARTMENTS` from model.
- Sidebar: `st.sidebar.slider()` for each parameter (default=paper value, min=slider_min, max=slider_max, step appropriate to scale).
- Sidebar: "Reset to Paper Defaults" button using `st.sidebar.button`.
- Main area: `st.title()` with model name, `st.markdown()` with paper title.
- Main area: Plotly line chart (`go.Figure` with `go.Scatter`) showing all compartments over time.
- Main area: Display key metrics (peak day, peak cases, R0 if computable).
- Use `st.plotly_chart(fig, use_container_width=True)`.

### config.json
- JSON with keys: "parameters" (name→value mapping), "initial_conditions", "population", "simulation_days", "compartments".
- Parameter values are the paper's default values (just the float, not the full Parameter object).

### requirements.txt
- List: streamlit, plotly, scipy, numpy

## Important Rules
- All files must be syntactically valid Python (or JSON for config.json).
- The app must work when run with `streamlit run app.py` from the output directory.
- Do NOT use any external data files — everything is self-contained.
- Use clear variable names and minimal comments."""


def generate_simulator(model: EpidemicModel, output_dir: Path) -> Path:
    """Generate a complete Streamlit simulator from an EpidemicModel spec.

    Returns the output directory path.
    """
    client = anthropic.Anthropic()

    model_json = model.model_dump_json(indent=2)
    tool_schema = GeneratedFiles.model_json_schema()

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=32768,
        system=BUILDER_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Generate a complete simulator for this epidemic model:\n\n{model_json}",
        }],
        tools=[{
            "name": "submit_files",
            "description": "Submit all generated simulator files",
            "input_schema": tool_schema,
        }],
        tool_choice={"type": "tool", "name": "submit_files"},
    )

    # Extract tool_use result
    files = None
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_files":
            files = GeneratedFiles.model_validate(block.input)
            break

    if files is None:
        raise ValueError("No submit_files tool_use block found in response")

    # Write files to output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_mapping = {
        "model.py": files.model_py,
        "solver.py": files.solver_py,
        "app.py": files.app_py,
        "config.json": files.config_json,
        "requirements.txt": files.requirements_txt,
    }

    for filename, content in file_mapping.items():
        (output_dir / filename).write_text(content)

    return output_dir
