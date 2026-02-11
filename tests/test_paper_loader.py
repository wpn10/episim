"""Tests for paper_loader — PDF extraction and arxiv handling."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import pytest

from episim.core.paper_loader import load_paper, _extract_pdf, _strip_headers_footers


def _create_test_pdf(path: Path, pages: list[str]) -> None:
    """Create a simple PDF with the given page texts."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


class TestExtractPdf:
    def test_single_page(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        _create_test_pdf(pdf_path, ["Hello world, this is page one."])
        text = _extract_pdf(pdf_path)
        assert "Hello world" in text

    def test_multi_page(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        _create_test_pdf(pdf_path, ["Page one content.", "Page two content."])
        text = _extract_pdf(pdf_path)
        assert "Page one" in text
        assert "Page two" in text


class TestStripHeadersFooters:
    def test_removes_repeated_lines(self):
        pages = [
            "Header Line\nActual content page 1\nFooter Line",
            "Header Line\nActual content page 2\nFooter Line",
            "Header Line\nActual content page 3\nFooter Line",
            "Header Line\nActual content page 4\nFooter Line",
        ]
        full_text = "\n\n".join(pages)
        result = _strip_headers_footers(full_text, pages)
        assert "Header Line" not in result
        assert "Footer Line" not in result
        assert "Actual content page 1" in result

    def test_keeps_unique_lines(self):
        pages = [
            "Header\nUnique A\nFooter",
            "Header\nUnique B\nFooter",
            "Header\nUnique C\nFooter",
        ]
        full_text = "\n\n".join(pages)
        result = _strip_headers_footers(full_text, pages)
        assert "Unique A" in result
        assert "Unique B" in result

    def test_short_doc_no_stripping(self):
        pages = ["Page 1", "Page 2"]
        full_text = "\n\n".join(pages)
        result = _strip_headers_footers(full_text, pages)
        assert result == full_text


class TestLoadPaper:
    def test_local_pdf(self, tmp_path):
        pdf_path = tmp_path / "paper.pdf"
        _create_test_pdf(pdf_path, ["SIR model differential equations."])
        text = load_paper(str(pdf_path))
        assert "SIR model" in text

    def test_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            load_paper("/nonexistent/path.pdf")

    def test_bare_arxiv_id_detection(self):
        """Verify bare arxiv ID triggers arxiv download path."""
        with patch("episim.core.paper_loader._load_arxiv", return_value="mock text") as mock:
            result = load_paper("2401.12345")
            mock.assert_called_once_with("2401.12345")
            assert result == "mock text"

    def test_arxiv_url_detection(self):
        """Verify arxiv URL triggers arxiv download path."""
        with patch("episim.core.paper_loader._load_arxiv", return_value="mock text") as mock:
            result = load_paper("https://arxiv.org/abs/2401.12345")
            mock.assert_called_once_with("2401.12345")

    def test_arxiv_pdf_url_detection(self):
        with patch("episim.core.paper_loader._load_arxiv", return_value="mock text") as mock:
            result = load_paper("https://arxiv.org/pdf/2401.12345")
            mock.assert_called_once_with("2401.12345")
