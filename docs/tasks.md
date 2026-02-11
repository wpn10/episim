# EpiSim — Task Breakdown

Each chapter is a self-contained unit of work. Complete in order — each depends on the previous.

---

## Chapter 1: Project Scaffolding — DONE
**Goal:** Repo structure, dependencies, package init files.

- [x] Create directory tree: `episim/core/`, `episim/agents/`, `tests/`
- [x] Add all `__init__.py` files
- [x] Write `requirements.txt`
- [x] Write `setup.py` with package metadata
- [x] Add `output/` to `.gitignore`
- [x] CLAUDE.md created
- [x] `episim/knowledge/` directory created

**Deliverable:** `pip install -e .` works. `import episim` works. ✓

---

## Chapter 2: Model Spec (Central Schema)
**Goal:** `episim/core/model_spec.py` — the contract between all agents.

- [x] `Parameter` — value, description, unit, slider_min, slider_max
- [x] `ExpectedResult` — metric, value, source, tolerance
- [x] `EpidemicModel` — name, paper_title, compartments, parameters, initial_conditions, ode_system, simulation_days, population, expected_results
- [x] Validation schemas (`MetricResult`, `ValidationReport`, `GeneratedFiles`)
- [x] Test: round-trip JSON serialization, schema generation for tool_use

**Deliverable:** `EpidemicModel.model_json_schema()` returns valid JSON schema.

---

## Chapter 3: Paper Loader
**Goal:** `episim/core/paper_loader.py` — PDF/arxiv → raw text.

- [x] `load_paper(source: str) -> str`
- [x] Local PDF path handling (fitz)
- [x] arxiv URL handling (download + fitz)
- [x] arxiv bare ID handling (e.g. `2401.12345`)
- [x] Header/footer stripping heuristic
- [x] Test with a real PDF

**Deliverable:** `load_paper("path/to/paper.pdf")` returns clean text.

---

## Chapter 4: Knowledge Base
**Goal:** `episim/knowledge/` — static reference files for Reader context.

- [x] `base_models.md` — SIR, SEIR, SEIRS, SIS formulations with ODE systems, compartment definitions, standard parameter names
- [x] `parameters.md` — WHO parameter ranges by disease (COVID, dengue, influenza, malaria, Ebola) with R0 ranges, incubation periods, recovery rates
- [x] `solver_guide.md` — scipy solve_ivp usage, method selection (RK45 vs BDF for stiff), max_step guidance, numerical stability tips

**Deliverable:** Three .md files with concise, accurate epidemiological reference content.

---

## Chapter 5: Context Builder
**Goal:** `episim/core/context_builder.py` — assemble the 1M-token context.

- [ ] `build_context(paper_text: str, knowledge_dir: Path) -> str`
- [ ] XML-tagged assembly: `<paper>`, `<reference_models>`, `<parameter_ranges>`, `<solver_guide>`
- [ ] Read knowledge files from package directory
- [ ] Test: output contains all sections with correct tags

**Deliverable:** `build_context(text)` returns XML-tagged context string.

---

## Chapter 6: Reader Agent
**Goal:** `agents/reader.py` — paper → EpidemicModel via Opus 4.6.

- [ ] `extract_model(context: str) -> tuple[EpidemicModel, str]` (model + thinking text)
- [ ] System prompt: epidemiologist role, extraction instructions, ode_system contract
- [ ] Anthropic API call: extended thinking (32K budget), tool_use with EpidemicModel schema
- [ ] Parse response: extract tool_use input → EpidemicModel, extract thinking blocks → str
- [ ] Error handling: retry once on malformed output
- [ ] Test with a known SIR paper text → verify correct extraction

**Deliverable:** Reader extracts a valid EpidemicModel from a paper's text.

---

## Chapter 7: Builder Agent
**Goal:** `agents/builder.py` — EpidemicModel → generated simulator files.

- [ ] `generate_simulator(model: EpidemicModel, output_dir: Path) -> Path`
- [ ] System prompt: engineer role, file contracts (model.py interface, solver.py interface, app.py requirements)
- [ ] Anthropic API call: tool_use with GeneratedFiles schema, 32K max tokens
- [ ] Write files to output_dir
- [ ] Test: generate from a hardcoded SIR EpidemicModel → verify files exist and are syntactically valid Python

**Deliverable:** Builder produces 5 files that form a runnable Streamlit app.

---

## Chapter 8: Validator
**Goal:** `agents/validator.py` — run generated code, compare metrics.

- [ ] `validate(output_dir: Path, model: EpidemicModel) -> ValidationReport`
- [ ] Generate `_validate.py` script dynamically based on model's expected_results
- [ ] Run via subprocess with 30s timeout
- [ ] Parse JSON output, compute match percentages
- [ ] Generate `reproduction_report.md` via Claude (formatted table)
- [ ] Test: create a known-good SIR simulator in a temp dir → validate → expect all pass

**Deliverable:** Validator runs generated code and produces a pass/fail report.

---

## Chapter 9: Debugger Agent
**Goal:** `agents/debugger.py` — fix validation failures.

- [ ] `debug_and_fix(report: ValidationReport, output_dir: Path, model: EpidemicModel) -> dict[str, str]`
- [ ] System prompt: provide model spec, generated code, validation results, stderr
- [ ] Anthropic API call: extended thinking (16K), tool_use returning file patches
- [ ] `apply_fixes(fixes: dict, output_dir: Path)` — overwrite files
- [ ] Test: intentionally break a working simulator → debugger fixes it

**Deliverable:** Debugger can analyze and patch failing generated code.

---

## Chapter 10: Orchestrator + CLI
**Goal:** `episim/core/orchestrator.py` — wire everything together.

- [ ] `run_pipeline(paper_source: str, output_base: str) -> Path`
- [ ] Sequential flow: load → context → read → build → validate → (debug loop) → report
- [ ] Progress printing to stdout
- [ ] `save_thinking(thinking_text, output_dir)` — save for demo display
- [ ] `argparse` CLI: `python -m episim.core.orchestrator --paper <source>`
- [ ] End-to-end test: real paper → working simulator

**Deliverable:** `python -m episim.core.orchestrator --paper paper.pdf` produces a complete validated simulator.

---

## Chapter 11: Testing & Hardening
**Goal:** Confidence that the pipeline works reliably.

- [ ] `test_model_spec.py` — schema validation, serialization
- [ ] `test_paper_loader.py` — PDF extraction, arxiv handling
- [ ] `test_sir_basic.py` — end-to-end on a classic SIR with known analytical solution
- [ ] `test_seir_basic.py` — end-to-end on a standard SEIR model
- [ ] `test_pipeline.py` — orchestrator integration test
- [ ] Edge cases: missing parameters, unclear equations, subprocess crashes

**Deliverable:** `pytest tests/` passes.

---

## Chapter 12: Main Streamlit App + Demo Polish
**Goal:** Single Streamlit app as the primary interface + demo-ready polish.

**Main app (`episim/app.py` or `app.py` at root):**
- [ ] Upload PDF or paste arxiv URL
- [ ] "Generate Simulator" button triggers `run_pipeline()` in-process
- [ ] Progress indicators for each pipeline stage (loading, reading, building, validating)
- [ ] Display Reader's extended thinking (expandable section — demo highlight)
- [ ] Render interactive epidemic curves with Plotly (sliders for all parameters)
- [ ] Show reproduction report (paper vs. simulator comparison table)
- [ ] "Reset to Paper Defaults" button

**Demo polish:**
- [ ] UI layout, colors, typography
- [ ] Pre-test on 2-3 demo papers (SIR, SEIR, SEIR+vaccination)
- [ ] Record demo video (upload → AI reasoning → slider interaction → validation)
- [ ] Clean up README with screenshots and setup instructions

**Deliverable:** `streamlit run app.py` → complete upload-to-interactive-simulator experience.

---

## Summary

| Ch | What | Files | Blocked By |
|----|------|-------|------------|
| 1 | Scaffolding | dirs, init, requirements | — |
| 2 | Model Spec | `model_spec.py` | 1 |
| 3 | Paper Loader | `paper_loader.py` | 1 |
| 4 | Knowledge Base | `knowledge/*.md` | 1 |
| 5 | Context Builder | `context_builder.py` | 3, 4 |
| 6 | Reader Agent | `reader.py` | 2, 5 |
| 7 | Builder Agent | `builder.py` | 2 |
| 8 | Validator | `validator.py` | 2, 7 |
| 9 | Debugger Agent | `debugger.py` | 2, 8 |
| 10 | Orchestrator | `orchestrator.py` | 6, 7, 8, 9 |
| 11 | Testing | `tests/*.py` | 10 |
| 12 | Demo Polish | UI, video, README | 11 |
