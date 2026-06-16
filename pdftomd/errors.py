"""Structured application errors."""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    PDF_NOT_FOUND = "PDF_NOT_FOUND"
    PDF_NOT_READABLE = "PDF_NOT_READABLE"
    PDF_TITLE_EXTRACT_FAILED = "PDF_TITLE_EXTRACT_FAILED"
    MARKER_IMPORT_FAILED = "MARKER_IMPORT_FAILED"
    MARKER_MODEL_LOAD_FAILED = "MARKER_MODEL_LOAD_FAILED"
    MARKER_RENDER_FAILED = "MARKER_RENDER_FAILED"
    MARKER_EMPTY_OUTPUT = "MARKER_EMPTY_OUTPUT"
    OUTPUT_DIR_CREATE_FAILED = "OUTPUT_DIR_CREATE_FAILED"
    OUTPUT_WRITE_FAILED = "OUTPUT_WRITE_FAILED"
    CONVERSION_CANCELLED = "CONVERSION_CANCELLED"
    UNHANDLED_ERROR = "UNHANDLED_ERROR"


DEFAULT_SUGGESTIONS: dict[str, str] = {
    ErrorCode.INVALID_INPUT: "Select valid PDF files and a writable output folder.",
    ErrorCode.PDF_NOT_FOUND: "Check that the PDF still exists and try again.",
    ErrorCode.PDF_NOT_READABLE: "Check file permissions or try opening the PDF in another viewer.",
    ErrorCode.PDF_TITLE_EXTRACT_FAILED: "Check whether the PDF is damaged or password protected.",
    ErrorCode.MARKER_IMPORT_FAILED: (
        "Install marker-pdf and its dependencies, then restart PDFtoMD."
    ),
    ErrorCode.MARKER_MODEL_LOAD_FAILED: (
        "Check the selected device and available memory, then try again."
    ),
    ErrorCode.MARKER_RENDER_FAILED: "Try another PDF or switch the device setting to CPU.",
    ErrorCode.MARKER_EMPTY_OUTPUT: (
        "Try another PDF or verify that marker can process this document."
    ),
    ErrorCode.OUTPUT_DIR_CREATE_FAILED: "Choose a writable output folder.",
    ErrorCode.OUTPUT_WRITE_FAILED: "Check free disk space and output folder permissions.",
    ErrorCode.CONVERSION_CANCELLED: "Start conversion again when ready.",
    ErrorCode.UNHANDLED_ERROR: "Check the log file for details or try again.",
}


class PDFtoMDError(RuntimeError):
    """Error that can be safely summarized in the GUI."""

    def __init__(
        self,
        error_code: str | ErrorCode,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        self.error_code = str(error_code)
        self.suggestion = suggestion or DEFAULT_SUGGESTIONS.get(
            self.error_code, DEFAULT_SUGGESTIONS[ErrorCode.UNHANDLED_ERROR]
        )
        super().__init__(message)

    @property
    def message(self) -> str:
        return str(self)
