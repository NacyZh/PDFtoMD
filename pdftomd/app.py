"""Application entrypoint."""

from __future__ import annotations

import os
import sys
from multiprocessing import freeze_support

from pdftomd.gui.main_window import MainWindow, create_app
from pdftomd.logging import configure_logging, get_logger


def main() -> int:
    freeze_support()
    dev_mode = os.getenv("PDFTOMD_DEV", "").lower() in {"1", "true", "yes"}
    configure_logging(dev_mode=dev_mode)
    logger = get_logger(__name__)
    logger.info("app_started")

    app = create_app()
    window = MainWindow()
    window.show()
    return int(app.exec())


if __name__ == "__main__":
    sys.exit(main())
