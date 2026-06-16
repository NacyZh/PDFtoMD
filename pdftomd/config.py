"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "PDFtoMD"
VALID_DEVICES = {"auto", "cpu", "cuda"}
VALID_FILENAME_FALLBACKS = {"title", "original"}


@dataclass(frozen=True)
class ConversionSettings:
    device: str = "auto"
    overwrite: bool = False
    filename_fallback: str = "title"
    keep_images: bool = True

    def __post_init__(self) -> None:
        if self.device not in VALID_DEVICES:
            raise ValueError(f"Unsupported device: {self.device}")
        if self.filename_fallback not in VALID_FILENAME_FALLBACKS:
            raise ValueError(f"Unsupported filename fallback: {self.filename_fallback}")


def default_output_dir() -> Path:
    documents = Path.home() / "Documents"
    return documents / APP_NAME


def user_data_dir() -> Path:
    if os.name == "nt":
        base = os.getenv("APPDATA")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Roaming" / APP_NAME

    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME
