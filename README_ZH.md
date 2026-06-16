# PDFtoMD

[English](README.md)

PDFtoMD 是一个本地桌面软件，用于把一个或多个 PDF 文件转换为 Markdown 文件。软件使用 PySide6 构建图形界面，使用 PyMuPDF 仅提取 PDF 标题用于文件命名，使用 marker 完成 PDF 到 Markdown 的转换。

PDFtoMD 只做 PDF 转 Markdown，不提供 RAG、向量数据库、论文总结、章节识别、元数据 JSON、YAML frontmatter 或云端模型调用。

## 硬件要求

PDFtoMD 依赖 marker。首次使用时，marker 可能下载约 3.5 GB 模型文件，用于版面分析和 OCR 辅助转换。

推荐配置：

- NVIDIA GPU 和可用 CUDA 环境
- 常规论文 PDF 建议至少 8 GB 显存，图片多或扫描版 PDF 建议更高显存
- 16 GB 或以上内存
- 首次运行时需要稳定网络下载模型

CPU 模式可以运行，但速度会非常慢。不支持 CUDA 的机器不建议批量转换大 PDF。

## Windows 安装

安装 Python 3.11 或更新版本，并在安装时勾选 **Add python.exe to PATH**。

在 PowerShell 中进入项目目录：

```powershell
cd D:\pdftomd
py -3.11 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
```

如果使用 NVIDIA GPU，先安装 CUDA 版 PyTorch。以下是 CUDA 12.8 示例：

```powershell
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

如果你的显卡驱动需要其他 CUDA 版本，请在 PyTorch 官方安装页选择对应命令：
<https://pytorch.org/get-started/locally/>

安装 PDFtoMD：

```powershell
python -m pip install -e .
```

验证 CUDA：

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

## Linux 安装

```bash
cd /mnt/d/pdftomd
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## 启动

```bash
python -m pdftomd.app
```

安装后也可以运行：

```bash
pdftomd
```

## 使用

1. 点击 **Add PDFs** 选择一个或多个 PDF，也可以拖拽 PDF 到窗口。
2. 点击 **Browse** 选择输出目录，默认目录是 `Documents/PDFtoMD`。
3. 选择设备：`auto`、`cpu` 或 `cuda`。
4. 按需选择 **Overwrite existing files**。
5. 勾选 **Keep images** 会保存 marker 输出图片；取消勾选则只生成 Markdown。
6. 点击 **Convert** 开始转换。

文件名默认优先使用 PyMuPDF 提取的 PDF 标题。标题为空时使用原始 PDF 文件名。未开启覆盖时，已有文件会自动追加序号，例如 `Title (1).md`。

PDF 文件选择器和输出目录选择器会记住上一次选择的目录。包含中文或其他非 ASCII 字符的 PDF 路径会在转换前自动暂存为短 ASCII 路径；输出命名仍使用原始 PDF 路径和提取标题。

## CPU、CUDA 和取消

`auto` 会优先使用 CUDA，不可用时回退到 CPU。显式选择 `cuda` 但 CUDA 不可用时，界面会显示错误，不会静默回退。

首次转换通常较慢，因为 marker 需要下载或加载模型，PyTorch/CUDA 也需要初始化。PDFtoMD 在独立子进程中运行 marker。点击取消时会终止 marker 子进程，中断当前转换并释放该进程持有的 GPU 显存；当前 PDF 和剩余队列文件会标记为已取消。

## 图片输出

启用 **Keep images** 时，PDFtoMD 会在 Markdown 文件旁创建资源目录：

```text
Title.md
Title_assets/
  image 1.png
```

Markdown 中的本地图片引用使用 wiki-link 图片格式：

```text
![[Title_assets/image 1.png]]
```

关闭 **Keep images** 时，不保存 marker 图片，也不会创建 assets 文件夹。

## Windows 打包

```powershell
.\.venv\Scripts\activate
python -m pip install pyinstaller
python -m PyInstaller packaging\pyinstaller.spec
```

生成的可执行文件位于：

```text
dist\PDFtoMD\PDFtoMD.exe
```

## 常见错误码

- `INVALID_INPUT`：请选择有效 PDF 和可写输出目录。
- `PDF_TITLE_EXTRACT_FAILED`：PyMuPDF 无法打开 PDF 提取标题。
- `MARKER_IMPORT_FAILED`：marker 或其依赖未安装。
- `MARKER_MODEL_LOAD_FAILED`：模型加载失败，检查 CUDA、显存或内存。
- `MARKER_RENDER_FAILED`：marker 转换失败，界面会显示底层异常摘要。
- `MARKER_EMPTY_OUTPUT`：marker 返回空 Markdown。
- `OUTPUT_DIR_CREATE_FAILED`：输出目录创建失败。
- `OUTPUT_WRITE_FAILED`：Markdown 写入失败，检查权限和磁盘空间。
- `CONVERSION_CANCELLED`：转换已取消。
