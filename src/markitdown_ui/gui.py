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

        self.files: list[FileItem] = []
        self.output_dir = tk.StringVar()
        self.status_text = tk.StringVar(value="Listo. A\u00f1ade archivos para convertir.")

        self._style_ui()
        self._build_ui()
        self._center_window()

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
        ttk.Label(header, text="MarkItDown Converter", style="Title.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )

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

        ttk.Label(left, text="Archivos a convertir", style="Header.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=(0, 4)
        )

        self.tree = ttk.Treeview(
            left,
            columns=("status",),
            show="tree",
            selectmode="extended",
        )
        self.tree.heading("#0", text="Nombre del archivo")
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
        ttk.Button(act_btns, text="+ A\u00f1adir", style="Small.TButton",
                   command=self._browse_files).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(act_btns, text="\u232b Quitar", style="Small.TButton",
                   command=self._remove_selected).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(act_btns, text="\u267b Limpiar", style="Small.TButton",
                   command=self._clear_files).pack(side=tk.LEFT)

        # --- spacer -------------------------------------------------------------
        ttk.Frame(middle, width=8).grid(row=0, column=1, sticky=tk.NS)

        # --- right: destination -------------------------------------------------
        right = ttk.Frame(middle, padding=(8, 0, 0, 0))
        right.grid(row=0, column=2, sticky=tk.NSEW)
        right.columnconfigure(1, weight=1)

        ttk.Label(right, text="Carpeta de destino", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 4)
        )

        ttk.Entry(right, textvariable=self.output_dir).grid(
            row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 4)
        )
        ttk.Button(right, text="Examinar...", command=self._browse_output).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 4)
        )

        # summary inside right panel
        self.summary_lbl = ttk.Label(
            right, text="0 archivos",
            style="Status.TLabel", foreground="#888"
        )
        self.summary_lbl.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(12, 0))

        # -- Convert button -------------------------------------------------------
        self.convert_btn = ttk.Button(
            outer, text="Convertir a Markdown", style="Convert.TButton",
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
        self.summary_lbl.configure(text=f"{n} archivo{'s' if n != 1 else ''}")

    def _browse_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Seleccionar archivos para convertir",
            filetypes=[("Todos los archivos", "*.*")],
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

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Seleccionar carpeta de destino")
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
            messagebox.showwarning("Aviso", "A\u00f1ade al menos un archivo.")
            return
        dst_dir = self.output_dir.get().strip()
        if not dst_dir:
            messagebox.showwarning("Aviso", "Selecciona una carpeta de destino.")
            return
        if not os.path.isdir(dst_dir):
            messagebox.showerror("Error", "La carpeta de destino no existe.")
            return

        for f in self.files:
            f.status = STATUS_PENDING

        self._set_busy(True)
        self.status_text.set("Convirtiendo...")
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

            self.root.after(0, lambda fi=f, i=idx: update_status(fi, STATUS_CONVERTING, i, f"Convirtiendo: {fi.name}"))

            try:
                result = self._engine.convert(f.path)
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(result.markdown)
                ok_count += 1
                self.root.after(
                    0,
                    lambda fi=f, i=idx, d=dst: update_status(fi, STATUS_OK, i, f"Convertido: {os.path.basename(d)}"),
                )
            except UnsupportedFormatException:
                err_count += 1
                self.root.after(
                    0,
                    lambda fi=f, i=idx: update_status(fi, STATUS_ERROR, i, f"Error: {fi.name} - formato no soportado"),
                )
            except Exception as e:
                err_count += 1
                self.root.after(
                    0,
                    lambda fi=f, i=idx, m=str(e): update_status(fi, STATUS_ERROR, i, f"Error: {fi.name} - {m}"),
                )

        def done() -> None:
            self._set_busy(False)
            msg = f"Completado: {ok_count} exitoso{'s' if ok_count != 1 else ''}"
            if err_count:
                msg += f", {err_count} error{'es' if err_count != 1 else ''}"
            self.status_text.set(msg)
            self.progress["value"] = 100

            if err_count > 0:
                messagebox.showwarning(
                    "Resultado",
                    f"{ok_count} archivo{'s' if ok_count != 1 else ''} convertido{'s' if ok_count != 1 else ''}.\n"
                    f"{err_count} archivo{'s' if err_count != 1 else ''} con error{'es' if err_count != 1 else ''}.",
                )
            else:
                ret = messagebox.askyesno(
                    "Completado",
                    f"{ok_count} archivo{'s' if ok_count != 1 else ''} convertido{'s' if ok_count != 1 else ''}.\n"
                    "\u00bfAbrir carpeta de destino?",
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
