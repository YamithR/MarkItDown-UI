"""JSONL server mode: persistent stdin/stdout bridge for the Electron UI.

Protocol (one JSON object per line, both directions):

Request  {"id": 1, "cmd": "convert", "paths": [...], "output": "...",
          "recursive": false, "overwrite": false, "include": ["pdf", "docx"],
          "ocr": {"enabled": true, "languages": ["es"]}, "backend": "EasyOCR (es)"}
Request  {"id": 2, "cmd": "list_backends"}
Request  {"id": 3, "cmd": "ping"}

Event    {"type": "ack", "id": 1}
Event    {"type": "backends", "id": 2, "names": [...], "default_langs": [...]}
Event    {"type": "batch_start", "id": 1, "total": 3}
Event    {"type": "file_status", "id": 1, "file": "a.pdf", "status": "converting"}
Event    {"type": "progress", "id": 1, "current": 1, "total": 3, "pct": 33.3}
Event    {"type": "file_done", "id": 1, "file": "a.pdf", "status": "ok",
          "output": "/out/a.md", "ocr": true}
Event    {"type": "batch_done", "id": 1, "ok": 3, "err": 0}
Event    {"type": "error", "id": 1, "message": "..."}
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

from markitdown import MarkItDown

from .cli import _collect_files, _detect_system_langs, SUPPORTED_EXTS
from .ocr_manager import OCRManager

IMAGE_LIKE = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


def _emit(event: dict) -> None:
    sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _emit_log(message: str) -> None:
    _emit({"type": "log", "message": message})


class BackendServer:
    def __init__(self):
        self._engine = MarkItDown()
        self._ocr = None
        self._ocr_config = {"ocr_languages": _detect_system_langs(), "ocr_gpu": False}
        self._lock = threading.Lock()
        self._active_batches: list[threading.Thread] = []

    def shutdown(self) -> None:
        for t in self._active_batches:
            t.join(timeout=600)

    def handle(self, req: dict) -> None:
        cmd = req.get("cmd")
        rid = req.get("id", 0)
        try:
            _emit({"type": "ack", "id": rid})
            if cmd == "ping":
                _emit({"type": "pong", "id": rid, "version": "2.0.0"})
            elif cmd == "list_backends":
                ocr = self._get_ocr(req)
                _emit({
                    "type": "backends",
                    "id": rid,
                    "names": ocr.get_all_names(),
                    "default_langs": _detect_system_langs(),
                })
            elif cmd == "convert":
                thread = threading.Thread(
                    target=self._convert_batch, args=(rid, req), daemon=True
                )
                thread.start()
                self._active_batches.append(thread)
            else:
                _emit({"type": "error", "id": rid, "message": f"unknown cmd: {cmd}"})
        except Exception as exc:
            _emit({"type": "error", "id": rid, "message": str(exc)})

    def _get_ocr(self, req: dict) -> OCRManager:
        ocr_cfg = req.get("ocr") or {}
        langs = ocr_cfg.get("languages") or _detect_system_langs()
        config = {
            "ocr_languages": langs,
            "ocr_gpu": bool(ocr_cfg.get("gpu", False)),
        }
        model_dir = os.environ.get("EASYOCR_MODEL_DIR")
        if model_dir:
            config["easyocr_model_dir"] = model_dir
        with self._lock:
            if self._ocr is None or self._ocr_config != config:
                _emit_log(f"initializing OCR backends (langs={langs})...")
                self._ocr = OCRManager(self._engine, config=config)
                self._ocr_config = config
                _emit_log("OCR backends ready: " + ", ".join(self._ocr.get_all_names()))
            return self._ocr

    def _convert_batch(self, rid: int, req: dict) -> None:
        try:
            ocr = self._get_ocr(req)
            ocr_cfg = req.get("ocr") or {}
            ocr_enabled = bool(ocr_cfg.get("enabled", True))
            backend_name = req.get("backend")
            if backend_name:
                ocr.set_active(backend_name)
            elif ocr_enabled:
                ocr.auto_select_best()
            active = ocr.get_active()
            _emit_log("OCR active: " + (active.get_name() if active else "none"))

            paths = req.get("paths") or []
            out_dir = Path(req.get("output") or os.getcwd())
            recursive = bool(req.get("recursive", False))
            overwrite = bool(req.get("overwrite", False))
            include_filters = req.get("include")
            include = {f".{e.lstrip('.')}" for e in include_filters} if include_filters else SUPPORTED_EXTS

            files = _collect_files(paths, recursive, include)
            total = len(files)
            _emit({"type": "batch_start", "id": rid, "total": total})

            ok_count, err_count = 0, 0
            for idx, f in enumerate(files):
                _emit({"type": "file_status", "id": rid, "file": str(f), "status": "converting"})
                try:
                    _emit_log(f"markitdown: {f.name}")
                    md_out = self._engine.convert(str(f)).markdown
                    if ocr_enabled and self._needs_ocr(f):
                        _emit_log(f"ocr: {f.name}")
                        md_out = self._apply_ocr(f, md_out, rid)
                    out_path = out_dir / (f.stem + ".md")
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(md_out, encoding="utf-8")
                    ok_count += 1
                    _emit({
                        "type": "file_done", "id": rid, "file": str(f),
                        "status": "ok", "output": str(out_path), "ocr": False,
                    })
                except Exception as exc:
                    err_count += 1
                    _emit_log(f"error: {f.name}: {exc}")
                    _emit({
                        "type": "file_done", "id": rid, "file": str(f),
                        "status": "error", "error": str(exc),
                    })
                _emit({
                    "type": "progress", "id": rid,
                    "current": idx + 1, "total": total,
                    "pct": round((idx + 1) / total * 100, 1) if total else 100.0,
                })
            _emit({"type": "batch_done", "id": rid, "ok": ok_count, "err": err_count})
        except Exception as exc:
            _emit({"type": "error", "id": rid, "message": str(exc)})

    def _needs_ocr(self, f: Path) -> bool:
        ext = f.suffix.lower()
        return ext in IMAGE_LIKE or ext == ".pdf"

    def _apply_ocr(self, f: Path, md_out: str, rid: int) -> str:
        ocr = self._get_ocr({"ocr": {}})
        active = ocr.get_active()
        if active is None or active.get_name().startswith("MarkItDown"):
            return md_out
        if f.suffix.lower() in IMAGE_LIKE:
            text = active.extract_text(f)
            if text:
                return f"*[Image OCR]\n{text}\n[End OCR]*\n\n{md_out}"
        elif f.suffix.lower() == ".pdf":
            import fitz
            doc = fitz.open(str(f))
            total_chars = sum(len(page.get_text().strip()) for page in doc)
            doc.close()
            if total_chars <= 100:
                _emit_log(f"scanned pdf: {f.name}, {total_chars} chars, ocr per page")
                doc = fitz.open(str(f))
                pages_md = []
                for pg in range(len(doc)):
                    _emit_log(f"ocr page {pg + 1}/{len(doc)}")
                    pages_md.append(active.extract_from_pdf(f, pg))
                doc.close()
                if any(pages_md):
                    return "\n\n".join(
                        f"## Page {i + 1}\n\n{text}"
                        for i, text in enumerate(pages_md) if text.strip()
                    )
        return md_out


def run_server() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    server = BackendServer()
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                _emit({"type": "error", "id": 0, "message": f"bad json: {exc}"})
                continue
            server.handle(req)
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(run_server())