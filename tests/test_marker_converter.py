from pathlib import Path
from types import ModuleType

import pytest

from pdftomd.converter.marker_converter import (
    MarkerMarkdownConverter,
    marker_safe_pdf_path,
    normalize_markdown,
)
from pdftomd.errors import ErrorCode, PDFtoMDError


def test_normalize_markdown() -> None:
    assert normalize_markdown(" A\u00a0B\r\n\r\n\r\nC \n") == "A B\n\nC"


def test_marker_lazy_import() -> None:
    converter = MarkerMarkdownConverter(device="cpu")

    assert converter._converter is None


def test_marker_empty_output_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_path = tmp_path / "demo.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    class FakePdfConverter:
        def __init__(self, artifact_dict: object) -> None:
            self.artifact_dict = artifact_dict

        def __call__(self, source: str) -> object:
            return {"source": source}

    pdf_module = ModuleType("marker.converters.pdf")
    pdf_module.PdfConverter = FakePdfConverter  # type: ignore[attr-defined]

    models_module = ModuleType("marker.models")
    models_module.create_model_dict = lambda: {"model": "fake"}  # type: ignore[attr-defined]

    output_module = ModuleType("marker.output")
    output_module.text_from_rendered = lambda rendered: ""  # type: ignore[attr-defined]

    monkeypatch.setitem(__import__("sys").modules, "marker", ModuleType("marker"))
    monkeypatch.setitem(
        __import__("sys").modules,
        "marker.converters",
        ModuleType("marker.converters"),
    )
    monkeypatch.setitem(__import__("sys").modules, "marker.converters.pdf", pdf_module)
    monkeypatch.setitem(__import__("sys").modules, "marker.models", models_module)
    monkeypatch.setitem(__import__("sys").modules, "marker.output", output_module)

    converter = MarkerMarkdownConverter(device="cpu")
    with pytest.raises(PDFtoMDError) as exc_info:
        converter.convert(pdf_path)

    assert exc_info.value.error_code == ErrorCode.MARKER_EMPTY_OUTPUT


def test_marker_safe_pdf_path_stages_non_ascii_path(tmp_path: Path) -> None:
    pdf_path = tmp_path / "中文文献.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with marker_safe_pdf_path(pdf_path) as staged:
        assert staged.name == "document.pdf"
        assert staged.read_bytes() == b"%PDF-1.4"
        str(staged).encode("ascii")

    assert pdf_path.exists()


def test_marker_safe_pdf_path_stages_ascii_path(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with marker_safe_pdf_path(pdf_path) as staged:
        assert staged != pdf_path
        assert staged.name == "document.pdf"
        assert staged.read_bytes() == b"%PDF-1.4"
