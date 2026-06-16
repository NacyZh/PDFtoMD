from pathlib import Path

from pytestqt.qtbot import QtBot

from pdftomd.config import ConversionSettings
from pdftomd.gui import worker as worker_module
from pdftomd.gui.worker import ConversionWorker
from pdftomd.models import ConversionStatus


class DummyConverter:
    terminated = False

    def __init__(self, device: str = "auto", keep_images: bool = True) -> None:
        self.device = device
        self.keep_images = keep_images
        self.last_images = {}

    def convert(self, pdf_path: Path, should_cancel=None) -> str:
        if pdf_path.name == "fail.pdf":
            from pdftomd.errors import ErrorCode, PDFtoMDError

            raise PDFtoMDError(ErrorCode.MARKER_RENDER_FAILED, "failed render")
        return "# Markdown"

    def terminate(self) -> None:
        type(self).terminated = True

    def close(self) -> None:
        return None


def test_worker_success_signal_updates_status(
    tmp_path: Path,
    monkeypatch,
    qtbot: QtBot,
) -> None:
    pdf_path = tmp_path / "ok.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(worker_module, "MarkerProcessClient", DummyConverter)
    monkeypatch.setattr(worker_module, "extract_pdf_title", lambda path: "Worker Title")

    worker = ConversionWorker([pdf_path], tmp_path / "out", ConversionSettings())
    with qtbot.waitSignal(worker.finished_all, timeout=3000) as blocker:
        worker.start()

    results = blocker.args[0]
    assert results[0].status == ConversionStatus.succeeded
    assert Path(results[0].output_path).name == "Worker Title.md"


def test_worker_failure_signal_updates_status(
    tmp_path: Path,
    monkeypatch,
    qtbot: QtBot,
) -> None:
    pdf_path = tmp_path / "fail.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(worker_module, "MarkerProcessClient", DummyConverter)
    monkeypatch.setattr(worker_module, "extract_pdf_title", lambda path: "")

    worker = ConversionWorker([pdf_path], tmp_path / "out", ConversionSettings())
    with qtbot.waitSignal(worker.finished_all, timeout=3000) as blocker:
        worker.start()

    results = blocker.args[0]
    assert results[0].status == ConversionStatus.failed
    assert results[0].error_code == "MARKER_RENDER_FAILED"


def test_worker_cancel_sets_flag(tmp_path: Path) -> None:
    worker = ConversionWorker([], tmp_path, ConversionSettings())
    worker.cancel()

    assert worker.cancel_requested is True


def test_worker_cancel_terminates_active_converter(tmp_path: Path) -> None:
    DummyConverter.terminated = False
    worker = ConversionWorker([], tmp_path, ConversionSettings())
    worker._converter = DummyConverter()

    worker.cancel()

    assert DummyConverter.terminated is True
