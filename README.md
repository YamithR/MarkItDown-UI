# MarkItDown UI

A cross-platform desktop app + CLI for [Microsoft MarkItDown](https://github.com/microsoft/markitdown), the Python utility for converting various file formats to Markdown — with **fully offline OCR** (EasyOCR / Tesseract), drag & drop, batch conversion and no cloud dependencies.

Convert PDF, DOCX, PPTX, XLSX, HTML, images, audio, EPUB, CSV, and many other formats — all locally.

---

## Features

- **Offline OCR (no AI, no APIs)** — three-tier backend, auto-selected:
  - **EasyOCR** (best quality, 80+ languages, CPU or GPU)
  - **Tesseract** (fast, lightweight)
  - **MarkItDown built-in** (zero extra dependencies)
- **Scanned PDF detection** — pages without a text layer are rendered and OCR'd page by page
- **Image OCR** — JPG/PNG/TIFF/WEBP/BMP/GIF get direct OCR, wrapped in `*[Image OCR]...*` blocks
- **Batch conversion** — drag & drop or browse multiple files, one-click convert
- **Per-file status + size + OCR indicator** in the file list
- **Determinate progress bar** with live per-file status
- **CLI / headless mode** — batch folders, recursive scan, dry-run, extension filters
- **Conversion history** — JSONL log at `~/.markitdown-ui/history.jsonl`
- **EN/ES language switching** in the GUI
- **Windows `.exe`** (PyInstaller) and **Linux `.deb`** packaging

## Screenshot

![MarkItDown UI](screenshots/captura.png)

---

## Quick Start

### Option 1 — Windows executable

Download `markitdown-ui-<version>-windows.exe` from the [Releases](https://github.com/YamithR/MarkItDown-UI/releases) page. No installation required — double-click to run.

### Option 2 — Install via `.deb` (Debian / Ubuntu)

```bash
sudo dpkg -i markitdown-gui_*.deb
sudo apt install -f
```

The package automatically installs the Python dependencies during installation. Launch from the applications menu or via:

```bash
markitdown-gui          # GUI
markitdown-gui --help   # CLI
```

### Option 3 — Run from source

```bash
git clone https://github.com/YamithR/MarkItDown-UI.git
cd MarkItDown-UI

pip install "markitdown[all]" PyMuPDF Pillow pytesseract tkinterdnd2
python3 src/markitdown_ui/gui.py        # GUI
python3 -m markitdown_ui --help         # CLI
```

---

## CLI usage

```bash
# Convert files/folders to the current directory
python3 -m markitdown_ui document.pdf report.xlsx

# Batch convert a folder recursively into ./out
python3 -m markitdown_ui ./docs -o ./out -r

# Only PDFs and DOCX, overwrite existing outputs
python3 -m markitdown_ui ./docs -o ./out --include pdf docx --overwrite

# Preview what would happen without writing anything
python3 -m markitdown_ui ./docs --dry-run

# OCR options
python3 -m markitdown_ui image.png -o . --ocr-lang en es --backend "EasyOCR (en, es)"
python3 -m markitdown_ui --list-backends
```

---

## Dependencies

| Dependency | Purpose | Install |
|-----------|---------|---------|
| Python ≥ 3.10 | runtime | apt / python.org |
| Tkinter | GUI | apt `python3-tk` |
| [MarkItDown](https://github.com/microsoft/markitdown)[all] | conversion engine | `pip install "markitdown[all]"` |
| PyMuPDF | PDF page rendering for scanned OCR | `pip install PyMuPDF` |
| Pillow | image handling | `pip install Pillow` |
| pytesseract | Tesseract OCR backend | `pip install pytesseract` (+ `tesseract-ocr` system package) |
| tkinterdnd2 | drag & drop (optional, graceful fallback) | `pip install tkinterdnd2` |
| easyocr + torch | high-quality offline OCR, 80+ languages (optional, ~1.5 GB) | `pip install easyocr` |

All conversion and OCR runs **100% locally**. No API keys, no telemetry, no uploads.

---

## Build from source

### Linux `.deb`

```bash
sudo apt install python3-tk python3-pip python3-pil
bash build-deb.sh
sudo dpkg -i dist/markitdown-gui_*.deb
```

### Windows `.exe`

```powershell
# PowerShell, on Windows
pip install pyinstaller "markitdown[all]" PyMuPDF Pillow pytesseract tkinterdnd2
# optional: pip install easyocr torch torchvision  # bundles offline OCR into the exe
powershell -ExecutionPolicy Bypass -File build-windows.ps1
```

Alternatively, push a `v*` tag and GitHub Actions builds and attaches both packages to a Release automatically.

---

## Project Structure

```
MarkItDown-UI/
├── .github/workflows/build.yml   # CI: builds .deb + .exe, publishes Releases
├── assets/                       # icon.ico (Windows), icon.png (Linux)
├── build-deb.sh                  # Build the .deb package
├── build-windows.ps1             # Build the Windows .exe
├── markitdown-ui.spec            # PyInstaller config
├── entrypoint.py                 # Frozen-app entry point
├── requirements.txt
└── src/markitdown_ui/
    ├── __init__.py
    ├── __main__.py               # python3 -m markitdown_ui (CLI/GUI dispatch)
    ├── cli.py                    # Headless CLI (batch/dry-run/history)
    ├── gui.py                    # Tkinter GUI (drag & drop, OCR panel)
    ├── ocr_backends.py           # EasyOCR / Tesseract / Builtin backends
    └── ocr_manager.py            # Backend auto-detection & selection
```

---

## Credits

This project is a front‑end for the excellent **[Microsoft MarkItDown](https://github.com/microsoft/markitdown)** library, created by Adam Fourney and contributors. All file conversion logic is handled by the upstream project. OCR backends: [EasyOCR](https://github.com/JaidedAI/EasyOCR) and Tesseract.

---

## License

MIT License. See [LICENSE](LICENSE).