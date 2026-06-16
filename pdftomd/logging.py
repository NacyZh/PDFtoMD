"""Application logging setup."""

from __future__ import annotations

import logging as py_logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pdftomd.config import user_data_dir

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(dev_mode: bool = False, log_dir: Path | None = None) -> Path:
    resolved_log_dir = log_dir or user_data_dir() / "logs"
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    log_file = resolved_log_dir / "pdftomd.log"

    root = py_logging.getLogger("pdftomd")
    root.setLevel(py_logging.DEBUG if dev_mode else py_logging.INFO)
    root.handlers.clear()

    formatter = py_logging.Formatter(LOG_FORMAT)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if dev_mode:
        console_handler = py_logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    return log_file


def get_logger(name: str) -> py_logging.Logger:
    return py_logging.getLogger(f"pdftomd.{name}")
