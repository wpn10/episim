"""Tests for the Summarizer agent — mocked, no API calls."""

from unittest.mock import MagicMock, patch

from episim.agents.summarizer import summarize_paper, SUMMARIZER_SYSTEM_PROMPT
from episim.core.model_spec import EpidemicModel, PaperSummary


def _sir_model():
    return EpidemicModel(
        name="SIR",
        paper_title="Test SIR Paper",
        compartments=["S", "I", "R"],
        parameters={
            "beta": {"value": 0.3, "description": "Transmission rate", "unit": "1/day", "slider_min": 0.03, "slider_max": 3.0},
            "gamma": {"value": 0.1, "description": "Recovery rate", "unit": "1/day", "slider_min": 0.01, "slider_max": 1.0},
        },
        initial_conditions={"S": 999, "I": 1, "R": 0},
        ode_system="def derivatives(t, y, params): pass",
        simulation_days=160,
        population=1000.0,
        expected_results=[],
    )


def _mock_summary_data():
    return {
        "title": "Test SIR Paper",
        "authors": "Smith et al.",
        "abstract_summary": "A study of disease spread using SIR.",
        "model_type": "SIR (3-compartment)",
        "key_findings": ["R0 is 3.0", "Peak at day 47"],
        "methodology": "Standard SIR ODE model.",
        "limitations": "Assumes homogeneous mixing.",
        "public_health_implications": "Early intervention reduces peak.",
    }


@patch("episim.agents.summarizer.anthropic.Anthropic")
def test_summarize_returns_valid_summary(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "submit_summary"
    mock_tool_block.input = _mock_summary_data()

    mock_response = MagicMock()
    mock_response.content = [mock_tool_block]

    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.get_final_message.return_value = mock_response
    mock_client.messages.stream.return_value = mock_stream

    result = summarize_paper("paper text", _sir_model())

    assert isinstance(result, PaperSummary)
    assert result.title == "Test SIR Paper"
    assert len(result.key_findings) == 2


def test_system_prompt_content():
    assert "science communicator" in SUMMARIZER_SYSTEM_PROMPT
    assert "submit_summary" in SUMMARIZER_SYSTEM_PROMPT


def test_paper_summary_schema():
    schema = PaperSummary.model_json_schema()
    assert "title" in schema["properties"]
    assert "key_findings" in schema["properties"]
    assert "public_health_implications" in schema["properties"]
