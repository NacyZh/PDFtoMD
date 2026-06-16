"""Shared conversion result models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ConversionStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class ConversionResult(BaseModel):
    source_path: str
    output_path: str = ""
    title: str = ""
    status: ConversionStatus
    error_code: str = ""
    message: str = ""
