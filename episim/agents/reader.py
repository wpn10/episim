"""Reader Agent — extracts EpidemicModel from paper text via Claude + extended thinking.

Supports real-time thinking streaming via an optional callback.
"""

from __future__ import annotations

import os
from typing import Callable

import anthropic

from episim.core.model_spec import EpidemicModel

MODEL = os.environ.get("EPISIM_MODEL", "claude-sonnet-4-5-20250929")

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

Be thorough. Extract ALL parameters, even if there are many. If the paper reports multiple scenarios, use the baseline/default scenario. If a parameter value is not explicitly stated but can be computed from other values, compute it and note the derivation in the description.

You MUST call the submit_model tool with the extracted model."""


def extract_model(
    context: str,
    on_thinking: Callable[[str], None] | None = None,
) -> tuple[EpidemicModel, str]:
    """Extract an EpidemicModel from assembled context.

    Args:
        context: XML-tagged context string (paper + knowledge base).
        on_thinking: Optional callback invoked with each thinking text chunk
                     as it streams from the API. Used for real-time UI display.

    Returns:
        (model, thinking_text) where thinking_text captures the full reasoning.
    """
    client = anthropic.Anthropic()

    tool_schema = EpidemicModel.model_json_schema()

    for attempt in range(2):
        try:
            thinking_text = ""
            in_thinking_block = False

            with client.messages.stream(
                model=MODEL,
                max_tokens=16384,
                thinking={"type": "enabled", "budget_tokens": 32768},
                system=READER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": context}],
                tools=[{
                    "name": "submit_model",
                    "description": "Submit the extracted epidemic model specification. You MUST use this tool.",
                    "input_schema": tool_schema,
                }],
            ) as stream:
                for event in stream:
                    # Thinking block boundaries
                    if event.type == "content_block_start":
                        block = event.content_block
                        if getattr(block, "type", None) == "thinking":
                            in_thinking_block = True
                        else:
                            in_thinking_block = False
                    elif event.type == "content_block_stop":
                        in_thinking_block = False

                    # Thinking text deltas — stream to callback
                    elif (
                        event.type == "content_block_delta"
                        and in_thinking_block
                    ):
                        delta = event.delta
                        chunk = getattr(delta, "thinking", None)
                        if chunk:
                            thinking_text += chunk
                            if on_thinking:
                                on_thinking(chunk)

                response = stream.get_final_message()

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
