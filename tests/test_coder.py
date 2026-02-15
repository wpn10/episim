"""Tests for the Coder agent — mocked, no API calls."""

from unittest.mock import MagicMock, patch

from episim.agents.coder import generate_standalone, CODER_SYSTEM_PROMPT
from episim.core.model_spec import EpidemicModel, StandaloneScript


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


def _mock_script_data():
    return {
        "filename": "sir_simulation.py",
        "code": "import numpy as np\nprint('hello')\n",
        "description": "Standalone SIR reproduction script",
    }


@patch("episim.agents.coder.anthropic.Anthropic")
def test_generate_returns_valid_script(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "submit_script"
    mock_tool_block.input = _mock_script_data()

    mock_response = MagicMock()
    mock_response.content = [mock_tool_block]

    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.get_final_message.return_value = mock_response
    mock_client.messages.stream.return_value = mock_stream

    result = generate_standalone(_sir_model(), "paper text here")

    assert isinstance(result, StandaloneScript)
    assert result.filename == "sir_simulation.py"
    assert "import numpy" in result.code


def test_system_prompt_content():
    assert "standalone" in CODER_SYSTEM_PROMPT.lower()
    assert "submit_script" in CODER_SYSTEM_PROMPT
    assert "matplotlib" in CODER_SYSTEM_PROMPT


def test_standalone_script_schema():
    schema = StandaloneScript.model_json_schema()
    assert "filename" in schema["properties"]
    assert "code" in schema["properties"]
    assert "description" in schema["properties"]


@patch("episim.agents.coder.anthropic.Anthropic")
def test_paper_text_truncated_to_8000(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "submit_script"
    mock_tool_block.input = _mock_script_data()

    mock_response = MagicMock()
    mock_response.content = [mock_tool_block]

    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.get_final_message.return_value = mock_response
    mock_client.messages.stream.return_value = mock_stream

    long_text = "x" * 20000
    generate_standalone(_sir_model(), long_text)

    # Verify the user message sent to the API contains truncated paper text
    call_kwargs = mock_client.messages.stream.call_args[1]
    user_msg = call_kwargs["messages"][0]["content"]
    # The paper_context section should not contain the full 20000 chars
    assert len(user_msg) < 20000
