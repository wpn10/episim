"""Tests for model_spec — round-trip serialization and schema generation."""

import json

from episim.core.model_spec import (
    EpidemicModel,
    ExpectedResult,
    GeneratedFiles,
    MetricResult,
    Parameter,
    ValidationReport,
)

# Fixture: a simple SIR model spec
SIR_SPEC = {
    "name": "SIR",
    "paper_title": "A Simple SIR Model",
    "compartments": ["S", "I", "R"],
    "parameters": {
        "beta": {"value": 0.3, "description": "Transmission rate", "unit": "1/day", "slider_min": 0.03, "slider_max": 3.0},
        "gamma": {"value": 0.1, "description": "Recovery rate", "unit": "1/day", "slider_min": 0.01, "slider_max": 1.0},
    },
    "initial_conditions": {"S": 999, "I": 1, "R": 0},
    "ode_system": "def derivatives(t, y, params):\n    S, I, R = y\n    N = sum(y)\n    beta = params['beta']\n    gamma = params['gamma']\n    return [-beta*S*I/N, beta*S*I/N - gamma*I, gamma*I]",
    "simulation_days": 160,
    "population": 1000.0,
    "expected_results": [
        {"metric": "R0", "value": 3.0, "source": "Section 2"},
    ],
}


def test_epidemic_model_round_trip():
    model = EpidemicModel(**SIR_SPEC)
    dumped = model.model_dump()
    restored = EpidemicModel(**dumped)
    assert restored == model


def test_epidemic_model_json_round_trip():
    model = EpidemicModel(**SIR_SPEC)
    json_str = model.model_dump_json()
    restored = EpidemicModel.model_validate_json(json_str)
    assert restored == model


def test_epidemic_model_schema_generation():
    schema = EpidemicModel.model_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "compartments" in schema["properties"]
    assert "parameters" in schema["properties"]


def test_generated_files_schema():
    schema = GeneratedFiles.model_json_schema()
    assert "model_py" in schema["properties"]
    assert "solver_py" in schema["properties"]


def test_validation_report_round_trip():
    report = ValidationReport(
        paper_title="Test",
        model_name="SIR",
        metrics=[
            MetricResult(metric="R0", expected=3.0, actual=2.95, match_pct=1.67, passed=True),
        ],
        all_passed=True,
        attempts=1,
    )
    restored = ValidationReport.model_validate_json(report.model_dump_json())
    assert restored == report


def test_parameter_defaults():
    p = Parameter(value=0.3, description="test", slider_min=0.03, slider_max=3.0)
    assert p.unit == ""


def test_expected_result_default_tolerance():
    er = ExpectedResult(metric="R0", value=3.0, source="Table 1")
    assert er.tolerance == 0.05
