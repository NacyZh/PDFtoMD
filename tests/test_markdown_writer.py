from pathlib import Path

import pytest
from PIL import Image

from pdftomd.converter.markdown_writer import write_markdown
from pdftomd.errors import ErrorCode, PDFtoMDError


def test_write_markdown_writes_utf8_and_lf(tmp_path: Path) -> None:
    output = write_markdown("A\r\n中文", tmp_path / "out", "Title.md", overwrite=False)

    assert output.read_bytes() == "A\n中文".encode()


def test_write_markdown_atomic_failure_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_replace(source: str | Path, target: str | Path) -> None:
        raise OSError(f"cannot replace {source} -> {target}")

    monkeypatch.setattr("pdftomd.converter.markdown_writer.os.replace", fail_replace)

    with pytest.raises(PDFtoMDError) as exc_info:
        write_markdown("content", tmp_path, "Title.md", overwrite=False)

    assert exc_info.value.error_code == ErrorCode.OUTPUT_WRITE_FAILED
    assert not (tmp_path / "Title.md").exists()
    assert list(tmp_path.glob("*.tmp-*")) == []


def test_write_markdown_writes_marker_images_and_rewrites_links(tmp_path: Path) -> None:
    image = Image.new("RGB", (2, 2), color="white")

    output = write_markdown(
        "![figure](image 1.png)",
        tmp_path,
        "Title.md",
        overwrite=False,
        images={"image 1.png": image},
    )

    assert output.read_text(encoding="utf-8") == "![[Title_assets/image 1.png]]"
    assert (tmp_path / "Title_assets" / "image 1.png").exists()


def test_write_markdown_rewrites_dot_slash_image_links(tmp_path: Path) -> None:
    image = Image.new("RGB", (2, 2), color="white")

    output = write_markdown(
        "![figure](./figure.png)",
        tmp_path,
        "Title.md",
        overwrite=False,
        images={"figure.png": image},
    )

    assert output.read_text(encoding="utf-8") == "![[Title_assets/figure.png]]"


def test_write_markdown_without_images_does_not_create_assets_dir(tmp_path: Path) -> None:
    output = write_markdown(
        "![figure](image.png)",
        tmp_path,
        "Title.md",
        overwrite=False,
        images=None,
    )

    assert output.read_text(encoding="utf-8") == "![figure](image.png)"
    assert not (tmp_path / "Title_assets").exists()
