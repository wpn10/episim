"""Tests for debugger agent — analyze failures and patch code."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from episim.agents.debugger import debug_and_fix, apply_fixes, DEBUGGER_SYSTEM_PROMPT, MODEL
from episim.core.model_spec import EpidemicModel, MetricResult, ValidationReport


def _sir_model():
    return EpidemicModel(
        name="SIR",
        paper_title="Test SIR",
        compartments=["S", "I", "R"],
        parameters={
            "beta": {"value": 0.3, "description": "Transmission rate", "unit": "1/day", "slider_min": 0.03, "slider_max": 3.0},
            "gamma": {"value": 0.1, "description": "Recovery rate", "unit": "1/day", "slider_min": 0.01, "slider_max": 1.0},
        },
        initial_conditions={"S": 999, "I": 1, "R": 0},
        ode_system="def derivatives(t, y, params): pass",
        simulation_days=160,
        population=1000.0,
        expected_results=[{"metric": "R0", "value": 3.0, "source": "Computed", "tolerance": 0.05}],
    )


def _failed_report():
    return ValidationReport(
        paper_title="Test SIR",
        model_name="SIR",
        metrics=[MetricResult(metric="R0", expected=3.0, actual=1.5, match_pct=50.0, passed=False)],
        all_passed=False,
        attempts=1,
        error=None,
    )


def _make_mock_response(fixes: dict):
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "submit_fixes"
    tool_block.input = {"fixes": fixes, "explanation": "Fixed ODE signs"}
    response = MagicMock()
    response.content = [tool_block]
    return response


def _setup_stream_mock(mock_client, response):
    """Set up mock_client.messages.stream() to work as a context manager."""
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = MagicMock(return_value=stream_ctx)
    stream_ctx.__exit__ = MagicMock(return_value=False)
    stream_ctx.get_final_message.return_value = response
    mock_client.messages.stream.return_value = stream_ctx
    return stream_ctx


@patch("episim.agents.debugger.anthropic.Anthropic")
def test_debug_returns_fixes(mock_cls, tmp_path):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    (tmp_path / "model.py").write_text("COMPARTMENTS = ['S','I','R']")
    (tmp_path / "solver.py").write_text("pass")
    (tmp_path / "app.py").write_text("pass")
    (tmp_path / "config.json").write_text("{}")

    expected_fixes = {"model.py": "# fixed model"}
    _setup_stream_mock(mock_client, _make_mock_response(expected_fixes))

    fixes = debug_and_fix(_failed_report(), tmp_path, _sir_model())
    assert fixes == expected_fixes


@patch("episim.agents.debugger.anthropic.Anthropic")
def test_debug_uses_correct_api_config(mock_cls, tmp_path):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    for f in ["model.py", "solver.py", "app.py", "config.json"]:
        (tmp_path / f).write_text("pass")

    _setup_stream_mock(mock_client, _make_mock_response({}))

    debug_and_fix(_failed_report(), tmp_path, _sir_model())

    kwargs = mock_client.messages.stream.call_args.kwargs
    assert kwargs["model"] == MODEL
    assert kwargs["max_tokens"] == 16384
    # No thinking or tool_choice (removed for API compatibility)
    assert "thinking" not in kwargs
    assert "tool_choice" not in kwargs


class TestApplyFixes:
    def test_writes_fixed_files(self, tmp_path):
        (tmp_path / "model.py").write_text("old content")
        apply_fixes({"model.py": "new content"}, tmp_path)
        assert (tmp_path / "model.py").read_text() == "new content"

    def test_only_overwrites_specified_files(self, tmp_path):
        (tmp_path / "model.py").write_text("original")
        (tmp_path / "solver.py").write_text("untouched")
        apply_fixes({"model.py": "fixed"}, tmp_path)
        assert (tmp_path / "solver.py").read_text() == "untouched"


def test_system_prompt_content():
    assert "debugger" in DEBUGGER_SYSTEM_PROMPT.lower() or "debug" in DEBUGGER_SYSTEM_PROMPT.lower()
    assert "ODE" in DEBUGGER_SYSTEM_PROMPT
