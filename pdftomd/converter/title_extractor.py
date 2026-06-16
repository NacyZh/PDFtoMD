"""Extract PDF titles with PyMuPDF only for output naming."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pdftomd.errors import ErrorCode, PDFtoMDError

SKIP_PATTERNS = (
    "doi",
    "abstract",
    "copyright",
    "arxiv",
)


def _clean_title(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _is_bad_candidate(line: str) -> bool:
    lowered = line.lower()
    if len(line) < 6:
        return True
    if any(pattern in lowered for pattern in SKIP_PATTERNS):
        return True
    if "@" in line:
        return True
    return bool(re.fullmatch(r"[\d\s.\-]+", line))


def _metadata_title(doc: Any) -> str:
    metadata = getattr(doc, "metadata", None) or {}
    title = metadata.get("title") or ""
    return _clean_title(str(title))


def _first_page_title(doc: Any) -> str:
    if getattr(doc, "page_count", 0) < 1:
        return ""
    page = doc.load_page(0)
    text = page.get_text("text")
    lines = [_clean_title(line) for line in str(text).splitlines()]
    candidates = [line for line in lines if line][:20]
    for line in candidates:
        if _is_bad_candidate(line):
            continue
        if 10 <= len(line) <= 180:
            return line
    return ""


def extract_pdf_title(pdf_path: Path) -> str:
    """Extract a best-effort PDF title.

    Raises a structured error only when the PDF cannot be opened/read.
    """

    try:
        import fitz
    except ImportError as exc:
        raise PDFtoMDError(
            ErrorCode.PDF_TITLE_EXTRACT_FAILED,
            "PyMuPDF is not installed.",
            "Install PyMuPDF, then restart PDFtoMD.",
        ) from exc

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise PDFtoMDError(
            ErrorCode.PDF_TITLE_EXTRACT_FAILED,
            f"Could not open PDF for title extraction: {pdf_path.name}",
        ) from exc

    try:
        title = _metadata_title(doc)
        if title:
            return title
        return _first_page_title(doc)
    except Exception:
        return ""
    finally:
        doc.close()
