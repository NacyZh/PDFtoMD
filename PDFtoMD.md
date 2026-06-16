# PDFtoMD 可视化软件规格驱动开发文档

## 1. 产品定位

PDFtoMD 是一个面向本地用户的可视化 PDF 转 Markdown 软件。用户通过图形界面选择一个或多个 PDF 文件，软件调用 marker 将 PDF 内容转换为 Markdown，并保存为 `.md` 文件。

项目必须保持职责单一：

- 只做 PDF 到 Markdown 的转换。
- 不做 RAG。
- 不做向量数据库。
- 不做论文总结。
- 不做章节识别。
- 不做公式结构化提取。
- 不做 DOI、作者、页数等元数据输出。
- 不提供 CLI 作为主要交互入口。

PyMuPDF 的唯一职责是：从 PDF 中提取论文标题，用于生成 Markdown 文件名。

## 2. 核心用户流程

1. 用户打开 PDFtoMD 可视化软件。
2. 用户通过界面中的文件系统选择器选择 PDF 文件。
3. 用户选择输出目录。
4. 用户点击转换按钮。
5. 软件提取 PDF 标题，用标题生成 `.md` 文件名。
6. 软件调用 marker 将 PDF 转换为 Markdown。
7. 软件将 Markdown 写入输出目录。
8. 软件在界面中显示转换状态、进度、成功文件路径或失败原因。

## 3. 非目标

以下功能不得在首版实现：

- 不实现命令行批处理作为主要入口。
- 不识别章节。
- 不切分 chunk。
- 不提取公式列表。
- 不生成 metadata JSON。
- 不生成 YAML frontmatter。
- 不做 OCR 后处理。
- 不做 LLM 总结。
- 不做数据库写入。
- 不做网络同步。
- 不做云端模型调用。
- 不做论文去重。

## 4. 技术形态

项目应封装为桌面可视化软件。

推荐实现路线：

```text
Python + PySide6 + marker + PyMuPDF
```

理由：

- PySide6 适合构建本地桌面 GUI。
- Python 生态可直接复用 marker 和 PyMuPDF。
- 后续可用 PyInstaller 打包为 Windows/Linux 可执行程序。

可接受替代：

```text
Python + PyQt6
```

不推荐首版使用 Web UI 或 Electron，除非明确需要跨语言前端。

## 5. 运行平台

首版目标平台：

- Windows 11。
- Linux。
- WSL2 可用于开发和测试，但最终用户软件应支持 Windows 原生运行，前提是 marker 依赖可安装。

设备策略：

- 支持 `auto`、`cpu`、`cuda`。
- 默认 `auto`。
- `auto` 规则：优先 CUDA，失败或不可用时使用 CPU。
- 显式选择 `cuda` 但不可用时，界面必须显示明确错误，不得静默回退。

## 6. 项目结构

推荐目录：

```text
pdftomd/
  __init__.py
  app.py
  config.py
  errors.py
  logging.py
  models.py
  gui/
    __init__.py
    main_window.py
    widgets.py
    worker.py
    styles.py
  converter/
    __init__.py
    title_extractor.py
    marker_converter.py
    markdown_writer.py
    filename.py
  packaging/
    pyinstaller.spec
tests/
  test_title_extractor.py
  test_filename.py
  test_marker_converter.py
  test_markdown_writer.py
  test_worker.py
pyproject.toml
README.md
.env.example
```

模块边界：

- `gui/` 只负责界面和用户交互。
- `converter/` 只负责 PDF 转换逻辑。
- `title_extractor.py` 是唯一允许调用 PyMuPDF 的模块。
- `marker_converter.py` 是唯一允许调用 marker 的模块。
- `markdown_writer.py` 负责输出文件写入和覆盖策略。

## 7. GUI 规格

主窗口必须包含：

- PDF 文件选择区域。
- 输出目录选择区域。
- 转换设置区域。
- 转换进度区域。
- 日志/状态区域。
- 转换按钮。
- 取消按钮。

### 7.1 文件选择区域

必须支持：

- 点击按钮打开系统文件选择器。
- 支持选择单个 PDF。
- 支持选择多个 PDF。
- 支持拖拽 PDF 文件到窗口。
- 只接受 `.pdf` 文件，扩展名大小写不敏感。
- 对非 PDF 文件显示错误提示。

界面字段：

```text
Selected PDFs
Add PDFs
Remove Selected
Clear
```

每个已选文件应展示：

- 文件名。
- 完整路径。
- 状态：等待、转换中、成功、失败、已取消。

### 7.2 输出目录区域

必须支持：

- 点击按钮打开系统目录选择器。
- 显示当前输出目录。
- 默认输出目录为用户文档目录下的 `PDFtoMD` 文件夹。
- 如果输出目录不存在，转换前自动创建。

界面字段：

```text
Output Folder
Browse
Open Output Folder
```

### 7.3 转换设置区域

必须包含：

```text
Device: auto / cpu / cuda
Overwrite existing files: true / false
Filename fallback: title / original filename
```

默认设置：

```text
Device = auto
Overwrite existing files = false
Filename fallback = title
```

说明：

- `Filename fallback=title` 表示优先使用 PyMuPDF 提取的标题命名。
- 如果标题为空或无效，回退到 PDF 原文件名 stem。

### 7.4 进度区域

必须展示：

- 当前正在转换的文件名。
- 总文件数。
- 已完成数量。
- 成功数量。
- 失败数量。
- 总体进度条。

### 7.5 日志/状态区域

必须展示用户可理解的状态：

```text
Ready
Loading marker model
Converting
Writing markdown
Completed
Failed
Cancelled
```

失败时必须展示：

- 文件名。
- 错误码。
- 简短错误原因。
- 建议操作。

## 8. 后台任务与界面响应

转换任务必须在后台线程执行，禁止阻塞 GUI 主线程。

要求：

- 使用 `QThread` 或 `QRunnable/QThreadPool`。
- marker 模型加载和 PDF 转换都必须在后台执行。
- GUI 主线程只接收信号更新状态。
- 用户点击取消后，未开始的文件不得继续转换。
- 正在转换的单个 PDF 可等待当前 marker 调用结束后停止。

并发策略：

- 首版必须串行转换。
- 不允许同时转换多个 PDF。
- 原因：marker/torch 可能占用大量显存，同时转换容易导致显存不足。

## 9. PyMuPDF 标题提取规格

PyMuPDF 只能用于提取标题，不能用于正文抽取、页数输出、DOI 输出、作者输出或 metadata JSON。

必须实现：

```python
def extract_pdf_title(pdf_path: Path) -> str:
    ...
```

标题提取优先级：

1. `doc.metadata["title"]`。
2. 如果 metadata title 为空，从第一页文本前若干行启发式提取标题。
3. 如果仍失败，返回空字符串，由调用方回退到原文件名。

第一页启发式规则：

- 读取第一页 `page.get_text("text")`。
- 取前 20 行非空文本。
- 跳过过短行：长度小于 6。
- 跳过明显非标题行：
  - 包含 `doi`
  - 包含 `abstract`
  - 包含 `copyright`
  - 包含 `arxiv`
  - 包含邮箱 `@`
  - 纯数字或页码
- 优先选择长度在 10 到 180 字符之间的第一条候选行。
- 返回前必须去除多余空白。

异常处理：

- PDF 打不开时抛出结构化错误 `PDF_TITLE_EXTRACT_FAILED`。
- 标题提取失败但 PDF 可打开时返回空字符串，不视为转换失败。

## 10. 文件名生成规格

必须实现：

```python
def build_markdown_filename(title: str, source_pdf: Path) -> str:
    ...
```

规则：

- 优先使用标题。
- 标题为空时使用 PDF 原始文件 stem。
- 保留中文、英文、数字、空格、下划线、短横线。
- 将 `/ \ : * ? " < > |` 等非法文件名字符替换为 `_`。
- 连续空白压缩为单个空格。
- 连续 `_` 压缩为单个 `_`。
- 去除首尾空白、点号和下划线。
- 文件名最大长度 120 字符。
- 最终扩展名固定为 `.md`。
- 如果结果为空，使用 `document.md`。

重复文件处理：

- 如果 `overwrite=false` 且目标文件存在，自动追加序号：

```text
Title.md
Title (1).md
Title (2).md
```

- 如果 `overwrite=true`，直接覆盖。

## 11. marker 转换规格

必须实现：

```python
class MarkerMarkdownConverter:
    def __init__(self, device: str = "auto"):
        ...

    def convert(self, pdf_path: Path) -> str:
        ...

    def close(self) -> None:
        ...
```

要求：

- marker 必须 lazy import。
- 软件启动、打开主窗口、选择文件时不得加载 marker。
- 用户点击转换后才允许加载 marker。
- 同一个 converter 实例在一次批量转换中复用 marker converter。
- `close()` 必须 best-effort 释放资源。

推荐 lazy import：

```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
```

转换流程：

1. 确认 PDF 路径存在。
2. 确认扩展名为 `.pdf`。
3. lazy-load marker converter。
4. 调用 marker converter。
5. 调用 `text_from_rendered` 得到 Markdown。
6. Markdown 为空时失败。
7. 规范化 Markdown。
8. 返回 Markdown 字符串。

## 12. Markdown 规范化

必须实现：

```python
def normalize_markdown(text: str) -> str:
    ...
```

规则：

- 将 `\u00a0` 替换为空格。
- CRLF/CR 统一为 LF。
- 连续 3 个以上空行压缩为 2 个换行。
- 去除首尾空白。
- 不做章节识别。
- 不删除 references。
- 不改写公式。
- 不插入 YAML frontmatter。
- 不插入额外说明文本。

最终输出文件内容必须尽量接近 marker 原始 Markdown，只做最低限度清理。

## 13. 输出写入规格

必须实现：

```python
def write_markdown(markdown: str, output_dir: Path, filename: str, overwrite: bool) -> Path:
    ...
```

要求：

- 输出目录不存在时自动创建。
- 文件编码固定为 UTF-8。
- 换行使用 `\n`。
- 写入采用临时文件 + 原子替换：

```text
Title.md.tmp-<uuid>
Title.md
```

- 写入失败不得留下半成品目标文件。
- 如果写入失败，清理本次创建的临时文件。

## 14. 转换结果模型

必须定义：

```python
class ConversionStatus(str, Enum):
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
```

GUI 内部状态可使用 dataclass，但跨模块返回值建议使用 Pydantic model。

## 15. 错误码

必须定义结构化错误：

```text
INVALID_INPUT
PDF_NOT_FOUND
PDF_NOT_READABLE
PDF_TITLE_EXTRACT_FAILED
MARKER_IMPORT_FAILED
MARKER_MODEL_LOAD_FAILED
MARKER_RENDER_FAILED
MARKER_EMPTY_OUTPUT
OUTPUT_DIR_CREATE_FAILED
OUTPUT_WRITE_FAILED
CONVERSION_CANCELLED
UNHANDLED_ERROR
```

错误对象：

```python
class PDFtoMDError(RuntimeError):
    error_code: str
    suggestion: str
```

GUI 展示：

- 不展示 Python traceback 给普通用户。
- 日志文件中可以记录 traceback。
- 界面展示错误码、简短原因和建议。

## 16. 日志规格

必须实现日志：

- 日志目录默认：用户应用数据目录下 `PDFtoMD/logs`。
- 文件日志启用 rotation。
- 控制台日志仅开发模式启用。
- 日志编码 UTF-8。

关键事件：

```text
app_started
pdf_selected
conversion_started
title_extracted
marker_loading
marker_loaded
marker_render_started
marker_render_finished
markdown_written
conversion_failed
conversion_cancelled
app_closed
```

日志不得记录：

- 用户完整环境变量。
- 任何 token 或密钥。

## 17. GUI 视觉与交互要求

界面应是实用型桌面工具，不做营销页。

设计要求：

- 第一屏就是转换工具。
- 不使用大幅 hero 区。
- 不使用说明性装饰卡片。
- 使用清晰的文件列表、按钮、进度条和状态栏。
- 按钮必须有明确图标或文本：
  - Add PDFs
  - Browse
  - Convert
  - Cancel
  - Open Output Folder
- 文本不得在小窗口下溢出。
- 最小窗口尺寸建议 `900x600`。
- 支持窗口缩放。

## 18. 打包规格

必须支持 PyInstaller 打包。

推荐命令：

```bash
python -m PyInstaller packaging/pyinstaller.spec
```

打包要求：

- Windows 输出 `.exe`。
- 应包含必要的 marker 运行依赖。
- 首次运行时如 marker 需要下载模型，应在界面显示“正在加载模型，首次运行可能较慢”。
- 打包后日志仍应写入用户应用数据目录。

## 19. 测试规格

测试不得下载真实 marker 模型。

### 19.1 单元测试

必须覆盖：

- `extract_pdf_title()` metadata title。
- `extract_pdf_title()` 首页启发式标题。
- `extract_pdf_title()` PDF 打不开。
- `build_markdown_filename()` 中文标题。
- `build_markdown_filename()` Windows 非法字符。
- `build_markdown_filename()` 空标题回退原文件名。
- `build_markdown_filename()` 重名追加序号。
- `normalize_markdown()`。
- `write_markdown()` UTF-8 写入。
- `write_markdown()` 原子写入失败清理。
- marker lazy import。
- marker 空输出错误。

### 19.2 GUI 测试

如果使用 PySide6，使用 `pytest-qt`。

必须覆盖：

- 添加 PDF 后文件列表出现记录。
- 移除选中文件。
- 清空列表。
- 选择输出目录。
- 点击转换后按钮状态变化。
- worker 成功信号更新状态。
- worker 失败信号更新状态。
- 取消按钮触发取消标志。

### 19.3 集成测试

使用 PyMuPDF 动态创建最小 PDF：

```python
doc = fitz.open()
page = doc.new_page()
page.insert_text((72, 72), "A Demo Paper Title\n\nThis is content.")
doc.save(path)
doc.close()
```

marker converter 在集成测试中必须 mock。

## 20. 质量门禁

交付前必须通过：

```bash
pytest tests -q
ruff check pdftomd tests
mypy pdftomd --no-sqlite-cache
python -m build
```

GUI 测试环境如无显示器，必须支持 offscreen：

```bash
QT_QPA_PLATFORM=offscreen pytest tests -q
```

## 21. README 要求

README 必须包含：

- 软件用途。
- 安装方式。
- 启动方式。
- 如何选择 PDF。
- 如何选择输出目录。
- CPU/CUDA 说明。
- 首次加载 marker 较慢说明。
- 常见错误码。
- Windows 打包说明。

## 22. 最小可接受版本

首版必须完成：

- PySide6 主窗口。
- PDF 文件选择器。
- 输出目录选择器。
- 单文件和多文件转换。
- PyMuPDF 标题提取，仅用于文件命名。
- marker PDF 到 Markdown。
- Markdown 文件写入。
- 串行后台转换 worker。
- 进度展示。
- 错误展示。
- 日志。
- 单元测试。
- GUI 基础测试。

首版不需要：

- CLI。
- 章节识别。
- 公式识别。
- metadata JSON。
- YAML frontmatter。
- 数据库。
- LLM。
- Web 服务。

## 23. AI 实现约束

AI 根据本文档实现项目时必须遵守：

- 不要实现 CLI 优先项目。
- 不要加入 RAG 相关功能。
- 不要加入章节识别、公式识别或 metadata JSON。
- 不要让 PyMuPDF 参与正文提取。
- 不要在软件启动时加载 marker。
- 不要阻塞 GUI 主线程。
- 不要并发转换多个 PDF。
- 不要在用户未确认 overwrite 时覆盖已有文件。
- 不要将 traceback 直接展示给普通用户。
- 不要在测试中下载真实 marker 模型。

## 24. 验收标准

实现完成后必须满足：

1. 用户可以通过 GUI 选择 PDF 文件。
2. 用户可以通过 GUI 选择输出目录。
3. 点击转换后，界面不会卡死。
4. 转换成功后，输出目录中出现 `.md` 文件。
5. `.md` 文件名优先来自 PyMuPDF 提取的 PDF 标题。
6. 标题为空时，`.md` 文件名回退为原 PDF 文件名。
7. Markdown 内容来自 marker 转换结果。
8. 输出 Markdown 不包含软件额外添加的 frontmatter。
9. 多文件转换时，单个失败不影响其它文件。
10. 取消后，未开始的文件不再转换。
11. marker import 失败时，界面显示 `MARKER_IMPORT_FAILED`。
12. 输出文件已存在且 overwrite=false 时，自动追加序号。
13. 所有测试、ruff、mypy、build 通过。
