"""Validator — runs generated simulator, compares metrics against paper's claims."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

from episim.core.model_spec import EpidemicModel, MetricResult, ValidationReport

# Metric computation snippets keyed by metric name.
# Each returns a float from `results` dict and `params` dict.
_METRIC_COMPUTATIONS = {
    "peak_day": 'results["t"][np.argmax(results[infected_compartment])]',
    "peak_cases": "float(np.max(results[infected_compartment]))",
    "R0": 'params["beta"] / params["gamma"]',
    "attack_rate": '1.0 - results["S"][-1] / population',
    "final_recovered": 'float(results["R"][-1])',
    "epidemic_duration": 'float(np.sum(results[infected_compartment] > population * 0.001))',
}


def _generate_validate_script(model: EpidemicModel) -> str:
    """Generate a _validate.py script that runs the simulator and prints metrics as JSON."""

    # Determine the infected compartment (usually "I")
    infected = "I"
    for c in model.compartments:
        if c.startswith("I"):
            infected = c
            break

    metric_lines = []
    for er in model.expected_results:
        comp = _METRIC_COMPUTATIONS.get(er.metric)
        if comp:
            expr = comp.replace("infected_compartment", f'"{infected}"')
            metric_lines.append(
                f'    metrics.append({{"metric": "{er.metric}", "actual": {expr}}})'
            )
        else:
            # Unknown metric — skip with a placeholder
            metric_lines.append(
                f'    metrics.append({{"metric": "{er.metric}", "actual": None}})'
            )

    metrics_block = "\n".join(metric_lines)

    # Build parameter values dict from model
    param_values = {k: v.value for k, v in model.parameters.items()}
    y0 = [model.initial_conditions[c] for c in model.compartments]

    script = textwrap.dedent(f"""\
        import sys
        import json
        import numpy as np
        from model import COMPARTMENTS, derivatives
        from solver import run_simulation

        params = {json.dumps(param_values)}
        y0 = {json.dumps(y0)}
        t_span = (0, {model.simulation_days})
        population = {model.population}

        try:
            results = run_simulation(params, y0, t_span)
            infected_compartment = "{infected}"
            metrics = []
        {metrics_block}
            print(json.dumps(metrics))
        except Exception as e:
            print(json.dumps({{"error": str(e)}}), file=sys.stderr)
            sys.exit(1)
    """)
    return script


def validate(output_dir: Path, model: EpidemicModel) -> ValidationReport:
    """Run the generated simulator and compare metrics against expected results.

    Returns a ValidationReport with pass/fail for each metric.
    """
    output_dir = Path(output_dir)

    # Write validation script
    script = _generate_validate_script(model)
    script_path = output_dir / "_validate.py"
    script_path.write_text(script)

    # Run via subprocess
    try:
        result = subprocess.run(
            [sys.executable, "_validate.py"],
            cwd=str(output_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return ValidationReport(
            paper_title=model.paper_title,
            model_name=model.name,
            metrics=[],
            all_passed=False,
            attempts=0,
            error="Validation script timed out after 30 seconds",
        )

    if result.returncode != 0:
        return ValidationReport(
            paper_title=model.paper_title,
            model_name=model.name,
            metrics=[],
            all_passed=False,
            attempts=0,
            error=f"Validation script failed: {result.stderr.strip()}",
        )

    # Parse output
    try:
        actual_metrics = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return ValidationReport(
            paper_title=model.paper_title,
            model_name=model.name,
            metrics=[],
            all_passed=False,
            attempts=0,
            error=f"Could not parse validation output: {result.stdout[:500]}",
        )

    # Build expected lookup
    expected_lookup = {er.metric: er for er in model.expected_results}

    # Compare metrics
    metric_results = []
    for actual in actual_metrics:
        metric_name = actual["metric"]
        actual_val = actual["actual"]
        er = expected_lookup.get(metric_name)

        if er is None or actual_val is None:
            continue

        if er.value == 0:
            match_pct = 0.0 if actual_val == 0 else 100.0
        else:
            match_pct = abs(1 - actual_val / er.value) * 100

        metric_results.append(MetricResult(
            metric=metric_name,
            expected=er.value,
            actual=actual_val,
            match_pct=round(match_pct, 2),
            passed=match_pct <= er.tolerance * 100,
        ))

    all_passed = len(metric_results) > 0 and all(m.passed for m in metric_results)

    return ValidationReport(
        paper_title=model.paper_title,
        model_name=model.name,
        metrics=metric_results,
        all_passed=all_passed,
        attempts=0,
    )


def write_report(report: ValidationReport, output_dir: Path) -> None:
    """Write a reproduction_report.md to the output directory."""
    lines = [
        f"# Reproduction Report: {report.model_name}",
        f"**Paper:** {report.paper_title}",
        f"**Status:** {'ALL PASSED' if report.all_passed else 'FAILED'}",
        f"**Attempts:** {report.attempts}",
        "",
        "## Metrics Comparison",
        "",
        "| Metric | Expected | Actual | Deviation | Status |",
        "|--------|----------|--------|-----------|--------|",
    ]

    for m in report.metrics:
        status = "PASS" if m.passed else "FAIL"
        lines.append(f"| {m.metric} | {m.expected:.4g} | {m.actual:.4g} | {m.match_pct:.2f}% | {status} |")

    if report.error:
        lines.extend(["", f"## Error", "", f"```\n{report.error}\n```"])

    (Path(output_dir) / "reproduction_report.md").write_text("\n".join(lines) + "\n")
