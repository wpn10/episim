"""Tests for validator — run generated code and compare metrics."""

import json
from pathlib import Path

import pytest

from episim.core.model_spec import EpidemicModel
from episim.agents.validator import validate, write_report, _generate_validate_script


def _create_sir_simulator(output_dir: Path) -> None:
    """Write a known-good SIR simulator into output_dir."""
    (output_dir / "model.py").write_text(
        'COMPARTMENTS = ["S", "I", "R"]\n\n'
        "def derivatives(t, y, params):\n"
        "    S, I, R = y\n"
        "    N = sum(y)\n"
        "    beta = params['beta']\n"
        "    gamma = params['gamma']\n"
        "    return [-beta*S*I/N, beta*S*I/N - gamma*I, gamma*I]\n"
    )
    (output_dir / "solver.py").write_text(
        "from scipy.integrate import solve_ivp\n"
        "import numpy as np\n"
        "from model import COMPARTMENTS, derivatives\n\n"
        "def run_simulation(params, y0, t_span, num_points=1000):\n"
        "    t_eval = np.linspace(t_span[0], t_span[1], num_points)\n"
        "    sol = solve_ivp(lambda t, y: derivatives(t, y, params),\n"
        "                    t_span, y0, method='RK45', t_eval=t_eval,\n"
        "                    max_step=1.0, rtol=1e-8, atol=1e-8)\n"
        "    results = {'t': sol.t}\n"
        "    for i, name in enumerate(COMPARTMENTS):\n"
        "        results[name] = sol.y[i]\n"
        "    return results\n"
    )


def _sir_model() -> EpidemicModel:
    return EpidemicModel(
        name="SIR",
        paper_title="Test SIR Paper",
        compartments=["S", "I", "R"],
        parameters={
            "beta": {"value": 0.3, "description": "Transmission rate", "unit": "1/day", "slider_min": 0.03, "slider_max": 3.0},
            "gamma": {"value": 0.1, "description": "Recovery rate", "unit": "1/day", "slider_min": 0.01, "slider_max": 1.0},
        },
        initial_conditions={"S": 999, "I": 1, "R": 0},
        ode_system="def derivatives(t, y, params):\n    S, I, R = y\n    N = sum(y)\n    return [-params['beta']*S*I/N, params['beta']*S*I/N - params['gamma']*I, params['gamma']*I]",
        simulation_days=160,
        population=1000.0,
        expected_results=[
            {"metric": "R0", "value": 3.0, "source": "Computed", "tolerance": 0.05},
        ],
    )


class TestValidate:
    def test_known_good_sir_passes(self, tmp_path):
        _create_sir_simulator(tmp_path)
        model = _sir_model()
        report = validate(tmp_path, model)

        assert report.all_passed
        assert len(report.metrics) == 1
        assert report.metrics[0].metric == "R0"
        assert report.metrics[0].passed

    def test_wrong_expected_value_fails(self, tmp_path):
        _create_sir_simulator(tmp_path)
        model = _sir_model()
        # Set wrong expected R0
        model.expected_results[0].value = 10.0

        report = validate(tmp_path, model)
        assert not report.all_passed
        assert not report.metrics[0].passed

    def test_broken_code_returns_error(self, tmp_path):
        (tmp_path / "model.py").write_text("raise Exception('broken')")
        (tmp_path / "solver.py").write_text("def run_simulation(*a, **kw): pass")
        model = _sir_model()
        report = validate(tmp_path, model)

        assert not report.all_passed
        assert report.error is not None


class TestGenerateScript:
    def test_script_is_valid_python(self):
        model = _sir_model()
        script = _generate_validate_script(model)
        compile(script, "_validate.py", "exec")

    def test_script_contains_metric(self):
        model = _sir_model()
        script = _generate_validate_script(model)
        assert "R0" in script


class TestWriteReport:
    def test_writes_markdown_file(self, tmp_path):
        from episim.core.model_spec import MetricResult, ValidationReport
        report = ValidationReport(
            paper_title="Test",
            model_name="SIR",
            metrics=[MetricResult(metric="R0", expected=3.0, actual=3.0, match_pct=0.0, passed=True)],
            all_passed=True,
            attempts=1,
        )
        write_report(report, tmp_path)
        md = (tmp_path / "reproduction_report.md").read_text()
        assert "ALL PASSED" in md
        assert "R0" in md
