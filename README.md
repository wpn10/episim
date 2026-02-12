# EpiSim

Transform epidemic modeling research papers into interactive public health simulators. Powered by Claude Opus 4.6 — 1M context, extended thinking, 128K output.

## Quick Start

```bash
# Clone and install
git clone https://github.com/wpn10/episim.git
cd episim
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .

# Set your API key
export ANTHROPIC_API_KEY=your_key_here

# Launch the app
streamlit run app.py
```

## Usage

### Web App (Recommended)

```bash
streamlit run app.py
```

Upload a PDF or paste an arxiv ID (e.g. `2003.09861`) and click **Generate Simulator**.

### CLI

```bash
python -m episim.core.orchestrator --paper 2003.09861
python -m episim.core.orchestrator --paper path/to/paper.pdf
```

Then launch the generated simulator:

```bash
cd output/{model_name} && streamlit run app.py
```

## How It Works

1. **Paper Loader** — Extracts text from PDF or arxiv
2. **Reader Agent** — Opus 4.6 + extended thinking extracts the mathematical model
3. **Builder Agent** — Generates a complete Streamlit simulator (model, solver, UI)
4. **Validator** — Runs the simulator, compares metrics against the paper's results
5. **Debugger Agent** — Automatically fixes discrepancies (up to 3 retries)

## Demo Paper

The [SIDARTHE COVID-19 model](https://arxiv.org/abs/2003.09861) (Giordano et al.) is a good test paper with 8 compartments and well-documented parameters.

## Tests

```bash
pytest tests/ -v
```

## Tech Stack

Python 3.11+ | Anthropic API (Opus 4.6) | scipy | Streamlit | Plotly | PyMuPDF

## License

MIT
