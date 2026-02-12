"""Tests for orchestrator — pipeline wiring and CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from episim.core.orchestrator import run_pipeline, _slugify, save_thinking
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


def _passing_report():
    return ValidationReport(
        paper_title="Test SIR",
        model_name="SIR",
        metrics=[MetricResult(metric="R0", expected=3.0, actual=3.0, match_pct=0.0, passed=True)],
        all_passed=True,
        attempts=1,
    )


def _failing_report():
    return ValidationReport(
        paper_title="Test SIR",
        model_name="SIR",
        metrics=[MetricResult(metric="R0", expected=3.0, actual=1.0, match_pct=66.7, passed=False)],
        all_passed=False,
        attempts=1,
    )


class TestSlugify:
    def test_pdf_path(self):
        assert _slugify("/path/to/my_paper.pdf") == "my_paper"

    def test_arxiv_id(self):
        assert _slugify("2401.12345") == "2401.12345"

    def test_url(self):
        slug = _slugify("https://arxiv.org/abs/2401.12345")
        assert "2401.12345" in slug

    def test_truncates_long_names(self):
        assert len(_slugify("a" * 200)) <= 80


class TestSaveThinking:
    def test_writes_thinking_file(self, tmp_path):
        save_thinking("Deep analysis here", tmp_path)
        content = (tmp_path / "thinking.md").read_text()
        assert "Deep analysis here" in content


@patch("episim.core.orchestrator.load_paper", return_value="paper text")
@patch("episim.core.orchestrator.build_context", return_value="full context")
@patch("episim.core.orchestrator.extract_model")
@patch("episim.core.orchestrator.generate_simulator")
@patch("episim.core.orchestrator.validate")
@patch("episim.core.orchestrator.write_report")
class TestRunPipeline:
    def test_happy_path(self, mock_write, mock_validate, mock_gen, mock_extract,
                        mock_context, mock_load, tmp_path):
        mock_extract.return_value = (_sir_model(), "thinking text")
        mock_validate.return_value = _passing_report()

        result = run_pipeline("test.pdf", str(tmp_path))

        assert Path(result).exists()
        mock_load.assert_called_once()
        mock_context.assert_called_once()
        mock_extract.assert_called_once()
        mock_gen.assert_called_once()
        mock_validate.assert_called_once()
        mock_write.assert_called_once()

    @patch("episim.core.orchestrator.debug_and_fix", return_value={"model.py": "fixed"})
    @patch("episim.core.orchestrator.apply_fixes")
    def test_debug_loop_on_failure(self, mock_apply, mock_debug,
                                    mock_write, mock_validate, mock_gen,
                                    mock_extract, mock_context, mock_load, tmp_path):
        mock_extract.return_value = (_sir_model(), "thinking")
        # First validation fails, second passes
        mock_validate.side_effect = [_failing_report(), _passing_report()]

        run_pipeline("test.pdf", str(tmp_path))

        assert mock_validate.call_count == 2
        mock_debug.assert_called_once()
        mock_apply.assert_called_once()
