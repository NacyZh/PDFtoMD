"""Markdown filename generation."""

from __future__ import annotations

import re
from pathlib import Path

INVALID_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|]')
WHITESPACE = re.compile(r"\s+")
UNDERSCORES = re.compile(r"_+")
MAX_STEM_LENGTH = 120


def sanitize_filename_stem(value: str) -> str:
    stem = INVALID_FILENAME_CHARS.sub("_", value)
    stem = WHITESPACE.sub(" ", stem)
    stem = UNDERSCORES.sub("_", stem)
    stem = stem.strip(" ._")
    if len(stem) > MAX_STEM_LENGTH:
        stem = stem[:MAX_STEM_LENGTH].strip(" ._")
    return stem or "document"


def build_markdown_filename(title: str, source_pdf: Path) -> str:
    stem_source = title.strip() if title.strip() else source_pdf.stem
    return f"{sanitize_filename_stem(stem_source)}.md"


def resolve_output_filename(output_dir: Path, filename: str, overwrite: bool) -> str:
    candidate = sanitize_filename_stem(Path(filename).stem)
    suffix = ".md"
    if overwrite:
        return f"{candidate}{suffix}"

    path = output_dir / f"{candidate}{suffix}"
    if not path.exists():
        return path.name

    index = 1
    while True:
        numbered_stem = f"{candidate} ({index})"
        if len(numbered_stem) > MAX_STEM_LENGTH:
            base_limit = MAX_STEM_LENGTH - len(f" ({index})")
            numbered_stem = f"{candidate[:base_limit].strip(' ._')} ({index})"
        numbered = output_dir / f"{numbered_stem}{suffix}"
        if not numbered.exists():
            return numbered.name
        index += 1
