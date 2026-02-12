"""EpiSim — Main Streamlit application.

Upload a PDF or paste an arxiv URL to generate an interactive epidemic simulator.
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="EpiSim",
    page_icon="🔬",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main .block-container { max-width: 1100px; padding-top: 2rem; }
    .stMetric { background: #f8f9fa; border-radius: 8px; padding: 12px; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("EpiSim")
st.markdown("**Transform epidemic modeling papers into interactive simulators** — powered by Claude Opus 4.6")
st.divider()

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
for key in ("model", "thinking", "report", "output_dir", "pipeline_done"):
    if key not in st.session_state:
        st.session_state[key] = None


# ---------------------------------------------------------------------------
# Sidebar — Paper input
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Paper Input")
    input_method = st.radio("Source", ["arxiv ID / URL", "Upload PDF"], horizontal=True)

    paper_source = None

    if input_method == "arxiv ID / URL":
        arxiv_input = st.text_input(
            "arxiv ID or URL",
            placeholder="e.g. 2003.09861",
        )
        if arxiv_input:
            paper_source = arxiv_input.strip()
    else:
        uploaded = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded:
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.write(uploaded.read())
            tmp.flush()
            paper_source = tmp.name

    st.divider()
    generate = st.button("Generate Simulator", type="primary", disabled=paper_source is None, use_container_width=True)


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------
def run_with_progress(paper_source: str):
    """Run the pipeline with Streamlit progress indicators."""
    from episim.core.paper_loader import load_paper
    from episim.core.context_builder import build_context
    from episim.agents.reader import extract_model
    from episim.agents.builder import generate_simulator
    from episim.agents.validator import validate, write_report
    from episim.agents.debugger import debug_and_fix, apply_fixes

    progress = st.progress(0, text="Loading paper...")

    # 1. Load
    paper_text = load_paper(paper_source)
    progress.progress(15, text="Building context...")

    # 2. Context
    context = build_context(paper_text)
    progress.progress(20, text="Reader agent analyzing paper (this may take a minute)...")

    # 3. Reader
    model, thinking_text = extract_model(context)
    progress.progress(50, text="Builder agent generating simulator...")

    # 4. Builder
    output_dir = Path("output") / model.name.lower().replace(" ", "_")
    generate_simulator(model, output_dir)
    progress.progress(75, text="Validating simulator...")

    # 5. Validate + debug loop
    report = None
    for attempt in range(1, 4):
        report = validate(output_dir, model)
        report.attempts = attempt
        if report.all_passed:
            break
        if attempt < 3:
            progress.progress(75 + attempt * 5, text=f"Debugging (attempt {attempt})...")
            fixes = debug_and_fix(report, output_dir, model)
            apply_fixes(fixes, output_dir)

    write_report(report, output_dir)
    progress.progress(100, text="Done!")

    # Store in session state
    st.session_state.model = model
    st.session_state.thinking = thinking_text
    st.session_state.report = report
    st.session_state.output_dir = str(output_dir)
    st.session_state.pipeline_done = True


if generate and paper_source:
    try:
        run_with_progress(paper_source)
        st.rerun()
    except Exception as e:
        st.error(f"Pipeline failed: {e}")

# ---------------------------------------------------------------------------
# Main content — show results if pipeline has run
# ---------------------------------------------------------------------------
if st.session_state.pipeline_done:
    model = st.session_state.model
    report = st.session_state.report
    output_dir = Path(st.session_state.output_dir)

    st.subheader(f"{model.name} — {model.paper_title}")

    # --- Thinking display ---
    if st.session_state.thinking:
        with st.expander("AI Reasoning (Reader Agent's Extended Thinking)", icon="🧠"):
            st.markdown(st.session_state.thinking)

    st.divider()

    # --- Interactive simulation ---
    st.subheader("Interactive Epidemic Curves")

    # Parameter sliders in sidebar
    with st.sidebar:
        st.divider()
        st.header("Model Parameters")

        if st.button("Reset to Paper Defaults", use_container_width=True):
            st.rerun()

        params = {}
        for pname, pspec in model.parameters.items():
            step = max(abs(pspec.value) * 0.01, 1e-6)
            params[pname] = st.slider(
                f"{pname} — {pspec.description}",
                min_value=float(pspec.slider_min),
                max_value=float(pspec.slider_max),
                value=float(pspec.value),
                step=step,
                format="%.4g",
            )

    # Run simulation with current params
    try:
        import sys
        import subprocess

        # Build a quick inline simulation
        y0 = [model.initial_conditions[c] for c in model.compartments]
        t_span = (0, model.simulation_days)

        # Load model and solver from output dir
        sim_script = (
            f"import sys, json\n"
            f"sys.path.insert(0, '{output_dir}')\n"
            f"from solver import run_simulation\n"
            f"import numpy as np\n"
            f"params = {json.dumps(params)}\n"
            f"y0 = {json.dumps(y0)}\n"
            f"r = run_simulation(params, y0, {t_span})\n"
            f"out = {{'t': r['t'].tolist()}}\n"
            f"for c in {json.dumps(model.compartments)}:\n"
            f"    out[c] = r[c].tolist()\n"
            f"print(json.dumps(out))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", sim_script],
            capture_output=True, text=True, timeout=30,
        )

        if result.returncode != 0:
            st.error(f"Simulation error: {result.stderr[:500]}")
        else:
            results = json.loads(result.stdout)
            t = np.array(results["t"])

            # Plotly chart
            fig = go.Figure()
            colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                       "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
            for i, comp in enumerate(model.compartments):
                fig.add_trace(go.Scatter(
                    x=t, y=np.array(results[comp]),
                    mode="lines",
                    name=comp,
                    line=dict(width=2, color=colors[i % len(colors)]),
                ))
            fig.update_layout(
                xaxis_title="Days",
                yaxis_title="Population",
                hovermode="x unified",
                legend=dict(orientation="h", y=1.12),
                margin=dict(t=40, b=40),
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Key metrics
            infected_comp = next((c for c in model.compartments if c.startswith("I")), model.compartments[1])
            I_arr = np.array(results[infected_comp])
            peak_idx = np.argmax(I_arr)

            col1, col2, col3 = st.columns(3)
            col1.metric("Peak Day", f"{t[peak_idx]:.1f}")
            col2.metric("Peak Cases", f"{I_arr[peak_idx]:,.0f}")
            if "S" in results:
                S_arr = np.array(results["S"])
                col3.metric("Attack Rate", f"{(1 - S_arr[-1] / model.population) * 100:.1f}%")

    except Exception as e:
        st.error(f"Could not run simulation: {e}")

    # --- Reproduction report ---
    if report:
        st.divider()
        st.subheader("Reproduction Report")

        status_color = "green" if report.all_passed else "red"
        st.markdown(f"**Status:** :{status_color}[{'ALL PASSED' if report.all_passed else 'FAILED'}] &nbsp; **Attempts:** {report.attempts}")

        if report.metrics:
            cols = st.columns([2, 2, 2, 2, 1])
            cols[0].markdown("**Metric**")
            cols[1].markdown("**Expected**")
            cols[2].markdown("**Actual**")
            cols[3].markdown("**Deviation**")
            cols[4].markdown("**Status**")

            for m in report.metrics:
                cols = st.columns([2, 2, 2, 2, 1])
                cols[0].write(m.metric)
                cols[1].write(f"{m.expected:.4g}")
                cols[2].write(f"{m.actual:.4g}")
                cols[3].write(f"{m.match_pct:.2f}%")
                cols[4].write("✅" if m.passed else "❌")

        if report.error:
            st.error(report.error)

else:
    # Landing state
    st.markdown("""
### How it works

1. **Upload** a research paper (PDF) or paste an arxiv ID
2. **AI Reader** extracts the mathematical model using extended thinking
3. **AI Builder** generates a complete interactive simulator
4. **Validator** checks the simulator reproduces the paper's results
5. **Explore** the epidemic dynamics with interactive parameter sliders

Built with **Claude Opus 4.6** — 1M context window, extended thinking, 128K output.
""")

    col1, col2, col3 = st.columns(3)
    col1.info("**SIR / SEIR / SEIRS / SIS**\n\nSupports standard and extended compartmental models")
    col2.info("**Interactive Sliders**\n\nExplore parameter sensitivity in real-time")
    col3.info("**Validated Results**\n\nAutomatically checks against paper's reported metrics")
