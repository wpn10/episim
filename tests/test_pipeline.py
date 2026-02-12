"""Integration tests for the orchestrator pipeline."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from episim.core.model_spec import EpidemicModel, MetricResult, ValidationReport, GeneratedFiles
from episim.core.orchestrator import run_pipeline


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


@patch("episim.core.orchestrator.load_paper", return_value="paper text")
@patch("episim.core.orchestrator.build_context", return_value="context")
@patch("episim.core.orchestrator.extract_model")
@patch("episim.core.orchestrator.generate_simulator")
@patch("episim.core.orchestrator.validate")
@patch("episim.core.orchestrator.write_report")
class TestPipelineIntegration:
    def test_output_dir_created(self, mock_wr, mock_val, mock_gen, mock_ext,
                                 mock_ctx, mock_load, tmp_path):
        mock_ext.return_value = (_sir_model(), "thinking")
        mock_val.return_value = _passing_report()

        result = run_pipeline("test.pdf", str(tmp_path))
        assert Path(result).exists()

    def test_thinking_file_saved(self, mock_wr, mock_val, mock_gen, mock_ext,
                                  mock_ctx, mock_load, tmp_path):
        mock_ext.return_value = (_sir_model(), "My deep analysis")
        mock_val.return_value = _passing_report()

        result = run_pipeline("test.pdf", str(tmp_path))
        thinking_file = Path(result) / "thinking.md"
        assert thinking_file.exists()
        assert "My deep analysis" in thinking_file.read_text()

    def test_report_written_on_pass(self, mock_wr, mock_val, mock_gen, mock_ext,
                                     mock_ctx, mock_load, tmp_path):
        mock_ext.return_value = (_sir_model(), "thinking")
        mock_val.return_value = _passing_report()

        run_pipeline("test.pdf", str(tmp_path))
        mock_wr.assert_called_once()

    def test_report_written_on_fail(self, mock_wr, mock_val, mock_gen, mock_ext,
                                     mock_ctx, mock_load, tmp_path):
        mock_ext.return_value = (_sir_model(), "thinking")
        # All 3 attempts fail
        mock_val.return_value = _failing_report()

        with patch("episim.core.orchestrator.debug_and_fix", return_value={}):
            with patch("episim.core.orchestrator.apply_fixes"):
                run_pipeline("test.pdf", str(tmp_path))

        # Report still written even on failure
        mock_wr.assert_called_once()

    @patch("episim.core.orchestrator.debug_and_fix", return_value={"model.py": "fixed"})
    @patch("episim.core.orchestrator.apply_fixes")
    def test_max_retries_respected(self, mock_apply, mock_debug,
                                    mock_wr, mock_val, mock_gen, mock_ext,
                                    mock_ctx, mock_load, tmp_path):
        mock_ext.return_value = (_sir_model(), "thinking")
        mock_val.return_value = _failing_report()

        run_pipeline("test.pdf", str(tmp_path))

        assert mock_val.call_count == 3
        # Debug called for attempts 1 and 2 (not after attempt 3)
        assert mock_debug.call_count == 2


class TestEdgeCases:
    @patch("episim.core.orchestrator.load_paper")
    def test_empty_paper_text(self, mock_load, tmp_path):
        mock_load.side_effect = FileNotFoundError("no file")
        with pytest.raises(FileNotFoundError):
            run_pipeline("nonexistent.pdf", str(tmp_path))

    @patch("episim.core.orchestrator.load_paper", return_value="text")
    @patch("episim.core.orchestrator.build_context", return_value="ctx")
    @patch("episim.core.orchestrator.extract_model")
    def test_reader_failure_propagates(self, mock_ext, mock_ctx, mock_load, tmp_path):
        mock_ext.side_effect = RuntimeError("API failed")
        with pytest.raises(RuntimeError, match="API failed"):
            run_pipeline("test.pdf", str(tmp_path))

    @patch("episim.core.orchestrator.load_paper", return_value="text")
    @patch("episim.core.orchestrator.build_context", return_value="ctx")
    @patch("episim.core.orchestrator.extract_model")
    @patch("episim.core.orchestrator.generate_simulator")
    @patch("episim.core.orchestrator.validate")
    @patch("episim.core.orchestrator.write_report")
    def test_subprocess_crash_in_validation(self, mock_wr, mock_val, mock_gen,
                                             mock_ext, mock_ctx, mock_load, tmp_path):
        mock_ext.return_value = (_sir_model(), "thinking")
        mock_val.return_value = ValidationReport(
            paper_title="Test", model_name="SIR", metrics=[],
            all_passed=False, attempts=1, error="subprocess crashed"
        )

        with patch("episim.core.orchestrator.debug_and_fix", return_value={}):
            with patch("episim.core.orchestrator.apply_fixes"):
                result = run_pipeline("test.pdf", str(tmp_path))

        # Pipeline completes (doesn't crash), report is written
        mock_wr.assert_called_once()
