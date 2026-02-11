"""Context Builder — assembles paper text + knowledge files into XML-tagged context."""

from __future__ import annotations

from pathlib import Path

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"

_SECTIONS = [
    ("reference_models", "base_models.md"),
    ("parameter_ranges", "parameters.md"),
    ("solver_guide", "solver_guide.md"),
]


def build_context(paper_text: str, knowledge_dir: Path | None = None) -> str:
    """Assemble paper text and knowledge base files into an XML-tagged context string."""
    kdir = knowledge_dir or _KNOWLEDGE_DIR

    parts = [f"<paper>\n{paper_text}\n</paper>"]

    for tag, filename in _SECTIONS:
        content = (kdir / filename).read_text()
        parts.append(f"<{tag}>\n{content}\n</{tag}>")

    return "\n\n".join(parts)
