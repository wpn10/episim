"""EpiSim — Main Streamlit application.

Upload a PDF or paste an arxiv URL to generate an interactive epidemic simulator.
Three-tab output: Summary | Simulation | Code.
"""

import json
import subprocess
import sys
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

# ═══════════════════════════════════════════════════════════════════════════
# Fonts
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,500;9..144,700;9..144,900&family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════════
# CSS Design System
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""<style>
/* ── Variables ─────────────────────────────────────────── */
:root {
    --bg: #080810;
    --surface: #0e0e1a;
    --surface-raised: #151528;
    --surface-hover: #1a1a30;
    --border: rgba(255,255,255,0.06);
    --border-accent: rgba(240,180,41,0.2);
    --border-accent-strong: rgba(240,180,41,0.4);
    --primary: #f0b429;
    --primary-dim: #c49020;
    --primary-glow: rgba(240,180,41,0.08);
    --accent: #06d6a0;
    --accent-glow: rgba(6,214,160,0.10);
    --error: #ef476f;
    --error-glow: rgba(239,71,111,0.10);
    --text: #e8e8f0;
    --text-secondary: #8888a8;
    --text-muted: #555570;
    --radius: 12px;
    --radius-sm: 8px;
    --radius-xs: 6px;
    --font-display: 'Fraunces', Georgia, serif;
    --font-body: 'Outfit', -apple-system, sans-serif;
    --font-mono: 'JetBrains Mono', 'Consolas', monospace;
}

/* ── Base Typography ───────────────────────────────────── */
html, body, [class*="css"] {
    font-family: var(--font-body) !important;
}
h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-display) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}
code, pre, [data-testid="stCodeBlock"] * {
    font-family: var(--font-mono) !important;
}

/* ── App Shell ─────────────────────────────────────────── */
.stApp {
    background: var(--bg);
}
[data-testid="stHeader"] {
    background: rgba(8,8,16,0.8) !important;
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
}
.block-container {
    max-width: 1100px !important;
    padding-top: 1.5rem !important;
}

/* ── Sidebar ───────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdown"] h3 {
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text-secondary) !important;
}
[data-testid="stSidebar"] hr {
    border-color: var(--border) !important;
    margin: 1rem 0 !important;
}

/* ── Tabs ──────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: var(--surface);
    border-radius: var(--radius);
    padding: 4px;
    border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm);
    font-family: var(--font-body) !important;
    font-weight: 500;
    font-size: 0.9rem;
    padding: 10px 24px;
    color: var(--text-secondary) !important;
    transition: all 0.2s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--text) !important;
    background: var(--surface-hover);
}
.stTabs [aria-selected="true"] {
    background: var(--surface-raised) !important;
    color: var(--primary) !important;
    font-weight: 600;
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}
.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* ── Metric Cards ──────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 20px 24px !important;
}
[data-testid="stMetric"] label {
    font-family: var(--font-body) !important;
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 500 !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: var(--font-display) !important;
    font-size: 1.8rem !important;
    color: var(--text) !important;
    font-weight: 700 !important;
}

/* ── Expander (Thinking Display) ───────────────────────── */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border-accent) !important;
    border-radius: var(--radius) !important;
}
[data-testid="stExpander"] summary {
    font-family: var(--font-body) !important;
    font-weight: 500;
}
[data-testid="stExpander"] [data-testid="stMarkdown"] {
    font-size: 0.9rem;
    line-height: 1.7;
    color: var(--text-secondary);
}

/* ── Buttons ───────────────────────────────────────────── */
button[kind="primary"],
[data-testid="stBaseButton-primary"] button {
    background: var(--primary) !important;
    color: #080810 !important;
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    letter-spacing: 0.3px;
    transition: all 0.2s ease;
}
button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"] button:hover {
    background: var(--primary-dim) !important;
    box-shadow: 0 0 24px var(--primary-glow);
}
button[kind="secondary"],
[data-testid="stBaseButton-secondary"] button {
    background: var(--surface-raised) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    font-family: var(--font-body) !important;
    font-weight: 500 !important;
    transition: all 0.2s ease;
}
button[kind="secondary"]:hover,
[data-testid="stBaseButton-secondary"] button:hover {
    border-color: var(--border-accent) !important;
    background: var(--surface-hover) !important;
}

/* ── Download Button ───────────────────────────────────── */
[data-testid="stDownloadButton"] button {
    background: var(--primary) !important;
    color: #080810 !important;
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    padding: 12px 24px !important;
    transition: all 0.2s ease;
}
[data-testid="stDownloadButton"] button:hover {
    background: var(--primary-dim) !important;
    box-shadow: 0 4px 20px var(--primary-glow);
}

/* ── Inputs ────────────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background: var(--surface-raised) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: var(--font-body) !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--border-accent-strong) !important;
    box-shadow: 0 0 0 2px var(--primary-glow) !important;
}

/* ── Progress Bar ──────────────────────────────────────── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--primary-dim), var(--primary)) !important;
    border-radius: 4px;
}

/* ── Alerts ────────────────────────────────────────────── */
[data-testid="stAlert"] {
    background: var(--surface) !important;
    border-radius: var(--radius-sm) !important;
}

/* ── Dividers ──────────────────────────────────────────── */
hr {
    border-color: var(--border) !important;
}

/* ── Code Blocks ───────────────────────────────────────── */
[data-testid="stCodeBlock"] {
    border-radius: var(--radius) !important;
}

/* ═══════ CUSTOM COMPONENTS ═══════════════════════════════ */

/* ── Hero ──────────────────────────────────────────────── */
.hero {
    text-align: center;
    padding: 48px 20px 32px;
    animation: fadeIn 0.6s ease-out;
}
.hero-badge {
    display: inline-block;
    font-family: var(--font-body);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 3px;
    color: var(--primary);
    background: var(--primary-glow);
    border: 1px solid var(--border-accent);
    padding: 6px 18px;
    border-radius: 20px;
    margin-bottom: 28px;
    text-transform: uppercase;
}
.hero-title {
    font-family: var(--font-display) !important;
    font-size: 4.2rem;
    font-weight: 900;
    color: var(--text);
    margin: 0 0 12px;
    line-height: 1.05;
    letter-spacing: -0.03em;
}
.hero-accent {
    color: var(--primary);
}
.hero-tagline {
    font-family: var(--font-body);
    font-size: 1.15rem;
    color: var(--text-secondary);
    line-height: 1.6;
    margin-bottom: 40px;
    font-weight: 300;
}

/* ── Pipeline Steps ────────────────────────────────────── */
.pipeline-flow {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 16px;
}
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--font-body);
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    transition: border-color 0.3s ease;
}
.pipeline-step:hover {
    border-color: var(--border-accent);
}
.pipeline-num {
    font-family: var(--font-display);
    font-size: 11px;
    font-weight: 700;
    color: var(--primary);
    background: var(--primary-glow);
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
}
.pipeline-arrow {
    color: var(--text-muted);
    font-size: 14px;
}

/* ── Feature Cards ─────────────────────────────────────── */
.features-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-top: 40px;
}
.feature-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 28px 24px;
    transition: all 0.3s ease;
    animation: fadeInUp 0.5s ease-out backwards;
}
.feature-card:nth-child(1) { animation-delay: 0.15s; }
.feature-card:nth-child(2) { animation-delay: 0.3s; }
.feature-card:nth-child(3) { animation-delay: 0.45s; }
.feature-card:hover {
    border-color: var(--border-accent);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.feature-num {
    font-family: var(--font-display);
    font-size: 2rem;
    font-weight: 900;
    color: var(--primary);
    opacity: 0.7;
    margin-bottom: 12px;
    line-height: 1;
}
.feature-title {
    font-family: var(--font-body);
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 8px;
}
.feature-desc {
    font-family: var(--font-body);
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.6;
    font-weight: 300;
}

/* ── Results Header ────────────────────────────────────── */
.results-header {
    margin-bottom: 8px;
    animation: fadeIn 0.5s ease-out;
}
.model-badge {
    display: inline-block;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 1px;
    color: var(--accent);
    background: var(--accent-glow);
    border: 1px solid rgba(6,214,160,0.2);
    padding: 4px 12px;
    border-radius: 4px;
    margin-bottom: 12px;
    text-transform: uppercase;
}
.model-name {
    font-family: var(--font-display) !important;
    font-size: 2.2rem;
    font-weight: 900;
    color: var(--text);
    margin: 0 0 6px;
    line-height: 1.15;
    letter-spacing: -0.02em;
}
.paper-title {
    font-family: var(--font-body);
    font-size: 1rem;
    color: var(--text-secondary);
    font-weight: 300;
    margin: 0;
}

/* ── Section Cards (Summary Tab) ───────────────────────── */
.section-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    height: 100%;
}
.section-label {
    font-family: var(--font-body);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text-muted);
    margin-bottom: 12px;
}

/* ── Findings List ─────────────────────────────────────── */
.findings-list {
    list-style: none;
    padding: 0;
    margin: 0;
}
.findings-list li {
    padding: 12px 0 12px 20px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    position: relative;
    font-family: var(--font-body);
    font-size: 0.92rem;
    line-height: 1.6;
    font-weight: 300;
}
.findings-list li:last-child {
    border-bottom: none;
}
.findings-list li::before {
    content: '';
    position: absolute;
    left: 0;
    top: 18px;
    width: 6px;
    height: 6px;
    background: var(--primary);
    border-radius: 50%;
}

/* ── Report Table ──────────────────────────────────────── */
.report-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-body);
    margin-top: 12px;
}
.report-table th {
    text-align: left;
    color: var(--text-muted);
    font-weight: 500;
    font-size: 0.72rem;
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
    letter-spacing: 1.5px;
}
.report-table td {
    padding: 14px 16px;
    color: var(--text);
    border-bottom: 1px solid var(--border);
    font-size: 0.9rem;
}
.report-table tr:last-child td {
    border-bottom: none;
}
.metric-name {
    font-weight: 500;
}
.metric-val {
    font-family: var(--font-mono);
    font-size: 0.85rem;
}
.status-badge {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 4px;
    letter-spacing: 0.5px;
}
.status-badge.pass {
    background: var(--accent-glow);
    color: var(--accent);
    border: 1px solid rgba(6,214,160,0.2);
}
.status-badge.fail {
    background: var(--error-glow);
    color: var(--error);
    border: 1px solid rgba(239,71,111,0.2);
}

/* ── Report Status ─────────────────────────────────────── */
.report-status {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
}
.attempts-label {
    font-family: var(--font-body);
    font-size: 0.85rem;
    color: var(--text-muted);
}

/* ── Model Type Badge (Summary Tab) ────────────────────── */
.model-type-badge {
    display: inline-block;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 500;
    color: var(--primary);
    background: var(--primary-glow);
    border: 1px solid var(--border-accent);
    padding: 6px 14px;
    border-radius: var(--radius-xs);
    margin: 8px 0 20px;
}

/* ── Powered By ────────────────────────────────────────── */
.powered-by {
    text-align: center;
    margin-top: 48px;
    padding-top: 24px;
    border-top: 1px solid var(--border);
}
.powered-label {
    font-family: var(--font-body);
    font-size: 0.8rem;
    color: var(--text-muted);
    font-weight: 300;
}
.powered-model {
    color: var(--primary);
    font-weight: 500;
}

/* ═══════ ANIMATIONS ══════════════════════════════════════ */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes pulseGlow {
    0%, 100% { border-color: var(--border-accent); }
    50% { border-color: var(--border-accent-strong); }
}

/* ── Thinking Pulse ────────────────────────────────────── */
.thinking-container [data-testid="stExpander"] {
    animation: pulseGlow 3s ease-in-out infinite;
}

/* ── Live Thinking Console ─────────────────────────────── */
.thinking-live-container {
    border: 1px solid rgba(6,214,160,0.2);
    border-radius: var(--radius);
    overflow: hidden;
    margin: 12px 0 20px;
}
.thinking-live-header {
    background: rgba(6,214,160,0.04);
    padding: 10px 20px;
    font-family: var(--font-body);
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 2px;
    color: var(--accent);
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid rgba(6,214,160,0.1);
}
.thinking-dot {
    width: 8px;
    height: 8px;
    background: var(--accent);
    border-radius: 50%;
    animation: pulse-dot 1.5s ease-in-out infinite;
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
.opus-tag {
    margin-left: auto;
    font-size: 0.6rem;
    font-weight: 600;
    color: var(--primary);
    background: var(--primary-glow);
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid var(--border-accent);
    letter-spacing: 1px;
}
.thinking-live-console {
    background: #060a10;
    color: #06d6a0;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    padding: 20px 24px;
    height: 200px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    font-size: 0.78rem;
    line-height: 1.7;
}
.thinking-content {
    white-space: pre-wrap;
    word-wrap: break-word;
}
.thinking-live-console .phase {
    display: block;
    color: var(--primary);
    font-weight: 600;
    font-size: 0.68rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 14px;
    margin-bottom: 4px;
    opacity: 0.85;
}
.thinking-live-console .phase:first-child {
    margin-top: 0;
}
.thinking-live-console .cursor {
    color: #06d6a0;
    animation: blink-cursor 0.7s infinite;
}
@keyframes blink-cursor {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}

/* ── Replay Mode ───────────────────────────────────────── */
.thinking-dot-slow {
    animation: pulse-dot 3s ease-in-out infinite !important;
}
.thinking-replay-header {
    color: var(--text-secondary) !important;
    border-bottom-color: rgba(255,255,255,0.04) !important;
    background: rgba(255,255,255,0.02) !important;
}
.thinking-replay-console {
    height: 180px;
    justify-content: flex-start;
}
.phase-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(6,214,160,0.06);
}
.phase-chip {
    font-size: 0.58rem;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: var(--accent);
    background: rgba(6,214,160,0.06);
    border: 1px solid rgba(6,214,160,0.1);
    padding: 2px 8px;
    border-radius: 3px;
    opacity: 0.65;
}
.replay-excerpt {
    color: rgba(6,214,160,0.55);
    line-height: 1.65;
    font-size: 0.75rem;
}
.replay-phase {
    display: block;
    color: var(--primary);
    font-weight: 600;
    font-size: 0.62rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 6px;
    opacity: 0.6;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Session state
# ═══════════════════════════════════════════════════════════════════════════
_STATE_KEYS = (
    "model", "thinking", "report", "output_dir",
    "pipeline_done", "summary", "standalone_script",
)
for key in _STATE_KEYS:
    if key not in st.session_state:
        st.session_state[key] = None


# ═══════════════════════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### Paper Input")
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
    generate = st.button(
        "Generate Simulator",
        type="primary",
        disabled=paper_source is None,
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Plotly chart theme (matches dark UI)
# ═══════════════════════════════════════════════════════════════════════════
CHART_COLORS = [
    "#f0b429", "#06d6a0", "#118ab2", "#ef476f",
    "#9b5de5", "#00bbf9", "#f15bb5", "#fee440",
    "#4cc9f0", "#80ed99",
]

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0b0b18",
    font=dict(family="Outfit, sans-serif", color="#e8e8f0", size=13),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.04)",
        zerolinecolor="rgba(255,255,255,0.06)",
        title_font=dict(size=13, color="#8888a8"),
        tickfont=dict(size=11, color="#555570"),
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.04)",
        zerolinecolor="rgba(255,255,255,0.06)",
        title_font=dict(size=13, color="#8888a8"),
        tickfont=dict(size=11, color="#555570"),
    ),
    legend=dict(
        orientation="h",
        y=1.12,
        font=dict(size=12, color="#8888a8"),
        bgcolor="rgba(0,0,0,0)",
    ),
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor="#1a1a30",
        bordercolor="#333355",
        font=dict(family="Outfit, sans-serif", size=12, color="#e8e8f0"),
    ),
    margin=dict(t=40, b=50, l=60, r=20),
    height=520,
)


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline execution
# ═══════════════════════════════════════════════════════════════════════════
def run_with_progress(paper_source: str):
    """Run the full pipeline with Streamlit progress indicators."""
    from episim.core.paper_loader import load_paper
    from episim.core.context_builder import build_context
    from episim.agents.reader import extract_model
    from episim.agents.summarizer import summarize_paper
    from episim.agents.builder import generate_simulator
    from episim.agents.validator import validate, write_report
    from episim.agents.debugger import debug_and_fix, apply_fixes
    from episim.agents.coder import generate_standalone

    progress = st.progress(0, text="Loading paper...")

    # 1. Load paper
    paper_text = load_paper(paper_source)
    progress.progress(10, text="Building context...")

    # 2. Build context
    context = build_context(paper_text)
    progress.progress(15, text="Analyzing paper with extended thinking...")

    # 3. Reader Agent — with real-time thinking display
    from episim.core.thinking_stream import ThinkingAccumulator

    thinking_slot = st.empty()
    accumulator = ThinkingAccumulator()

    def _on_thinking(chunk: str):
        accumulator.add_chunk(chunk)
        thinking_slot.markdown(
            accumulator.format_live_html(), unsafe_allow_html=True,
        )

    model, thinking_text = extract_model(context, on_thinking=_on_thinking)

    # ── Transition to replay mode — keep user engaged during remaining stages ──
    progress.progress(40, text="Generating paper summary...")
    thinking_slot.markdown(
        accumulator.format_replay_html("Generating Summary", 0),
        unsafe_allow_html=True,
    )

    # 4. Summarizer Agent (non-critical)
    summary = None
    try:
        summary = summarize_paper(paper_text, model)
    except Exception:
        pass

    progress.progress(50, text="Building interactive simulator...")
    thinking_slot.markdown(
        accumulator.format_replay_html("Building Simulator", 1),
        unsafe_allow_html=True,
    )

    # 5. Builder Agent
    output_dir = Path("output") / model.name.lower().replace(" ", "_")
    generate_simulator(model, output_dir)

    progress.progress(70, text="Validating against paper results...")
    thinking_slot.markdown(
        accumulator.format_replay_html("Validating Results", 2),
        unsafe_allow_html=True,
    )

    # 6. Validate + debug loop
    report = None
    for attempt in range(1, 4):
        report = validate(output_dir, model)
        report.attempts = attempt
        if report.all_passed:
            break
        if attempt < 3:
            progress.progress(70 + attempt * 5, text=f"Debugging discrepancy (attempt {attempt})...")
            thinking_slot.markdown(
                accumulator.format_replay_html("Debugging Code", 3),
                unsafe_allow_html=True,
            )
            fixes = debug_and_fix(report, output_dir, model)
            apply_fixes(fixes, output_dir)

    write_report(report, output_dir)

    progress.progress(85, text="Generating standalone reproduction script...")
    thinking_slot.markdown(
        accumulator.format_replay_html("Generating Code", 4),
        unsafe_allow_html=True,
    )

    # 7. Coder Agent (non-critical)
    standalone_script = None
    try:
        standalone_script = generate_standalone(model, paper_text)
        if standalone_script:
            (output_dir / standalone_script.filename).write_text(standalone_script.code)
    except Exception:
        pass

    thinking_slot.empty()
    progress.progress(100, text="Complete.")

    # Store in session state
    st.session_state.model = model
    st.session_state.thinking = thinking_text
    st.session_state.report = report
    st.session_state.output_dir = str(output_dir)
    st.session_state.pipeline_done = True
    st.session_state.summary = summary
    st.session_state.standalone_script = standalone_script


if generate and paper_source:
    try:
        run_with_progress(paper_source)
        st.rerun()
    except Exception as e:
        st.error(f"Pipeline failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# Main Content
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.pipeline_done:
    model = st.session_state.model
    report = st.session_state.report
    output_dir = Path(st.session_state.output_dir)
    summary = st.session_state.summary
    standalone_script = st.session_state.standalone_script

    # ── Results Header ──────────────────────────────────────────────────
    st.markdown(f"""
    <div class="results-header">
        <div class="model-badge">{len(model.compartments)} compartments</div>
        <div class="model-name">{model.name}</div>
        <p class="paper-title">{model.paper_title}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Extended Thinking ───────────────────────────────────────────────
    if st.session_state.thinking:
        st.markdown('<div class="thinking-container">', unsafe_allow_html=True)
        with st.expander("Extended Thinking — AI Reasoning Process"):
            st.caption(
                "Watch how Claude Opus 4.6 analyzes the paper's mathematical model "
                "using extended thinking — deep reasoning chains visible in real-time."
            )
            st.markdown(st.session_state.thinking)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Sidebar: Parameter Sliders ──────────────────────────────────────
    with st.sidebar:
        st.divider()
        st.markdown("### Parameters")

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

    # ═══════════════════════════════════════════════════════════════════
    # Tabs
    # ═══════════════════════════════════════════════════════════════════
    tab_summary, tab_simulation, tab_code = st.tabs([
        "Summary", "Simulation", "Code",
    ])

    # ── Tab 1: Summary ──────────────────────────────────────────────────
    with tab_summary:
        if summary:
            st.markdown(f"### {summary.title}")
            st.markdown(f"*{summary.authors}*")

            st.markdown(
                f'<div class="model-type-badge">{summary.model_type}</div>',
                unsafe_allow_html=True,
            )

            st.markdown(summary.abstract_summary)

            # Key findings
            findings_html = "".join(
                f"<li>{f}</li>" for f in summary.key_findings
            )
            st.markdown(
                f'<div class="section-label">Key Findings</div>'
                f'<ul class="findings-list">{findings_html}</ul>',
                unsafe_allow_html=True,
            )

            st.markdown("")  # spacing

            col_meth, col_lim = st.columns(2)
            with col_meth:
                st.markdown(
                    '<div class="section-card">'
                    '<div class="section-label">Methodology</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(summary.methodology)
            with col_lim:
                st.markdown(
                    '<div class="section-card">'
                    '<div class="section-label">Limitations</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(summary.limitations)

            st.markdown("")

            st.markdown(
                '<div class="section-label">Public Health Implications</div>',
                unsafe_allow_html=True,
            )
            st.markdown(summary.public_health_implications)
        else:
            st.info("Paper summary not available.")

        # ── Reproduction Report ─────────────────────────────────────────
        if report:
            st.markdown("---")
            st.markdown(
                '<div class="section-label">Reproduction Report</div>',
                unsafe_allow_html=True,
            )

            if report.all_passed:
                status_html = '<span class="status-badge pass">ALL PASSED</span>'
            else:
                status_html = '<span class="status-badge fail">FAILED</span>'

            st.markdown(
                f'<div class="report-status">'
                f'{status_html}'
                f'<span class="attempts-label">Attempts: {report.attempts}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if report.metrics:
                rows_html = ""
                for m in report.metrics:
                    sc = "pass" if m.passed else "fail"
                    sl = "PASS" if m.passed else "FAIL"
                    rows_html += (
                        f'<tr>'
                        f'<td class="metric-name">{m.metric}</td>'
                        f'<td class="metric-val">{m.expected:.4g}</td>'
                        f'<td class="metric-val">{m.actual:.4g}</td>'
                        f'<td class="metric-val">{m.match_pct:.2f}%</td>'
                        f'<td><span class="status-badge {sc}">{sl}</span></td>'
                        f'</tr>'
                    )
                st.markdown(
                    f'<table class="report-table">'
                    f'<thead><tr>'
                    f'<th>Metric</th><th>Expected</th><th>Actual</th>'
                    f'<th>Deviation</th><th>Status</th>'
                    f'</tr></thead>'
                    f'<tbody>{rows_html}</tbody></table>',
                    unsafe_allow_html=True,
                )

            if report.error:
                st.error(report.error)

    # ── Tab 2: Simulation ───────────────────────────────────────────────
    with tab_simulation:
        st.caption("Adjust parameters in the sidebar to explore different scenarios.")

        try:
            y0 = [model.initial_conditions[c] for c in model.compartments]
            t_span = (0, model.simulation_days)

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
                st.error(f"Simulation error:\n```\n{result.stderr}\n```")
            else:
                results = json.loads(result.stdout)
                t = np.array(results["t"])

                fig = go.Figure()
                for i, comp in enumerate(model.compartments):
                    fig.add_trace(go.Scatter(
                        x=t,
                        y=np.array(results[comp]),
                        mode="lines",
                        name=comp,
                        line=dict(width=2.5, color=CHART_COLORS[i % len(CHART_COLORS)]),
                    ))
                fig.update_layout(**CHART_LAYOUT)
                fig.update_layout(
                    xaxis_title="Days",
                    yaxis_title="Population",
                )
                st.plotly_chart(fig, use_container_width=True)

                # Key metrics
                infected_comp = next(
                    (c for c in model.compartments if c.startswith("I")),
                    model.compartments[1],
                )
                I_arr = np.array(results[infected_comp])
                peak_idx = np.argmax(I_arr)

                col1, col2, col3 = st.columns(3)
                col1.metric("Peak Day", f"{t[peak_idx]:.1f}")
                col2.metric("Peak Cases", f"{I_arr[peak_idx]:,.0f}")
                if "S" in results:
                    S_arr = np.array(results["S"])
                    attack_rate = (1 - S_arr[-1] / model.population) * 100
                    col3.metric("Attack Rate", f"{attack_rate:.1f}%")

        except Exception as e:
            st.error(f"Could not run simulation: {e}")

    # ── Tab 3: Code ─────────────────────────────────────────────────────
    with tab_code:
        if standalone_script:
            st.markdown(
                '<div class="section-label">Standalone Reproduction Script</div>',
                unsafe_allow_html=True,
            )
            st.markdown(standalone_script.description)
            st.markdown("")
            st.download_button(
                label=f"Download {standalone_script.filename}",
                data=standalone_script.code,
                file_name=standalone_script.filename,
                mime="text/x-python",
                use_container_width=True,
            )
            st.markdown("")
            st.code(standalone_script.code, language="python")
        else:
            st.info("Standalone script not available.")


else:
    # ═══════════════════════════════════════════════════════════════════
    # Landing Page
    # ═══════════════════════════════════════════════════════════════════

    st.markdown("""
    <div class="hero">
        <div class="hero-badge">Powered by Claude Opus 4.6</div>
        <div class="hero-title">Epi<span class="hero-accent">Sim</span></div>
        <p class="hero-tagline">
            Transform epidemic modeling research papers<br>
            into interactive public health simulators
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="pipeline-flow">
        <div class="pipeline-step"><span class="pipeline-num">1</span> Upload Paper</div>
        <span class="pipeline-arrow">&rarr;</span>
        <div class="pipeline-step"><span class="pipeline-num">2</span> AI Analysis</div>
        <span class="pipeline-arrow">&rarr;</span>
        <div class="pipeline-step"><span class="pipeline-num">3</span> Summary</div>
        <span class="pipeline-arrow">&rarr;</span>
        <div class="pipeline-step"><span class="pipeline-num">4</span> Simulator</div>
        <span class="pipeline-arrow">&rarr;</span>
        <div class="pipeline-step"><span class="pipeline-num">5</span> Validate</div>
        <span class="pipeline-arrow">&rarr;</span>
        <div class="pipeline-step"><span class="pipeline-num">6</span> Code</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="features-grid">
        <div class="feature-card">
            <div class="feature-num">01</div>
            <div class="feature-title">AI Reader</div>
            <div class="feature-desc">
                Extended thinking extracts the complete mathematical model
                from any epidemic modeling paper &mdash; compartments, ODEs,
                parameters, and validation targets.
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-num">02</div>
            <div class="feature-title">Live Simulator</div>
            <div class="feature-desc">
                Interactive parameter sliders with real-time epidemic curve
                visualization. Explore what-if scenarios instantly.
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-num">03</div>
            <div class="feature-title">Validated Results</div>
            <div class="feature-desc">
                Automatically runs the simulator with the paper's parameters
                and verifies output matches reported results within 5%
                tolerance.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="powered-by">
        <span class="powered-label">
            1M context window &middot; Extended thinking &middot; 128K output &middot;
            Built with <span class="powered-model">Claude Opus 4.6</span>
        </span>
    </div>
    """, unsafe_allow_html=True)
