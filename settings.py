"""
settings.py — App Settings Manager
Handles: export dir, company info (name/logo), DB restore from backup.
Settings are stored in app_metadata SQLite table.
"""
import os
import json
import shutil
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk          # pillow for logo preview

from config import T, BASE_DIR, bind_hover, VERSION
from database import SQLITE_DB, BACKUP_DIR, backup_manual

# ── Settings file path ─────────────────────────────────────────────────────────
SETTINGS_FILE = os.path.join(BASE_DIR, "app_settings.json")

_DEFAULTS = {
    "company_name":    "Tasniah Fabrics Ltd",
    "company_subtitle":"Garment Order Tracking System",
    "export_dir":      os.path.join(BASE_DIR, "exports"),
    "logo_path":       "",              # absolute path to PNG/JPG logo
    "backup_dir":      BACKUP_DIR,
    "max_daily_backups": 30,
    "theme":           "dark",          # reserved for future light/dark toggle
    "show_default_creds": True,
    "reminder_days":   7,               # Lead time for shipment alerts
    "license_key":     "NONE",          # User license key
}


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            # merge with defaults so new keys always exist
            merged = dict(_DEFAULTS)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(_DEFAULTS)


def save_settings(s: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)


# ── Main Settings Dialog ───────────────────────────────────────────────────────
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("\u2699  Settings")
        self.geometry("640x700")
        self.configure(bg=T["bg"])
        self.resizable(False, True)
        self.grab_set()
        self.on_saved = on_saved
        self.settings  = load_settings()
        self._logo_img = None          # keep PIL ref alive
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────────
    def _build(self):
        tk.Frame(self, bg=T["accent"], height=3).pack(fill="x")

        hdr = tk.Frame(self, bg=T["surf"]); hdr.pack(fill="x")
        tk.Frame(hdr, bg=T["accent"], width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="  \u2699  SETTINGS & CUSTOMISATION",
                 font=(T["mono"], 11, "bold"), fg=T["text"],
                 bg=T["surf"]).pack(side="left", pady=12, padx=6)
        tk.Frame(self, bg=T["border"], height=1).pack(fill="x")

        # Scrollable body
        canvas = tk.Canvas(self, bg=T["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg=T["bg"])
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw", width=622)

        # Sections
        self._build_company_section(body)
        self._build_alert_section(body)
        self._build_export_section(body)
        self._build_licensing_section(body)
        self._build_version_section(body)
        self._build_restore_section(body)

        # Bottom bar
        bot = tk.Frame(self, bg=T["surf"], pady=10); bot.pack(fill="x", side="bottom")
        self._status_var = tk.StringVar()
        tk.Label(bot, textvariable=self._status_var,
                 font=(T["font"], 8), fg=T["green"],
                 bg=T["surf"]).pack(side="left", padx=16)
        _btn(bot, "\u2715  Cancel", T["surf3"], T["muted"],
             self.destroy).pack(side="right", padx=6)
        _btn(bot, "\U0001f4be  Save Settings", T["accent"], "white",
             self._save, T["accent2"]).pack(side="right", padx=12)

    def _build_alert_section(self, body):
        self._section(body, "\U0001f514  AUTOMATED SHIPMENT ALERTS", T["accent"])
        f = tk.Frame(body, bg=T["surf2"], padx=20, pady=16)
        f.pack(fill="x", padx=12, pady=(0, 8))
        
        tk.Label(f, text="Alert Lead Time (Days)", font=(T["font"], 9, "bold"),
                 fg=T["text"], bg=T["surf2"]).grid(row=0, column=0, sticky="w")
        
        self._reminder_days = tk.StringVar(value=str(self.settings.get("reminder_days", 7)))
        _entry(f, self._reminder_days, width=10).grid(row=1, column=0, sticky="w", pady=(4, 0), ipady=5)
        
        tk.Label(f, text="\u2139  The system will remind you about upcoming shipments X days before their ToD.",
                 font=(T["font"], 8), fg=T["muted"], bg=T["surf2"], wraplength=540, justify="left").grid(row=2, column=0, sticky="w", pady=(8, 0))

    # ── Section: Company ───────────────────────────────────────────────────────
    def _build_company_section(self, body):
        self._section(body, "\U0001f3e2  COMPANY INFORMATION", T["gold"])
        f = tk.Frame(body, bg=T["surf2"], padx=20, pady=16)
        f.pack(fill="x", padx=12, pady=(0, 8))

        # Company Name
        tk.Label(f, text="Company Name", font=(T["font"], 9, "bold"),
                 fg=T["text"], bg=T["surf2"]).grid(row=0, column=0, sticky="w",
                                                    pady=(0, 4))
        self._cname = tk.StringVar(value=self.settings["company_name"])
        _entry(f, self._cname, width=40).grid(row=1, column=0, sticky="ew",
                                               pady=(0, 10), ipady=5)

        # Company Subtitle
        tk.Label(f, text="Subtitle / Department", font=(T["font"], 9, "bold"),
                 fg=T["text"], bg=T["surf2"]).grid(row=2, column=0, sticky="w",
                                                     pady=(0, 4))
        self._csub = tk.StringVar(value=self.settings["company_subtitle"])
        _entry(f, self._csub, width=40).grid(row=3, column=0, sticky="ew",
                                              pady=(0, 10), ipady=5)

        # Logo
        tk.Label(f, text="Company Logo  (PNG / JPG — for PDF reports)",
                 font=(T["font"], 9, "bold"), fg=T["text"],
                 bg=T["surf2"]).grid(row=4, column=0, sticky="w", pady=(0, 4))

        logo_row = tk.Frame(f, bg=T["surf2"]); logo_row.grid(row=5, column=0, sticky="ew")
        self._logo_path_var = tk.StringVar(value=self.settings.get("logo_path", ""))
        logo_entry = _entry(logo_row, self._logo_path_var, width=28)
        logo_entry.pack(side="left", ipady=5, padx=(0, 6))
        _btn(logo_row, "\U0001f4c2  Browse", T["surf3"], T["text"],
             self._browse_logo, T["surf4"], size=8).pack(side="left")
        _btn(logo_row, "\u2715  Clear", T["red_bg"], T["red"],
             self._clear_logo, T["red_bg"], size=8).pack(side="left", padx=6)

        # Logo preview
        self._logo_preview = tk.Label(f, bg=T["surf3"], width=18, height=5,
                                      text="No logo", font=(T["font"], 8),
                                      fg=T["muted"], relief="flat")
        self._logo_preview.grid(row=6, column=0, sticky="w", pady=(8, 0),
                                padx=0, ipadx=4, ipady=4)
        self._refresh_logo_preview()

    def _browse_logo(self):
        p = filedialog.askopenfilename(
            title="Select Logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")])
        if p:
            self._logo_path_var.set(p)
            self._refresh_logo_preview()

    def _clear_logo(self):
        self._logo_path_var.set("")
        self._logo_preview.config(image="", text="No logo", fg=T["muted"])
        self._logo_img = None

    def _refresh_logo_preview(self):
        p = self._logo_path_var.get()
        if p and os.path.exists(p):
            try:
                img = Image.open(p)
                img.thumbnail((160, 60))
                self._logo_img = ImageTk.PhotoImage(img)
                self._logo_preview.config(image=self._logo_img, text="",
                                          width=160, height=60)
                return
            except Exception:
                pass
        self._logo_preview.config(image="", text="No logo",
                                  fg=T["muted"], width=18, height=5)
        self._logo_img = None

    # ── Section: Export ────────────────────────────────────────────────────────
    def _build_export_section(self, body):
        self._section(body, "\U0001f4c1  EXPORT DIRECTORY", T["blue"])
        f = tk.Frame(body, bg=T["surf2"], padx=20, pady=16)
        f.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(f, text="Default folder for Excel / PDF exports",
                 font=(T["font"], 9, "bold"), fg=T["text"],
                 bg=T["surf2"]).pack(anchor="w", pady=(0, 6))

        row = tk.Frame(f, bg=T["surf2"]); row.pack(fill="x")
        self._export_dir_var = tk.StringVar(value=self.settings["export_dir"])
        _entry(row, self._export_dir_var, width=34).pack(side="left", ipady=5,
                                                          padx=(0, 6))
        _btn(row, "\U0001f4c2  Browse", T["surf3"], T["text"],
             self._browse_export, T["surf4"], size=8).pack(side="left")
        _btn(row, "\U0001f4c2  Open", T["surf3"], T["text"],
             self._open_export, T["surf4"], size=8).pack(side="left", padx=6)

        tk.Label(f,
                 text="\u2139  Reports and Excel files will be saved here by default.",
                 font=(T["font"], 8), fg=T["muted"],
                 bg=T["surf2"]).pack(anchor="w", pady=(8, 0))

    def _browse_export(self):
        d = filedialog.askdirectory(title="Select Export Folder")
        if d: self._export_dir_var.set(d)

    def _build_licensing_section(self, body):
        from updater import get_hwid
        self._section(body, "\U0001f512  LICENSE & DEVICE BINDING", T["gold"])
        f = tk.Frame(body, bg=T["surf2"], padx=20, pady=16)
        f.pack(fill="x", padx=12, pady=(0, 8))
        
        # Device ID (Read Only)
        tk.Label(f, text="Your Device ID (Send this to Admin)", font=(T["font"], 8, "bold"),
                 fg=T["muted"], bg=T["surf2"]).grid(row=0, column=0, sticky="w")
        hwid_f = tk.Frame(f, bg=T["surf3"], padx=8, pady=4)
        hwid_f.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        tk.Label(hwid_f, text=get_hwid(), font=(T["mono"], 10, "bold"),
                 fg=T["accent"], bg=T["surf3"]).pack(side="left")
        
        # License Key Input
        tk.Label(f, text="Enter License Key", font=(T["font"], 9, "bold"),
                 fg=T["text"], bg=T["surf2"]).grid(row=2, column=0, sticky="w")
        self._license_key_var = tk.StringVar(value=self.settings.get("license_key", "NONE"))
        _entry(f, self._license_key_var, width=40).grid(row=3, column=0, sticky="ew", pady=(4, 0), ipady=5)

    def _build_export_section(self, body):
        self._section(body, "\U0001f4dc  SYSTEM VERSION & UPDATES", T["purple"])
        f = tk.Frame(body, bg=T["surf2"], padx=20, pady=16)
        f.pack(fill="x", padx=12, pady=(0, 8))
        
        tk.Label(f, text=f"Current Version:  v{VERSION}", font=(T["font"], 10, "bold"),
                 fg=T["text"], bg=T["surf2"]).pack(side="left")
        
        from dialogs import VersionHistoryDialog
        def show_v(): VersionHistoryDialog(self)
        
        _btn(f, "📜  View What's New", T["purple_bg"], T["purple"],
             show_v, T["surf4"], size=8).pack(side="right")

        def check_upd():
            self._status_var.set("⏳ Validating license...")
            from updater import check_for_updates
            import threading
            lkey = self._license_key_var.get().strip()
            def worker():
                upd, v, cl = check_for_updates(lkey)
                if upd:
                    self.after(0, lambda: self._status_var.set(f"🚀 Version v{v} available!"))
                    if hasattr(self.master, "_prompt_update"):
                        self.after(0, lambda: self.master._prompt_update(v, cl))
                elif v is None and cl and cl.startswith("LICENSE_ERROR"):
                    self.after(0, lambda: self._status_var.set("⚠ " + cl.replace("LICENSE_ERROR: ","")))
                else:
                    self.after(0, lambda: self._status_var.set("✓ Latest version & License Valid"))
            threading.Thread(target=worker, daemon=True).start()

        _btn(f, "🔄  Check for Updates", T["surf3"], T["text"],
             check_upd, T["surf4"], size=8).pack(side="right", padx=10)

    # ── Section: Restore ───────────────────────────────────────────────────────
    def _build_restore_section(self, body):
        self._section(body, "\U0001f504  RESTORE DATABASE FROM BACKUP", T["teal"])
        f = tk.Frame(body, bg=T["surf2"], padx=20, pady=16)
        f.pack(fill="x", padx=12, pady=(0, 12))

        # Backup list
        tk.Label(f, text="Available Backup Files",
                 font=(T["font"], 9, "bold"), fg=T["text"],
                 bg=T["surf2"]).pack(anchor="w", pady=(0, 6))

        list_f = tk.Frame(f, bg=T["surf3"]); list_f.pack(fill="x")
        s = ttk.Style()
        s.configure("BK.Treeview",
                    background=T["surf3"], foreground=T["text"],
                    fieldbackground=T["surf3"], rowheight=24,
                    font=(T["mono"], 8))
        s.configure("BK.Treeview.Heading",
                    background=T["surf4"], foreground=T["muted"],
                    font=(T["font"], 8, "bold"), relief="flat")
        s.map("BK.Treeview",
              background=[("selected", T["accent3"])],
              foreground=[("selected", "white")])

        cols = ("category", "filename", "size", "date")
        self._bk_tree = ttk.Treeview(list_f, columns=cols,
                                      show="headings", style="BK.Treeview",
                                      height=8)
        for col, hdr, w in [("category","Category",90), ("filename","File",220),
                              ("size","Size",70),  ("date","Modified",140)]:
            self._bk_tree.heading(col, text=hdr)
            self._bk_tree.column(col, width=w, anchor="w" if col in ("filename","category") else "center")
        ys = ttk.Scrollbar(list_f, orient="vertical", command=self._bk_tree.yview)
        self._bk_tree.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self._bk_tree.pack(fill="x")
        self._populate_backup_list()

        btn_row = tk.Frame(f, bg=T["surf2"]); btn_row.pack(fill="x", pady=(10, 0))
        _btn(btn_row, "\U0001f504  Refresh List", T["surf3"], T["text"],
             self._populate_backup_list, T["surf4"], size=8).pack(side="left")
        _btn(btn_row, "\U0001f4c2  Browse Backup File\u2026", T["surf3"], T["text"],
             self._browse_backup, T["surf4"], size=8).pack(side="left", padx=8)
        _btn(btn_row, "\u26a0  RESTORE SELECTED", T["red_bg"], T["red"],
             self._restore_selected, T["red"], size=9).pack(side="right")

        warn = tk.Frame(f, bg="#1A0808", padx=10, pady=6)
        warn.pack(fill="x", pady=(10, 0))
        tk.Label(warn,
                 text="\u26a0  Restoring will REPLACE the current database. "
                      "A backup of the current DB will be saved first.",
                 font=(T["font"], 8), fg=T["red"], bg="#1A0808",
                 wraplength=540, justify="left").pack(anchor="w")

    def _populate_backup_list(self):
        self._bk_tree.delete(*self._bk_tree.get_children())
        if not os.path.isdir(BACKUP_DIR):
            return
        for sub in ("daily", "on_close", "manual"):
            d = os.path.join(BACKUP_DIR, sub)
            if not os.path.isdir(d): continue
            files = sorted(os.listdir(d), reverse=True)
            for fn in files:
                if not fn.endswith(".sqlite"): continue
                fp  = os.path.join(d, fn)
                sz  = f"{os.path.getsize(fp) // 1024} KB"
                mod = __import__("datetime").datetime.fromtimestamp(
                    os.path.getmtime(fp)).strftime("%d-%b-%Y %H:%M")
                self._bk_tree.insert("", "end",
                    values=(sub.replace("_", "-"), fn, sz, mod),
                    tags=(sub,))
        # tag colors
        self._bk_tree.tag_configure("daily",    foreground="#F59E0B")
        self._bk_tree.tag_configure("on_close", foreground="#3B82F6")
        self._bk_tree.tag_configure("manual",   foreground="#14B8A6")

    def _browse_backup(self):
        p = filedialog.askopenfilename(
            title="Select Backup File",
            initialdir=BACKUP_DIR,
            filetypes=[("SQLite DB", "*.sqlite"), ("All", "*.*")])
        if p:
            self._do_restore(p)

    def _restore_selected(self):
        sel = self._bk_tree.selection()
        if not sel:
            messagebox.showinfo("", "Please select a backup file first.", parent=self)
            return
        vals = self._bk_tree.item(sel[0])["values"]
        sub  = vals[0].replace("-", "_")
        fn   = vals[1]
        path = os.path.join(BACKUP_DIR, sub, fn)
        self._do_restore(path)

    def _do_restore(self, src: str):
        if not os.path.exists(src):
            messagebox.showerror("Error", "File not found.", parent=self); return
        if not messagebox.askyesno(
                "\u26a0  Confirm Restore",
                f"Restore from:\n{os.path.basename(src)}\n\n"
                "This will REPLACE the current database.\n"
                "A safety backup will be created first.\n\n"
                "Are you sure?", parent=self):
            return

        # 1. Safety backup of current DB
        safe = backup_manual()

        # 2. Replace current DB
        try:
            # Make sure target is writable
            if os.name == "nt":
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(SQLITE_DB, 128)
            shutil.copy2(src, SQLITE_DB)
            messagebox.showinfo(
                "\u2705 Restored",
                f"Database restored successfully!\n\n"
                f"Safety backup saved:\n{os.path.basename(safe) if safe else 'n/a'}\n\n"
                "Please restart the application to load restored data.",
                parent=self)
            self._status_var.set("\u2705 Restored — please restart the app")
        except Exception as e:
            messagebox.showerror("Restore Failed", str(e), parent=self)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _section(self, parent, title, color):
        f = tk.Frame(parent, bg=T["bg"]); f.pack(fill="x", padx=12, pady=(14, 2))
        tk.Frame(f, bg=color, width=3, height=18).pack(side="left", padx=(0, 8))
        tk.Label(f, text=title, font=(T["font"], 9, "bold"),
                 fg=color, bg=T["bg"]).pack(side="left")

    def _save(self):
        self.settings["company_name"]    = self._cname.get().strip()
        self.settings["company_subtitle"] = self._csub.get().strip()
        self.settings["logo_path"]       = self._logo_path_var.get().strip()
        self.settings["export_dir"]      = self._export_dir_var.get().strip()
        self.settings["reminder_days"]   = int(self._reminder_days.get().strip() or "7")
        self.settings["license_key"]     = self._license_key_var.get().strip()

        # Create export dir if needed
        ed = self.settings["export_dir"]
        if ed: os.makedirs(ed, exist_ok=True)

        try:
            save_settings(self.settings)
            self._status_var.set("\u2705 Settings saved!")
            if self.on_saved: self.on_saved(self.settings)
            self.after(1500, self.destroy)
        except Exception as e:
            self._status_var.set("\u26a0 Save failed")
            messagebox.showerror("Save Error", f"Failed to save settings:\n{e}", parent=self)


# ── Small widget helpers (local) ───────────────────────────────────────────────
def _btn(parent, text, bg, fg, cmd, hov_bg=None, size=9):
    b = tk.Button(parent, text=text, font=(T["font"], size, "bold"),
                  bg=bg, fg=fg, relief="flat",
                  padx=12, pady=6, cursor="hand2", command=cmd,
                  activebackground=hov_bg or bg, activeforeground=fg)
    if hov_bg: bind_hover(b, bg, hov_bg, fg, fg)
    return b


def _entry(parent, var, width=30):
    return tk.Entry(parent, textvariable=var,
                    font=(T["mono"], 9), bg=T["surf3"],
                    fg=T["text"], relief="flat", bd=0,
                    width=width, insertbackground=T["text"],
                    disabledforeground=T["muted"])
