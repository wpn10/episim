"""Reader Agent — extracts EpidemicModel from paper text via Opus 4.6 + extended thinking."""

from __future__ import annotations

import json
import os

import anthropic

from episim.core.model_spec import EpidemicModel

READER_SYSTEM_PROMPT = """You are an expert epidemiologist and mathematical modeler. Your task is to extract a complete mathematical epidemic model specification from the research paper provided.

You must identify and extract:

1. **Model name** — e.g. "SIR", "SEIR with Vaccination", "SIDARTHE"
2. **Paper title** — the full title of the paper
3. **Compartments** — ordered list of compartment names (e.g. ["S", "I", "R"])
4. **Parameters** — every model parameter with:
   - Its numerical value as reported in the paper
   - A brief description
   - Unit (if stated)
   - slider_min: 0.1 × value (for interactive exploration)
   - slider_max: 10.0 × value (for interactive exploration)
5. **Initial conditions** — the starting value for each compartment
6. **ODE system** — a complete, self-contained Python function:
   ```python
   def derivatives(t, y, params):
       # Unpack y in the SAME ORDER as compartments list
       S, I, R = y
       N = sum(y)
       beta = params['beta']
       gamma = params['gamma']
       # ... compute derivatives ...
       return [dSdt, dIdt, dRdt]
   ```
   Rules for ode_system:
   - The function signature MUST be: def derivatives(t, y, params)
   - Unpack y variables in the exact order matching the compartments list
   - Access parameters via params['name'] dict lookups
   - Use only basic math operations (no imports needed inside the function)
   - Return a list of derivatives in the same order as compartments
7. **Simulation days** — total simulation duration
8. **Population** — total population N
9. **Expected results** — key metrics reported in the paper that we can validate against:
   - peak_day, peak_cases, R0, attack_rate, or custom metrics
   - Include the value, source reference (e.g. "Figure 3", "Table 2"), and tolerance (default 0.05)

Be thorough. Extract ALL parameters, even if there are many. If the paper reports multiple scenarios, use the baseline/default scenario. If a parameter value is not explicitly stated but can be computed from other values, compute it and note the derivation in the description."""


def extract_model(context: str) -> tuple[EpidemicModel, str]:
    """Extract an EpidemicModel from assembled context using Opus 4.6.

    Returns (model, thinking_text) where thinking_text captures the AI's reasoning.
    """
    client = anthropic.Anthropic()

    tool_schema = EpidemicModel.model_json_schema()

    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=16384,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 32768,
                },
                system=READER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": context}],
                tools=[{
                    "name": "submit_model",
                    "description": "Submit the extracted epidemic model specification",
                    "input_schema": tool_schema,
                }],
                tool_choice={"type": "tool", "name": "submit_model"},
            )

            # Extract thinking text
            thinking_text = ""
            for block in response.content:
                if block.type == "thinking":
                    thinking_text += block.thinking + "\n"

            # Extract tool_use input
            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_model":
                    model = EpidemicModel.model_validate(block.input)
                    return model, thinking_text.strip()

            raise ValueError("No submit_model tool_use block found in response")

        except Exception:
            if attempt == 0:
                continue
            raise

    raise RuntimeError("Failed to extract model after 2 attempts")
