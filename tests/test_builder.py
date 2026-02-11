"""Tests for builder agent — EpidemicModel → generated simulator files."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from episim.agents.builder import generate_simulator, BUILDER_SYSTEM_PROMPT
from episim.core.model_spec import EpidemicModel, GeneratedFiles


_SIR_MODEL = EpidemicModel(
    name="SIR",
    paper_title="A Simple SIR Model",
    compartments=["S", "I", "R"],
    parameters={
        "beta": {"value": 0.3, "description": "Transmission rate", "unit": "1/day", "slider_min": 0.03, "slider_max": 3.0},
        "gamma": {"value": 0.1, "description": "Recovery rate", "unit": "1/day", "slider_min": 0.01, "slider_max": 1.0},
    },
    initial_conditions={"S": 999, "I": 1, "R": 0},
    ode_system="def derivatives(t, y, params):\n    S, I, R = y\n    N = sum(y)\n    beta = params['beta']\n    gamma = params['gamma']\n    return [-beta*S*I/N, beta*S*I/N - gamma*I, gamma*I]",
    simulation_days=160,
    population=1000.0,
    expected_results=[{"metric": "R0", "value": 3.0, "source": "Section 2", "tolerance": 0.05}],
)

_MOCK_FILES = GeneratedFiles(
    model_py='COMPARTMENTS = ["S", "I", "R"]\n\ndef derivatives(t, y, params):\n    S, I, R = y\n    N = sum(y)\n    beta = params["beta"]\n    gamma = params["gamma"]\n    return [-beta*S*I/N, beta*S*I/N - gamma*I, gamma*I]\n',
    solver_py='from scipy.integrate import solve_ivp\nimport numpy as np\nfrom model import COMPARTMENTS, derivatives\n\ndef run_simulation(params, y0, t_span, num_points=1000):\n    t_eval = np.linspace(t_span[0], t_span[1], num_points)\n    sol = solve_ivp(lambda t, y: derivatives(t, y, params), t_span, y0, method="RK45", t_eval=t_eval, max_step=1.0, rtol=1e-8, atol=1e-8)\n    results = {"t": sol.t}\n    for i, name in enumerate(COMPARTMENTS):\n        results[name] = sol.y[i]\n    return results\n',
    app_py='import streamlit as st\nimport plotly.graph_objects as go\nimport json\nfrom solver import run_simulation\nfrom model import COMPARTMENTS\n\nst.title("SIR Model")\n',
    config_json='{"parameters": {"beta": 0.3, "gamma": 0.1}, "initial_conditions": {"S": 999, "I": 1, "R": 0}, "population": 1000, "simulation_days": 160, "compartments": ["S", "I", "R"]}',
    requirements_txt='streamlit\nplotly\nscipy\nnumpy\n',
)


def _make_mock_response(files: GeneratedFiles):
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "submit_files"
    tool_block.input = files.model_dump()
    response = MagicMock()
    response.content = [tool_block]
    return response


@patch("episim.agents.builder.anthropic.Anthropic")
def test_generate_creates_all_files(mock_anthropic_cls, tmp_path):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(_MOCK_FILES)

    output_dir = tmp_path / "test_output"
    result = generate_simulator(_SIR_MODEL, output_dir)

    assert result == output_dir
    for fname in ["model.py", "solver.py", "app.py", "config.json", "requirements.txt"]:
        assert (output_dir / fname).exists()


@patch("episim.agents.builder.anthropic.Anthropic")
def test_generated_model_py_is_valid_python(mock_anthropic_cls, tmp_path):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(_MOCK_FILES)

    output_dir = tmp_path / "test_output"
    generate_simulator(_SIR_MODEL, output_dir)

    code = (output_dir / "model.py").read_text()
    compile(code, "model.py", "exec")  # raises SyntaxError if invalid


@patch("episim.agents.builder.anthropic.Anthropic")
def test_generated_solver_py_is_valid_python(mock_anthropic_cls, tmp_path):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(_MOCK_FILES)

    output_dir = tmp_path / "test_output"
    generate_simulator(_SIR_MODEL, output_dir)

    code = (output_dir / "solver.py").read_text()
    compile(code, "solver.py", "exec")


@patch("episim.agents.builder.anthropic.Anthropic")
def test_generated_config_is_valid_json(mock_anthropic_cls, tmp_path):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(_MOCK_FILES)

    output_dir = tmp_path / "test_output"
    generate_simulator(_SIR_MODEL, output_dir)

    config = json.loads((output_dir / "config.json").read_text())
    assert "parameters" in config
    assert "compartments" in config


@patch("episim.agents.builder.anthropic.Anthropic")
def test_uses_correct_api_config(mock_anthropic_cls, tmp_path):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(_MOCK_FILES)

    generate_simulator(_SIR_MODEL, tmp_path / "out")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-opus-4-6"
    assert call_kwargs["max_tokens"] == 32768
    assert call_kwargs["tool_choice"]["name"] == "submit_files"


def test_system_prompt_has_file_contracts():
    assert "model.py" in BUILDER_SYSTEM_PROMPT
    assert "solver.py" in BUILDER_SYSTEM_PROMPT
    assert "app.py" in BUILDER_SYSTEM_PROMPT
    assert "COMPARTMENTS" in BUILDER_SYSTEM_PROMPT
    assert "run_simulation" in BUILDER_SYSTEM_PROMPT
