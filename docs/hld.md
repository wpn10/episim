# EpiSim — High-Level Design

## Mission

Three-agent pipeline: PDF/arxiv paper → validated interactive Streamlit epidemic simulator.
Uses Opus 4.6 (1M context, extended thinking, 128K output).

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.11+ | Ecosystem (scipy, streamlit, anthropic SDK) |
| AI | `anthropic` Python SDK (raw, not Agent SDK) | Pipeline pattern; one prompt → one response per agent |
| LLM | Opus 4.6 (`claude-opus-4-6`) | 1M context, extended thinking, 128K output |
| Schemas | Pydantic v2 | JSON schema for tool_use, validation, serialization |
| ODE Solver | `scipy.integrate.solve_ivp` | Industry standard, handles stiff + non-stiff |
| UI | Streamlit (single app: upload + pipeline + results) | Fastest path to interactive sliders + demo |
| Charts | Plotly | Interactive (hover, zoom, pan) |
| PDF parsing | PyMuPDF (`fitz`) | Fast, reliable text extraction |
| Tests | pytest | Standard |

**No FastAPI.** Streamlit serves as both the frontend and the pipeline trigger. One app does everything: upload → process → interactive results. No separate backend needed.

---

## Data Flow

```
Paper (PDF/arxiv URL)
    │
    ▼
┌─────────────┐
│ Paper Loader │  PyMuPDF text extraction
└──────┬──────┘
       │ raw text (str)
       ▼
┌─────────────────┐
│ Context Builder  │  paper + knowledge/*.md → single prompt
└──────┬──────────┘
       │ assembled context (~50-80K tokens)
       ▼
┌──────────────────┐
│ Reader Agent     │  Opus 4.6 + extended thinking
│ (Epidemiologist) │  Structured output via tool_use
└──────┬───────────┘
       │ EpidemicModel (Pydantic JSON)
       ▼
┌──────────────────┐
│ Builder Agent    │  Opus 4.6 + 128K output
│ (Engineer)       │  Generates all files in one pass
└──────┬───────────┘
       │ model.py, solver.py, app.py, config.json, requirements.txt
       ▼
┌──────────────────┐
│ Validator        │  Runs generated code via subprocess
│ (Referee)        │  Compares metrics vs paper's claims
└──────┬───────────┘
       │
       ├─ ALL PASS (≤5% deviation) → write reproduction_report.md → done
       │
       └─ ANY FAIL → Debugger Agent (Opus 4.6 + extended thinking)
                      │ analyzes discrepancy, patches code
                      └→ re-validate (max 3 retries)
```

---

## Component Specifications

### 1. Paper Loader — `episim/core/paper_loader.py`

```
load_paper(source: str) -> str
```

| Input | Processing | Output |
|-------|-----------|--------|
| Local PDF path | `fitz.open(path)` → extract text per page | Concatenated text |
| arxiv URL | Extract ID → download `https://arxiv.org/pdf/{id}` to tempfile → fitz | Concatenated text |
| arxiv ID (e.g. `2401.12345`) | Normalize to URL → same as above | Concatenated text |

Implementation notes:
- Use `page.get_text("text")` for each page — handles multi-column
- Strip running headers/footers via heuristic (repeated short lines across pages)
- Preserve section structure (detect `# ` style headings from font size changes if possible, else pass raw text)
- Return raw text. Reader Agent handles interpretation.

### 2. Context Builder — `episim/core/context_builder.py`

```
build_context(paper_text: str, knowledge_dir: Path = "episim/knowledge/") -> str
```

Assembles a single string in this exact order:

```
<paper>
{paper_text}
</paper>

<reference_models>
{contents of knowledge/base_models.md}
</reference_models>

<parameter_ranges>
{contents of knowledge/parameters.md}
</parameter_ranges>

<solver_guide>
{contents of knowledge/solver_guide.md}
</solver_guide>
```

Uses XML tags for clear section boundaries. Total budget: 50-80K tokens (well within 1M limit; remaining space available for papers with extensive supplementary materials or multiple referenced papers).

### 3. Model Spec — `episim/core/model_spec.py`

Central schema. **Pydantic v2** for validation, JSON serialization, and tool_use schema generation.

```python
from pydantic import BaseModel

class Parameter(BaseModel):
    value: float
    description: str
    unit: str = ""
    slider_min: float    # default: 0.1 * value
    slider_max: float    # default: 10.0 * value

class ExpectedResult(BaseModel):
    metric: str          # "peak_day" | "peak_cases" | "R0" | "attack_rate" | custom
    value: float
    source: str          # "Figure 3", "Table 2", "Section 4.1"
    tolerance: float = 0.05

class EpidemicModel(BaseModel):
    name: str                              # "SEIR with Vaccination"
    paper_title: str
    compartments: list[str]                # ["S", "E", "I", "R"]
    parameters: dict[str, Parameter]
    initial_conditions: dict[str, float]   # {"S": 999900, "I": 100, ...}
    ode_system: str                        # Complete Python function (see below)
    simulation_days: int
    population: float
    expected_results: list[ExpectedResult]
```

**`ode_system` contract** — Must be a complete, self-contained Python function:
```python
def derivatives(t, y, params):
    S, E, I, R = y
    N = sum(y)
    beta = params['beta']
    sigma = params['sigma']
    gamma = params['gamma']
    dSdt = -beta * S * I / N
    dEdt = beta * S * I / N - sigma * E
    dIdt = sigma * E - gamma * I
    dRdt = gamma * I
    return [dSdt, dEdt, dIdt, dRdt]
```

The `y` unpacking order MUST match the `compartments` list order.

### 4. Reader Agent — `agents/reader.py`

```
extract_model(context: str) -> EpidemicModel
```

| Config | Value |
|--------|-------|
| Model | `claude-opus-4-6` |
| Extended thinking | `enabled`, `budget_tokens=32768` |
| Output method | `tool_use` with EpidemicModel JSON schema |
| Temperature | Not set (thinking mode ignores it) |
| Max tokens | 16384 (for the non-thinking output) |

**System prompt strategy:**
- Role: expert epidemiologist extracting a mathematical model
- Task: identify compartments, transitions, ODE system, all parameters with values, initial conditions, and key reported results to validate against
- Constraints: write `ode_system` as a complete Python function using only basic math ops and `params` dict lookups; `y` unpacking must match `compartments` order
- Provide the Pydantic JSON schema via `tools` parameter

**Why tool_use not JSON mode:** Tool use enforces exact schema compliance. The model MUST return valid EpidemicModel JSON.

**Capture thinking blocks:** Store the `thinking` content blocks from the response — they're displayed in the demo to show "AI reasoning like an epidemiologist."

```python
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 32768},
    system=READER_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": context}],
    tools=[{
        "name": "submit_model",
        "description": "Submit the extracted epidemic model specification",
        "input_schema": EpidemicModel.model_json_schema()
    }],
    tool_choice={"type": "tool", "name": "submit_model"}
)
```

### 5. Builder Agent — `agents/builder.py`

```
generate_simulator(model: EpidemicModel, output_dir: Path) -> Path
```

| Config | Value |
|--------|-------|
| Model | `claude-opus-4-6` |
| Extended thinking | Optional (enable for complex models) |
| Output method | `tool_use` with file contents schema |
| Max tokens | 32768 |

**Input:** EpidemicModel serialized as JSON in the user message.

**Output schema (via tool_use):**
```python
class GeneratedFiles(BaseModel):
    model_py: str
    solver_py: str
    app_py: str
    config_json: str
    requirements_txt: str
```

**Generated file contracts:**

**model.py** must contain:
- `COMPARTMENTS: list[str]` — compartment names
- `def derivatives(t, y, params) -> list[float]` — the ODE system
- Matching the `ode_system` from the model spec but as importable Python

**solver.py** must contain:
- `from scipy.integrate import solve_ivp`
- `def run_simulation(params: dict, y0: list[float], t_span: tuple, num_points: int = 1000) -> dict`
- Returns `{"t": ndarray, "S": ndarray, "I": ndarray, ...}` — keys match compartment names
- Uses `method="RK45"` with `max_step=1.0` for stability

**app.py** must contain:
- Streamlit app with `st.sidebar` sliders for every parameter
- Slider defaults = paper values, range = `[slider_min, slider_max]`
- Main area: Plotly line chart with all compartments over time
- "Reset to Paper Defaults" button
- Title and description from model spec

**config.json** — serialized `EpidemicModel.model_dump()`

**requirements.txt** — `streamlit`, `plotly`, `scipy`, `numpy`

### 6. Validator — `agents/validator.py`

```
validate(output_dir: Path, model: EpidemicModel) -> ValidationReport
```

**This is primarily Python logic, not an LLM agent.** It:

1. Writes `_validate.py` into `output_dir`:
   - Imports `model` and `solver` from the output dir
   - Loads `config.json` for parameters and initial conditions
   - Calls `solver.run_simulation(...)` with paper defaults
   - Computes each metric from `model.expected_results`:
     - `peak_day`: `t[argmax(I)]`
     - `peak_cases`: `max(I)`
     - `R0`: `params['beta'] / params['gamma']` (or as specified)
     - `attack_rate`: `(N - S[-1]) / N`
     - Custom metrics: computed based on metric name
   - Prints JSON: `[{"metric": "...", "actual": ...}, ...]`

2. Runs via `subprocess.run(["python", "_validate.py"], cwd=output_dir, capture_output=True, timeout=30)`

3. Parses stdout JSON, compares each metric against `ExpectedResult`

4. Uses Claude to generate `reproduction_report.md` (formatted comparison table)

```python
class MetricResult(BaseModel):
    metric: str
    expected: float
    actual: float
    match_pct: float        # abs(1 - actual/expected) as percentage
    passed: bool            # match_pct <= tolerance * 100

class ValidationReport(BaseModel):
    paper_title: str
    model_name: str
    metrics: list[MetricResult]
    all_passed: bool
    attempts: int
    error: str | None = None  # if subprocess crashed
```

### 7. Debugger Agent — `agents/debugger.py`

```
debug_and_fix(report: ValidationReport, output_dir: Path, model: EpidemicModel) -> dict[str, str]
```

| Config | Value |
|--------|-------|
| Model | `claude-opus-4-6` |
| Extended thinking | `enabled`, `budget_tokens=16384` |
| Max tokens | 16384 |

**Triggered only when validation fails.** Receives:
- The `EpidemicModel` (what we intended)
- The generated code files (what we produced)
- The `ValidationReport` (what went wrong — which metrics deviated and by how much)
- subprocess stderr if the code crashed

**Returns:** `dict[str, str]` mapping filename → updated content for files that need fixes.

Orchestrator writes fixes to disk and triggers re-validation.

### 8. Orchestrator — `episim/core/orchestrator.py`

```
run_pipeline(paper_source: str, output_base: str = "output") -> Path
```

**Sequence:**
```python
def run_pipeline(paper_source: str, output_base: str = "output") -> Path:
    # 1. Load paper
    paper_text = load_paper(paper_source)
    paper_name = slugify(paper_source)

    # 2. Build context
    context = build_context(paper_text)

    # 3. Extract model (Reader Agent)
    model, thinking_text = extract_model(context)  # capture thinking for demo

    # 4. Generate simulator (Builder Agent)
    output_dir = Path(output_base) / paper_name
    generate_simulator(model, output_dir)

    # 5. Validate + Debug loop
    MAX_RETRIES = 3
    for attempt in range(1, MAX_RETRIES + 1):
        report = validate(output_dir, model)
        report.attempts = attempt
        if report.all_passed:
            break
        if attempt < MAX_RETRIES:
            fixes = debug_and_fix(report, output_dir, model)
            apply_fixes(fixes, output_dir)

    # 6. Write reproduction report
    write_report(report, output_dir)

    # 7. Save thinking chain for demo display
    save_thinking(thinking_text, output_dir)

    return output_dir
```

**CLI:**
```bash
python -m episim.core.orchestrator --paper <path_or_arxiv_url> [--output-dir output/]
```

Uses `argparse`. Prints progress to stdout at each stage.

---

## Directory Structure

```
episim/                              # repo root
├── CLAUDE.md
├── README.md
├── LICENSE
├── requirements.txt                 # project dependencies
├── setup.py
│
├── docs/
│   ├── hld.md                       # this document
│   └── (future: lld, api-reference)
│
├── episim/                          # Python package
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── paper_loader.py
│   │   ├── context_builder.py
│   │   └── model_spec.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── reader.py
│   │   ├── builder.py
│   │   ├── validator.py
│   │   └── debugger.py
│   └── knowledge/
│       ├── base_models.md
│       ├── parameters.md
│       └── solver_guide.md
│
├── output/                          # generated simulators (gitignored)
│   └── {paper_name}/
│       ├── model.py
│       ├── solver.py
│       ├── app.py
│       ├── config.json
│       ├── reproduction_report.md
│       └── requirements.txt
│
└── tests/
    ├── __init__.py
    ├── test_paper_loader.py
    ├── test_model_spec.py
    ├── test_sir_basic.py
    ├── test_seir_basic.py
    └── test_pipeline.py
```

---

## API Configuration

| Agent | Model | Thinking | Thinking Budget | Max Output Tokens | Output Method |
|-------|-------|----------|----------------|-------------------|---------------|
| Reader | `claude-opus-4-6` | enabled | 32768 | 16384 | tool_use (EpidemicModel schema) |
| Builder | `claude-opus-4-6` | optional | 16384 | 32768 | tool_use (GeneratedFiles schema) |
| Debugger | `claude-opus-4-6` | enabled | 16384 | 16384 | tool_use (file patches) |
| Report writer | `claude-opus-4-6` | disabled | — | 4096 | plain text |

All agents use the `anthropic` Python SDK directly. No Agent SDK needed — this is a pipeline (one prompt → one response per agent), not a conversational system.

---

## Generated Code Interface Contracts

These contracts are critical. ALL generated code MUST follow these interfaces so the Validator can work generically.

**model.py:**
```python
COMPARTMENTS: list[str] = ["S", "E", "I", "R"]  # ordered

def derivatives(t: float, y: list[float], params: dict) -> list[float]:
    """ODE system. y order matches COMPARTMENTS."""
    ...
```

**solver.py:**
```python
def run_simulation(params: dict, y0: list[float], t_span: tuple[float, float],
                   num_points: int = 1000) -> dict[str, np.ndarray]:
    """Returns {"t": array, "S": array, "I": array, ...}"""
    ...
```

**config.json:**
```json
{
  "parameters": {"beta": 0.3, "gamma": 0.1, ...},
  "initial_conditions": {"S": 999900, "I": 100, ...},
  "population": 1000000,
  "simulation_days": 365,
  "compartments": ["S", "E", "I", "R"]
}
```

**app.py:** Streamlit app. No specific API contract needed — it's the end-user interface.

---

## Validation Metrics Computation

Standard metrics the Validator can compute from simulation output:

| Metric | Computation | Requires |
|--------|------------|----------|
| `peak_day` | `t[argmax(results["I"])]` | Infected compartment (or specified compartment) |
| `peak_cases` | `max(results["I"])` | Infected compartment |
| `R0` | `beta / gamma` (SIR/SEIR) or `beta * sigma / (gamma * (sigma + mu))` | Parameter values |
| `attack_rate` | `1 - results["S"][-1] / N` | Susceptible compartment, population |
| `epidemic_duration` | Days where `I > threshold` | Infected compartment |
| `final_recovered` | `results["R"][-1]` | Recovered compartment |

For non-standard metrics, the Validator reads the `metric` string from `ExpectedResult` and attempts to compute it. If unrecognized, it flags it in the report as "unable to validate."

---

## Build Order (Implementation Sequence)

Each step depends on the previous. Implement in this order:

| # | Component | Dependencies | Est. Complexity |
|---|-----------|-------------|-----------------|
| 1 | `model_spec.py` | None | Low — Pydantic classes |
| 2 | `paper_loader.py` | PyMuPDF | Low — PDF text extraction |
| 3 | Knowledge base files | Domain knowledge | Medium — curate reference content |
| 4 | `context_builder.py` | paper_loader, knowledge files | Low — string assembly |
| 5 | `reader.py` | model_spec, Anthropic SDK | Medium — prompt engineering |
| 6 | `builder.py` | model_spec, Anthropic SDK | Medium — prompt engineering |
| 7 | `validator.py` | model_spec, subprocess | Medium — metric computation |
| 8 | `debugger.py` | model_spec, Anthropic SDK | Low — similar pattern to reader |
| 9 | `orchestrator.py` | All above | Low — glue code |
| 10 | Tests | All above | Medium |

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Schema library | Pydantic v2 | JSON schema generation for tool_use, validation, serialization |
| Structured output | tool_use (not JSON mode) | Enforces exact schema compliance |
| Code generation | Single API call, all files | 128K output capacity; ensures cross-file consistency |
| Code execution | subprocess | Isolates generated code; catches crashes safely |
| ODE solver | scipy `solve_ivp` with RK45 | Industry standard, reliable for stiff and non-stiff systems |
| Web framework | Streamlit | Fastest path to interactive sliders + plots |
| Charts | Plotly | Interactive (hover, zoom, pan) — better demo than matplotlib |
| API approach | Raw `anthropic` SDK | Pipeline pattern (not conversational); no Agent SDK overhead |
| Max debug retries | 3 | Prevents infinite loops; enough for most fixable issues |
| Validation tolerance | 5% | Accounts for numerical precision + rounding in papers |

---

## Constraints

- **Python 3.11+** required
- **ANTHROPIC_API_KEY** must be set in environment
- Generated simulators are self-contained — each `output/{paper}/` directory runs independently
- No database. No external services. All state is files.
- Knowledge base files are static reference material, not generated

## Anti-Patterns to Avoid

- Do NOT make agents conversational (multi-turn). Each agent: one prompt → one response.
- Do NOT use `exec()` to run generated code. Always subprocess.
- Do NOT hardcode disease-specific logic. The pipeline must be generic.
- Do NOT over-engineer error handling. Fail fast with clear messages.
- Do NOT generate README.md or documentation files in the output — focus on working code + reproduction report.
- Do NOT use templates/Jinja for code generation — let Claude generate complete files for demo credibility.

---

## Dependencies

```
anthropic>=0.50.0
pymupdf>=1.24.0
pydantic>=2.0
scipy>=1.12.0
numpy>=1.26.0
streamlit>=1.35.0
plotly>=5.20.0
pytest>=8.0.0
```
