"""Main PySide6 window."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pdftomd.config import ConversionSettings, default_output_dir
from pdftomd.errors import ErrorCode, PDFtoMDError
from pdftomd.gui.styles import APP_STYLESHEET
from pdftomd.gui.widgets import is_pdf_path, show_user_error
from pdftomd.gui.worker import ConversionWorker
from pdftomd.logging import get_logger
from pdftomd.models import ConversionResult, ConversionStatus

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDFtoMD")
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)
        self.setStyleSheet(APP_STYLESHEET)

        self.settings_store = QSettings("PDFtoMD", "PDFtoMD")
        self.last_pdf_dir = self._stored_dir("last_pdf_dir", Path.home())
        self.output_dir = self._stored_dir("output_dir", default_output_dir())
        self._worker: ConversionWorker | None = None
        self._paths: list[Path] = []

        self._build_ui()
        self._update_progress(0, 0, 0, 0)
        self._log("Ready")

    def _stored_dir(self, key: str, fallback: Path) -> Path:
        value = self.settings_store.value(key, str(fallback))
        path = Path(str(value))
        return path if path.exists() else fallback

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)

        layout.addWidget(self._build_file_group(), stretch=3)
        layout.addWidget(self._build_output_group())
        layout.addWidget(self._build_settings_group())
        layout.addWidget(self._build_progress_group())
        layout.addWidget(self._build_log_group(), stretch=2)
        layout.addLayout(self._build_action_row())

        self.setCentralWidget(central)

    def _build_file_group(self) -> QGroupBox:
        group = QGroupBox("Selected PDFs")
        layout = QVBoxLayout(group)

        self.file_table = QTableWidget(0, 3)
        self.file_table.setHorizontalHeaderLabels(["File Name", "Path", "Status"])
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.file_table.setColumnWidth(0, 220)
        self.file_table.setColumnWidth(1, 520)
        layout.addWidget(self.file_table)

        row = QHBoxLayout()
        self.add_button = QPushButton("Add PDFs")
        self.add_button.clicked.connect(self.choose_pdfs)
        row.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected)
        row.addWidget(self.remove_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_files)
        row.addWidget(self.clear_button)
        row.addStretch()
        layout.addLayout(row)
        return group

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("Output Folder")
        layout = QHBoxLayout(group)
        self.output_edit = QLineEdit(str(self.output_dir))
        self.output_edit.setReadOnly(True)
        layout.addWidget(self.output_edit, stretch=1)

        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.choose_output_dir)
        layout.addWidget(self.browse_button)

        self.open_output_button = QPushButton("Open Output Folder")
        self.open_output_button.clicked.connect(self.open_output_folder)
        layout.addWidget(self.open_output_button)
        return group

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("Conversion Settings")
        layout = QGridLayout(group)

        layout.addWidget(QLabel("Device"), 0, 0)
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cpu", "cuda"])
        layout.addWidget(self.device_combo, 0, 1)

        self.overwrite_check = QCheckBox("Overwrite existing files")
        self.overwrite_check.setChecked(False)
        layout.addWidget(self.overwrite_check, 0, 2)

        self.keep_images_check = QCheckBox("Keep images")
        self.keep_images_check.setChecked(True)
        layout.addWidget(self.keep_images_check, 0, 3)

        layout.addWidget(QLabel("Filename fallback"), 1, 0)
        self.filename_combo = QComboBox()
        self.filename_combo.addItems(["title", "original"])
        layout.addWidget(self.filename_combo, 1, 1)
        layout.setColumnStretch(4, 1)
        return group

    def _build_progress_group(self) -> QGroupBox:
        group = QGroupBox("Conversion Progress")
        layout = QGridLayout(group)

        self.current_file_label = QLabel("Current file: -")
        layout.addWidget(self.current_file_label, 0, 0, 1, 4)

        self.total_label = QLabel("Total: 0")
        self.completed_label = QLabel("Completed: 0")
        self.success_label = QLabel("Succeeded: 0")
        self.failed_label = QLabel("Failed: 0")
        layout.addWidget(self.total_label, 1, 0)
        layout.addWidget(self.completed_label, 1, 1)
        layout.addWidget(self.success_label, 1, 2)
        layout.addWidget(self.failed_label, 1, 3)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar, 2, 0, 1, 4)
        return group

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("Status")
        layout = QVBoxLayout(group)
        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)
        return group

    def _build_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch()
        self.convert_button = QPushButton("Convert")
        self.convert_button.clicked.connect(self.start_conversion)
        row.addWidget(self.convert_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_conversion)
        row.addWidget(self.cancel_button)
        return row

    def choose_pdfs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add PDFs",
            str(self.last_pdf_dir),
            "PDF Files (*.pdf *.PDF)",
        )
        if files:
            self.last_pdf_dir = Path(files[0]).parent
            self.settings_store.setValue("last_pdf_dir", str(self.last_pdf_dir))
        self.add_pdf_paths([Path(file) for file in files])

    def add_pdf_paths(self, paths: list[Path]) -> None:
        invalid = [path for path in paths if not is_pdf_path(path)]
        if invalid:
            error = PDFtoMDError(
                ErrorCode.INVALID_INPUT,
                f"Only PDF files can be added: {invalid[0].name}",
            )
            show_user_error(self, "Invalid file", error)

        for path in paths:
            resolved = path.resolve()
            if not is_pdf_path(resolved) or resolved in self._paths:
                continue
            self.last_pdf_dir = resolved.parent
            self.settings_store.setValue("last_pdf_dir", str(self.last_pdf_dir))
            self._paths.append(resolved)
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)
            self.file_table.setItem(row, 0, QTableWidgetItem(resolved.name))
            path_item = QTableWidgetItem(str(resolved))
            path_item.setData(Qt.ItemDataRole.UserRole, str(resolved))
            self.file_table.setItem(row, 1, path_item)
            self.file_table.setItem(row, 2, QTableWidgetItem("pending"))
            logger.info("pdf_selected file=%s", resolved.name)
        self._update_progress(0, len(self._paths), 0, 0)

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.file_table.selectedIndexes()}, reverse=True)
        for row in rows:
            item = self.file_table.item(row, 1)
            if item is None:
                continue
            path = Path(item.data(Qt.ItemDataRole.UserRole))
            if path in self._paths:
                self._paths.remove(path)
            self.file_table.removeRow(row)
        self._update_progress(0, len(self._paths), 0, 0)

    def clear_files(self) -> None:
        self._paths.clear()
        self.file_table.setRowCount(0)
        self._update_progress(0, 0, 0, 0)
        self.current_file_label.setText("Current file: -")

    def choose_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Output Folder",
            str(self.output_dir),
        )
        if selected:
            self.output_dir = Path(selected)
            self.settings_store.setValue("output_dir", str(self.output_dir))
            self.output_edit.setText(str(self.output_dir))

    def open_output_folder(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))

    def start_conversion(self) -> None:
        if not self._paths:
            show_user_error(
                self,
                "No PDFs selected",
                PDFtoMDError(ErrorCode.INVALID_INPUT, "Add at least one PDF file."),
            )
            return

        settings = ConversionSettings(
            device=self.device_combo.currentText(),
            overwrite=self.overwrite_check.isChecked(),
            filename_fallback=self.filename_combo.currentText(),
            keep_images=self.keep_images_check.isChecked(),
        )
        self._set_running(True)
        self._set_all_pending()
        self._log("Loading marker model")
        self._worker = ConversionWorker(list(self._paths), self.output_dir, settings)
        self._worker.item_started.connect(self._on_item_started)
        self._worker.item_finished.connect(self._on_item_finished)
        self._worker.progress_changed.connect(self._update_progress)
        self._worker.status_message.connect(self._log)
        self._worker.finished_all.connect(self._on_finished_all)
        self._worker.start()

    def cancel_conversion(self) -> None:
        if self._worker is not None:
            self._worker.cancel()

    def _on_item_started(self, source_path: str) -> None:
        path = Path(source_path)
        self.current_file_label.setText(f"Current file: {path.name}")
        self._set_status(path, ConversionStatus.running.value)

    def _on_item_finished(self, result: ConversionResult) -> None:
        source = Path(result.source_path)
        self._set_status(source, result.status.value)
        if result.status == ConversionStatus.succeeded:
            self._log(f"Completed: {source.name} -> {result.output_path}")
        elif result.status == ConversionStatus.cancelled:
            self._log(f"Cancelled: {source.name}")
        else:
            self._log(
                f"Failed: {source.name} [{result.error_code}] {result.message}",
            )

    def _on_finished_all(self, _results: list[ConversionResult]) -> None:
        self._set_running(False)
        self.current_file_label.setText("Current file: -")
        self._worker = None

    def _update_progress(self, completed: int, total: int, succeeded: int, failed: int) -> None:
        self.total_label.setText(f"Total: {total}")
        self.completed_label.setText(f"Completed: {completed}")
        self.success_label.setText(f"Succeeded: {succeeded}")
        self.failed_label.setText(f"Failed: {failed}")
        self.progress_bar.setValue(0 if total == 0 else int((completed / total) * 100))

    def _set_status(self, path: Path, status: str) -> None:
        for row in range(self.file_table.rowCount()):
            item = self.file_table.item(row, 1)
            if item and Path(item.data(Qt.ItemDataRole.UserRole)) == path:
                self.file_table.setItem(row, 2, QTableWidgetItem(status))
                return

    def _set_all_pending(self) -> None:
        for row in range(self.file_table.rowCount()):
            self.file_table.setItem(row, 2, QTableWidgetItem(ConversionStatus.pending.value))

    def _set_running(self, running: bool) -> None:
        for button in (
            self.add_button,
            self.remove_button,
            self.clear_button,
            self.browse_button,
            self.convert_button,
        ):
            button.setEnabled(not running)
        self.cancel_button.setEnabled(running)

    def _log(self, message: str) -> None:
        self.log_edit.appendPlainText(message)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        self.add_pdf_paths(paths)
        event.acceptProposedAction()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        logger.info("app_closed")
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        super().closeEvent(event)


def create_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)
