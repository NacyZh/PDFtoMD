"""Small GUI helpers."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget

from pdftomd.errors import PDFtoMDError


def show_user_error(parent: QWidget, title: str, error: PDFtoMDError) -> None:
    QMessageBox.warning(
        parent,
        title,
        f"{error.error_code}\n\n{error.message}\n\nSuggested action: {error.suggestion}",
    )


def is_pdf_path(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".pdf"
