import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import queue
import threading

from markitdown import MarkItDown, UnsupportedFormatException

from .ocr_manager import OCRManager

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

VERSION = "1.2.0"

STATUS_PENDING = "\u2b1c"
STATUS_CONVERTING = "\u23f3"
STATUS_OK = "\u2705"
STATUS_ERROR = "\u274c"

LANG = {
    "en": {
        "title": "MarkItDown Converter",
        "lang_label": "Language:",
        "files_header": "Files to convert",
        "file_col": "File name",
        "btn_add": "+ Add",
        "btn_remove": "\u232b Remove",
        "btn_clear": "\u267b Clear",
        "dest_header": "Destination folder",
        "btn_browse": "Browse...",
        "summary": "{} file{}",
        "summary_plural": "s",
        "convert_btn": "Convert to Markdown",
        "status_ready": "Ready. Add files to convert.",
        "status_converting": "Converting...",
        "status_converting_file": "Converting: {}",
        "status_converted": "Converted: {}",
        "status_error_fmt": "Error: {} - {}",
        "status_error_unsupported": "Error: {} - unsupported format",
        "status_done": "Completed: {} successful{}",
        "status_done_plural": "s",
        "status_done_errors": ", {} error{}",
        "status_done_errors_plural": "s",
        "warn_no_files_title": "Notice",
        "warn_no_files": "Add at least one file.",
        "warn_no_dest_title": "Notice",
        "warn_no_dest": "Select a destination folder.",
        "err_no_dest_title": "Error",
        "err_no_dest": "The destination folder does not exist.",
        "result_title": "Result",
        "result_mixed": "{} file{} converted.\n{} file{} with error{}.",
        "result_mixed_fp": "s",
        "result_mixed_ep": "s",
        "completed_title": "Completed",
        "completed_ok": "{} file{} converted.\nOpen destination folder?",
        "completed_ok_plural": "s",
        "open_folder": "Open destination folder?",
        "ocr_section": "OCR (offline)",
        "ocr_backend": "Backend:",
        "ocr_lang": "Languages:",
        "ocr_enabled": "Enable OCR for scanned files",
        "ocr_detecting": "Checking for scanned pages...",
        "ocr_scan": "OCR reading text...",
        "status_ocr_fallback": "{} - scanned, OCR applied",
        "warn_ocr_none": "No OCR backend available.\nInstall: easyocr, pytesseract, or system tesseract.",
    },
    "es": {
        "title": "MarkItDown Converter",
        "lang_label": "Idioma:",
        "files_header": "Archivos a convertir",
        "file_col": "Nombre del archivo",
        "btn_add": "+ A\u00f1adir",
        "btn_remove": "\u232b Quitar",
        "btn_clear": "\u267b Limpiar",
        "dest_header": "Carpeta de destino",
        "btn_browse": "Examinar...",
        "summary": "{} archivo{}",
        "summary_plural": "s",
        "convert_btn": "Convertir a Markdown",
        "status_ready": "Listo. A\u00f1ade archivos para convertir.",
        "status_converting": "Convirtiendo...",
        "status_converting_file": "Convirtiendo: {}",
        "status_converted": "Convertido: {}",
        "status_error_fmt": "Error: {} - {}",
        "status_error_unsupported": "Error: {} - formato no soportado",
        "status_done": "Completado: {} exitoso{}",
        "status_done_plural": "s",
        "status_done_errors": ", {} error{}",
        "status_done_errors_plural": "es",
        "warn_no_files_title": "Aviso",
        "warn_no_files": "A\u00f1ade al menos un archivo.",
        "warn_no_dest_title": "Aviso",
        "warn_no_dest": "Selecciona una carpeta de destino.",
        "err_no_dest_title": "Error",
        "err_no_dest": "La carpeta de destino no existe.",
        "result_title": "Resultado",
        "result_mixed": "{} archivo{} convertido{}.\n{} archivo{} con error{}.",
        "result_mixed_fp": "s",
        "result_mixed_fp2": "s",
        "result_mixed_ep": "es",
        "completed_title": "Completado",
        "completed_ok": "{} archivo{} convertido{}.\n\u00bfAbrir carpeta de destino?",
        "completed_ok_plural": "s",
        "open_folder": "\u00bfAbrir carpeta de destino?",
        "ocr_section": "OCR (sin conexi\u00f3n)",
        "ocr_backend": "Motor:",
        "ocr_lang": "Idiomas:",
        "ocr_enabled": "Activar OCR para archivos escaneados",
        "ocr_detecting": "Comprobando p\u00e1ginas escaneadas...",
        "ocr_scan": "OCR leyendo texto...",
        "status_ocr_fallback": "{} - escaneado, OCR aplicado",
        "warn_ocr_none": "Ning\u00fan backend OCR disponible.\nInstala: easyocr, pytesseract o tesseract del sistema.",
    },
}


class FileItem:
    def __init__(self, path: str) -> None:
        self.path = path
        self.name = os.path.basename(path)
        self.status = STATUS_PENDING
        self.output_name = os.path.splitext(os.path.basename(path))[0] + ".md"
        self.ocr_applied = False
        try:
            self.size = os.path.getsize(path)
        except OSError:
            self.size = 0

    @property
    def size_human(self) -> str:
        n = float(self.size)
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024 or unit == "GB":
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024
        return f"{self.size} B"


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


class MarkItDownGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MarkItDown Converter")
        self.root.geometry("720x540")
        self.root.minsize(600, 400)
        self._engine = MarkItDown()
        self._ocr = OCRManager(self._engine)
        self.lang = tk.StringVar(value="en")
        self._lang_code = "en"
        self.ocr_enabled = tk.BooleanVar(value=True)
        self._ocr_enabled_flag = True
        self.ocr_lang = tk.StringVar(value="en")
        self.ocr_backend = tk.StringVar()
        self.ocr_info = tk.StringVar()
        self._ocr_langs_cache = ["en"]

        self.files: list[FileItem] = []
        self.output_dir = tk.StringVar()
        self.status_text = tk.StringVar()
        self._ui_queue = queue.Queue()
        self._last_dst = ""
        self._poll_ui_queue()

        self._style_ui()
        self._build_ui()
        self._apply_language()
        self._prepare_ocr()
        self._center_window()

    def _tr(self, key: str, *args: str) -> str:
        s = LANG.get(self._lang_code, LANG["en"]).get(key, key)
        if args:
            return s.format(*args)
        return s

    @staticmethod
    def _set_label_text(widget, text: str) -> None:
        try:
            widget.configure(text=text)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Theme / style
    # ------------------------------------------------------------------
    def _style_ui(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        bg = "#f5f7fa"
        fg = "#1f2937"
        accent = "#1a73e8"
        border = "#d1d5db"
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("Header.TLabel", font=("Segoe UI", 10, "bold"), foreground="#374151")
        style.configure("Title.TLabel", font=("Segoe UI", 13, "bold"), foreground=accent)
        style.configure("Status.TLabel", font=("Segoe UI", 9), foreground="#6b7280")
        style.configure("Convert.TButton", font=("Segoe UI", 11, "bold"), padding=10,
                        background=accent, foreground="#ffffff", borderwidth=0)
        style.map("Convert.TButton",
                  background=[("active", "#1557b0"), ("disabled", "#9db9e8")],
                  foreground=[("disabled", "#e5e7eb")])
        style.configure("Small.TButton", font=("Segoe UI", 9), padding=4)
        style.configure("TLabelframe", background=bg, bordercolor=border)
        style.configure("TLabelframe.Label", background=bg, foreground="#374151",
                        font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10),
                        background="#ffffff", fieldbackground="#ffffff", foreground=fg)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"),
                        background="#eef2f7", foreground="#374151")
        style.map("Treeview", background=[("selected", "#dbeafe")],
                  foreground=[("selected", fg)])
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor=border)
        style.configure("TCombobox", fieldbackground="#ffffff", bordercolor=border)
        style.configure("Horizontal.TProgressbar", background=accent, troughcolor="#e5e7eb",
                        bordercolor=border, lightcolor=accent, darkcolor=accent)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, padding=12)
        outer.grid(row=0, column=0, sticky=tk.NSEW)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        # -- Header ---------------------------------------------------------------
        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        header.columnconfigure(0, weight=1)

        self.title_lbl = ttk.Label(header, text="MarkItDown Converter", style="Title.TLabel")
        self.title_lbl.grid(row=0, column=0, sticky=tk.W)

        lang_frame = ttk.Frame(header)
        lang_frame.grid(row=0, column=1, sticky=tk.E)
        self.lang_lbl = ttk.Label(lang_frame, text="Language:", style="Status.TLabel")
        self.lang_lbl.pack(side=tk.LEFT, padx=(0, 4))
        lang_combo = ttk.Combobox(
            lang_frame, textvariable=self.lang, values=["en", "es"],
            state="readonly", width=5
        )
        lang_combo.pack(side=tk.LEFT)
        lang_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_language())

        # -- File list + destination side by side --------------------------------
        middle = ttk.Frame(outer)
        middle.grid(row=1, column=0, sticky=tk.NSEW, pady=(0, 8))
        middle.columnconfigure(0, weight=3)
        middle.columnconfigure(1, weight=0)
        middle.columnconfigure(2, weight=2)
        middle.rowconfigure(0, weight=1)

        # --- left: file list ----------------------------------------------------
        left = ttk.Frame(middle, padding=(0, 0, 8, 0))
        left.grid(row=0, column=0, sticky=tk.NSEW)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        self.lbl_files = ttk.Label(left, text="Files to convert", style="Header.TLabel")
        self.lbl_files.grid(row=0, column=0, sticky=tk.W, pady=(0, 4))

        self.tree = ttk.Treeview(
            left,
            columns=("size", "ocr", "status"),
            show="tree",
            selectmode="extended",
        )
        self.tree.heading("#0", text="File name")
        self.tree.column("#0", width=260, minwidth=150, stretch=True)
        self.tree.heading("size", text="Size")
        self.tree.column("size", width=70, minwidth=60, stretch=False, anchor=tk.E)
        self.tree.heading("ocr", text="OCR")
        self.tree.column("ocr", width=45, minwidth=40, stretch=False, anchor=tk.CENTER)
        self.tree.heading("status", text="")
        self.tree.column("status", width=40, minwidth=40, stretch=False, anchor=tk.CENTER)
        self.tree.grid(row=1, column=0, sticky=tk.NSEW)

        if _HAS_DND:
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind("<<Drop>>", self._on_drop)

        scroll_tree = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_tree.grid(row=1, column=1, sticky=tk.NS)
        self.tree.configure(yscrollcommand=scroll_tree.set)

        # file action buttons
        act_btns = ttk.Frame(left)
        act_btns.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        self.btn_add = ttk.Button(act_btns, text="+ Add", style="Small.TButton",
                                  command=self._browse_files)
        self.btn_add.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_remove = ttk.Button(act_btns, text="\u232b Remove", style="Small.TButton",
                                     command=self._remove_selected)
        self.btn_remove.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_clear = ttk.Button(act_btns, text="\u267b Clear", style="Small.TButton",
                                    command=self._clear_files)
        self.btn_clear.pack(side=tk.LEFT)

        # --- spacer -------------------------------------------------------------
        ttk.Frame(middle, width=8).grid(row=0, column=1, sticky=tk.NS)

        # --- right: destination -------------------------------------------------
        right = ttk.Frame(middle, padding=(8, 0, 0, 0))
        right.grid(row=0, column=2, sticky=tk.NSEW)
        right.columnconfigure(1, weight=1)

        self.lbl_dest = ttk.Label(right, text="Destination folder", style="Header.TLabel")
        self.lbl_dest.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

        ttk.Entry(right, textvariable=self.output_dir).grid(
            row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 4)
        )
        self.btn_browse = ttk.Button(right, text="Browse...", command=self._browse_output)
        self.btn_browse.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

        self.summary_lbl = ttk.Label(
            right, text="0 files",
            style="Status.TLabel", foreground="#888"
        )
        self.summary_lbl.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(12, 0))

        # -- OCR section ----------------------------------------------------------
        self.ocr_frame = ttk.LabelFrame(right, text="OCR (offline)", padding=8)
        self.ocr_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(16, 0))
        self.ocr_frame.columnconfigure(1, weight=1)

        self.ocr_check = ttk.Checkbutton(
            self.ocr_frame, text="Enable OCR for scanned files",
            variable=self.ocr_enabled, command=self._update_ocr_state
        )
        self.ocr_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))

        ttk.Label(self.ocr_frame, text="Backend:", style="Status.TLabel").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 4)
        )
        self.ocr_backend_combo = ttk.Combobox(
            self.ocr_frame, textvariable=self.ocr_backend,
            state="readonly", width=22
        )
        self.ocr_backend_combo.grid(row=1, column=1, sticky=tk.EW)
        self.ocr_backend_combo.bind("<<ComboboxSelected>>", self._on_backend_change)

        ttk.Label(self.ocr_frame, text="Languages:", style="Status.TLabel").grid(
            row=2, column=0, sticky=tk.W, padx=(0, 4), pady=(4, 0)
        )
        self.ocr_lang_entry = ttk.Entry(self.ocr_frame, textvariable=self.ocr_lang, width=22)
        self.ocr_lang_entry.grid(row=2, column=1, sticky=tk.EW, pady=(4, 0))

        ttk.Label(self.ocr_frame, textvariable=self.ocr_info, style="Status.TLabel",
                  foreground="#888").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))

        # -- Convert button -------------------------------------------------------
        self.convert_btn = ttk.Button(
            outer, text="Convert to Markdown", style="Convert.TButton",
            command=self._convert
        )
        self.convert_btn.grid(row=2, column=0, sticky=tk.EW, pady=(0, 8), ipady=4)

        # -- Progress -------------------------------------------------------------
        self.progress = ttk.Progressbar(outer, mode="determinate")
        self.progress.grid(row=3, column=0, sticky=tk.EW, pady=(0, 4))

        self.progress_lbl = ttk.Label(
            outer, textvariable=self.status_text, style="Status.TLabel",
            foreground="#555"
        )
        self.progress_lbl.grid(row=4, column=0, sticky=tk.W)

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------
    def _apply_language(self) -> None:
        self._lang_code = self.lang.get()
        self.root.title(self._tr("title"))
        self.title_lbl.configure(text=self._tr("title"))
        self.lang_lbl.configure(text=self._tr("lang_label"))
        self.lbl_files.configure(text=self._tr("files_header"))
        self.tree.heading("#0", text=self._tr("file_col"))
        self.lbl_dest.configure(text=self._tr("dest_header"))
        self.btn_add.configure(text=self._tr("btn_add"))
        self.btn_remove.configure(text=self._tr("btn_remove"))
        self.btn_clear.configure(text=self._tr("btn_clear"))
        self.btn_browse.configure(text=self._tr("btn_browse"))
        self.convert_btn.configure(text=self._tr("convert_btn"))
        self.ocr_check.configure(text=self._tr("ocr_enabled"))
        self._set_label_text(self.ocr_frame, self._tr("ocr_section"))
        if not self.files:
            self.status_text.set(self._tr("status_ready"))
        self._refresh_tree()

    # ------------------------------------------------------------------
    # Window centering
    # ------------------------------------------------------------------
    def _center_window(self) -> None:
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    # ------------------------------------------------------------------
    # File list management
    # ------------------------------------------------------------------
    def _refresh_tree(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for f in self.files:
            ocr_mark = "✓" if f.ocr_applied else ""
            self.tree.insert(
                "", tk.END, text=f.name,
                values=(f.size_human, ocr_mark, f.status),
            )
        n = len(self.files)
        s = self._tr("summary_plural") if n != 1 else ""
        self.summary_lbl.configure(text=self._tr("summary").format(n, s))

    def _browse_files(self) -> None:
        title = self._tr("files_header") if self.lang.get() == "en" else "Seleccionar archivos para convertir"
        paths = filedialog.askopenfilenames(
            title=title,
            filetypes=[("All files", "*.*")],
        )
        if not paths:
            return
        if paths and not self.output_dir.get():
            self.output_dir.set(os.path.dirname(paths[0]))
        self._add_paths(paths)

    def _on_drop(self, event) -> None:
        raw = self.root.tk.splitlist(event.data)
        paths = [p for p in raw if os.path.isfile(p)]
        if not paths:
            return
        if paths and not self.output_dir.get():
            self.output_dir.set(os.path.dirname(paths[0]))
        self._add_paths(paths)

    def _add_paths(self, paths) -> None:
        existing = {f.path for f in self.files}
        added = 0
        for p in paths:
            if p not in existing:
                self.files.append(FileItem(p))
                added += 1
        if added:
            self._refresh_tree()

    def _remove_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        paths = {self.tree.item(iid)["text"] for iid in sel}
        self.files = [f for f in self.files if f.name not in paths]
        self._refresh_tree()

    def _clear_files(self) -> None:
        if not self.files:
            return
        self.files.clear()
        self._refresh_tree()
        self.status_text.set(self._tr("status_ready"))

    def _browse_output(self) -> None:
        title = self._tr("dest_header") if self.lang.get() == "en" else "Seleccionar carpeta de destino"
        path = filedialog.askdirectory(title=title)
        if path:
            self.output_dir.set(path)

    # ------------------------------------------------------------------
    # OCR management
    # ------------------------------------------------------------------
    def _refresh_ocr_backends(self) -> None:
        names = self._ocr.get_all_names()
        self.ocr_backend_combo["values"] = names
        if names:
            active = self._ocr.get_active()
            if active:
                self.ocr_backend.set(active.get_name())
            else:
                self.ocr_backend.set(names[0])
            self._on_backend_change()
        else:
            self.ocr_info.set(self._tr("warn_ocr_none"))

    def _on_backend_change(self, _event=None) -> None:
        name = self.ocr_backend.get()
        if name:
            self._ocr.set_active(name)
            self.ocr_info.set(f"{name} | {self.ocr_lang.get()}")

    def _update_ocr_state(self) -> None:
        self._ocr_enabled_flag = bool(self.ocr_enabled.get())
        state = "normal" if self._ocr_enabled_flag else "disabled"
        self.ocr_backend_combo.configure(state=state)
        self.ocr_lang_entry.configure(state=state)

    def _prepare_ocr(self) -> None:
        langs = [l.strip() for l in self.ocr_lang.get().split(",") if l.strip()] or ["en"]
        self._ocr_langs_cache = langs
        self._ocr_enabled_flag = bool(self.ocr_enabled.get())
        self._ocr.config = {
            "ocr_languages": langs,
            "ocr_gpu": False,
            "tesseract_lang": langs[0],
        }
        self._ocr._init_backends()
        self._refresh_ocr_backends()

    def _needs_ocr(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in IMAGE_EXTS or ext == ".pdf"

    def _ocr_image_to_markdown(self, path: str) -> str:
        backend = self._ocr.get_active()
        if backend is None:
            return ""
        text = backend.extract_text(path)
        return f"*[Image OCR]\n{text}\n[End OCR]*"

    def _pdf_is_scanned(self, path: str) -> bool:
        try:
            import fitz
            doc = fitz.open(path)
            total_chars = 0
            for idx, page in enumerate(doc):
                total_chars += len(page.get_text().strip())
                if total_chars > 100:
                    doc.close()
                    return False
            doc.close()
            return total_chars <= 100
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Convert
    # ------------------------------------------------------------------
    def _set_busy(self, busy: bool) -> None:
        children = self.tree.get_children()
        for iid in children:
            self.tree.item(iid, tags=("disabled",) if busy else ())
        self.convert_btn.configure(state="disabled" if busy else "normal")
        self.progress.configure(mode="indeterminate" if busy else "determinate")

    def _convert(self) -> None:
        if not self.files:
            messagebox.showwarning(self._tr("warn_no_files_title"),
                                   self._tr("warn_no_files"))
            return
        dst_dir = self.output_dir.get().strip()
        if not dst_dir:
            messagebox.showwarning(self._tr("warn_no_dest_title"),
                                   self._tr("warn_no_dest"))
            return
        if not os.path.isdir(dst_dir):
            messagebox.showerror(self._tr("err_no_dest_title"),
                                 self._tr("err_no_dest"))
            return

        for f in self.files:
            f.status = STATUS_PENDING

        self._set_busy(True)
        self.status_text.set(self._tr("status_converting"))
        self._refresh_tree()
        threading.Thread(
            target=self._do_batch, args=(dst_dir,), daemon=True
        ).start()

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                msg = self._ui_queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    self.progress["value"] = msg[1]
                elif kind == "status":
                    self.status_text.set(msg[1])
                elif kind == "file_status":
                    fi, status = msg[1], msg[2]
                    fi.status = status
                    self._refresh_tree()
                elif kind == "done":
                    ok_count, err_count = msg[1], msg[2]
                    self._set_busy(False)
                    sp = self._tr("status_done_plural") if ok_count != 1 else ""
                    text = self._tr("status_done").format(ok_count, sp)
                    if err_count:
                        ep = self._tr("status_done_errors_plural") if err_count != 1 else ""
                        text += self._tr("status_done_errors").format(err_count, ep)
                    self.status_text.set(text)
                    self.progress["value"] = 100
                    if err_count > 0:
                        fp = self._tr("result_mixed_fp") if ok_count != 1 else ""
                        fp2 = self._tr("result_mixed_fp2") if ok_count != 1 else ""
                        ep = self._tr("result_mixed_ep") if err_count != 1 else ""
                        messagebox.showwarning(
                            self._tr("result_title"),
                            self._tr("result_mixed").format(ok_count, fp, fp2, err_count, ep),
                        )
                    else:
                        p = self._tr("completed_ok_plural") if ok_count != 1 else ""
                        ret = messagebox.askyesno(
                            self._tr("completed_title"),
                            self._tr("completed_ok").format(ok_count, p, p),
                        )
                        if ret:
                            self._open_folder(self._last_dst)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_ui_queue)

    def _do_batch(self, dst_dir: str) -> None:
        total = len(self.files)
        ok_count = 0
        err_count = 0
        self._last_dst = dst_dir

        for idx, f in enumerate(self.files):
            dst = os.path.join(dst_dir, f.output_name)
            pct = (idx + 1) / total * 100
            self._ui_queue.put(("progress", pct))
            self._ui_queue.put(("status", self._tr("status_converting_file", f.name)))
            self._ui_queue.put(("file_status", f, STATUS_CONVERTING))

            try:
                result = self._engine.convert(f.path)
                markdown_out = result.markdown

                if self._ocr_enabled_flag and self._needs_ocr(f.path):
                    ext = os.path.splitext(f.path)[1].lower()
                    if ext in IMAGE_EXTS:
                        self._ui_queue.put(("status", self._tr("ocr_scan", f.name)))
                        ocr_text = self._ocr_image_to_markdown(f.path)
                        if ocr_text:
                            markdown_out = ocr_text + "\n\n" + markdown_out
                    elif ext == ".pdf" and self._pdf_is_scanned(f.path):
                        self._ui_queue.put(("status", self._tr("ocr_detecting", f.name)))
                        import fitz
                        doc = fitz.open(f.path)
                        pages_md = []
                        for pg in range(len(doc)):
                            self._ui_queue.put((
                                "status",
                                self._tr("ocr_scan", f"{f.name} (p{pg + 1})"),
                            ))
                            pages_md.append(self._ocr.extract_pdf_page_text(f.path, pg))
                        doc.close()
                        if any(pages_md):
                            markdown_out = "\n\n".join(
                                f"## Page {i + 1}\n\n{text}"
                                for i, text in enumerate(pages_md) if text.strip()
                            )
                            f.ocr_applied = True

                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(markdown_out)
                ok_count += 1
                self._ui_queue.put(("status", self._tr("status_converted", os.path.basename(dst))))
                self._ui_queue.put(("file_status", f, STATUS_OK))
            except UnsupportedFormatException:
                err_count += 1
                self._ui_queue.put(("status", self._tr("status_error_unsupported", f.name)))
                self._ui_queue.put(("file_status", f, STATUS_ERROR))
            except Exception as e:
                err_count += 1
                self._ui_queue.put(("status", self._tr("status_error_fmt", f.name, str(e))))
                self._ui_queue.put(("file_status", f, STATUS_ERROR))

        self._ui_queue.put(("done", ok_count, err_count))

    @staticmethod
    def _open_folder(path: str) -> None:
        import subprocess
        subprocess.Popen(["xdg-open", path])


def main() -> None:
    if _HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    MarkItDownGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
