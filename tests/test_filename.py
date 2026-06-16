from pathlib import Path

from pdftomd.converter.filename import build_markdown_filename, resolve_output_filename


def test_build_markdown_filename_keeps_chinese_title() -> None:
    assert build_markdown_filename("中文 论文标题", Path("source.pdf")) == "中文 论文标题.md"


def test_build_markdown_filename_replaces_windows_illegal_chars() -> None:
    assert (
        build_markdown_filename('A/B\\C:D*E?F"G<H>I|J', Path("x.pdf"))
        == "A_B_C_D_E_F_G_H_I_J.md"
    )


def test_build_markdown_filename_empty_title_falls_back_to_original_stem() -> None:
    assert build_markdown_filename("   ", Path("Original Name.pdf")) == "Original Name.md"


def test_resolve_output_filename_appends_number_when_file_exists(tmp_path: Path) -> None:
    (tmp_path / "Title.md").write_text("old", encoding="utf-8")
    (tmp_path / "Title (1).md").write_text("old", encoding="utf-8")

    assert resolve_output_filename(tmp_path, "Title.md", overwrite=False) == "Title (2).md"


def test_resolve_output_filename_overwrites_name(tmp_path: Path) -> None:
    (tmp_path / "Title.md").write_text("old", encoding="utf-8")

    assert resolve_output_filename(tmp_path, "Title.md", overwrite=True) == "Title.md"
