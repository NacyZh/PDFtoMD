"""Lazy marker PDF-to-Markdown conversion."""

from __future__ import annotations

import contextlib
import gc
import os
import re
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pdftomd.config import VALID_DEVICES
from pdftomd.errors import ErrorCode, PDFtoMDError
from pdftomd.logging import get_logger

logger = get_logger(__name__)


def normalize_markdown(text: str) -> str:
    normalized = text.replace("\u00a0", " ")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


@contextlib.contextmanager
def marker_safe_pdf_path(pdf_path: Path) -> Iterator[Path]:
    """Yield a marker-friendly PDF path.

    Some lower-level dependencies used by marker can fail on non-ASCII paths,
    spaces, or Windows-mounted paths under WSL. Stage every input to a short
    ASCII path while preserving the original path for title extraction and
    output naming.
    """

    resolved = pdf_path.resolve()
    with tempfile.TemporaryDirectory(prefix="pdftomd-marker-") as tmp_dir:
        staged = Path(tmp_dir) / "document.pdf"
        shutil.copy2(resolved, staged)
        yield staged


class MarkerMarkdownConverter:
    def __init__(self, device: str = "auto", keep_images: bool = True) -> None:
        if device not in VALID_DEVICES:
            raise PDFtoMDError(ErrorCode.INVALID_INPUT, f"Unsupported device: {device}")
        self.device = device
        self.keep_images = keep_images
        self._resolved_device: str | None = None
        self._converter: Any | None = None
        self._text_from_rendered: Any | None = None
        self.last_images: dict[str, Any] = {}

    def _cuda_available(self) -> bool:
        try:
            import torch
        except ImportError:
            return False
        try:
            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def _resolve_device(self) -> str:
        if self.device == "cpu":
            return "cpu"
        if self.device == "cuda":
            if not self._cuda_available():
                raise PDFtoMDError(
                    ErrorCode.MARKER_MODEL_LOAD_FAILED,
                    "CUDA was selected but is not available.",
                    "Select auto or cpu, or install a CUDA-enabled PyTorch build.",
                )
            return "cuda"
        return "cuda" if self._cuda_available() else "cpu"

    def _load(self) -> None:
        if self._converter is not None:
            return

        self._resolved_device = self._resolve_device()
        os.environ["TORCH_DEVICE"] = self._resolved_device
        logger.info("marker_loading device=%s", self._resolved_device)

        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.output import text_from_rendered
        except ImportError as exc:
            raise PDFtoMDError(
                ErrorCode.MARKER_IMPORT_FAILED,
                "Could not import marker.",
            ) from exc

        try:
            artifact_dict = create_model_dict()
            self._converter = self._build_pdf_converter(PdfConverter, artifact_dict)
            self._text_from_rendered = text_from_rendered
        except PDFtoMDError:
            raise
        except Exception as exc:
            raise PDFtoMDError(
                ErrorCode.MARKER_MODEL_LOAD_FAILED,
                "Could not load marker model.",
            ) from exc

        logger.info("marker_loaded device=%s", self._resolved_device)

    def _build_pdf_converter(self, pdf_converter_cls: Any, artifact_dict: Any) -> Any:
        try:
            from marker.config import parser as marker_parser
        except ImportError:
            config_parser_cls = None
        else:
            config_parser_cls = marker_parser.ConfigParser

        if config_parser_cls is not None:
            config = {
                "output_format": "markdown",
                "disable_image_extraction": not self.keep_images,
                "use_llm": False,
                "torch_device": self._resolved_device,
            }
            try:
                parser = config_parser_cls(config)
                return pdf_converter_cls(
                    config=parser.generate_config_dict(),
                    artifact_dict=artifact_dict,
                    processor_list=parser.get_processors(),
                    renderer=parser.get_renderer(),
                    llm_service=parser.get_llm_service(),
                )
            except TypeError:
                pass

        try:
            return pdf_converter_cls(artifact_dict=artifact_dict)
        except TypeError:
            return pdf_converter_cls(artifact_dict)

    def convert(self, pdf_path: Path) -> str:
        if not pdf_path.exists():
            raise PDFtoMDError(ErrorCode.PDF_NOT_FOUND, f"PDF not found: {pdf_path}")
        if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
            raise PDFtoMDError(ErrorCode.INVALID_INPUT, f"Not a PDF file: {pdf_path}")

        self._load()
        assert self._converter is not None
        assert self._text_from_rendered is not None

        logger.info("marker_render_started file=%s", pdf_path.name)
        try:
            with marker_safe_pdf_path(pdf_path) as marker_pdf_path:
                rendered = self._converter(str(marker_pdf_path))
            extracted = self._text_from_rendered(rendered)
            images: dict[str, Any] = {}
            if isinstance(extracted, tuple | list):
                markdown = extracted[0]
                if len(extracted) >= 3 and isinstance(extracted[2], dict):
                    images = extracted[2]
            else:
                markdown = extracted
            markdown = normalize_markdown(str(markdown or ""))
        except PDFtoMDError:
            raise
        except Exception as exc:
            logger.exception("marker_render_failed file=%s", pdf_path.name)
            detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            raise PDFtoMDError(
                ErrorCode.MARKER_RENDER_FAILED,
                f"marker could not convert: {pdf_path.name}. Detail: {detail}",
            ) from exc

        if not markdown:
            raise PDFtoMDError(
                ErrorCode.MARKER_EMPTY_OUTPUT,
                f"marker returned empty Markdown: {pdf_path.name}",
            )

        self.last_images = images if self.keep_images else {}
        logger.info("marker_render_finished file=%s", pdf_path.name)
        return markdown

    def close(self) -> None:
        self._converter = None
        self._text_from_rendered = None
        self.last_images = {}
        gc.collect()
        try:
            import torch
        except ImportError:
            return
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception:
            return
