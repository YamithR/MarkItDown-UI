import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading

from markitdown import MarkItDown, UnsupportedFormatException

VERSION = "1.0.0"

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
    },
}


class FileItem:
    def __init__(self, path: str) -> None:
        self.path = path
        self.name = os.path.basename(path)
        self.status = STATUS_PENDING
        self.output_name = os.path.splitext(os.path.basename(path))[0] + ".md"


class MarkItDownGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MarkItDown Converter")
        self.root.geometry("720x540")
        self.root.minsize(600, 400)
        self._engine = MarkItDown()
        self.lang = tk.StringVar(value="en")

        self.files: list[FileItem] = []
        self.output_dir = tk.StringVar()
        self.status_text = tk.StringVar()

        self._style_ui()
        self._build_ui()
        self._apply_language()
        self._center_window()

    def _tr(self, key: str, *args: str) -> str:
        s = LANG.get(self.lang.get(), LANG["en"]).get(key, key)
        if args:
            return s.format(*args)
        return s

    # ------------------------------------------------------------------
    # Theme / style
    # ------------------------------------------------------------------
    def _style_ui(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f5f5")
        style.configure("Header.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 11, "bold"), foreground="#1a73e8")
        style.configure("Status.TLabel", font=("Segoe UI", 9), foreground="#555")
        style.configure("Convert.TButton", font=("Segoe UI", 11, "bold"), padding=8)
        style.configure("Small.TButton", font=("Segoe UI", 9), padding=2)
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

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
            columns=("status",),
            show="tree",
            selectmode="extended",
        )
        self.tree.heading("#0", text="File name")
        self.tree.column("#0", width=320, minwidth=200, stretch=True)
        self.tree.heading("status", text="")
        self.tree.column("status", width=40, minwidth=40, stretch=False, anchor=tk.CENTER)
        self.tree.grid(row=1, column=0, sticky=tk.NSEW)

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
        lang = self.lang.get()
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
            self.tree.insert("", tk.END, text=f.name, values=(f.status,))
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
        existing = {f.path for f in self.files}
        for p in paths:
            if p not in existing:
                self.files.append(FileItem(p))
        if paths and not self.output_dir.get():
            self.output_dir.set(os.path.dirname(paths[0]))
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

    def _do_batch(self, dst_dir: str) -> None:
        total = len(self.files)
        ok_count = 0
        err_count = 0

        for idx, f in enumerate(self.files):
            dst = os.path.join(dst_dir, f.output_name)

            def update_status(fi: FileItem, s: str, i: int, msg: str) -> None:
                fi.status = s
                self._refresh_tree()
                self.progress["value"] = (i + 1) / total * 100
                self.status_text.set(msg)

            self.root.after(
                0,
                lambda fi=f, i=idx: update_status(
                    fi, STATUS_CONVERTING, i, self._tr("status_converting_file", fi.name)
                ),
            )

            try:
                result = self._engine.convert(f.path)
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(result.markdown)
                ok_count += 1
                self.root.after(
                    0,
                    lambda fi=f, i=idx, d=dst: update_status(
                        fi, STATUS_OK, i, self._tr("status_converted", os.path.basename(d))
                    ),
                )
            except UnsupportedFormatException:
                err_count += 1
                self.root.after(
                    0,
                    lambda fi=f, i=idx: update_status(
                        fi, STATUS_ERROR, i, self._tr("status_error_unsupported", fi.name)
                    ),
                )
            except Exception as e:
                err_count += 1
                self.root.after(
                    0,
                    lambda fi=f, i=idx, m=str(e): update_status(
                        fi, STATUS_ERROR, i, self._tr("status_error_fmt", fi.name, m)
                    ),
                )

        def done() -> None:
            self._set_busy(False)

            sp = self._tr("status_done_plural") if ok_count != 1 else ""
            msg = self._tr("status_done").format(ok_count, sp)
            if err_count:
                ep = self._tr("status_done_errors_plural") if err_count != 1 else ""
                msg += self._tr("status_done_errors").format(err_count, ep)
            self.status_text.set(msg)
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
                    self._open_folder(dst_dir)

        self.root.after(0, done)

    @staticmethod
    def _open_folder(path: str) -> None:
        import subprocess
        subprocess.Popen(["xdg-open", path])


def main() -> None:
    root = tk.Tk()
    MarkItDownGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
