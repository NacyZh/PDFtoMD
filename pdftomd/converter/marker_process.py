"""Run marker conversion in a killable child process."""

from __future__ import annotations

import io
import multiprocessing
import queue
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pdftomd.converter.marker_converter import MarkerMarkdownConverter
from pdftomd.errors import ErrorCode, PDFtoMDError
from pdftomd.logging import configure_logging

Response = dict[str, Any]


def _serialize_images(images: dict[str, Any]) -> dict[str, bytes]:
    serialized: dict[str, bytes] = {}
    for name, image in images.items():
        if isinstance(image, bytes):
            serialized[name] = image
            continue
        if isinstance(image, bytearray):
            serialized[name] = bytes(image)
            continue
        if isinstance(image, Path):
            serialized[name] = image.read_bytes()
            continue
        if isinstance(image, str):
            source = Path(image)
            if source.exists():
                serialized[name] = source.read_bytes()
                continue

        save = getattr(image, "save", None)
        if callable(save):
            buffer = io.BytesIO()
            save(buffer, format=getattr(image, "format", None) or "PNG")
            serialized[name] = buffer.getvalue()

    return serialized


def _marker_process_main(
    device: str,
    keep_images: bool,
    request_queue: multiprocessing.Queue[Any],
    response_queue: multiprocessing.Queue[Response],
) -> None:
    converter: MarkerMarkdownConverter | None = None
    try:
        configure_logging(dev_mode=False)
        converter = MarkerMarkdownConverter(device=device, keep_images=keep_images)
        while True:
            request = request_queue.get()
            command = request.get("command")
            if command == "close":
                return
            if command != "convert":
                continue

            request_id = request["request_id"]
            pdf_path = Path(request["pdf_path"])
            try:
                markdown = converter.convert(pdf_path)
                response_queue.put(
                    {
                        "request_id": request_id,
                        "ok": True,
                        "markdown": markdown,
                        "images": _serialize_images(converter.last_images) if keep_images else {},
                    }
                )
            except PDFtoMDError as exc:
                response_queue.put(
                    {
                        "request_id": request_id,
                        "ok": False,
                        "error_code": exc.error_code,
                        "message": exc.message,
                        "suggestion": exc.suggestion,
                    }
                )
            except Exception as exc:
                response_queue.put(
                    {
                        "request_id": request_id,
                        "ok": False,
                        "error_code": ErrorCode.UNHANDLED_ERROR,
                        "message": str(exc) or "Unexpected marker subprocess error.",
                        "suggestion": "Check the log file for details or try again.",
                    }
                )
    finally:
        if converter is not None:
            converter.close()


class MarkerProcessClient:
    """A small client for a persistent marker subprocess.

    The subprocess can be terminated from the GUI thread while the worker thread
    is blocked waiting for marker, which is the key difference from using marker
    directly inside QThread.
    """

    def __init__(self, device: str = "auto", keep_images: bool = True) -> None:
        self.device = device
        self.keep_images = keep_images
        self.last_images: dict[str, bytes] = {}
        self._context = multiprocessing.get_context("spawn")
        self._request_queue: multiprocessing.Queue[Any] | None = None
        self._response_queue: multiprocessing.Queue[Response] | None = None
        self._process: Any | None = None
        self._process_lock = threading.RLock()
        self._request_id = 0
        self._terminated_by_cancel = False

    def _start(self) -> None:
        with self._process_lock:
            if self._process is not None and self._process.is_alive():
                return
            self._request_queue = self._context.Queue()
            self._response_queue = self._context.Queue()
            self._terminated_by_cancel = False
            self._process = self._context.Process(
                target=_marker_process_main,
                args=(
                    self.device,
                    self.keep_images,
                    self._request_queue,
                    self._response_queue,
                ),
            )
            self._process.start()

    def convert(
        self,
        pdf_path: Path,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str:
        self._start()
        assert self._request_queue is not None
        assert self._response_queue is not None
        assert self._process is not None
        process = self._process

        self._request_id += 1
        request_id = self._request_id
        self._request_queue.put(
            {
                "command": "convert",
                "request_id": request_id,
                "pdf_path": str(pdf_path),
            }
        )

        while True:
            if should_cancel is not None and should_cancel():
                self.terminate()
                raise PDFtoMDError(
                    ErrorCode.CONVERSION_CANCELLED,
                    f"Conversion cancelled: {pdf_path.name}",
                )

            if not process.is_alive():
                if self._terminated_by_cancel:
                    raise PDFtoMDError(
                        ErrorCode.CONVERSION_CANCELLED,
                        f"Conversion cancelled: {pdf_path.name}",
                    )
                raise PDFtoMDError(
                    ErrorCode.MARKER_RENDER_FAILED,
                    "marker subprocess stopped unexpectedly.",
                    "Try again, or switch to CPU if the GPU ran out of memory.",
                )

            try:
                response = self._response_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if response.get("request_id") != request_id:
                continue
            if response.get("ok"):
                self.last_images = response.get("images", {})
                return str(response.get("markdown", ""))

            raise PDFtoMDError(
                str(response.get("error_code", ErrorCode.UNHANDLED_ERROR)),
                str(response.get("message", "marker subprocess failed.")),
                str(response.get("suggestion", "")) or None,
            )

    def terminate(self) -> None:
        self._terminated_by_cancel = True
        with self._process_lock:
            process = self._process
            self._process = None
        if process is not None and process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
        self.last_images = {}

    def close(self) -> None:
        with self._process_lock:
            process = self._process
            request_queue = self._request_queue
            self._process = None
        if process is None:
            return
        if process.is_alive() and request_queue is not None:
            try:
                request_queue.put({"command": "close"})
                process.join(timeout=10)
            except Exception:
                pass
        if process.is_alive():
            self._terminated_by_cancel = True
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
        self.last_images = {}
