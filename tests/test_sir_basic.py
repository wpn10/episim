"""End-to-end test on a classic SIR model with known analytical properties.

No LLM calls — tests the validator + solver chain with a hand-written simulator.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from episim.core.model_spec import EpidemicModel
from episim.agents.validator import validate


def _sir_model() -> EpidemicModel:
    """Classic SIR: beta=0.3, gamma=0.1, R0=3, N=10000."""
    return EpidemicModel(
        name="SIR",
        paper_title="Kermack-McKendrick SIR",
        compartments=["S", "I", "R"],
        parameters={
            "beta": {"value": 0.3, "description": "Transmission rate", "unit": "1/day", "slider_min": 0.03, "slider_max": 3.0},
            "gamma": {"value": 0.1, "description": "Recovery rate", "unit": "1/day", "slider_min": 0.01, "slider_max": 1.0},
        },
        initial_conditions={"S": 9999, "I": 1, "R": 0},
        ode_system=(
            "def derivatives(t, y, params):\n"
            "    S, I, R = y\n"
            "    N = sum(y)\n"
            "    beta = params['beta']\n"
            "    gamma = params['gamma']\n"
            "    return [-beta*S*I/N, beta*S*I/N - gamma*I, gamma*I]"
        ),
        simulation_days=300,
        population=10000.0,
        expected_results=[
            {"metric": "R0", "value": 3.0, "source": "beta/gamma", "tolerance": 0.05},
            {"metric": "attack_rate", "value": 0.94, "source": "Final size equation", "tolerance": 0.05},
        ],
    )


def _write_sir_simulator(output_dir: Path) -> None:
    """Write a correct SIR simulator."""
    (output_dir / "model.py").write_text(
        'COMPARTMENTS = ["S", "I", "R"]\n\n'
        "def derivatives(t, y, params):\n"
        "    S, I, R = y\n"
        "    N = sum(y)\n"
        "    beta = params['beta']\n"
        "    gamma = params['gamma']\n"
        "    dSdt = -beta * S * I / N\n"
        "    dIdt = beta * S * I / N - gamma * I\n"
        "    dRdt = gamma * I\n"
        "    return [dSdt, dIdt, dRdt]\n"
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


class TestSIRBasic:
    def test_r0_validation_passes(self, tmp_path):
        _write_sir_simulator(tmp_path)
        model = _sir_model()
        report = validate(tmp_path, model)
        r0_result = next(m for m in report.metrics if m.metric == "R0")
        assert r0_result.passed
        assert abs(r0_result.actual - 3.0) < 0.01

    def test_attack_rate_validation(self, tmp_path):
        _write_sir_simulator(tmp_path)
        model = _sir_model()
        report = validate(tmp_path, model)
        ar_result = next(m for m in report.metrics if m.metric == "attack_rate")
        # SIR with R0=3 has attack rate ~0.94 (from final size equation)
        assert ar_result.passed
        assert 0.90 < ar_result.actual < 0.98

    def test_all_metrics_pass(self, tmp_path):
        _write_sir_simulator(tmp_path)
        model = _sir_model()
        report = validate(tmp_path, model)
        assert report.all_passed

    def test_population_conserved(self, tmp_path):
        """Verify S + I + R = N at all time points."""
        _write_sir_simulator(tmp_path)
        # Run simulation directly
        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            from importlib import import_module
            # Use subprocess to avoid import caching issues
            import subprocess
            result = subprocess.run(
                [sys.executable, "-c",
                 "import sys; sys.path.insert(0, '.')\n"
                 "from solver import run_simulation\n"
                 "r = run_simulation({'beta': 0.3, 'gamma': 0.1}, [9999, 1, 0], (0, 300))\n"
                 "import numpy as np\n"
                 "total = r['S'] + r['I'] + r['R']\n"
                 "print(f'{np.max(np.abs(total - 10000))}')\n"],
                cwd=str(tmp_path), capture_output=True, text=True, timeout=30
            )
            max_deviation = float(result.stdout.strip())
            assert max_deviation < 1e-4, f"Population not conserved: max deviation {max_deviation}"
        finally:
            sys.path.pop(0)

    def test_epidemic_peaks_then_declines(self, tmp_path):
        """Verify I rises, peaks, then falls to near zero."""
        _write_sir_simulator(tmp_path)
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.')\n"
             "from solver import run_simulation\n"
             "import numpy as np\n"
             "r = run_simulation({'beta': 0.3, 'gamma': 0.1}, [9999, 1, 0], (0, 300))\n"
             "I = r['I']\n"
             "peak = np.max(I)\n"
             "final = I[-1]\n"
             "print(f'{peak},{final}')\n"],
            cwd=str(tmp_path), capture_output=True, text=True, timeout=30
        )
        peak, final = [float(x) for x in result.stdout.strip().split(",")]
        assert peak > 1000, f"Peak too low: {peak}"
        assert final < 1, f"Final infected too high: {final}"
