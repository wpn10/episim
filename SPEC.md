# EpiSim — Full Specification

## Vision

A live, paper-to-simulator platform for epidemic modeling research. User uploads a PDF or pastes an arxiv URL through a Streamlit web UI and gets three outputs:

1. **Technical Summary** — structured digest of the paper's model, methodology, and findings
2. **Interactive Simulation** — real-time epidemic curves with parameter sliders
3. **Standalone Code** — downloadable, well-commented Python script that reproduces the paper's model — runnable outside Streamlit, replicating the paper's logic with full documentation

## Target Users

Researchers, epidemiologists, and students who want to quickly understand, interact with, and reproduce epidemic models from papers — without writing code themselves.

## Scope

Epidemic modeling papers only (SIR, SEIR, SIDARTHE, and variants). No general-purpose paper analysis.

## Architecture

```
User (Streamlit UI)
  │
  ├─ Upload PDF / Paste arxiv URL
  │
  ▼
Paper Loader ──► Context Builder ──► Reader Agent (extract EpidemicModel)
                                         │
                                         ├──► Summarizer Agent (paper digest)      [NEW]
                                         │
                                         ├──► Builder Agent (generate simulator)
                                         │       │
                                         │       ▼
                                         │    Validator (run & check metrics)
                                         │       │
                                         │       ▼ (on failure, max 3 retries)
                                         │    Debugger Agent (patch code)
                                         │
                                         └──► Coder Agent (standalone script)      [NEW]
                                                 │
                                                 ▼
                                    Streamlit UI (3 tabs)
                                      ├─ Summary
                                      ├─ Simulation (plots + sliders)
                                      └─ Code (view + download)
```

## Agent Specifications

### Reader Agent (exists)

- **Input:** XML-tagged context (paper text + knowledge base)
- **Output:** `EpidemicModel` Pydantic schema via `tool_use`
- **Model:** Sonnet 4.5 (default), Opus 4.6 for demo
- **Behavior:** Extracts compartments, parameters, ODEs, initial conditions, expected results

### Summarizer Agent (NEW)

- **Input:** Paper text + extracted `EpidemicModel` (so it can reference what was extracted)
- **Output:** `PaperSummary` via `tool_use`
- **Model:** Sonnet 4.5 (lightweight call)
- **Schema:**

```python
class PaperSummary(BaseModel):
    title: str                    # Paper title
    authors: str                  # Author list
    abstract_summary: str         # 2-3 sentence plain-English summary
    model_type: str               # e.g. "SIDARTHE (8-compartment COVID-19 model)"
    key_findings: list[str]       # 3-5 bullet points
    methodology: str              # How the model works, what data it uses
    limitations: str              # What the paper acknowledges as limitations
    public_health_implications: str  # Real-world relevance
```

- **Runs:** After Reader (uses extracted model for grounding)
- **System prompt focus:** Produce a clear, accessible summary that a non-specialist can understand. Reference specific numbers and results from the paper.

### Builder Agent (exists)

- **Input:** `EpidemicModel` JSON
- **Output:** `GeneratedFiles` (model.py, solver.py, app.py, config.json, requirements.txt)
- **Model:** Sonnet 4.5 (default), Opus 4.6 for demo
- **Behavior:** Generates complete runnable Streamlit simulator

### Validator (exists, mostly Python)

- **Input:** Output directory + `EpidemicModel`
- **Output:** `ValidationReport`
- **Behavior:** Generates `_validate.py`, runs via subprocess, compares metrics
- **Rules:**
  - Only uses R0=beta/gamma for standard models (<=4 compartments)
  - Treats "no computable metrics" as pass (prevents wasted debugger calls)
  - 30-second timeout

### Debugger Agent (exists)

- **Input:** `ValidationReport` + generated files + `EpidemicModel`
- **Output:** Patched file contents via `tool_use`
- **Model:** Sonnet 4.5 (default)
- **Behavior:** Triggered only on validation failure. Max 3 retries.

### Coder Agent (NEW)

- **Input:** `EpidemicModel` + paper text (for context on methodology)
- **Output:** `StandaloneScript` via `tool_use`
- **Model:** Sonnet 4.5 (lightweight call)
- **Schema:**

```python
class StandaloneScript(BaseModel):
    filename: str        # e.g. "sidarthe_simulation.py"
    code: str            # Complete standalone Python script
    description: str     # One-line description for the download button
```

- **Runs:** After Builder (can reference validated code)
- **Requirements for generated script:**
  - Single file, runs with `python script.py`
  - Only depends on numpy, scipy, matplotlib (standard scientific Python)
  - Has a docstring explaining the paper, model, and what the script does
  - Inline comments explaining each ODE term and parameter
  - Prints key metrics (R0, peak day, attack rate) to console
  - Generates a matplotlib plot saved as PNG
  - Parameters clearly defined at top for easy modification
  - NOT a copy of the generated simulator — a clean, educational reproduction

## Streamlit UI Specification

### Layout

Three-tab interface after pipeline completes:

```
[Summary] [Simulation] [Code]
```

### Sidebar (always visible)

- Paper input (arxiv ID/URL or PDF upload)
- "Generate Simulator" button
- Parameter sliders (when simulation tab active)

### Tab 1: Summary

- Paper title and authors
- Plain-English abstract summary
- Model type badge (e.g. "SIDARTHE — 8 compartments")
- Key findings (bullet list)
- Methodology section
- Limitations
- Public health implications
- Reproduction report status (PASS/FAIL with metric table)

### Tab 2: Simulation (exists, needs minor updates)

- Interactive Plotly epidemic curves
- Parameter sliders in sidebar
- Key metrics (peak day, peak cases, attack rate)
- Reset to paper defaults button

### Tab 3: Code

- Syntax-highlighted code viewer (st.code)
- Download button for the standalone script
- Brief description of what the script does

### During Pipeline Execution

- Progress bar with descriptive status messages:
  - "Loading paper..."
  - "Analyzing paper structure..."
  - "Extracting epidemic model..."
  - "Generating technical summary..."
  - "Building interactive simulator..."
  - "Validating results..."
  - "Generating standalone code..."
  - "Done!"

## Pipeline Execution Order

```
1. Paper Loader          (no API call)
2. Context Builder       (no API call)
3. Reader Agent          (API call 1)
4. Summarizer Agent      (API call 2) — runs after Reader, uses extracted model
5. Builder Agent         (API call 3)
6. Validator             (no API call — subprocess only)
7. Debugger Agent        (API call 4 — only if validation fails, up to 2 more)
8. Coder Agent           (API call 5) — runs after Builder, uses validated code
```

**Typical cost:** 5 API calls per successful run (Sonnet 4.5).
**Worst case:** 7 API calls (if debugger triggers twice).

## Generated Code Contracts (unchanged)

- **model.py:** `COMPARTMENTS: list[str]` + `def derivatives(t, y, params) -> list[float]`
- **solver.py:** `def run_simulation(params, y0, t_span, num_points=1000) -> dict[str, ndarray]`
- **config.json:** `{"parameters": {...}, "initial_conditions": {...}, "population": N, "simulation_days": D, "compartments": [...]}`

## Model Configuration

| Env Var | Purpose | Default |
|---------|---------|---------|
| `ANTHROPIC_API_KEY` | API authentication | required |
| `EPISIM_MODEL` | Model for all agents | `claude-sonnet-4-5-20250929` |

For demo: `export EPISIM_MODEL=claude-opus-4-6`

## Schema Additions to model_spec.py

```python
class PaperSummary(BaseModel):
    title: str
    authors: str
    abstract_summary: str
    model_type: str
    key_findings: list[str]
    methodology: str
    limitations: str
    public_health_implications: str

class StandaloneScript(BaseModel):
    filename: str
    code: str
    description: str
```

## Implementation Priority

### P0 — Must have (4 hours)
1. Summarizer agent (new)
2. Coder agent (new)
3. Wire both into orchestrator
4. Streamlit UI: 3-tab layout with summary + code download
5. Test full pipeline with SIDARTHE

### P1 — Should have (1.5 hours)
6. Test with 1-2 additional papers
7. Fix any failures
8. Final run on Opus 4.6

### P2 — Nice to have (0.5 hours)
9. Live status updates during pipeline
10. UI styling polish

## Testing Budget

- 35 pipeline runs available
- Development/testing on Sonnet 4.5 (cheap)
- Final 2-3 runs on Opus 4.6 (demo quality)
- Target: use no more than 10 runs for development, save 25 for testing + demo

## File Structure After Implementation

```
episim/
  agents/
    reader.py          (exists)
    summarizer.py      (NEW)
    builder.py         (exists)
    validator.py       (exists)
    debugger.py        (exists)
    coder.py           (NEW)
  core/
    model_spec.py      (add PaperSummary, StandaloneScript)
    orchestrator.py    (wire new agents)
    paper_loader.py    (exists)
    context_builder.py (exists)
  knowledge/           (exists, unchanged)
app.py                 (major update — 3-tab UI)
tests/
  test_summarizer.py   (NEW)
  test_coder.py        (NEW)
  ... (existing tests)
```
