"""Paper Loader — PDF/arxiv → raw text via PyMuPDF."""

from __future__ import annotations

import re
import tempfile
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF
import requests


_ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})")
_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")


def load_paper(source: str) -> str:
    """Load a paper from a local PDF path, arxiv URL, or bare arxiv ID.

    Returns the extracted text content.
    """
    source = source.strip()

    # Bare arxiv ID
    if _ARXIV_ID_RE.match(source):
        return _load_arxiv(source)

    # Arxiv URL
    m = _ARXIV_URL_RE.search(source)
    if m:
        return _load_arxiv(m.group(1))

    # Local PDF path
    path = Path(source)
    if path.is_file():
        return _extract_pdf(path)

    raise FileNotFoundError(f"Cannot load paper from: {source}")


def _load_arxiv(arxiv_id: str) -> str:
    """Download PDF from arxiv and extract text."""
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(resp.content)
        tmp.flush()
        return _extract_pdf(Path(tmp.name))


def _extract_pdf(path: Path) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    doc = fitz.open(str(path))
    pages: list[str] = []

    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text)

    doc.close()

    full_text = "\n\n".join(pages)
    return _strip_headers_footers(full_text, pages)


def _strip_headers_footers(full_text: str, pages: list[str]) -> str:
    """Remove repeated short lines that appear across multiple pages (headers/footers)."""
    if len(pages) < 3:
        return full_text

    # Collect first and last lines from each page
    edge_lines: list[str] = []
    for page_text in pages:
        lines = [l.strip() for l in page_text.strip().splitlines() if l.strip()]
        if lines:
            edge_lines.append(lines[0])
            if len(lines) > 1:
                edge_lines.append(lines[-1])

    # Lines appearing on more than half the pages are likely headers/footers
    threshold = len(pages) // 2
    counts = Counter(edge_lines)
    repeated = {line for line, count in counts.items() if count >= threshold and len(line) < 80}

    if not repeated:
        return full_text

    # Remove those lines
    result_lines = []
    for line in full_text.splitlines():
        if line.strip() not in repeated:
            result_lines.append(line)
    return "\n".join(result_lines)
