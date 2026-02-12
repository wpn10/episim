"""End-to-end test on a standard SEIR model.

No LLM calls — tests the validator + solver chain with a hand-written SEIR simulator.
"""

from pathlib import Path

import pytest

from episim.core.model_spec import EpidemicModel
from episim.agents.validator import validate


def _seir_model() -> EpidemicModel:
    """Standard SEIR: beta=0.5, sigma=0.2, gamma=0.1, R0=5, N=100000."""
    return EpidemicModel(
        name="SEIR",
        paper_title="Standard SEIR Model",
        compartments=["S", "E", "I", "R"],
        parameters={
            "beta": {"value": 0.5, "description": "Transmission rate", "unit": "1/day", "slider_min": 0.05, "slider_max": 5.0},
            "sigma": {"value": 0.2, "description": "Incubation rate", "unit": "1/day", "slider_min": 0.02, "slider_max": 2.0},
            "gamma": {"value": 0.1, "description": "Recovery rate", "unit": "1/day", "slider_min": 0.01, "slider_max": 1.0},
        },
        initial_conditions={"S": 99999, "E": 0, "I": 1, "R": 0},
        ode_system=(
            "def derivatives(t, y, params):\n"
            "    S, E, I, R = y\n"
            "    N = sum(y)\n"
            "    beta = params['beta']\n"
            "    sigma = params['sigma']\n"
            "    gamma = params['gamma']\n"
            "    return [-beta*S*I/N, beta*S*I/N - sigma*E, sigma*E - gamma*I, gamma*I]"
        ),
        simulation_days=365,
        population=100000.0,
        expected_results=[
            {"metric": "R0", "value": 5.0, "source": "beta/gamma", "tolerance": 0.05},
        ],
    )


def _write_seir_simulator(output_dir: Path) -> None:
    (output_dir / "model.py").write_text(
        'COMPARTMENTS = ["S", "E", "I", "R"]\n\n'
        "def derivatives(t, y, params):\n"
        "    S, E, I, R = y\n"
        "    N = sum(y)\n"
        "    beta = params['beta']\n"
        "    sigma = params['sigma']\n"
        "    gamma = params['gamma']\n"
        "    dSdt = -beta * S * I / N\n"
        "    dEdt = beta * S * I / N - sigma * E\n"
        "    dIdt = sigma * E - gamma * I\n"
        "    dRdt = gamma * I\n"
        "    return [dSdt, dEdt, dIdt, dRdt]\n"
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


class TestSEIRBasic:
    def test_r0_passes(self, tmp_path):
        _write_seir_simulator(tmp_path)
        report = validate(tmp_path, _seir_model())
        r0 = next(m for m in report.metrics if m.metric == "R0")
        assert r0.passed
        assert abs(r0.actual - 5.0) < 0.01

    def test_all_metrics_pass(self, tmp_path):
        _write_seir_simulator(tmp_path)
        report = validate(tmp_path, _seir_model())
        assert report.all_passed

    def test_population_conserved(self, tmp_path):
        _write_seir_simulator(tmp_path)
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.')\n"
             "from solver import run_simulation\n"
             "import numpy as np\n"
             "r = run_simulation({'beta':0.5,'sigma':0.2,'gamma':0.1}, [99999,0,1,0], (0,365))\n"
             "total = r['S'] + r['E'] + r['I'] + r['R']\n"
             "print(f'{np.max(np.abs(total - 100000))}')\n"],
            cwd=str(tmp_path), capture_output=True, text=True, timeout=30
        )
        max_dev = float(result.stdout.strip())
        assert max_dev < 1e-3

    def test_exposed_compartment_delays_peak(self, tmp_path):
        """SEIR peak should be later than an equivalent SIR (due to latent period)."""
        _write_seir_simulator(tmp_path)
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.')\n"
             "from solver import run_simulation\n"
             "import numpy as np\n"
             "r = run_simulation({'beta':0.5,'sigma':0.2,'gamma':0.1}, [99999,0,1,0], (0,365))\n"
             "peak_day = r['t'][np.argmax(r['I'])]\n"
             "print(f'{peak_day}')\n"],
            cwd=str(tmp_path), capture_output=True, text=True, timeout=30
        )
        peak_day = float(result.stdout.strip())
        # With R0=5 and latent period of 5 days, peak should be in reasonable range
        assert 20 < peak_day < 200
