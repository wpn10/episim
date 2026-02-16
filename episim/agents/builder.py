"""Builder Agent — converts EpidemicModel into a complete Streamlit simulator."""

from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic

from episim.core.model_spec import EpidemicModel, GeneratedFiles

MODEL = os.environ.get("EPISIM_MODEL", "claude-sonnet-4-5-20250929")

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
CRITICAL: Use this EXACT template, only changing nothing. Do not deviate:

```python
from scipy.integrate import solve_ivp
import numpy as np
from model import COMPARTMENTS, derivatives

def run_simulation(params, y0, t_span, num_points=1000):
    t_eval = np.linspace(t_span[0], t_span[1], num_points)
    sol = solve_ivp(
        fun=lambda t, y: derivatives(t, y, params),
        t_span=t_span,
        y0=y0,
        method='RK45',
        t_eval=t_eval,
        max_step=1.0,
        rtol=1e-8,
        atol=1e-8,
    )
    if not sol.success:
        raise RuntimeError(f"ODE solver failed: {sol.message}")
    results = {"t": sol.t}
    for i, name in enumerate(COMPARTMENTS):
        results[name] = sol.y[i]
    return results
```

- The `fun` argument MUST be `lambda t, y: derivatives(t, y, params)` — wrapping params via closure.
- `y0` is passed directly as a list. Do NOT convert or reshape it.
- `t_span` is a tuple `(0, days)`. Do NOT unpack it differently.
- Returns `{"t": ndarray, "compartment_name": ndarray, ...}` with keys = "t" + COMPARTMENTS

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
- Use clear variable names and minimal comments.

You MUST call the submit_files tool with all generated files."""


def generate_simulator(model: EpidemicModel, output_dir: Path) -> Path:
    """Generate a complete Streamlit simulator from an EpidemicModel spec.

    Returns the output directory path.
    """
    client = anthropic.Anthropic()

    model_json = model.model_dump_json(indent=2)
    tool_schema = GeneratedFiles.model_json_schema()

    api_kwargs = dict(
        model=MODEL,
        max_tokens=16384,
        system=BUILDER_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Generate a complete simulator for this epidemic model:\n\n{model_json}",
        }],
        tools=[{
            "name": "submit_files",
            "description": "Submit all generated simulator files. You MUST use this tool.",
            "input_schema": tool_schema,
        }],
    )
    if "opus-4-6" in MODEL:
        api_kwargs["thinking"] = {"type": "adaptive"}
        api_kwargs["output_config"] = {"effort": "high"}
        api_kwargs["max_tokens"] = 32000

    with client.messages.stream(**api_kwargs) as stream:
        response = stream.get_final_message()

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
        # Fix escaped newlines — LLM sometimes returns literal \n instead of real newlines
        if '\\n' in content[:200]:
            content = content.replace('\\n', '\n').replace('\\t', '\t')
        (output_dir / filename).write_text(content)

    return output_dir
