from pathlib import Path

from pytestqt.qtbot import QtBot

from pdftomd.gui.main_window import MainWindow


class CaptureWorker:
    created_args = None

    def __init__(self, *args, **kwargs) -> None:
        from PySide6.QtCore import QObject, Signal

        class Signals(QObject):
            item_started = Signal(str)
            item_finished = Signal(object)
            progress_changed = Signal(int, int, int, int)
            status_message = Signal(str)
            finished_all = Signal(list)

        type(self).created_args = args
        self.signals = Signals()
        self.item_started = self.signals.item_started
        self.item_finished = self.signals.item_finished
        self.progress_changed = self.signals.progress_changed
        self.status_message = self.signals.status_message
        self.finished_all = self.signals.finished_all
        self.cancelled = False

    def start(self) -> None:
        return None

    def cancel(self) -> None:
        self.cancelled = True

    def isRunning(self) -> bool:  # noqa: N802
        return False

    def wait(self, timeout: int) -> None:
        return None


def test_add_pdf_after_selection_appears_in_list(tmp_path: Path, qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    window.add_pdf_paths([pdf_path])

    assert window.file_table.rowCount() == 1
    assert window.file_table.item(0, 0).text() == "paper.pdf"


def test_remove_selected_file(tmp_path: Path, qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    window.add_pdf_paths([pdf_path])

    window.file_table.selectRow(0)
    window.remove_selected()

    assert window.file_table.rowCount() == 0


def test_clear_files(tmp_path: Path, qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    window.add_pdf_paths([pdf_path])

    window.clear_files()

    assert window.file_table.rowCount() == 0


def test_choose_output_dir(
    tmp_path: Path,
    monkeypatch,
    qtbot: QtBot,
) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(
        "pdftomd.gui.main_window.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(tmp_path),
    )

    window.choose_output_dir()

    assert window.output_dir == tmp_path


def test_choose_output_dir_persists_last_path(
    tmp_path: Path,
    monkeypatch,
    qtbot: QtBot,
) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(
        "pdftomd.gui.main_window.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(tmp_path),
    )

    window.choose_output_dir()

    assert window.settings_store.value("output_dir") == str(tmp_path)


def test_choose_pdfs_uses_last_pdf_dir(
    tmp_path: Path,
    monkeypatch,
    qtbot: QtBot,
) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.last_pdf_dir = tmp_path
    seen_dir = ""

    def fake_get_open_file_names(*args, **kwargs):
        nonlocal seen_dir
        seen_dir = args[2]
        return [], ""

    monkeypatch.setattr(
        "pdftomd.gui.main_window.QFileDialog.getOpenFileNames",
        fake_get_open_file_names,
    )

    window.choose_pdfs()

    assert seen_dir == str(tmp_path)


def test_click_convert_button_state_changes(
    tmp_path: Path,
    monkeypatch,
    qtbot: QtBot,
) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    window.add_pdf_paths([pdf_path])

    monkeypatch.setattr("pdftomd.gui.main_window.ConversionWorker", CaptureWorker)

    window.start_conversion()

    assert not window.convert_button.isEnabled()
    assert window.cancel_button.isEnabled()


def test_cancel_button_triggers_cancel_flag(
    tmp_path: Path,
    monkeypatch,
    qtbot: QtBot,
) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    window.add_pdf_paths([pdf_path])

    monkeypatch.setattr("pdftomd.gui.main_window.ConversionWorker", CaptureWorker)

    window.start_conversion()
    window.cancel_conversion()

    assert window._worker.cancelled is True


def test_keep_images_setting_passed_to_worker(
    tmp_path: Path,
    monkeypatch,
    qtbot: QtBot,
) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    window.add_pdf_paths([pdf_path])
    window.keep_images_check.setChecked(False)
    monkeypatch.setattr("pdftomd.gui.main_window.ConversionWorker", CaptureWorker)

    window.start_conversion()

    assert CaptureWorker.created_args is not None
    settings = CaptureWorker.created_args[2]
    assert settings.keep_images is False
