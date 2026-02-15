"""Central schema — the contract between all agents."""

from __future__ import annotations

from pydantic import BaseModel


class Parameter(BaseModel):
    value: float
    description: str
    unit: str = ""
    slider_min: float
    slider_max: float


class ExpectedResult(BaseModel):
    metric: str  # "peak_day" | "peak_cases" | "R0" | "attack_rate" | custom
    value: float
    source: str  # "Figure 3", "Table 2", "Section 4.1"
    tolerance: float = 0.05


class EpidemicModel(BaseModel):
    name: str
    paper_title: str
    compartments: list[str]
    parameters: dict[str, Parameter]
    initial_conditions: dict[str, float]
    ode_system: str  # Complete Python function as string
    simulation_days: int
    population: float
    expected_results: list[ExpectedResult]


class GeneratedFiles(BaseModel):
    model_py: str
    solver_py: str
    app_py: str
    config_json: str
    requirements_txt: str


class PaperSummary(BaseModel):
    title: str
    authors: str
    abstract_summary: str  # 2-3 sentence plain-English summary
    model_type: str  # e.g. "SIDARTHE (8-compartment COVID-19 model)"
    key_findings: list[str]  # 3-5 bullet points
    methodology: str
    limitations: str
    public_health_implications: str


class StandaloneScript(BaseModel):
    filename: str  # e.g. "sidarthe_simulation.py"
    code: str  # Complete standalone Python script
    description: str  # One-line description for the download button


class MetricResult(BaseModel):
    metric: str
    expected: float
    actual: float
    match_pct: float  # abs(1 - actual/expected) as percentage
    passed: bool  # match_pct <= tolerance * 100


class ValidationReport(BaseModel):
    paper_title: str
    model_name: str
    metrics: list[MetricResult]
    all_passed: bool
    attempts: int
    error: str | None = None
