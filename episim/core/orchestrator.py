"""Orchestrator — wires the full pipeline and provides CLI entry point."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from episim.core.paper_loader import load_paper
from episim.core.context_builder import build_context
from episim.agents.reader import extract_model
from episim.agents.builder import generate_simulator
from episim.agents.validator import validate, write_report
from episim.agents.debugger import debug_and_fix, apply_fixes

MAX_RETRIES = 3


def _slugify(source: str) -> str:
    """Convert a paper source (path/URL/ID) into a safe directory name."""
    if source.endswith(".pdf"):
        name = Path(source).stem
    elif "/" in source:
        # URL — grab last path segment
        name = source.rstrip("/").rsplit("/", 1)[-1]
    else:
        name = source
    name = re.sub(r"[^\w\-.]", "_", name)
    return name[:80]


def _log(msg: str) -> None:
    print(f"[episim] {msg}", flush=True)


def save_thinking(thinking_text: str, output_dir: Path) -> None:
    """Save the Reader agent's thinking chain for demo display."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    (Path(output_dir) / "thinking.md").write_text(
        f"# Reader Agent Thinking\n\n{thinking_text}\n"
    )


def run_pipeline(paper_source: str, output_base: str = "output") -> Path:
    """Run the full EpiSim pipeline: paper → validated interactive simulator.

    Returns the output directory path.
    """
    # 1. Load paper
    _log(f"Loading paper: {paper_source}")
    paper_text = load_paper(paper_source)
    paper_name = _slugify(paper_source)
    _log(f"Extracted {len(paper_text)} characters of text")

    # 2. Build context
    _log("Building context with knowledge base...")
    context = build_context(paper_text)
    _log(f"Context assembled: {len(context)} characters")

    # 3. Extract model (Reader Agent)
    _log("Reader agent extracting epidemic model (this may take a minute)...")
    model, thinking_text = extract_model(context)
    _log(f"Extracted model: {model.name} with {len(model.compartments)} compartments")

    # 4. Generate simulator (Builder Agent)
    output_dir = Path(output_base) / paper_name
    _log(f"Builder agent generating simulator in {output_dir}/...")
    generate_simulator(model, output_dir)
    _log("Simulator files generated")

    # 5. Validate + Debug loop
    report = None
    for attempt in range(1, MAX_RETRIES + 1):
        _log(f"Validation attempt {attempt}/{MAX_RETRIES}...")
        report = validate(output_dir, model)
        report.attempts = attempt

        if report.all_passed:
            _log("All metrics passed!")
            break

        failed = [m.metric for m in report.metrics if not m.passed]
        _log(f"Failed metrics: {', '.join(failed) if failed else 'error'}")

        if report.error:
            _log(f"Error: {report.error}")

        if attempt < MAX_RETRIES:
            _log("Debugger agent analyzing and patching...")
            fixes = debug_and_fix(report, output_dir, model)
            apply_fixes(fixes, output_dir)
            _log(f"Applied fixes to: {', '.join(fixes.keys())}")

    # 6. Write reproduction report
    write_report(report, output_dir)
    _log("Reproduction report written")

    # 7. Save thinking chain for demo display
    save_thinking(thinking_text, output_dir)
    _log("Thinking chain saved")

    _log(f"Done! Output: {output_dir}")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EpiSim — Transform epidemic modeling papers into interactive simulators",
    )
    parser.add_argument(
        "--paper",
        required=True,
        help="Path to PDF, arxiv URL, or arxiv ID (e.g. 2401.12345)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Base output directory (default: output/)",
    )
    args = parser.parse_args()

    try:
        output_dir = run_pipeline(args.paper, args.output_dir)
        print(f"\nSimulator ready! Run:\n  cd {output_dir} && streamlit run app.py")
    except Exception as e:
        print(f"\n[episim] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
