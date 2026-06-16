# PDFtoMD

[中文文档](README_ZH.md)

PDFtoMD is a local desktop application that converts one or more PDF files to Markdown. It uses PySide6 for the GUI, PyMuPDF only to extract a PDF title for output naming, and marker for PDF-to-Markdown conversion.

PDFtoMD only converts PDF to Markdown. 

## Hardware Requirements

PDFtoMD depends on marker. On first use, marker may download about 3.5 GB of model files for layout analysis and OCR-assisted conversion.

Recommended:

- NVIDIA GPU with CUDA support
- At least 8 GB VRAM for typical academic PDFs; more for scanned or image-heavy PDFs
- 16 GB or more system RAM
- Stable network access for the first model download

CPU mode is supported but can be very slow. Machines without CUDA are not recommended for large PDFs or batch conversion.

## Windows Install

Install Python 3.11 or newer and enable **Add python.exe to PATH**.

Open PowerShell in the project directory:

```powershell
cd D:\pdftomd
py -3.11 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
```

For NVIDIA GPU acceleration, install a CUDA-enabled PyTorch wheel first. Example for CUDA 12.8:

```powershell
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

For other CUDA versions, use the PyTorch selector:
<https://pytorch.org/get-started/locally/>

Install PDFtoMD:

```powershell
python -m pip install -e .
```

Verify CUDA:

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

## Linux Install

```bash
cd /mnt/d/pdftomd
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Start

```bash
python -m pdftomd.app
```

After installation, you can also run:

```bash
pdftomd
```

## Use

1. Click **Add PDFs** to select one or more PDFs, or drag PDFs into the window.
2. Click **Browse** to choose an output folder. The default is `Documents/PDFtoMD`.
3. Choose the device: `auto`, `cpu`, or `cuda`.
4. Enable **Overwrite existing files** only if replacement is intended.
5. Keep **Keep images** checked to save marker images, or uncheck it for Markdown only.
6. Click **Convert**.

Output filenames prefer the PDF title extracted by PyMuPDF. If no valid title is found, PDFtoMD uses the original PDF filename. Existing files are not overwritten by default; numbered names such as `Title (1).md` are used instead.

The PDF picker and output folder picker remember the last selected directory. PDF paths containing Chinese or other non-ASCII characters are staged to a short ASCII temporary path before marker conversion; output naming still uses the original PDF path and extracted title.

## CPU, CUDA, and Cancel

`auto` tries CUDA first and falls back to CPU if CUDA is unavailable. If `cuda` is explicitly selected but unavailable, the GUI shows an error instead of silently falling back.

The first conversion can be slow because marker may download or load models, and PyTorch/CUDA needs initialization. PDFtoMD runs marker in a dedicated child process. Cancelling conversion terminates that child process, interrupts the current conversion, and releases GPU memory held by that process; the current PDF and remaining queued PDFs are marked as cancelled.

## Image Output

When **Keep images** is enabled, PDFtoMD creates an assets folder next to the Markdown file:

```text
Title.md
Title_assets/
  image 1.png
```

Local image references use wiki-link image syntax:

```text
![[Title_assets/image 1.png]]
```

When **Keep images** is disabled, marker images are not saved and no assets folder is created.

## Windows Packaging

```powershell
.\.venv\Scripts\activate
python -m pip install pyinstaller
python -m PyInstaller packaging\pyinstaller.spec
```

The executable is created at:

```text
dist\PDFtoMD\PDFtoMD.exe
```

## Common Error Codes

- `INVALID_INPUT`: Select valid PDFs and a writable output folder.
- `PDF_TITLE_EXTRACT_FAILED`: PyMuPDF could not open the PDF for title extraction.
- `MARKER_IMPORT_FAILED`: marker or its dependencies are not installed.
- `MARKER_MODEL_LOAD_FAILED`: Model loading failed; check CUDA, VRAM, or RAM.
- `MARKER_RENDER_FAILED`: marker conversion failed; the GUI shows a short underlying error summary.
- `MARKER_EMPTY_OUTPUT`: marker returned empty Markdown.
- `OUTPUT_DIR_CREATE_FAILED`: Failed to create the output folder.
- `OUTPUT_WRITE_FAILED`: Failed to write Markdown; check permissions and disk space.
- `CONVERSION_CANCELLED`: Conversion was cancelled.
