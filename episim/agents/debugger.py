"""Debugger Agent — analyzes validation failures and patches generated code."""

from __future__ import annotations

from pathlib import Path

import anthropic

from episim.core.model_spec import EpidemicModel, ValidationReport

DEBUGGER_SYSTEM_PROMPT = """You are an expert Python debugger specializing in scientific computing and epidemic modeling. A generated epidemic simulator has failed validation — some metrics don't match the paper's expected values, or the code crashed.

You will receive:
1. The EpidemicModel specification (what the code SHOULD implement)
2. The generated source files (what was actually produced)
3. The ValidationReport (which metrics failed and by how much, or the error message)

Your task is to analyze the discrepancy and return FIXED versions of only the files that need changes.

Common issues to look for:
- ODE system doesn't match the model spec (wrong signs, missing terms, wrong compartment order)
- Parameter names in code don't match config.json keys
- solver.py doesn't pass parameters correctly to derivatives()
- Initial conditions in wrong order relative to COMPARTMENTS
- Numerical issues (need smaller max_step, different solver method for stiff systems)
- Import errors or typos in generated code

Return only the files that need fixing. Do not modify files that are correct."""


def debug_and_fix(
    report: ValidationReport,
    output_dir: Path,
    model: EpidemicModel,
) -> dict[str, str]:
    """Analyze validation failure and return patched files.

    Returns dict mapping filename -> updated content for files that need fixes.
    """
    client = anthropic.Anthropic()
    output_dir = Path(output_dir)

    # Read current generated files
    file_contents = {}
    for fname in ["model.py", "solver.py", "app.py", "config.json"]:
        fpath = output_dir / fname
        if fpath.exists():
            file_contents[fname] = fpath.read_text()

    # Build the user message with all context
    parts = [
        "## EpidemicModel Specification",
        model.model_dump_json(indent=2),
        "",
        "## Generated Files",
    ]
    for fname, content in file_contents.items():
        parts.append(f"### {fname}\n```\n{content}\n```")

    parts.append("\n## Validation Report")
    parts.append(report.model_dump_json(indent=2))

    user_message = "\n\n".join(parts)

    # Define tool schema for returning fixes
    fix_schema = {
        "type": "object",
        "properties": {
            "fixes": {
                "type": "object",
                "description": "Mapping of filename to updated file content. Only include files that need changes.",
                "additionalProperties": {"type": "string"},
            },
            "explanation": {
                "type": "string",
                "description": "Brief explanation of what was wrong and what was fixed.",
            },
        },
        "required": ["fixes", "explanation"],
    }

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=16384,
        thinking={
            "type": "enabled",
            "budget_tokens": 16384,
        },
        system=DEBUGGER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        tools=[{
            "name": "submit_fixes",
            "description": "Submit the fixed file contents",
            "input_schema": fix_schema,
        }],
        tool_choice={"type": "tool", "name": "submit_fixes"},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_fixes":
            return block.input.get("fixes", {})

    raise ValueError("No submit_fixes tool_use block found in response")


def apply_fixes(fixes: dict[str, str], output_dir: Path) -> None:
    """Write patched files to disk."""
    output_dir = Path(output_dir)
    for filename, content in fixes.items():
        (output_dir / filename).write_text(content)
