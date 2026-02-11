"""Tests for reader agent — model extraction from paper context."""

from unittest.mock import MagicMock, patch

from episim.agents.reader import extract_model, READER_SYSTEM_PROMPT
from episim.core.model_spec import EpidemicModel


# A valid SIR model spec that the mock API will return
_SIR_TOOL_INPUT = {
    "name": "SIR",
    "paper_title": "A Contribution to the Mathematical Theory of Epidemics",
    "compartments": ["S", "I", "R"],
    "parameters": {
        "beta": {"value": 0.3, "description": "Transmission rate", "unit": "1/day", "slider_min": 0.03, "slider_max": 3.0},
        "gamma": {"value": 0.1, "description": "Recovery rate", "unit": "1/day", "slider_min": 0.01, "slider_max": 1.0},
    },
    "initial_conditions": {"S": 999, "I": 1, "R": 0},
    "ode_system": (
        "def derivatives(t, y, params):\n"
        "    S, I, R = y\n"
        "    N = sum(y)\n"
        "    beta = params['beta']\n"
        "    gamma = params['gamma']\n"
        "    dSdt = -beta * S * I / N\n"
        "    dIdt = beta * S * I / N - gamma * I\n"
        "    dRdt = gamma * I\n"
        "    return [dSdt, dIdt, dRdt]"
    ),
    "simulation_days": 160,
    "population": 1000.0,
    "expected_results": [
        {"metric": "R0", "value": 3.0, "source": "Section 2", "tolerance": 0.05},
    ],
}


def _make_mock_response(tool_input: dict, include_thinking: bool = True):
    """Create a mock Anthropic API response with thinking + tool_use blocks."""
    blocks = []

    if include_thinking:
        thinking_block = MagicMock()
        thinking_block.type = "thinking"
        thinking_block.thinking = "This paper describes a classic SIR model with beta=0.3 and gamma=0.1."
        blocks.append(thinking_block)

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "submit_model"
    tool_block.input = tool_input
    blocks.append(tool_block)

    response = MagicMock()
    response.content = blocks
    return response


@patch("episim.agents.reader.anthropic.Anthropic")
def test_extract_model_returns_valid_model(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(_SIR_TOOL_INPUT)

    model, thinking = extract_model("fake paper context")

    assert isinstance(model, EpidemicModel)
    assert model.name == "SIR"
    assert model.compartments == ["S", "I", "R"]
    assert "beta" in model.parameters
    assert model.population == 1000.0


@patch("episim.agents.reader.anthropic.Anthropic")
def test_extract_model_captures_thinking(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(_SIR_TOOL_INPUT)

    model, thinking = extract_model("fake context")

    assert "SIR model" in thinking


@patch("episim.agents.reader.anthropic.Anthropic")
def test_extract_model_retries_on_failure(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    # First call fails, second succeeds
    mock_client.messages.create.side_effect = [
        Exception("API error"),
        _make_mock_response(_SIR_TOOL_INPUT),
    ]

    model, thinking = extract_model("fake context")
    assert model.name == "SIR"
    assert mock_client.messages.create.call_count == 2


@patch("episim.agents.reader.anthropic.Anthropic")
def test_extract_model_uses_correct_api_config(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(_SIR_TOOL_INPUT)

    extract_model("context")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-opus-4-6"
    assert call_kwargs["max_tokens"] == 16384
    assert call_kwargs["thinking"]["budget_tokens"] == 32768
    assert call_kwargs["tool_choice"]["name"] == "submit_model"


def test_system_prompt_has_key_instructions():
    assert "epidemiologist" in READER_SYSTEM_PROMPT
    assert "compartments" in READER_SYSTEM_PROMPT.lower()
    assert "ode_system" in READER_SYSTEM_PROMPT or "ODE" in READER_SYSTEM_PROMPT
    assert "derivatives" in READER_SYSTEM_PROMPT
