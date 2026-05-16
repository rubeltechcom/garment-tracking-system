"""
settings.py — App Settings Manager (Professional Version)
"""
import os
import json
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

from config import T, BASE_DIR, bind_hover, VERSION
from widgets import mk_btn, mk_entry
from database import SQLITE_DB, BACKUP_DIR, backup_manual

SETTINGS_FILE = os.path.join(BASE_DIR, "app_settings.json")

_DEFAULTS = {
    "company_name":    "Tasniah Fabrics Ltd",
    "company_subtitle":"Garment Order Tracking System",
    "export_dir":      os.path.join(BASE_DIR, "exports"),
    "logo_path":       "",
    "backup_dir":      BACKUP_DIR,
    "max_daily_backups": 30,
    "theme":           "dark",
    "show_default_creds": True,
    "reminder_days":   7,
}

def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(_DEFAULTS); merged.update(data)
            return merged
        except: pass
    return dict(_DEFAULTS)

def save_settings(s: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("\u2699  System Settings")
        self.geometry("640x720")
        self.configure(bg=T["bg"])
        self.resizable(False, True)
        self.grab_set()
        
        self.on_saved = on_saved
        self.settings = load_settings()
        self._logo_img = None
        
        # Initialize StringVars
        self._status_var = tk.StringVar(value="Ready")
        self._cname = tk.StringVar(value=self.settings.get("company_name", ""))
        self._csub = tk.StringVar(value=self.settings.get("company_subtitle", ""))
        self._logo_path_var = tk.StringVar(value=self.settings.get("logo_path", ""))
        self._export_dir_var = tk.StringVar(value=self.settings.get("export_dir", ""))
        self._reminder_days = tk.StringVar(value=str(self.settings.get("reminder_days", 7)))
        
        self._build()

    def _build(self):
        # Header
        tk.Frame(self, bg=T["accent"], height=3).pack(fill="x")
        hdr = tk.Frame(self, bg=T["surf"]); hdr.pack(fill="x")
        tk.Frame(hdr, bg=T["accent"], width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="  \u2699  SETTINGS & CUSTOMISATION",
                 font=(T["mono"], 11, "bold"), fg=T["text"], bg=T["surf"]).pack(side="left", pady=12)
        tk.Frame(self, bg=T["border"], height=1).pack(fill="x")

        # Fixed Bottom Bar
        bot = tk.Frame(self, bg=T["surf2"], pady=14)
        bot.pack(fill="x", side="bottom")
        tk.Frame(bot, bg=T["border"], height=1).place(x=0, y=0, relwidth=1)
        
        tk.Label(bot, textvariable=self._status_var, font=(T["font"], 9, "bold"),
                 fg=T["green"], bg=T["surf2"]).pack(side="left", padx=20)
        
        _mk_btn(bot, "   \U0001f4be  SAVE ALL SETTINGS   ", T["accent"], "white",
                self._save, T["accent2"]).pack(side="right", padx=20)
        _mk_btn(bot, "  Cancel  ", T["surf3"], T["muted"], self.destroy).pack(side="right")

        # Scrollable Area
        canvas = tk.Canvas(self, bg=T["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        
        self.body = tk.Frame(canvas, bg=T["bg"])
        self.body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.body, anchor="nw", width=622)

        # Mousewheel binding
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to canvas and all its children
        def bind_recursive(w):
            w.bind("<MouseWheel>", _on_mousewheel)
            for child in w.winfo_children():
                bind_recursive(child)
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        # We'll call bind_recursive after building sections
        self._bind_mouse = bind_recursive

        # Build Sections in Order
        self._build_company_section()
        self._build_alert_section()
        self._build_export_section()
        self._build_version_section()
        self._build_restore_section()
        self._bind_mouse(self.body)

    def _build_company_section(self):
        f = self._section("🏢  COMPANY INFORMATION", T["gold"])
        
        tk.Label(f, text="Company Name", font=(T["font"], 9, "bold"), fg=T["text"], bg=T["surf2"]).pack(anchor="w")
        _mk_entry(f, self._cname).pack(fill="x", pady=(4, 10))
        
        tk.Label(f, text="Subtitle / Department", font=(T["font"], 9, "bold"), fg=T["text"], bg=T["surf2"]).pack(anchor="w")
        _mk_entry(f, self._csub).pack(fill="x", pady=(4, 10))
        
        tk.Label(f, text="Company Logo (PNG/JPG)", font=(T["font"], 9, "bold"), fg=T["text"], bg=T["surf2"]).pack(anchor="w")
        lrow = tk.Frame(f, bg=T["surf2"]); lrow.pack(fill="x", pady=4)
        _mk_entry(lrow, self._logo_path_var, width=35).pack(side="left", padx=(0, 6))
        _mk_btn(lrow, "Browse", T["surf3"], T["text"], self._browse_logo, T["surf4"], size=8).pack(side="left")
        
        self._logo_preview = tk.Label(f, bg=T["surf3"], text="No logo", font=(T["font"], 8), fg=T["muted"])
        self._logo_preview.pack(anchor="w", pady=6, ipadx=10, ipady=10)
        self._refresh_logo_preview()

    def _build_alert_section(self):
        f = self._section("🔔  SHIPMENT ALERTS", T["purple"])
        tk.Label(f, text="Alert Lead Time (Days)", font=(T["font"], 10, "bold"), fg=T["text"], bg=T["surf2"]).pack(anchor="w")
        _mk_entry(f, self._reminder_days, width=12).pack(anchor="w", pady=(6, 0))
        tk.Label(f, text="System will remind you X days before ToD.", font=(T["font"], 8), fg=T["muted"], bg=T["surf2"]).pack(anchor="w", pady=4)

    def _build_export_section(self):
        f = self._section("📁  EXPORT DIRECTORY", T["blue"])
        tk.Label(f, text="Default folder for reports", font=(T["font"], 9, "bold"), fg=T["text"], bg=T["surf2"]).pack(anchor="w")
        row = tk.Frame(f, bg=T["surf2"]); row.pack(fill="x", pady=4)
        _mk_entry(row, self._export_dir_var, width=40).pack(side="left", padx=(0, 6))
        _mk_btn(row, "Browse", T["surf3"], T["text"], self._browse_export, T["surf4"], size=8).pack(side="left")

    def _build_version_section(self):
        f = self._section("📜  SYSTEM VERSION", T["purple"])
        tk.Label(f, text=f"Current Version: v{VERSION}", font=(T["font"], 10, "bold"), fg=T["text"], bg=T["surf2"]).pack(side="left")
        
        from dialogs import VersionHistoryDialog
        _mk_btn(f, "What's New", T["purple_bg"], T["purple"], lambda: VersionHistoryDialog(self), T["surf4"], size=8).pack(side="right")
        
        def check_upd():
            self._status_var.set("⏳ Checking...")
            from updater import check_for_updates
            import threading
            def worker():
                upd, v, cl = check_for_updates()
                if upd:
                    self.after(0, lambda: self._status_var.set(f"🚀 v{v} available!"))
                    if hasattr(self.master, "_prompt_update"): self.after(0, lambda: self.master._prompt_update(v, cl))
                else: self.after(0, lambda: self._status_var.set("✓ Up to date"))
            threading.Thread(target=worker, daemon=True).start()
        _mk_btn(f, "  Check for Updates  ", T["accent"], "white", check_upd, T["accent2"], size=8).pack(side="right", padx=10)

    def _build_restore_section(self):
        f = self._section("🔄  RESTORE DATABASE", T["teal"])
        tk.Label(f, text="Available Backups", font=(T["font"], 9, "bold"), fg=T["text"], bg=T["surf2"]).pack(anchor="w")
        lf = tk.Frame(f, bg=T["surf3"]); lf.pack(fill="x", pady=4)
        
        self._bk_tree = ttk.Treeview(lf, columns=("cat", "file", "size", "date"), 
                                     show="headings", height=5, style="Main.Treeview")
        for col, head, w in [("cat","Type",80), ("file","File",220), ("size","Size",70), ("date","Date",140)]:
            self._bk_tree.heading(col, text=head); self._bk_tree.column(col, width=w)
        self._bk_tree.pack(fill="x")
        self._populate_backups()
        
        rrow = tk.Frame(f, bg=T["surf2"]); rrow.pack(fill="x", pady=6)
        _mk_btn(rrow, "Refresh", T["surf3"], T["text"], self._populate_backups, size=8).pack(side="left")
        _mk_btn(rrow, "RESTORE SELECTED", T["red_bg"], T["red"], self._restore_selected, T["red"]).pack(side="right")

    # ── Logic ──────────────────────────────────────────────────────────────────
    def _section(self, title, color):
        s = tk.Frame(self.body, bg=T["bg"]); s.pack(fill="x", padx=14, pady=(20, 2))
        tk.Frame(s, bg=color, width=4, height=22).pack(side="left", padx=(0, 10))
        tk.Label(s, text=title, font=(T["font"], 11, "bold"), fg=color, bg=T["bg"]).pack(side="left")
        f = tk.Frame(self.body, bg=T["surf2"], padx=24, pady=20)
        f.pack(fill="x", padx=14, pady=(0, 10))
        return f

    def _save(self):
        try:
            self.settings["company_name"] = self._cname.get()
            self.settings["company_subtitle"] = self._csub.get()
            self.settings["logo_path"] = self._logo_path_var.get()
            self.settings["export_dir"] = self._export_dir_var.get()
            self.settings["reminder_days"] = int(self._reminder_days.get() or "7")
            
            save_settings(self.settings)
            self._status_var.set("✅ SAVED!")
            messagebox.showinfo("Success", "Settings saved successfully!", parent=self)
            if self.on_saved: self.on_saved(self.settings)
            self.after(500, self.destroy)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _browse_logo(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if p: self._logo_path_var.set(p); self._refresh_logo_preview()

    def _refresh_logo_preview(self):
        p = self._logo_path_var.get()
        if p and os.path.exists(p):
            try:
                img = Image.open(p); img.thumbnail((160, 60))
                self._logo_img = ImageTk.PhotoImage(img)
                self._logo_preview.config(image=self._logo_img, text="")
                return
            except: pass
        self._logo_preview.config(image="", text="No logo")

    def _browse_export(self):
        d = filedialog.askdirectory(); 
        if d: self._export_dir_var.set(d)

    def _populate_backups(self):
        self._bk_tree.delete(*self._bk_tree.get_children())
        if not os.path.isdir(BACKUP_DIR): return
        for sub in ("daily", "on_close", "manual"):
            d = os.path.join(BACKUP_DIR, sub)
            if not os.path.isdir(d): continue
            for fn in sorted(os.listdir(d), reverse=True):
                if not fn.endswith(".sqlite"): continue
                fp = os.path.join(d, fn)
                sz = f"{os.path.getsize(fp)//1024} KB"
                mod = __import__("datetime").datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%d-%b-%y")
                self._bk_tree.insert("", "end", values=(sub, fn, sz, mod))

    def _restore_selected(self):
        sel = self._bk_tree.selection()
        if not sel: return
        vals = self._bk_tree.item(sel[0])["values"]
        path = os.path.join(BACKUP_DIR, vals[0], vals[1])
        if messagebox.askyesno("Confirm", "Replace database?", parent=self):
            backup_manual()
            shutil.copy2(path, SQLITE_DB)
            messagebox.showinfo("Done", "Restored! Please restart.", parent=self)

# ── Helpers ──────────────────────────────────────────────────────────────────
# Thin aliases so existing call sites keep working after centralisation in widgets.py
def _mk_btn(parent, text, bg, fg, cmd, hov_bg=None, size=9):
    return mk_btn(parent, text, bg, fg, cmd, hov_bg, size)

def _mk_entry(parent, var, width=30):
    return mk_entry(parent, var, width)
