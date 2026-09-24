import argparse
import json
import os
import sys
import time
from pathlib import Path

from markitdown import MarkItDown

from .ocr_manager import OCRManager

HISTORY_FILE = Path.home() / ".markitdown-ui" / "history.jsonl"

SUPPORTED_EXTS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
    ".html", ".htm", ".xml", ".csv", ".json", ".epub",
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".gif",
    ".wav", ".mp3",
}


def _log_entry(entry: dict) -> None:
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _collect_files(paths: list[str], recursive: bool, include_filter: set[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_file():
            if not include_filter or path.suffix.lower() in include_filter:
                files.append(path)
        elif path.is_dir():
            it = path.rglob("*") if recursive else path.glob("*")
            for child in it:
                if child.is_file() and (
                    not include_filter or child.suffix.lower() in include_filter
                ):
                    files.append(child)
    return sorted(set(files))


def run_cli(args: argparse.Namespace) -> int:
    engine = MarkItDown()
    ocr = OCRManager(engine, config={
        "ocr_languages": args.ocr_lang,
        "ocr_gpu": args.gpu,
    })

    if args.list_backends:
        for b in ocr.get_all_names():
            print(b)
        return 0

    if args.backend:
        ocr.set_active(args.backend)
    active = ocr.get_active()
    print(f"OCR backend: {active.get_name() if active else 'none'}")

    out_dir = Path(args.output) if args.output else Path.cwd()
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    include = {f".{e.lstrip('.')}" for e in args.include} if args.include else SUPPORTED_EXTS
    files = _collect_files(args.paths, args.recursive, include)

    if not files:
        print("No matching files found.")
        return 1

    ok, err, skipped = 0, 0, 0
    started = time.time()

    for f in files:
        dst = out_dir / (f.stem + ".md")
        if dst.exists() and not args.overwrite:
            print(f"[skip] {f}")
            skipped += 1
            continue
        if args.dry_run:
            print(f"[dry]  {f} -> {dst.name}")
            ok += 1
            continue
        print(f"[conv] {f} -> {dst.name}", flush=True)
        try:
            result = engine.convert(str(f))
            markdown_out = result.markdown
            markdown_out = _apply_ocr_if_needed(ocr, f, markdown_out)
            dst.write_text(markdown_out, encoding="utf-8")
            ok += 1
            used_ocr = active is not None and not active.get_name().startswith("MarkItDown")
            _log_entry({
                "ts": time.time(),
                "file": str(f),
                "out": str(dst),
                "status": "ok",
                "ocr": used_ocr,
            })
        except Exception as exc:
            err += 1
            print(f"[fail] {f}: {exc}")
            _log_entry({"ts": time.time(), "file": str(f), "status": "error", "error": str(exc)})

    elapsed = time.time() - started
    print(f"\nDone in {elapsed:.1f}s: {ok} ok, {err} errors, {skipped} skipped")
    return 0 if err == 0 else 1


def _apply_ocr_if_needed(ocr, f: Path, markdown_out: str) -> str:
    active = ocr.get_active()
    if active is None or active.get_name().startswith("MarkItDown"):
        return markdown_out
    if f.suffix.lower() in IMAGE_LIKE:
        text = active.extract_text(f)
        if text:
            return f"*[Image OCR]\n{text}\n[End OCR]*\n\n{markdown_out}"
    return markdown_out


IMAGE_LIKE = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markitdown-ui",
        description="Offline file-to-Markdown converter with OCR (GUI or CLI)",
    )
    parser.add_argument("paths", nargs="*", help="Files or folders to convert")
    parser.add_argument("--gui", action="store_true", help="Launch the graphical interface")
    parser.add_argument("-o", "--output", help="Destination folder (default: current dir)")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan folders recursively")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .md files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be converted")
    parser.add_argument("--include", nargs="*", help="Only these extensions (e.g. pdf docx)")
    parser.add_argument("--ocr-lang", nargs="*", default=["en"], help="OCR languages")
    parser.add_argument("--backend", help="OCR backend name (see --list-backends)")
    parser.add_argument("--list-backends", action="store_true", help="List available OCR backends")
    parser.add_argument("--gpu", action="store_true", help="Use GPU for EasyOCR if available")
    parser.add_argument("-v", "--version", action="version", version="markitdown-ui 1.2.0")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.gui or (not args.paths and not args.list_backends):
        from .gui import main as gui_main
        gui_main()
        return 0
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())