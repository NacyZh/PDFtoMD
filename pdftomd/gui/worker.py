"""Background serial conversion worker."""

from __future__ import annotations

import logging
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from pdftomd.config import ConversionSettings
from pdftomd.converter.filename import build_markdown_filename
from pdftomd.converter.markdown_writer import write_markdown
from pdftomd.converter.marker_process import MarkerProcessClient
from pdftomd.converter.title_extractor import extract_pdf_title
from pdftomd.errors import ErrorCode, PDFtoMDError
from pdftomd.logging import get_logger
from pdftomd.models import ConversionResult, ConversionStatus

logger = get_logger(__name__)


class ConversionWorker(QThread):
    item_started = Signal(str)
    item_finished = Signal(object)
    progress_changed = Signal(int, int, int, int)
    status_message = Signal(str)
    finished_all = Signal(list)

    def __init__(
        self,
        pdf_paths: list[Path],
        output_dir: Path,
        settings: ConversionSettings,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.pdf_paths = pdf_paths
        self.output_dir = output_dir
        self.settings = settings
        self._cancel_requested = False
        self._converter: MarkerProcessClient | None = None

    def cancel(self) -> None:
        self._cancel_requested = True
        self.status_message.emit("Cancelling current PDF")
        if self._converter is not None:
            self._converter.terminate()

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_requested

    def run(self) -> None:
        logger.info("conversion_started count=%s", len(self.pdf_paths))
        results: list[ConversionResult] = []
        completed = 0
        succeeded = 0
        failed = 0
        total = len(self.pdf_paths)

        try:
            self._converter = MarkerProcessClient(
                device=self.settings.device,
                keep_images=self.settings.keep_images,
            )
            self.status_message.emit("Loading marker model")

            for index, pdf_path in enumerate(self.pdf_paths):
                if self._cancel_requested:
                    completed = self._cancel_remaining(
                        self.pdf_paths[index:],
                        results,
                        completed,
                        total,
                        succeeded,
                        failed,
                    )
                    break

                self.item_started.emit(str(pdf_path))
                self.status_message.emit("Converting")
                result = self._convert_one(pdf_path, self._converter)
                results.append(result)
                self.item_finished.emit(result)

                completed += 1
                if result.status == ConversionStatus.succeeded:
                    succeeded += 1
                elif result.status == ConversionStatus.failed:
                    failed += 1
                self.progress_changed.emit(completed, total, succeeded, failed)

                if self._cancel_requested:
                    self._converter.close()
                    self._converter = None
                    completed = self._cancel_remaining(
                        self.pdf_paths[index + 1 :],
                        results,
                        completed,
                        total,
                        succeeded,
                        failed,
                    )
                    break

            self.status_message.emit("Cancelled" if self._cancel_requested else "Completed")
        finally:
            if self._converter is not None:
                self._converter.close()
                self._converter = None
            logger.info("conversion_cancelled" if self._cancel_requested else "conversion_finished")
            self.finished_all.emit(results)

    def _convert_one(
        self,
        pdf_path: Path,
        converter: MarkerProcessClient,
    ) -> ConversionResult:
        title = ""
        try:
            if self.settings.filename_fallback == "title":
                title = extract_pdf_title(pdf_path)
                if title:
                    logger.info("title_extracted file=%s", pdf_path.name)

            if self._cancel_requested:
                return self._cancelled_result(pdf_path)

            filename_title = title if self.settings.filename_fallback == "title" else ""
            filename = build_markdown_filename(filename_title, pdf_path)
            markdown = converter.convert(pdf_path, lambda: self.cancel_requested)

            if self._cancel_requested:
                return self._cancelled_result(pdf_path)

            self.status_message.emit("Writing markdown")
            output_path = write_markdown(
                markdown,
                self.output_dir,
                filename,
                self.settings.overwrite,
                images=converter.last_images if self.settings.keep_images else None,
            )
            logger.info("markdown_written file=%s output=%s", pdf_path.name, output_path.name)
            return ConversionResult(
                source_path=str(pdf_path),
                output_path=str(output_path),
                title=title,
                status=ConversionStatus.succeeded,
                message="Completed",
            )
        except PDFtoMDError as exc:
            if exc.error_code == ErrorCode.CONVERSION_CANCELLED:
                return self._cancelled_result(pdf_path)

            logger.warning(
                "conversion_failed file=%s code=%s message=%s",
                pdf_path.name,
                exc.error_code,
                exc.message,
            )
            return ConversionResult(
                source_path=str(pdf_path),
                title=title,
                status=ConversionStatus.failed,
                error_code=exc.error_code,
                message=f"{exc.message} Suggested action: {exc.suggestion}",
            )
        except Exception as exc:
            logger.error(
                "conversion_failed file=%s code=%s\n%s",
                pdf_path.name,
                ErrorCode.UNHANDLED_ERROR,
                traceback.format_exc(),
            )
            logging.getLogger("pdftomd").debug("unhandled_exception", exc_info=exc)
            error = PDFtoMDError(ErrorCode.UNHANDLED_ERROR, "Unexpected conversion error.")
            return ConversionResult(
                source_path=str(pdf_path),
                title=title,
                status=ConversionStatus.failed,
                error_code=error.error_code,
                message=f"{error.message} Suggested action: {error.suggestion}",
            )

    def _cancelled_result(self, pdf_path: Path) -> ConversionResult:
        logger.info("conversion_cancelled file=%s", pdf_path.name)
        return ConversionResult(
            source_path=str(pdf_path),
            status=ConversionStatus.cancelled,
            error_code=ErrorCode.CONVERSION_CANCELLED,
            message="Cancelled",
        )

    def _cancel_remaining(
        self,
        remaining_paths: list[Path],
        results: list[ConversionResult],
        completed: int,
        total: int,
        succeeded: int,
        failed: int,
    ) -> int:
        for pdf_path in remaining_paths:
            result = self._cancelled_result(pdf_path)
            results.append(result)
            self.item_finished.emit(result)
            completed += 1
            self.progress_changed.emit(completed, total, succeeded, failed)
        return completed
