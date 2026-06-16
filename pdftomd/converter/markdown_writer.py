"""Atomic Markdown output writer."""

from __future__ import annotations

import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from pdftomd.converter.filename import resolve_output_filename
from pdftomd.errors import ErrorCode, PDFtoMDError

IMAGE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._ -]+")
MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*]\(([^)]+)\)")


def _safe_image_name(name: str, index: int) -> str:
    source = Path(name).name or f"image-{index}.png"
    stem = IMAGE_NAME_PATTERN.sub("_", Path(source).stem).strip(" ._") or f"image-{index}"
    suffix = Path(source).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}:
        suffix = ".png"
    return f"{stem[:80].strip(' ._')}{suffix}"


def _unique_name(name: str, used: set[str]) -> str:
    if name not in used:
        used.add(name)
        return name

    path = Path(name)
    index = 1
    while True:
        candidate = f"{path.stem} ({index}){path.suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def _save_image(image: Any, path: Path) -> None:
    if isinstance(image, bytes):
        path.write_bytes(image)
        return
    if isinstance(image, bytearray):
        path.write_bytes(bytes(image))
        return
    if isinstance(image, Path):
        shutil.copyfile(image, path)
        return
    if isinstance(image, str):
        source = Path(image)
        if source.exists():
            shutil.copyfile(source, path)
            return

    save = getattr(image, "save", None)
    if callable(save):
        save(path)
        return

    raise TypeError(f"Unsupported marker image type: {type(image)!r}")


def _replace_image_references(markdown: str, replacements: dict[str, str]) -> str:
    def replace_markdown_image(match: re.Match[str]) -> str:
        target = match.group(1).strip().strip("<>")
        normalized_target = target[2:] if target.startswith("./") else target
        replacement = replacements.get(normalized_target)
        if replacement is None:
            return match.group(0)
        return f"![[{replacement}]]"

    updated = MARKDOWN_IMAGE_PATTERN.sub(replace_markdown_image, markdown)
    for original, replacement in replacements.items():
        updated = updated.replace(f"![[./{original}]]", f"![[{replacement}]]")
        updated = updated.replace(f"![[{original}]]", f"![[{replacement}]]")
    return updated


def _write_images(
    markdown: str,
    images: dict[str, Any],
    tmp_assets_dir: Path,
    assets_dir_name: str,
) -> str:
    if not images:
        return markdown

    tmp_assets_dir.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()
    replacements: dict[str, str] = {}
    for index, (original_name, image) in enumerate(images.items(), start=1):
        safe_name = _unique_name(_safe_image_name(original_name, index), used_names)
        _save_image(image, tmp_assets_dir / safe_name)
        replacements[original_name] = f"{assets_dir_name}/{safe_name}"

    return _replace_image_references(markdown, replacements)


def write_markdown(
    markdown: str,
    output_dir: Path,
    filename: str,
    overwrite: bool,
    images: dict[str, Any] | None = None,
) -> Path:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise PDFtoMDError(
            ErrorCode.OUTPUT_DIR_CREATE_FAILED,
            f"Could not create output folder: {output_dir}",
        ) from exc

    final_name = resolve_output_filename(output_dir, filename, overwrite)
    final_path = output_dir / final_name
    tmp_path = output_dir / f"{final_name}.tmp-{uuid.uuid4().hex}"
    assets_dir = output_dir / f"{final_path.stem}_assets"
    tmp_assets_dir = output_dir / f"{assets_dir.name}.tmp-{uuid.uuid4().hex}"

    try:
        markdown_with_images = _write_images(
            markdown,
            images or {},
            tmp_assets_dir,
            assets_dir.name,
        )
        normalized = markdown_with_images.replace("\r\n", "\n").replace("\r", "\n")
        tmp_path.write_text(normalized, encoding="utf-8", newline="\n")
        os.replace(tmp_path, final_path)
        if images:
            if assets_dir.exists():
                shutil.rmtree(assets_dir)
            os.replace(tmp_assets_dir, assets_dir)
    except Exception as exc:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
            if tmp_assets_dir.exists():
                shutil.rmtree(tmp_assets_dir)
        except OSError:
            pass
        raise PDFtoMDError(
            ErrorCode.OUTPUT_WRITE_FAILED,
            f"Could not write Markdown file: {final_path.name}",
        ) from exc

    return final_path
