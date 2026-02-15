# EpiSim — Complete Project Specification

## Hackathon: Built with Opus 4.6 (Feb 10–16, 2026)
## Problem Statement: PS2 — Break the Barriers

---

## 1. THE PROBLEM

### What We're Solving

**The research-to-response gap in epidemic modeling costs lives.**

During every disease outbreak, a critical race begins: researchers publish mathematical models predicting how the disease will spread and what interventions will work. Public health officials need these models to make policy decisions — when to lockdown, who to vaccinate first, how to allocate hospital beds.

But there's a fatal bottleneck: **turning a research paper into a usable tool takes weeks or months of expert work.** By the time a model is implemented, the policy window has closed.

### The Evidence

- During COVID-19, "decisions often had to be made before data and models matured" — there was no way to rapidly deploy new models as the science evolved (Health Affairs, 2023)
- "Errors in model coding or internal logic" were identified as a key factor in modeling failures (NCBI, 2024)
- "Prior to COVID-19, there was little readiness for global health systems, and many science-policy networks were assembled ad-hoc" (PLOS Global Public Health, 2025)
- "There is still no international guidance or standard of practice on how modelled evidence should guide policy during major health crises"
- At the local level, "policies informed by state or county data were insufficient and/or inefficient for disease mitigation"

### Who Suffers

1. **Public health officials** in developing countries who lack epidemiologists on staff but desperately need disease models for resource allocation
2. **Policymakers** who need to make intervention decisions (lockdowns, vaccination campaigns, travel restrictions) but can't access or run the latest models
3. **Researchers** who publish models but see them sit unused because there's no pipeline to deployment
4. **The public** — who bear the consequences of delayed, uninformed policy decisions during outbreaks

### What's Locked Behind Expertise

Implementing an epidemic model from a paper requires:
- Differential equations knowledge (ODEs/PDEs)
- Python/R programming ability
- Numerical methods understanding (ODE solvers, parameter fitting)
- Epidemiological domain knowledge (compartmental models, reproduction numbers, contact matrices)
- Visualization skills (epidemic curves, phase portraits)

A public health official in rural Kenya, a hospital administrator in rural India, a mayor in a small Brazilian city — none have these skills. But they ALL need these models during an outbreak.

### The Gap in Numbers

- Thousands of epidemic modeling papers published annually
- Average time to implement a published model: 2-6 weeks (for an expert)
- Number of countries with >10 trained epidemic modelers: ~30 (out of 195)
- Result: The vast majority of the world has no capacity to rapidly deploy published epidemic models

---

## 2. OUR SOLUTION

### EpiSim: From Disease Modeling Paper to Interactive Public Health Simulator

**Input:** A published epidemic modeling paper (PDF or arxiv link)

**Output:** A fully functional, interactive web-based epidemic simulator with:
- Working implementation of the paper's mathematical model
- Parameter sliders for real-time exploration of intervention scenarios
- Visual epidemic curves matching the paper's reported results
- A validated reproduction report comparing our output against the paper's claims

### The Core Idea

EpiSim uses Opus 4.6's 1M token context window to ingest an epidemic modeling paper along with all necessary context (referenced models, WHO guidelines, demographic data). It uses extended thinking to deeply reason through the mathematical model — understanding compartments, transitions, parameters, and dynamics. Then it generates a complete, validated, interactive simulator that any public health official can use without writing a single line of code.

### What Makes This Different From "Just Asking Claude to Code It"

1. **Automated end-to-end pipeline** — Not a chatbot conversation. A structured multi-agent system that reliably produces working simulators.
2. **Validated reproduction** — We don't just generate code. We RUN it and VERIFY that results match the paper's reported outcomes.
3. **Interactive output** — Not a Python script. A web-based tool with sliders, plots, and real-time feedback that non-programmers can use.
4. **Contextual understanding** — 1M context window means we feed the paper alongside referenced models, parameter databases, and domain knowledge. The AI understands the FULL context, not just isolated equations.
5. **Iterative debugging** — If initial code doesn't reproduce the paper's results, a debugger agent analyzes the discrepancy and fixes it.

---

## 3. HOW WE'RE SOLVING IT

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    1M TOKEN CONTEXT WINDOW                    │
│                                                              │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Target   │  │  Referenced  │  │  Domain Knowledge      │ │
│  │  Paper    │  │  Base Models │  │  - SIR/SEIR/SIS basics │ │
│  │  (PDF)    │  │  (from refs) │  │  - ODE solving methods │ │
│  │           │  │              │  │  - WHO parameter DBs   │ │
│  └──────────┘  └──────────────┘  └────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │    AGENT 1: READER     │
              │    (Extended Thinking)  │
              │                        │
              │  Extracts:             │
              │  • Model type (SIR,    │
              │    SEIR, SEIRS, etc.)  │
              │  • Compartments &      │
              │    transitions         │
              │  • ODE system          │
              │  • Parameters + values │
              │  • Initial conditions  │
              │  • Key figures/tables  │
              │    to reproduce        │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   AGENT 2: BUILDER     │
              │                        │
              │  Generates:            │
              │  • ODE system in       │
              │    Python (scipy)      │
              │  • Parameter config    │
              │  • Streamlit app with  │
              │    interactive sliders │
              │  • Plotting code       │
              │    (matplotlib/plotly) │
              │  • requirements.txt    │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  AGENT 3: VALIDATOR    │
              │                        │
              │  Actions:              │
              │  • Runs the generated  │
              │    simulator           │
              │  • Compares outputs    │
              │    against paper's     │
              │    reported results    │
              │  • Generates           │
              │    reproduction report │
              │                        │
              │  If mismatch > 5%:     │
              │  → Debugger sub-agent  │
              │    analyzes error      │
              │  → Fixes code          │
              │  → Re-validates        │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │       OUTPUTS          │
              │                        │
              │  1. Interactive        │
              │     Streamlit App      │
              │     (with sliders)     │
              │                        │
              │  2. Reproduction       │
              │     Report             │
              │     (paper vs. ours)   │
              │                        │
              │  3. Complete source    │
              │     code repository    │
              └────────────────────────┘
```

### Agent Details

#### Agent 1: Reader (The Epidemiologist)
**Role:** Read the paper with the depth of a trained epidemiologist.
**Uses:** Extended thinking to reason through mathematical models.

**Extraction targets:**
```
{
  "model_type": "SEIR with vaccination",
  "compartments": ["S", "E", "I", "R", "V"],
  "transitions": [
    {"from": "S", "to": "E", "rate": "β*S*I/N"},
    {"from": "S", "to": "V", "rate": "ν*S"},
    {"from": "E", "to": "I", "rate": "σ*E"},
    {"from": "I", "to": "R", "rate": "γ*I"},
    ...
  ],
  "parameters": {
    "β": {"value": 0.3, "description": "transmission rate"},
    "σ": {"value": 0.2, "description": "incubation rate (1/5 days)"},
    "γ": {"value": 0.1, "description": "recovery rate (1/10 days)"},
    "ν": {"value": 0.01, "description": "vaccination rate"},
    ...
  },
  "initial_conditions": {
    "N": 1000000,
    "I0": 100,
    "E0": 50,
    ...
  },
  "simulation_period": 365,
  "key_results": [
    {"figure": "Figure 3", "description": "Infection curve peaks at day 47 with ~15,000 active cases"},
    {"table": "Table 2", "description": "R0 = 2.8, final attack rate = 62%"},
    ...
  ]
}
```

**Why extended thinking is essential here:**
- Papers don't always state equations cleanly — they may describe transitions in prose
- Parameters might be stated across multiple sections (methods, supplementary, results)
- Some transitions involve complex functions (saturation terms, age-dependent rates)
- The AI needs to REASON about what the model is doing, not just pattern-match

#### Agent 2: Builder (The Engineer)
**Role:** Turn the extracted model specification into a working interactive application.

**Generates a complete project:**
```
episim_output/
├── model.py           # ODE system definition
├── solver.py          # scipy.integrate wrapper
├── app.py             # Streamlit interactive UI
├── plots.py           # Visualization functions
├── config.json        # Parameters and initial conditions
├── requirements.txt   # Dependencies
└── README.md          # Auto-generated documentation
```

**Key design decisions:**
- Uses `scipy.integrate.solve_ivp` for ODE solving (industry standard, reliable)
- Streamlit for interactive UI (fastest path to sliders + plots)
- Plotly for interactive charts (hover, zoom, pan)
- All parameters exposed as sliders with paper's values as defaults
- Range bounds for sliders: 0.1x to 10x of paper's parameter values

#### Agent 3: Validator (The Referee)
**Role:** Ensure the generated simulator actually reproduces the paper's results.

**Validation process:**
1. Run simulator with paper's exact parameters
2. Extract key metrics (peak timing, peak height, R0, final size, etc.)
3. Compare each metric against paper's reported values
4. Calculate reproduction accuracy (% match)
5. If any metric deviates >5%: trigger debugger sub-agent
6. Generate reproduction report

**Reproduction Report format:**
```
╔══════════════════════════════════════════════════╗
║           EPISIM REPRODUCTION REPORT             ║
╠══════════════════════════════════════════════════╣
║ Paper: "SEIR Model with Vaccination for         ║
║         Dengue Outbreak Response"                ║
║ Authors: Smith et al. (2024)                     ║
║ Source: arxiv.org/abs/2024.XXXXX                 ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║ MODEL EXTRACTION                                 ║
║ ├─ Type: SEIR + Vaccination (5 compartments) ✓   ║
║ ├─ Parameters: 7/7 extracted                 ✓   ║
║ ├─ Initial conditions: 4/4 extracted         ✓   ║
║ └─ ODE system: 5 equations                  ✓   ║
║                                                  ║
║ VALIDATION RESULTS                               ║
║ ┌──────────────┬────────┬────────┬───────────┐   ║
║ │ Metric       │ Paper  │  Ours  │  Match    │   ║
║ ├──────────────┼────────┼────────┼───────────┤   ║
║ │ Peak day     │  47    │  46    │  97.9% ✓  │   ║
║ │ Peak cases   │ 14,820 │ 14,755 │  99.6% ✓  │   ║
║ │ R0           │  2.80  │  2.79  │  99.6% ✓  │   ║
║ │ Attack rate  │ 62.0%  │ 61.8%  │  99.7% ✓  │   ║
║ │ Vacc. impact │ -43%   │ -42.5% │  98.8% ✓  │   ║
║ └──────────────┴────────┴────────┴───────────┘   ║
║                                                  ║
║ OVERALL: 5/5 metrics reproduced within 3%    ✓   ║
║ VERDICT: PAPER CLAIMS FULLY VALIDATED            ║
╚══════════════════════════════════════════════════╝
```

### Why Each Opus 4.6 Capability Is Essential

| Capability | How EpiSim Uses It | Why It's Essential |
|------------|-------------------|-------------------|
| **1M token context** | Paper (20-40 pages) + referenced base models (SIR, SEIR, SIS formulations) + WHO parameter guidelines + demographic data + solver documentation | Models reference other models. Parameters reference databases. Without full context, extraction fails. A 70K-token model would miss critical cross-references. |
| **Extended thinking** | Agent 1 uses extended thinking to reason through complex model dynamics: "This paper extends SEIR by adding a hospitalization compartment with age-dependent rates... I need to decompose the contact matrix..." | Epidemic models aren't just equations — they're interconnected systems with implicit assumptions. Extended thinking lets the AI REASON about model behavior, not just transcribe equations. |
| **128K output** | Complete Streamlit application + model code + solver + plotting + config + README + reproduction report — all generated in a single comprehensive output | A complete working application requires thousands of lines across multiple files. 128K output means we generate the ENTIRE project in one coherent pass. |

---

## 4. DEMO PLAN

### Demo Video Script (2 minutes)

#### Opening (0:00–0:15)
**Visual:** Split screen — left: epidemic curve from a real outbreak. Right: a research paper PDF.
**Voiceover:**
"In 2020, scientists published life-saving epidemic models. But turning a paper into a tool policymakers could use took weeks. By then, the policy window had closed. EpiSim changes that."

#### The Feed (0:15–0:30)
**Visual:** EpiSim interface. User pastes an arxiv link to a real SEIR paper with vaccination dynamics.
**Voiceover:**
"Feed any epidemic modeling paper to EpiSim."
**On screen:** Paper ingesting — show the 1M context loading: paper + referenced models + WHO parameters.

#### The Read (0:30–0:55)
**Visual:** Extended thinking output scrolling — showing Opus 4.6 reasoning through the model:
```
"I identify a 5-compartment SEIR model with vaccination...
The transmission rate β = 0.3 per day implies R0 ≈ 3.0...
Vaccination reduces susceptible population at rate ν...
Age-structured contact matrix from Mossong et al. (2008)...
I need to implement this as a system of 5 coupled ODEs..."
```
**Voiceover:**
"Opus 4.6 reads the paper like an epidemiologist — understanding not just the equations, but the dynamics."

#### The Build (0:55–1:10)
**Visual:** Code generation — model.py, solver.py, app.py appearing. Then the Streamlit app launching.
**Voiceover:**
"It generates a complete interactive simulator — ready to use."

#### THE MOMENT (1:10–1:35)
**Visual:** Interactive Streamlit app running. Epidemic curves matching the paper's Figure 3.
**Action sequence:**
1. Show default parameters → curves match paper exactly
2. **DRAG the vaccination slider from 30% to 80%** → hospitalization curve drops dramatically
3. **DRAG the lockdown timing slider** → show how early intervention flattens the curve
4. Show reproduction report: "5/5 metrics validated within 3%"

**Voiceover:**
"Every parameter is a slider. Drag vaccination from 30% to 80% — hospitalizations drop 60%. This is what policymakers needed in real-time."

#### The Close (1:35–2:00)
**Visual:** Side-by-side: Paper's Figure 3 | EpiSim's output. They match.
**Voiceover:**
"EpiSim validated every claim in this paper in under 3 minutes. No epidemiology degree required. No programming. Just a paper and a question: what if?"

**Final text on screen:**
```
EpiSim
From paper to pandemic preparedness in minutes.
Because the next outbreak won't wait for someone to read the manual.
```

### Live Demo Plan (Round 2)
If we make top 6, we'll demo live:
1. Feed a paper the judges haven't seen before (prepared but not rehearsed)
2. Show extended thinking processing it in real-time
3. Launch the interactive simulator
4. Let a JUDGE drag the sliders themselves
5. Show the reproduction report validating against the paper

---

## 5. TECHNICAL SPECIFICATION

### Tech Stack
```
Language:       Python 3.11+
AI:             Anthropic API (Opus 4.6) / Claude Agent SDK
ODE Solving:    scipy.integrate.solve_ivp
Web UI:         Streamlit
Plotting:       Plotly (interactive charts)
Math:           NumPy, SciPy
PDF Parsing:    PyMuPDF (fitz) for PDF text extraction
Config:         JSON for model specifications
Testing:        pytest for validation pipeline
```

### Project Structure
```
episim/
├── README.md
├── requirements.txt
├── setup.py
│
├── agents/
│   ├── reader.py          # Agent 1: Paper analysis + model extraction
│   ├── builder.py         # Agent 2: Code generation
│   ├── validator.py       # Agent 3: Execution + validation
│   └── debugger.py        # Sub-agent: Fix discrepancies
│
├── core/
│   ├── paper_loader.py    # PDF/arxiv ingestion
│   ├── context_builder.py # Assemble 1M context (paper + refs + knowledge)
│   ├── model_spec.py      # Structured model specification (dataclass)
│   └── orchestrator.py    # Pipeline coordination
│
├── knowledge/
│   ├── base_models.md     # SIR, SEIR, SEIRS, SIS reference formulations
│   ├── parameters.md      # Common epidemiological parameter ranges
│   └── solver_guide.md    # scipy.integrate best practices
│
├── templates/
│   ├── streamlit_app.py   # Template for generated Streamlit apps
│   └── model_template.py  # Template for ODE systems
│
├── output/                # Generated simulators go here
│   └── {paper_name}/
│       ├── model.py
│       ├── solver.py
│       ├── app.py
│       ├── config.json
│       ├── reproduction_report.md
│       └── requirements.txt
│
└── tests/
    ├── test_sir_basic.py      # Validate on known SIR solution
    ├── test_seir_basic.py     # Validate on known SEIR solution
    └── test_pipeline.py       # End-to-end pipeline test
```

### Key Implementation Details

#### Context Assembly (1M tokens)
```python
context = f"""
# TARGET PAPER
{paper_full_text}

# REFERENCED BASE MODELS
{sir_model_reference}
{seir_model_reference}
{seirs_model_reference}

# EPIDEMIOLOGICAL PARAMETER DATABASE
{who_parameter_ranges}
{common_disease_parameters}

# ODE SOLVER DOCUMENTATION
{scipy_solve_ivp_docs}
{numerical_stability_guide}

# STREAMLIT COMPONENT REFERENCE
{streamlit_slider_docs}
{plotly_chart_docs}

# VALIDATION CRITERIA
{validation_methodology}
"""
```

#### Model Specification Schema
```python
@dataclass
class EpidemicModel:
    name: str                           # "SEIR with Vaccination"
    compartments: List[str]             # ["S", "E", "I", "R", "V"]
    parameters: Dict[str, Parameter]    # {"beta": Parameter(value=0.3, ...)}
    initial_conditions: Dict[str, float]
    ode_system: str                     # Python code for dY/dt
    simulation_days: int
    key_results: List[ExpectedResult]   # What the paper reports

@dataclass
class Parameter:
    value: float
    description: str
    unit: str
    slider_min: float       # 0.1x of value
    slider_max: float       # 10x of value

@dataclass
class ExpectedResult:
    metric: str             # "peak_day"
    value: float            # 47
    source: str             # "Figure 3" or "Table 2"
    tolerance: float        # 0.05 (5%)
```

---

## 6. DEMO PAPERS (Pre-selected for reliability)

### Primary Demo Paper
**Target:** A clean, well-structured SEIR paper with:
- Clear ODE system stated explicitly
- All parameters listed in a table
- Epidemic curves as key results
- Vaccination or intervention component (for slider demo)
- Open access on arxiv

**Candidate:** "Multi-feature SEIR model for epidemic analysis and vaccine prioritization" (PLOS ONE, 2024)
- Open access ✓
- Code available on GitHub (for validation) ✓
- Clear SEIR + vaccination model ✓
- Standard parameters ✓
- Multiple result figures ✓

### Backup Demo Papers
1. "Optimal Control of an Epidemic with Intervention Design" (arxiv, 2025) — includes intervention optimization
2. "SEIR Model with Mass Vaccination" (arxiv, 2025) — clean vaccination dynamics
3. Classic SIR with known analytical solution — for guaranteed validation

### Validation Strategy
Before the demo, we:
1. Manually verify that our pipeline works on these specific papers
2. Know the exact expected outputs
3. Have the paper's figures ready for side-by-side comparison
4. But also prepare to demo on a FRESH paper for Round 2 (shows generalizability)

---

## 7. JUDGING CRITERIA ALIGNMENT

### Demo (30%) — Score: 10/10
- **Interactive Streamlit app with real-time sliders** — most engaging demo format possible
- **Visual epidemic curves** — universally understood post-COVID
- **THE MOMENT:** Dragging vaccination slider and watching curves respond — visceral, immediate
- **Side-by-side validation:** Paper's Figure 3 vs. our output — undeniable proof
- **Story arc:** Problem → Solution → Live demo → Validation → Impact

### Opus 4.6 Use (25%) — Score: 9.5/10
- **1M context:** Paper + ALL referenced models + WHO data + solver docs + domain knowledge
  - Without 1M context, the AI can't understand the full model in its research context
  - This is IMPOSSIBLE with smaller context models (Paper2Code limited to 70K)
- **Extended thinking:** Deep mathematical reasoning about ODE systems, parameter relationships, model dynamics
  - Visible in the demo — shows the AI "thinking like an epidemiologist"
  - This is the "Most Creative Opus 4.6 Exploration" angle
- **128K output:** Complete multi-file application generated in one coherent pass
  - model.py + solver.py + app.py + config.json + report = needs extensive output

### Impact (25%) — Score: 10/10
- **Who benefits:** Public health officials in 165+ countries with limited modeling capacity
- **Scale of problem:** Pandemic preparedness affects 8 billion people
- **Documented need:** COVID exposed the research-to-response gap as a life-or-death issue
- **Could become a product:** WHO, CDC, national health agencies would use this
- **PS2 perfect fit:** Epidemic modeling expertise locked behind math + programming → accessible to anyone

### Depth & Execution (20%) — Score: 9/10
- **Multi-agent architecture:** Reader → Builder → Validator with feedback loop
- **Structured extraction:** Not just "summarize this paper" but precise mathematical model extraction
- **Validation loop:** Iterative debugging until results match — shows engineering rigor
- **Interactive output:** Going beyond code generation to a usable APPLICATION
- **"Keep Thinking" prize angle:** Document iteration from simple SIR → complex SEIR → age-structured → validated

---

## 8. BUILD TIMELINE

### Day 1 (Feb 12): Foundation
**Morning:**
- [ ] Set up project structure
- [ ] Implement paper_loader.py (PDF → text extraction)
- [ ] Create knowledge base (base_models.md, parameters.md, solver_guide.md)
- [ ] Build context_builder.py (assemble 1M context)

**Afternoon:**
- [ ] Implement Agent 1 (Reader) — paper analysis with extended thinking
- [ ] Define model_spec.py schema
- [ ] Test Reader on a simple SIR paper → verify correct extraction

### Day 2 (Feb 13): Core Pipeline
**Morning:**
- [ ] Implement Agent 2 (Builder) — code generation from model spec
- [ ] Create Streamlit app template with parameter sliders
- [ ] Generate first working simulator from a real paper

**Afternoon:**
- [ ] Implement Agent 3 (Validator) — execution + comparison
- [ ] Build reproduction report generation
- [ ] End-to-end test: paper → simulator → validation

### Day 3 (Feb 14): Polish & Edge Cases
**Morning:**
- [ ] Add debugger sub-agent for handling validation failures
- [ ] Test on 3 different papers (simple SIR, medium SEIR, complex SEIR+vaccination)
- [ ] Handle edge cases: missing parameters, unclear equations, supplementary materials

**Afternoon:**
- [ ] Polish Streamlit UI (layout, colors, labels, responsiveness)
- [ ] Add reproduction report visual display in the app
- [ ] Make the extended thinking output visible and beautiful in demo

### Day 4 (Feb 15): Demo & Submission
**Morning:**
- [ ] Record demo video (multiple takes, pick best)
- [ ] Write README with clear project description
- [ ] Prepare GitHub repo (clean code, good documentation)

**Afternoon:**
- [ ] Final testing on demo papers
- [ ] Prepare for potential live demo (Round 2)
- [ ] Submit by 3 PM ET deadline (Feb 16)
- [ ] Write project description for submission form

---

## 9. SPECIAL PRIZE STRATEGY

### "Most Creative Opus 4.6 Exploration" ($5K)
**Angle:** Using extended thinking to reason through mathematical epidemiological models is a capability nobody has explored. The visible thinking chain — watching Opus 4.6 reason through compartmental dynamics, derive R0, and understand parameter sensitivities — teaches the judges something new about what this model can do.

**Highlight in submission:** "We discovered that Opus 4.6's extended thinking can reason through systems of differential equations with epidemiological semantics — not just solving math, but understanding what the math MEANS for disease dynamics."

### "Keep Thinking Prize" ($5K)
**Angle:** Document the iteration journey:
- v0.1: Simple string extraction → unreliable
- v0.2: Structured extraction with schema → better but misses implicit parameters
- v0.3: Extended thinking for deep reasoning → breakthrough in extraction accuracy
- v0.4: Added validation loop → caught errors that v0.3 missed
- v0.5: Interactive Streamlit output → transformed from tool to application

Show the evolution in the submission video: "We didn't stop at our first idea."

---

## 10. RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Model extraction fails on complex papers | Medium | High | Start with simple SIR/SEIR papers. Build complexity incrementally. Have 3 pre-tested demo papers. |
| Generated code doesn't run | Low | High | Validator agent catches this. Debugger agent fixes. Template-based generation reduces error rate. |
| Validation numbers don't match paper | Low | Medium | ODE solutions are deterministic — if equations + parameters are correct, results MUST match. Mismatch means extraction error → debugger fixes. |
| COVID framing feels insensitive | Low | Medium | Use dengue, malaria, or influenza papers for demo. Frame as "pandemic preparedness" not "COVID retrospective." |
| Similar project from another team | Very Low | High | Nobody else will build paper→epidemic-simulator. The domain expertise required is a natural moat. |
| API rate limits / credit usage | Medium | Medium | Pre-cache context assembly. Minimize API calls during demo. Use $500 credits strategically. |
| Streamlit deployment issues in demo | Low | High | Run locally. Pre-launch the app. Have a recorded backup demo. |

---

## 11. SUBMISSION CHECKLIST

- [ ] GitHub repo (public, open source)
  - [ ] Clean code with clear structure
  - [ ] README with project description, setup instructions, screenshots
  - [ ] LICENSE (MIT)
  - [ ] requirements.txt
  - [ ] Example output (pre-generated simulator for one paper)

- [ ] Demo video (≤3 minutes)
  - [ ] Problem statement (15 seconds)
  - [ ] Solution overview (15 seconds)
  - [ ] Live demo with slider interaction (60 seconds)
  - [ ] Validation / reproduction report (20 seconds)
  - [ ] Impact statement (10 seconds)

- [ ] Project description
  - [ ] Problem we're solving
  - [ ] How Opus 4.6 is essential (1M context, extended thinking, 128K output)
  - [ ] Technical approach
  - [ ] Impact and potential
  - [ ] Problem Statement: PS2 — Break the Barriers

---

## 12. ONE-LINE SUMMARY

**EpiSim transforms epidemic modeling research papers into interactive public health simulators using Opus 4.6's 1M context window and extended thinking — putting pandemic preparedness in every public health official's hands, no epidemiology degree required.**
