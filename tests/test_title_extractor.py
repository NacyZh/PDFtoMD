from pathlib import Path
from types import ModuleType

import pytest

from pdftomd.converter.title_extractor import extract_pdf_title
from pdftomd.errors import ErrorCode, PDFtoMDError


def test_extract_pdf_title_metadata(tmp_path: Path) -> None:
    import fitz

    pdf_path = tmp_path / "metadata.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.set_metadata({"title": "  Metadata   Title  "})
    doc.save(pdf_path)
    doc.close()

    assert extract_pdf_title(pdf_path) == "Metadata Title"


def test_extract_pdf_title_first_page_heuristic(tmp_path: Path) -> None:
    import fitz

    pdf_path = tmp_path / "page.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "A Demo Paper Title\n\nThis is content.")
    doc.save(pdf_path)
    doc.close()

    assert extract_pdf_title(pdf_path) == "A Demo Paper Title"


def test_extract_pdf_title_open_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeFitz(ModuleType):
        def open(self, path: Path) -> object:
            raise RuntimeError(f"cannot open {path}")

    monkeypatch.setitem(__import__("sys").modules, "fitz", FakeFitz("fitz"))

    with pytest.raises(PDFtoMDError) as exc_info:
        extract_pdf_title(tmp_path / "broken.pdf")

    assert exc_info.value.error_code == ErrorCode.PDF_TITLE_EXTRACT_FAILED
