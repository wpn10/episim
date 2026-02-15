"""Coder Agent — generates a standalone reproduction script."""

from __future__ import annotations

import os

import anthropic

from episim.core.model_spec import EpidemicModel, StandaloneScript

MODEL = os.environ.get("EPISIM_MODEL", "claude-sonnet-4-5-20250929")

CODER_SYSTEM_PROMPT = """You are an expert scientific Python programmer. Your task is to generate a clean, standalone Python script that reproduces an epidemic model from a research paper.

You will receive an EpidemicModel specification and context about the paper.

## Requirements for the generated script

1. **Single file** — runs with `python script.py` (no arguments needed)
2. **Dependencies** — only numpy, scipy, matplotlib (standard scientific Python)
3. **Docstring** — at the top, explain the paper title, model type, and what the script does
4. **Inline comments** — explain each ODE term and parameter
5. **Console output** — print key metrics to stdout:
   - R0 (if computable from the model parameters)
   - Peak day and peak number of infected
   - Attack rate (fraction of population infected)
6. **Plot** — generate a matplotlib figure showing all compartment curves over time, saved as PNG
7. **Parameters at top** — clearly defined in a dict for easy modification
8. **Educational** — this is a clean, well-documented reproduction, NOT a copy of the Streamlit app

## Script structure

```python
\"\"\"
[Paper title]
Model: [model type] ([N] compartments)

Standalone reproduction script. Run: python [filename]
Generates: [filename_without_py].png
\"\"\"

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# ── Parameters ──────────────────────────────────────────
params = {
    'beta': 0.3,   # Transmission rate (per day)
    'gamma': 0.1,  # Recovery rate (1/infectious period)
    ...
}

POPULATION = ...
SIMULATION_DAYS = ...

# ── Initial Conditions ──────────────────────────────────
y0 = [...]  # [S0, I0, R0, ...]

# ── ODE System ──────────────────────────────────────────
def derivatives(t, y, params):
    S, I, R = y
    N = sum(y)
    ...
    return [dSdt, dIdt, dRdt]

# ── Simulation ──────────────────────────────────────────
t_eval = np.linspace(0, SIMULATION_DAYS, 1000)
sol = solve_ivp(...)
...

# ── Metrics ─────────────────────────────────────────────
print(f"R0: ...")
print(f"Peak day: ...")
...

# ── Plot ────────────────────────────────────────────────
plt.figure(figsize=(10, 6))
...
plt.savefig('...png', dpi=150, bbox_inches='tight')
print(f"Plot saved: ...png")
plt.show()
```

Generate a filename like `{model_name_lowercase}_simulation.py` (use underscores, no spaces).

You MUST call the submit_script tool with the complete script."""


def generate_standalone(model: EpidemicModel, paper_text: str) -> StandaloneScript:
    """Generate a standalone reproduction script.

    Args:
        model: The extracted EpidemicModel.
        paper_text: Raw paper text for context (first 8000 chars used).

    Returns:
        StandaloneScript with filename, code, and description.
    """
    client = anthropic.Anthropic()

    tool_schema = StandaloneScript.model_json_schema()

    # Truncate paper text — the model spec has all the details;
    # paper text is just for docstring context
    paper_context = paper_text[:8000]

    user_message = (
        f"Generate a standalone reproduction script for this epidemic model:\n\n"
        f"<model>\n{model.model_dump_json(indent=2)}\n</model>\n\n"
        f"<paper_context>\n{paper_context}\n</paper_context>"
    )

    with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        system=CODER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        tools=[{
            "name": "submit_script",
            "description": "Submit the standalone reproduction script. You MUST use this tool.",
            "input_schema": tool_schema,
        }],
    ) as stream:
        response = stream.get_final_message()

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_script":
            return StandaloneScript.model_validate(block.input)

    raise ValueError("No submit_script tool_use block found in response")
