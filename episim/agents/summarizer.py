"""Summarizer Agent — generates a plain-English paper summary."""

from __future__ import annotations

import os

import anthropic

from episim.core.model_spec import EpidemicModel, PaperSummary

MODEL = os.environ.get("EPISIM_MODEL", "claude-sonnet-4-5-20250929")

SUMMARIZER_SYSTEM_PROMPT = """You are a science communicator specializing in epidemiology and public health. Your task is to produce a clear, accessible summary of an epidemic modeling research paper.

You will receive:
1. The full text of the paper
2. The extracted mathematical model specification (for grounding — so you know what was extracted)

Produce a summary that a non-specialist (e.g., a public health official, journalist, or student) can understand.

Guidelines:
- Be specific: reference actual numbers, results, and findings from the paper
- Avoid jargon where possible; when technical terms are necessary, briefly explain them
- Key findings should be 3-5 concrete bullet points with numbers
- Methodology should explain how the model works in plain language
- Public health implications should focus on real-world actionable relevance

You MUST call the submit_summary tool with the complete summary."""


def summarize_paper(paper_text: str, model: EpidemicModel) -> PaperSummary:
    """Generate a plain-English summary of the paper.

    Args:
        paper_text: Raw text of the paper.
        model: The extracted EpidemicModel (for grounding).

    Returns:
        PaperSummary with structured summary fields.
    """
    client = anthropic.Anthropic()

    tool_schema = PaperSummary.model_json_schema()

    user_message = (
        f"<paper>\n{paper_text}\n</paper>\n\n"
        f"<extracted_model>\n{model.model_dump_json(indent=2)}\n</extracted_model>"
    )

    with client.messages.stream(
        model=MODEL,
        max_tokens=4096,
        system=SUMMARIZER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        tools=[{
            "name": "submit_summary",
            "description": "Submit the paper summary. You MUST use this tool.",
            "input_schema": tool_schema,
        }],
    ) as stream:
        response = stream.get_final_message()

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_summary":
            return PaperSummary.model_validate(block.input)

    raise ValueError("No submit_summary tool_use block found in response")
