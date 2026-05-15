import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from copy import deepcopy

from config import T, COLUMNS, STATUS_OPTIONS, DEFAULT_COUNTRY_CUTOFF, bind_hover, CHANGELOG_FILE
from logic import calculate_row
from database import auth_load, _auth_save, _hp, log_action
import json

# ── Mousewheel Helper ────────────────────────────────────────────────────────
def add_mouse_wheel(widget, canvas):
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def bind_recursive(w):
        w.bind("<MouseWheel>", _on_mousewheel)
        for child in w.winfo_children():
            bind_recursive(child)
    
    canvas.bind("<MouseWheel>", _on_mousewheel)
    bind_recursive(widget)


# ── Professional Confirmation / Info / Warning Popup ─────────────────────────
class ProToast(tk.Toplevel):
    """Premium dark-themed confirmation / info / warning / error popup."""
    _PRESETS = {
        "success":  {"icon": "✓", "accent": "#22C55E", "bg_tint": "#0D2418"},
        "info":     {"icon": "ℹ", "accent": "#3B82F6", "bg_tint": "#0A1530"},
        "warning":  {"icon": "⚠", "accent": "#F59E0B", "bg_tint": "#251A05"},
        "error":    {"icon": "✗", "accent": "#EF4444", "bg_tint": "#260D0D"},
        "confirm":  {"icon": "?", "accent": "#F59E0B", "bg_tint": "#251A05"},
    }

    def __init__(self, parent, mode, title, message, on_yes=None, on_no=None):
        super().__init__(parent)
        preset = self._PRESETS.get(mode, self._PRESETS["info"])
        accent = preset["accent"]
        bg_tint = preset["bg_tint"]
        is_confirm = mode == "confirm"
        self.on_yes = on_yes
        self.on_no = on_no
        self._result = False

        self.configure(bg=T["border"])
        self.attributes("-topmost", True)
        self.transient(parent)
        
        # Windows-specific: make it a tool window (no min/max buttons)
        if os.name == "nt":
            self.attributes("-toolwindow", True)
            
        self.wait_visibility()
        self.grab_set()
        self.focus_force()

        # Inner frame (1px border effect)
        inner = tk.Frame(self, bg=T["bg"])
        inner.pack(padx=1, pady=1, fill="both", expand=True)

        # Top accent strip
        tk.Frame(inner, bg=accent, height=4).pack(fill="x")

        # Icon + title header
        hdr = tk.Frame(inner, bg=bg_tint, pady=16)
        hdr.pack(fill="x")
        icon_cv = tk.Canvas(hdr, width=44, height=44, bg=bg_tint, highlightthickness=0)
        icon_cv.pack(side="left", padx=(22, 14))
        icon_cv.create_oval(2, 2, 42, 42, fill=accent, outline="")
        icon_cv.create_text(22, 22, text=preset["icon"],
                            font=(T["mono"], 18, "bold"), fill="white")
        tf = tk.Frame(hdr, bg=bg_tint)
        tf.pack(side="left", fill="y")
        tk.Label(tf, text=title, font=(T["font"], 13, "bold"),
                 fg=T["text"], bg=bg_tint).pack(anchor="w")
        tk.Label(tf, text=mode.upper(), font=(T["mono"], 7),
                 fg=accent, bg=bg_tint).pack(anchor="w")

        # Message body
        body = tk.Frame(inner, bg=T["bg"], pady=14, padx=26)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=message, font=(T["font"], 10),
                 fg=T["muted"], bg=T["bg"], wraplength=380,
                 justify="left").pack(anchor="w")

        # Separator
        tk.Frame(inner, bg=T["border"], height=1).pack(fill="x")

        # Button bar
        btn_bar = tk.Frame(inner, bg=T["surf"], pady=14, padx=22)
        btn_bar.pack(fill="x", side="bottom")

        if is_confirm:
            # No button
            no_btn = tk.Button(btn_bar, text="   ✕  No   ",
                               font=(T["font"], 10, "bold"), bg=T["surf3"],
                               fg=T["text"], relief="flat", padx=18, pady=8,
                               cursor="hand2", command=self._on_cancel,
                               activebackground=T["surf4"], activeforeground=T["text"])
            no_btn.pack(side="right", padx=(8, 0))
            bind_hover(no_btn, T["surf3"], T["surf4"], T["text"], T["text"])

            # Yes button
            yes_btn = tk.Button(btn_bar, text="   ✓  Yes   ",
                                font=(T["font"], 10, "bold"), bg=accent,
                                fg="white", relief="flat", padx=18, pady=8,
                                cursor="hand2", command=self._on_confirm,
                                activebackground=accent, activeforeground="white")
            yes_btn.pack(side="right")
            bind_hover(yes_btn, accent, "#D97706", "white", "white")
            yes_btn.focus_set()
            self.bind("<Return>", lambda _: self._on_confirm())
            self.bind("<Escape>", lambda _: self._on_cancel())
        else:
            ok_btn = tk.Button(btn_bar, text="   OK   ",
                               font=(T["font"], 10, "bold"), bg=accent,
                               fg="white", relief="flat", padx=30, pady=8,
                               cursor="hand2", command=self._dismiss,
                               activebackground=accent, activeforeground="white")
            ok_btn.pack(side="right")
            ok_btn.focus_set()
            self.bind("<Return>", lambda _: self._dismiss())
            self.bind("<Escape>", lambda _: self._dismiss())
            if mode in ("success", "info"):
                self.after(3500, lambda: self._dismiss() if self.winfo_exists() else None)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel if is_confirm else self._dismiss)

        # Center on parent
        msg_len = len(message.split("\n"))
        h_extra = min(msg_len * 18, 150)
        w, h = 440, (260 + h_extra) if is_confirm else (230 + h_extra // 2)
        self.geometry(f"{w}x{h}")
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")

    def _on_confirm(self):
        self._result = True
        cb = self.on_yes
        self.grab_release()
        self.destroy()
        if cb: cb()

    def _on_cancel(self):
        self._result = False
        cb = self.on_no
        self.grab_release()
        self.destroy()
        if cb: cb()

    def _dismiss(self):
        try: self.destroy()
        except: pass


def show_confirm(parent, title, message, on_yes):
    """Shortcut for confirmation dialogs with Yes/No buttons."""
    ProToast(parent, "confirm", title, message, on_yes=on_yes)




class SearchableCombobox(ttk.Combobox):
    """A premium Combobox that filters its values as the user types."""
    def __init__(self, parent, values=None, **kwargs):
        self._all_vals = values or []
        super().__init__(parent, values=self._all_vals, **kwargs)
        self.bind("<KeyRelease>", self._on_key)
        self.bind("<FocusIn>", lambda _: self.event_generate('<Down>'))

    def _on_key(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"): return
        q = self.get().lower()
        if not q:
            self["values"] = self._all_vals
        else:
            filt = [v for v in self._all_vals if q in str(v).lower()]
            self["values"] = filt
        
        # Keep dropdown open while typing
        self.event_generate('<Down>')

class RowEditor(tk.Toplevel):
    def __init__(self, parent, row_data, title, on_save, current_user, 
                 factory_merchants=None, countries=None, colors=None, seasons=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("700x640")
        self.configure(bg=T["bg"])
        self.resizable(True, True)
        self.row_data = deepcopy(row_data)
        self.on_save = on_save
        self.current_user = current_user
        self._vars = {}
        self.factory_merchants = factory_merchants or []
        self.countries = countries or []
        self.colors = colors or []
        self.seasons = seasons or []
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=T["surf"], pady=8)
        top.pack(fill="x")
        tk.Label(top, text=self.title(), font=(T["mono"], 10, "bold"),
                 fg=T["accent"], bg=T["surf"]).pack(side="left", padx=16)
        
        canvas = tk.Canvas(self, bg=T["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=8, pady=8)
        
        form = tk.Frame(canvas, bg=T["bg"])
        canvas.create_window((0, 0), window=form, anchor="nw")
        form.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        groups = {
            "📋 Order Info (PDF Auto — Editable)": [c for c in COLUMNS if c["type"]=="pdf_auto"],
            "✏  Manual Entry":          [c for c in COLUMNS if c["type"]=="manual"],
            "🔢 Auto Calculated":       [c for c in COLUMNS if c["type"] in ("calc","auto","auto_co","auto_fl")],
            "📦 Status":                [c for c in COLUMNS if c["type"]=="status"],
        }
        
        for grp, cols in groups.items():
            if not cols: continue
            gh = tk.Frame(form, bg=T["surf2"])
            gh.pack(fill="x", pady=(10, 2), padx=4)
            tk.Label(gh, text=grp, font=(T["font"], 9, "bold"), fg=T["gold"],
                     bg=T["surf2"], pady=5, padx=10).pack(side="left")
            
            grid = tk.Frame(form, bg=T["bg"])
            grid.pack(fill="x", padx=8, pady=2)
            
            for i, col in enumerate(cols):
                rf = i // 2
                cf = (i % 2) * 2
                lbl = col["label"]
                if col["type"] == "auto_co": lbl += "  [Auto·Country]"
                elif col["type"] == "auto_fl": lbl += "  [Auto·ToD]"
                
                tk.Label(grid, text=lbl, font=(T["font"], 8), fg=T["muted"], bg=T["bg"],
                         anchor="w").grid(row=rf*2, column=cf, sticky="w", padx=(8, 4), pady=(4, 0))
                
                var = tk.StringVar(value=str(self.row_data.get(col["key"], "") or ""))
                self._vars[col["key"]] = var
                ro = col["type"] in ("calc", "auto", "auto_co", "auto_fl")
                
                # Widget Mapping
                if col["type"] == "status":
                    w = ttk.Combobox(grid, textvariable=var, values=STATUS_OPTIONS,
                                   state="readonly", font=(T["font"], 9), width=22)
                elif col["key"] == "country":
                    w = SearchableCombobox(grid, textvariable=var, values=self.countries,
                                          font=(T["font"], 9), width=22)
                elif col["key"] == "colour":
                    w = SearchableCombobox(grid, textvariable=var, values=self.colors,
                                          font=(T["font"], 9), width=22)
                elif col["key"] == "season":
                    w = SearchableCombobox(grid, textvariable=var, values=self.seasons,
                                          font=(T["font"], 9), width=22)
                elif col["key"] == "factory_merch":
                    w = SearchableCombobox(grid, textvariable=var, values=self.factory_merchants,
                                          font=(T["font"], 9), width=22)
                else:
                    w = tk.Entry(grid, textvariable=var, font=(T["mono"], 9),
                               bg=T["surf"] if ro else T["surf2"],
                               fg=T["muted"] if ro else T["text"],
                               disabledforeground=T["muted"],
                               readonlybackground=T["surf"],
                               relief="flat", bd=0,
                               state="readonly" if ro else "normal",
                               insertbackground=T["text"], width=24)
                
                w.grid(row=rf*2+1, column=cf, sticky="ew", padx=(8, 16), pady=(0, 2), ipady=4, ipadx=4)
        
        bf = tk.Frame(self, bg=T["surf"], pady=10)
        bf.pack(fill="x")
        self.save_btn = tk.Button(bf, text="💾  SAVE", font=(T["mono"], 10, "bold"), bg=T["green"], fg="white",
                  relief="flat", padx=20, pady=8, cursor="hand2", command=self._save)
        self.save_btn.pack(side="right", padx=12)
        
        tk.Button(bf, text="✕  Cancel", font=(T["font"], 9), bg=T["surf2"], fg=T["muted"],
                  relief="flat", padx=14, pady=8, cursor="hand2", command=self.destroy).pack(side="right", padx=4)

    def _save(self):
        updated = dict(self.row_data)
        changes = []
        is_new = not any(self.row_data.get(k) for k in ("order_no", "style_name", "colour"))
        
        for key, var in self._vars.items():
            col = next((c for c in COLUMNS if c["key"] == key), None)
            if col and col["type"] not in ("auto", "auto_co", "auto_fl", "calc"):
                val = var.get()
                old_val = str(self.row_data.get(key, "") or "")
                if val != old_val:
                    lbl = col["label"]
                    changes.append(f"  • {lbl}:  '{old_val}'  →  '{val}'")
                updated[key] = val
        
        if not is_new and not changes:
            ProToast(self, "info", "No Changes", "No changes were detected to save."); return

        updated = calculate_row(updated)
        updated["date_added"] = updated.get("date_added") or datetime.now().strftime("%d-%b-%Y")
        updated["added_by"] = self.current_user.get("username", "")

        if is_new:
            msg = f"Save this new record for Order '{updated.get('order_no','N/A')}'?"
        else:
            msg = f"Save changes to Order '{updated.get('order_no','N/A')}'?\n\n"
            msg += "\n".join(changes[:8])
            if len(changes) > 8:
                msg += f"\n  ... and {len(changes)-8} more fields."
        def _do_save():
            frames = ["⏳ Saving.", "⏳ Saving..", "⏳ Saving..."]
            self.save_btn.config(state="disabled", bg=T["surf3"], fg=T["gold"])
            def finish():
                try:
                    self.on_save(updated); self.destroy()
                except Exception as e:
                    self.save_btn.config(state="normal", text="💾  SAVE", bg=T["green"], fg="white")
                    ProToast(self, "error", "Save Failed", f"Database error:\n{e}")
            def step(i):
                if i < len(frames):
                    self.save_btn.config(text=frames[i])
                    self.after(150, lambda: step(i+1))
                else:
                    self.save_btn.config(text="✅ SAVED!", bg=T["green"], fg="white")
                    self.after(300, finish)
            step(0)
        show_confirm(self, "Save Changes?", msg, on_yes=_do_save)

class BulkEditor(tk.Toplevel):
    EDITABLE=[("hm_merch","H&M Merch"),("hm_tech","H&M Tech"),
              ("factory_merch","Factory Merch"),("ship_qty_set","Ship Qty In Set"),
              ("carton_qty","Carton Qty"),("shipped_status","Shipped Status")]
    def __init__(self,parent,rows,on_save,factory_merchants=None):
        super().__init__(parent)
        self.title(f"Bulk Edit — {len(rows)} rows selected")
        self.geometry("500x400"); self.configure(bg=T["bg"]); self.resizable(False,True)
        self._rows=rows; self._on_save=on_save; self._vars={}; self._apply={}; self.factory_merchants = factory_merchants or []
        self._build()

    def _build(self):
        top=tk.Frame(self,bg=T["surf"],pady=8); top.pack(fill="x")
        tk.Label(top,text=f"BULK EDIT — {len(self._rows)} ROWS",font=(T["mono"],10,"bold"),
                 fg=T["accent"],bg=T["surf"]).pack(side="left",padx=16)
        info=tk.Frame(self,bg=T["surf2"],pady=5); info.pack(fill="x",padx=10,pady=(4,0))
        tk.Label(info,text="  ☑ Only checked fields will be updated. Others will remain unchanged.",
                 font=(T["font"],8),fg=T["gold"],bg=T["surf2"]).pack(anchor="w",padx=8)
        sf=tk.Frame(self,bg=T["bg"]); sf.pack(fill="both",expand=True,padx=8,pady=8)
        for key,label in self.EDITABLE:
            rf=tk.Frame(sf,bg=T["bg"]); rf.pack(fill="x",padx=8,pady=6)
            av=tk.BooleanVar(value=False); self._apply[key]=av
            tk.Checkbutton(rf,variable=av,bg=T["bg"],fg=T["text"],
                           activebackground=T["bg"],selectcolor=T["surf2"],
                           relief="flat").pack(side="left",padx=(0,4))
            tk.Label(rf,text=label,font=(T["font"],9),fg=T["muted"],bg=T["bg"],
                     width=18,anchor="w").pack(side="left")
            var=tk.StringVar(); self._vars[key]=var
            if key=="shipped_status":
                w=ttk.Combobox(rf,textvariable=var,values=STATUS_OPTIONS,
                               state="readonly",font=(T["font"],9),width=22)
            elif key=="factory_merch":
                w=ttk.Combobox(rf,textvariable=var,values=self.factory_merchants,
                               font=(T["font"],9),width=22)
            else:
                w=tk.Entry(rf,textvariable=var,font=(T["mono"],9),
                           bg=T["surf2"],fg=T["text"],relief="flat",bd=0,
                           width=24,insertbackground=T["text"])
            w.pack(side="left",ipady=4,ipadx=4)
        bf=tk.Frame(self,bg=T["surf"],pady=10); bf.pack(fill="x")
        self.save_btn = tk.Button(bf,text="💾  Apply Changes",font=(T["mono"],10,"bold"),bg=T["green"],fg="white",
                  relief="flat",padx=20,pady=8,cursor="hand2",command=self._save)
        self.save_btn.pack(side="right",padx=12)
        tk.Button(bf,text="✕  Cancel",font=(T["font"],9),bg=T["surf2"],fg=T["muted"],
                  relief="flat",padx=14,pady=8,cursor="hand2",command=self.destroy).pack(side="right",padx=4)

    def _save(self):
        changed=[(k,self._vars[k].get()) for k,_ in self.EDITABLE if self._apply[k].get()]
        if not changed: ProToast(self, "info", "No Selection", "No field was checked for update."); return
        updated=[]
        for row in self._rows:
            r=dict(row)
            for k,v in changed: r[k]=v
            updated.append(calculate_row(r))
        def _do_bulk():
            frames = ["⏳ Saving.", "⏳ Saving..", "⏳ Saving..."]
            self.save_btn.config(state="disabled", bg=T["surf3"], fg=T["gold"])
            def finish():
                try:
                    self._on_save(updated); self.destroy()
                    log_action("N/A", "Bulk Edit", f"Applied changes to {len(self._targets)} rows.")
                except Exception as e:
                    self.save_btn.config(state="normal", text="💾  Apply Changes", bg=T["green"], fg="white")
                    ProToast(self, "error", "Bulk Edit Failed", f"Database error:\n{e}")
            def step(i):
                if i < len(frames):
                    self.save_btn.config(text=frames[i])
                    self.after(150, lambda: step(i+1))
                else:
                    self.save_btn.config(text="✅ APPLIED!", bg=T["green"], fg="white")
                    self.after(300, finish)
            step(0)
        show_confirm(self, "Apply Bulk Edit?",
                     f"Update {len(changed)} field(s) across {len(self._rows)} row(s)?",
                     on_yes=_do_bulk)

class FactoryMerchantManager(tk.Toplevel):
    def __init__(self, parent, db, on_save):
        super().__init__(parent)
        self.title("🏭 Factory & Merchant Manager")
        self.geometry("400x500"); self.configure(bg=T["bg"])
        self.grab_set()
        self.db = db; self.on_save = on_save
        self.items = list(db.get("factory_merchants", []))
        self._build()
        
    def _build(self):
        hdr = tk.Frame(self, bg=T["surf"], pady=12); hdr.pack(fill="x")
        tk.Label(hdr, text="🏭 FACTORY & MERCHANT LIST", font=(T["mono"],11,"bold"), fg=T["accent"], bg=T["surf"]).pack()
        
        main = tk.Frame(self, bg=T["bg"], padx=20, pady=10); main.pack(fill="both", expand=True)
        
        af = tk.Frame(main, bg=T["surf2"], pady=10, padx=10); af.pack(fill="x", pady=(0,10))
        self.new_var = tk.StringVar()
        tk.Entry(af, textvariable=self.new_var, font=(T["mono"],10), bg=T["surf"], fg=T["text"], insertbackground=T["text"], width=20, relief="flat").pack(side="left", padx=5, ipady=4)
        tk.Button(af, text="➕ ADD", font=(T["font"],9,"bold"), bg=T["green"], fg="white", relief="flat", cursor="hand2", command=self._add).pack(side="left", padx=5)
        
        self.lb = tk.Listbox(main, bg=T["surf2"], fg=T["text"], font=(T["mono"],10), selectbackground=T["surf"], selectforeground=T["gold"], relief="flat", bd=0)
        self.lb.pack(fill="both", expand=True)
        for it in self.items: self.lb.insert("end", it)

        def _on_mousewheel(event):
            self.lb.yview_scroll(int(-1*(event.delta/120)), "units")
        self.lb.bind("<MouseWheel>", _on_mousewheel)
        
        tk.Button(main, text="🗑️ Delete Selected", font=(T["font"],9), bg=T["red"], fg="white", relief="flat", cursor="hand2", command=self._delete).pack(pady=10)
        
        bf = tk.Frame(self, bg=T["surf"], pady=10); bf.pack(fill="x")
        self.save_btn = tk.Button(bf, text="💾 SAVE", font=(T["mono"],10,"bold"), bg=T["blue"], fg="white", relief="flat", padx=20, pady=8, cursor="hand2", command=self._do_save)
        self.save_btn.pack()
        
    def _add(self):
        v = self.new_var.get().strip()
        if v and v not in self.items:
            self.items.append(v)
            self.lb.insert("end", v)
            self.new_var.set("")
            
    def _delete(self):
        sel = self.lb.curselection()
        if not sel: return
        idx = sel[0]
        name = self.items[idx]
        def _do_del():
            del self.items[idx]
            self.lb.delete(idx)
        show_confirm(self, "Delete Item?",
                     f"Remove '{name}' from the list?", on_yes=_do_del)

    def _do_save(self):
        def _do():
            self.db["factory_merchants"] = sorted(self.items)
            frames = ["⏳ Saving.", "⏳ Saving..", "⏳ Saving..."]
            self.save_btn.config(state="disabled", bg=T["surf3"], fg=T["gold"])
            def finish():
                self.on_save(self.db)
                self.destroy()
            def step(i):
                if i < len(frames):
                    self.save_btn.config(text=frames[i])
                    self.after(150, lambda: step(i+1))
                else:
                    self.save_btn.config(text="✅ SAVED!", bg=T["green"], fg="white")
                    self.after(300, finish)
            step(0)
        show_confirm(self, "Save Changes?",
                     "Save the Factory & Merchant list?", on_yes=_do)

class AdvancedSearchDialog(tk.Toplevel):
    """Full-featured advanced filter dialog with:
    - Multi-select Shipped Status checkboxes
    - Date Range (ToD)
    - Colour / Season / Country combos
    """
    def __init__(self, parent, colors, seasons, countries, current_filters, on_apply):
        super().__init__(parent)
        self.title("\U0001f50d  Advanced Filter")
        self.geometry("480x620"); self.configure(bg=T["bg"]); self.resizable(False, True)
        self.grab_set()
        self.on_apply   = on_apply
        self.prev       = dict(current_filters) if current_filters else {}
        self.colors     = sorted(list(colors))
        self.seasons    = sorted(list(seasons))
        self.countries  = sorted(list(countries))
        self._status_vars = {}
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────────
    def _build(self):
        # Accent top bar
        tk.Frame(self, bg=T["accent"], height=3).pack(fill="x")

        # Header
        hdr = tk.Frame(self, bg=T["surf"]); hdr.pack(fill="x")
        tk.Frame(hdr, bg=T["accent"], width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="  \U0001f50d  ADVANCED FILTER",
                 font=(T["mono"], 11, "bold"), fg=T["text"],
                 bg=T["surf"]).pack(side="left", pady=12, padx=6)
        # Active filter indicator
        self._active_lbl = tk.Label(hdr, text="",
                                    font=(T["font"], 8), fg=T["gold"], bg=T["surf"])
        self._active_lbl.pack(side="right", padx=12)
        self._update_active_lbl()

        # Scrollable body
        canvas = tk.Canvas(self, bg=T["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y"); canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg=T["bg"])
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw", width=464)
        add_mouse_wheel(body, canvas)

        # ── Section 1: Status ────────────────────────────────────────────────
        self._section(body, "SHIPPED STATUS", T["blue"])
        sf = tk.Frame(body, bg=T["surf2"], padx=16, pady=10)
        sf.pack(fill="x", padx=12, pady=(0, 6))
        prev_statuses = set(self.prev.get("statuses") or [])
        all_statuses  = ["Pending", "Shipped", "Cancelled",
                         "1st Shipment", "Last Shipment"]
        cols = 2
        for i, st in enumerate(all_statuses):
            var = tk.BooleanVar(value=(st in prev_statuses) if prev_statuses else False)
            self._status_vars[st] = var
            r, c = divmod(i, cols)
            cb = tk.Checkbutton(sf, text=f"  {st}", variable=var,
                                font=(T["font"], 9), bg=T["surf2"],
                                fg=self._status_color(st),
                                activebackground=T["surf2"],
                                selectcolor=T["surf3"],
                                relief="flat", anchor="w",
                                command=self._update_active_lbl)
            cb.grid(row=r, column=c, sticky="w", padx=8, pady=3)

        # ── Section 2: Colour & Season ───────────────────────────────────────
        self._section(body, "COLOUR & SEASON", T["gold"])
        cs_f = tk.Frame(body, bg=T["surf2"], padx=16, pady=12)
        cs_f.pack(fill="x", padx=12, pady=(0, 6))

        self._colour_var = self._make_combo(cs_f, "\U0001f3a8  Colour",
                                            self.colors, "colour", row=0)
        self._season_var = self._make_combo(cs_f, "\U0001f324  Season",
                                            self.seasons, "season", row=1)

        # ── Section 3: Country ───────────────────────────────────────────────
        self._section(body, "COUNTRY", T["teal"])
        ct_f = tk.Frame(body, bg=T["surf2"], padx=16, pady=12)
        ct_f.pack(fill="x", padx=12, pady=(0, 6))
        self._country_var = self._make_combo(ct_f, "\U0001f30d  Country",
                                             self.countries, "country", row=0)

        # ── Section 4: Date Range (ToD) ──────────────────────────────────────
        self._section(body, "TOD DATE RANGE", T["accent"])
        dr_f = tk.Frame(body, bg=T["surf2"], padx=16, pady=12)
        dr_f.pack(fill="x", padx=12, pady=(0, 10))

        self.use_date = tk.BooleanVar(value=bool(self.prev.get("use_date", False)))
        ck = tk.Checkbutton(dr_f, text="  Enable Date Range Filter",
                            variable=self.use_date, font=(T["font"], 9),
                            bg=T["surf2"], fg=T["text"],
                            activebackground=T["surf2"], selectcolor=T["surf3"],
                            relief="flat", command=self._toggle_date)
        ck.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        from tkcalendar import DateEntry
        date_kw = dict(width=14, background="#0D2137", foreground="white",
                       borderwidth=0, date_pattern="dd-M-yy",
                       headersbackground=T["accent"], headersforeground="white",
                       selectbackground=T["accent"], selectforeground="white")

        tk.Label(dr_f, text="From:", font=(T["font"], 9),
                 fg=T["muted"], bg=T["surf2"]).grid(row=1, column=0, sticky="w", padx=(0, 6))
        self.d_start = DateEntry(dr_f, **date_kw)
        if self.prev.get("start_date"): self.d_start.set_date(self.prev["start_date"])
        self.d_start.grid(row=1, column=1, padx=(0, 16))

        tk.Label(dr_f, text="To:", font=(T["font"], 9),
                 fg=T["muted"], bg=T["surf2"]).grid(row=1, column=2, sticky="w", padx=(0, 6))
        self.d_end = DateEntry(dr_f, **date_kw)
        if self.prev.get("end_date"): self.d_end.set_date(self.prev["end_date"])
        self.d_end.grid(row=1, column=3)

        # Quick date shortcuts
        qf = tk.Frame(dr_f, bg=T["surf2"]); qf.grid(row=2, column=0, columnspan=4, pady=(10, 0))
        from datetime import date, timedelta
        today = date.today()
        quick_btns = [
            ("This Month",  date(today.year, today.month, 1),
                             date(today.year, today.month+1, 1) - timedelta(1) if today.month < 12
                             else date(today.year, 12, 31)),
            ("Next Month",  date(today.year, today.month % 12 + 1, 1) if today.month < 12
                             else date(today.year+1, 1, 1),
                             date(today.year, (today.month % 12) + 1,
                                  28) if today.month < 12 else date(today.year+1, 1, 31)),
            ("This Week",   today - timedelta(days=today.weekday()),
                             today - timedelta(days=today.weekday()) + timedelta(6)),
            ("+30 Days",    today, today + timedelta(30)),
        ]
        for label, d1, d2 in quick_btns:
            b = tk.Button(qf, text=label,
                          font=(T["font"], 8), bg=T["surf3"], fg=T["text"],
                          relief="flat", padx=8, pady=3, cursor="hand2",
                          command=lambda a=d1, b_=d2: (
                              self.d_start.set_date(a),
                              self.d_end.set_date(b_),
                              self.use_date.set(True),
                              self._toggle_date()))
            b.pack(side="left", padx=3)
            bind_hover(b, T["surf3"], T["accent3"], T["text"], "white")

        self._toggle_date()  # set initial enabled/disabled state

        # ── Bottom bar ───────────────────────────────────────────────────────
        bot = tk.Frame(self, bg=T["surf"], pady=10); bot.pack(fill="x", side="bottom")
        clr_btn = tk.Button(bot, text="\U0001f9f9  Clear All", font=(T["font"], 9),
                            bg=T["red_bg"], fg=T["red"], relief="flat",
                            padx=14, pady=7, cursor="hand2", command=self._clear)
        clr_btn.pack(side="left", padx=14)
        bind_hover(clr_btn, T["red_bg"], T["red"], T["red"], "white")

        self.apply_btn = tk.Button(bot, text="\U0001f50d  Apply Filter",
                                   font=(T["font"], 10, "bold"),
                                   bg=T["accent"], fg="white", relief="flat",
                                   padx=20, pady=8, cursor="hand2",
                                   command=self._apply,
                                   activebackground=T["accent2"], activeforeground="white")
        self.apply_btn.pack(side="right", padx=14)
        bind_hover(self.apply_btn, T["accent"], T["accent2"], "white", "white")

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _section(self, parent, title, color):
        f = tk.Frame(parent, bg=T["bg"]); f.pack(fill="x", padx=12, pady=(12, 2))
        tk.Frame(f, bg=color, width=3, height=16).pack(side="left", padx=(0, 8))
        tk.Label(f, text=title, font=(T["font"], 8, "bold"),
                 fg=color, bg=T["bg"]).pack(side="left")

    def _make_combo(self, parent, label, values, key, row=0):
        tk.Label(parent, text=label, font=(T["font"], 9, "bold"),
                 fg=T["text"], bg=T["surf2"], width=14,
                 anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        prev_val = self.prev.get(key, "")
        var = tk.StringVar(value=prev_val if prev_val else "All")
        cb = ttk.Combobox(parent, textvariable=var,
                          values=["All"] + values,
                          state="readonly", width=24, font=(T["font"], 9))
        cb.grid(row=row, column=1, sticky="w", pady=4)
        cb.bind("<<ComboboxSelected>>", lambda _: self._update_active_lbl())
        return var

    def _status_color(self, st):
        return {
            "Shipped": T["green"], "Pending": T["gold"],
            "Cancelled": T["red"], "1st Shipment": T["blue"],
            "Last Shipment": T["teal"],
        }.get(st, T["text"])

    def _toggle_date(self):
        state = "normal" if self.use_date.get() else "disabled"
        self.d_start.config(state=state)
        self.d_end.config(state=state)
        self._update_active_lbl()

    def _update_active_lbl(self):
        n = 0
        selected = [s for s, v in self._status_vars.items() if v.get()]
        if selected: n += 1
        if getattr(self, "_colour_var", None) and self._colour_var.get() not in ("", "All"): n += 1
        if getattr(self, "_season_var",  None) and self._season_var.get()  not in ("", "All"): n += 1
        if getattr(self, "_country_var", None) and self._country_var.get() not in ("", "All"): n += 1
        if getattr(self, "use_date",     None) and self.use_date.get(): n += 1
        self._active_lbl.config(text=f"  {n} filter(s) active" if n else "")

    # ── Actions ────────────────────────────────────────────────────────────────
    def _clear(self):
        self.on_apply({})
        self.destroy()

    def _apply(self):
        statuses = [s for s, v in self._status_vars.items() if v.get()]
        res = {
            "statuses":    statuses,
            "colour":      self._colour_var.get() if self._colour_var.get() != "All" else "",
            "season":      self._season_var.get()  if self._season_var.get()  != "All" else "",
            "country":     self._country_var.get() if self._country_var.get() != "All" else "",
            "use_date":    self.use_date.get(),
            "start_date":  self.d_start.get_date() if self.use_date.get() else None,
            "end_date":    self.d_end.get_date()   if self.use_date.get() else None,
        }
        frames = ["\u29d6 Applying.", "\u29d6 Applying..", "\u29d6 Applying..."]
        self.apply_btn.config(state="disabled", bg=T["surf3"], fg=T["gold"])
        def finish():
            self.on_apply(res); self.destroy()
        def step(i):
            if i < len(frames):
                self.apply_btn.config(text=frames[i])
                self.after(100, lambda: step(i + 1))
            else:
                self.apply_btn.config(text="\u2705 APPLIED!", bg=T["green"], fg="white")
                self.after(300, finish)
        step(0)




class CutoffManager(tk.Toplevel):
    def __init__(self, parent, cutoff_dict: dict, on_save_cb):
        super().__init__(parent)
        self.title("🗺  Country Cut Off Manager")
        self.geometry("580x600"); self.resizable(True,True)
        self.configure(bg=T["bg"])
        self.grab_set()
        self._co = dict(cutoff_dict)
        self._on_save = on_save_cb
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=T["surf"], pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text="🗺  COUNTRY CUT OFF MANAGER",
                 font=(T["mono"],11,"bold"), fg=T["accent"], bg=T["surf"]).pack(side="left",padx=16)

        info = tk.Frame(self, bg="#1A160E", pady=6); info.pack(fill="x",padx=10,pady=(6,0))
        tk.Label(info,
            text="  Add new country · Edit existing · Delete unnecessary ones\n"
                 "  Saving will apply to all orders immediately.",
            font=(T["font"],8), fg=T["gold"], bg="#1A160E",
            justify="left").pack(padx=10, anchor="w")

        frm = tk.Frame(self, bg=T["bg"]); frm.pack(fill="both",expand=True,padx=10,pady=8)
        s = ttk.Style()
        s.configure("CO.Treeview",background=T["surf2"],foreground=T["text"],
                    fieldbackground=T["surf2"],rowheight=24,font=(T["mono"],9))
        s.configure("CO.Treeview.Heading",background=T["surf3"],foreground=T["gold"],
                    font=(T["font"],9,"bold"),relief="flat")
        s.map("CO.Treeview",
              background=[("selected",T["accent"])],foreground=[("selected","white")])

        self.tree = ttk.Treeview(frm, columns=("code","co","note"), show="headings",
                                  style="CO.Treeview", height=14)
        self.tree.heading("code", text="Country Code")
        self.tree.heading("co",   text="Cut Off")
        self.tree.heading("note", text="Note")
        self.tree.column("code", width=140, anchor="center")
        self.tree.column("co",   width=120, anchor="center")
        self.tree.column("note", width=260, anchor="w")
        ys = ttk.Scrollbar(frm,orient="vertical",command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        ys.pack(side="right",fill="y"); self.tree.pack(fill="both",expand=True)
        self.tree.tag_configure("1st", foreground="#7DCF7D")
        self.tree.tag_configure("2nd", foreground="#7DAECF")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._refresh_tree()

        ef = tk.Frame(self, bg=T["surf"], pady=10, padx=14); ef.pack(fill="x",padx=10,pady=(0,4))
        tk.Label(ef, text="Add / Update Entry", font=(T["font"],9,"bold"),
                 fg=T["gold"], bg=T["surf"]).grid(row=0,column=0,columnspan=6,sticky="w",pady=(0,6))

        tk.Label(ef, text="Country Code:", font=(T["font"],9),
                 fg=T["muted"], bg=T["surf"]).grid(row=1,column=0,sticky="e",padx=(0,6))
        self._cv = tk.StringVar()
        ce = tk.Entry(ef, textvariable=self._cv, font=(T["mono"],11),
                      bg=T["surf2"], fg=T["text"], relief="flat", bd=0,
                      width=8, insertbackground=T["text"])
        ce.grid(row=1,column=1,ipady=6,ipadx=6,padx=(0,14))

        tk.Label(ef, text="Cut Off:", font=(T["font"],9),
                 fg=T["muted"], bg=T["surf"]).grid(row=1,column=2,sticky="e",padx=(0,6))
        self._cof = tk.StringVar(value="1st")
        cb = ttk.Combobox(ef, textvariable=self._cof, values=["1st","2nd"],
                          state="readonly", font=(T["font"],10), width=7)
        cb.grid(row=1,column=3,ipady=4,padx=(0,14))

        tk.Label(ef, text="Note (optional):", font=(T["font"],9),
                 fg=T["muted"], bg=T["surf"]).grid(row=1,column=4,sticky="e",padx=(0,6))
        self._nv = tk.StringVar()
        tk.Entry(ef, textvariable=self._nv, font=(T["font"],9),
                 bg=T["surf2"], fg=T["text"], relief="flat", bd=0,
                 width=18, insertbackground=T["text"]).grid(row=1,column=5,ipady=6,ipadx=4)

        bf = tk.Frame(ef, bg=T["surf"]); bf.grid(row=2,column=0,columnspan=6,pady=(10,0),sticky="w")
        for txt, cmd, bg in [
            ("➕  Add / Update", self._add_update, T["green"]),
            ("🗑  Delete Selected", self._delete, T["red"]),
            ("⟳  Reset Defaults", self._reset, T["surf3"]),
        ]:
            tk.Button(bf, text=txt, font=(T["font"],9,"bold" if "Add" in txt else "normal"),
                      bg=bg, fg="white" if bg!=T["surf3"] else T["muted"],
                      relief="flat", padx=12, pady=6, cursor="hand2",
                      command=cmd).pack(side="left",padx=(0,8))

        bot = tk.Frame(self, bg=T["surf"], pady=10); bot.pack(fill="x",padx=10)
        self.save_btn = tk.Button(bot, text="💾  Save & Apply",
                  font=(T["mono"],10,"bold"), bg=T["accent"], fg="white",
                  relief="flat", padx=22, pady=8, cursor="hand2",
                  command=self._save)
        self.save_btn.pack(side="right",padx=8)
        tk.Button(bot, text="✕  Cancel",
                  font=(T["font"],9), bg=T["surf2"], fg=T["muted"],
                  relief="flat", padx=14, pady=8, cursor="hand2",
                  command=self.destroy).pack(side="right",padx=4)
        tk.Label(bot, text=f"  {len(self._co)} entries loaded",
                 font=(T["mono"],8), fg=T["muted"], bg=T["surf"]).pack(side="left",padx=8)

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for code in sorted(self._co):
            co = self._co[code]
            note = "1st Cut — Ship first" if co=="1st" else "2nd Cut — Ship later"
            self.tree.insert("","end", values=(code, co, note), tags=(co,))

    def _on_select(self, *_):
        sel = self.tree.selection()
        if not sel: return
        v = self.tree.item(sel[0])["values"]
        self._cv.set(str(v[0]).upper()); self._cof.set(str(v[1]))

    def _add_update(self):
        code = self._cv.get().strip().upper()
        co   = self._cof.get().strip()
        if not code:
            ProToast(self, "warning", "Missing Code", "Please enter a Country code."); return
        if co not in ("1st","2nd"):
            ProToast(self, "warning", "Invalid Cut Off", "Cut Off must be 1st or 2nd."); return
        existed = code in self._co
        action = "Update" if existed else "Add"
        def _do():
            self._co[code] = co
            self._refresh_tree()
            self._cv.set(""); self._nv.set("")
            act = "Updated" if existed else "Added"
            self._status(f"✓  {act}: {code} → {co}")
        show_confirm(self, f"{action} Country?",
                     f"{action} country '{code}' with cut off '{co}'?", on_yes=_do)

    def _delete(self):
        sel = self.tree.selection()
        if not sel: ProToast(self, "info", "No Selection", "Please select a row first."); return
        code = str(self.tree.item(sel[0])["values"][0])
        def _do():
            self._co.pop(code, None); self._refresh_tree()
            self._status(f"✓  Deleted: {code}")
        show_confirm(self, "Delete Country?",
                     f"Remove country '{code}' from the cut off list?", on_yes=_do)

    def _reset(self):
        def _do_reset():
            self._co = dict(DEFAULT_COUNTRY_CUTOFF); self._refresh_tree()
            self._status(f"✓  Reset to defaults ({len(self._co)} entries)")
        show_confirm(self, "Reset to Defaults?",
                     "Reset to default list?\nAll custom changes will be lost.",
                     on_yes=_do_reset)

    def _save(self):
        def _do():
            frames = ["⏳ Saving.", "⏳ Saving..", "⏳ Saving..."]
            self.save_btn.config(state="disabled", bg=T["surf3"], fg=T["gold"])
            def finish():
                try:
                    self._on_save(dict(self._co)); self.destroy()
                except Exception as e:
                    self.save_btn.config(state="normal", text="💾  Save & Apply", bg=T["accent"], fg="white")
                    ProToast(self, "error", "Save Failed", f"Database error:\n{e}")
            def step(i):
                if i < len(frames):
                    self.save_btn.config(text=frames[i])
                    self.after(100, lambda: step(i+1))
                else:
                    self.save_btn.config(text="✅ SAVED!", bg=T["green"], fg="white")
                    self.after(200, finish)
            step(0)
        show_confirm(self, "Save & Apply?",
                     f"Save cut off settings ({len(self._co)} entries)?\nChanges will apply to all orders.",
                     on_yes=_do)

    def _status(self, msg):
        self.title(msg)
        self.after(2000, lambda: self.title("🗺  Country Cut Off Manager"))

class UserManager(tk.Toplevel):
    """
    Admin-only User Manager dialog.
    NOTE: No grab_set/transient — avoids Windows focus/deadlock issues.
    """
    def __init__(self, parent, current_user):
        super().__init__(parent)
        self.title("USER MANAGER")
        self.geometry("620x520")
        self.configure(bg=T["bg"])
        self.resizable(False, False)
        self.current_user = current_user
        self.users = auth_load()
        # Safe: bring to front without locking the event loop
        self.lift()
        self.focus_force()
        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────────
    def _build(self):
        # ── Header
        hdr = tk.Frame(self, bg=T["surf"], pady=0)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=T["accent"], height=3).pack(fill="x")
        tk.Label(hdr, text="  USER MANAGEMENT",
                 font=(T["mono"], 12, "bold"),
                 fg=T["accent"], bg=T["surf"], pady=10).pack(side="left")

        # ── User list tree
        tree_f = tk.Frame(self, bg=T["bg"])
        tree_f.pack(fill="both", padx=16, pady=(10, 4))

        s = ttk.Style()
        s.configure("UM.Treeview",
                    background=T["surf2"], foreground=T["text"],
                    fieldbackground=T["surf2"], rowheight=24,
                    font=(T["mono"], 9))
        s.configure("UM.Treeview.Heading",
                    background=T["surf"], foreground=T["gold"],
                    font=(T["font"], 9, "bold"), relief="flat")
        s.map("UM.Treeview",
              background=[("selected", T["accent"])],
              foreground=[("selected", "white")])

        cols = ("Username", "Full Name", "Role")
        self.tree = ttk.Treeview(tree_f, columns=cols,
                                 show="headings", style="UM.Treeview", height=7)
        self.tree.heading("Username",  text="Username")
        self.tree.heading("Full Name", text="Full Name")
        self.tree.heading("Role",      text="Role")
        self.tree.column("Username",  width=160, anchor="w")
        self.tree.column("Full Name", width=200, anchor="w")
        self.tree.column("Role",      width=180, anchor="center")

        ys = ttk.Scrollbar(tree_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._refresh()

        # ── Divider
        tk.Frame(self, bg=T["border"], height=1).pack(fill="x", padx=12, pady=6)

        # ── Form panel
        form = tk.Frame(self, bg=T["surf"], padx=16, pady=12)
        form.pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(form, text="ADD NEW USER / CHANGE PASSWORD",
                 font=(T["font"], 9, "bold"),
                 fg=T["gold"], bg=T["surf"]).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

        self._nu = tk.StringVar()
        self._nn = tk.StringVar()
        self._np = tk.StringVar()
        self._nr = tk.StringVar(value="user")

        # Row 1: Username + Full Name
        tk.Label(form, text="Username *", font=(T["font"], 9),
                 fg=T["muted"], bg=T["surf"]).grid(row=1, column=0, sticky="e", padx=(0, 6))
        tk.Entry(form, textvariable=self._nu,
                 font=(T["mono"], 10), bg=T["surf2"], fg=T["text"],
                 relief="flat", bd=0, width=16,
                 insertbackground=T["text"]).grid(
            row=1, column=1, sticky="ew", ipady=5, ipadx=4, padx=(0, 18))

        tk.Label(form, text="Full Name", font=(T["font"], 9),
                 fg=T["muted"], bg=T["surf"]).grid(row=1, column=2, sticky="e", padx=(0, 6))
        tk.Entry(form, textvariable=self._nn,
                 font=(T["mono"], 10), bg=T["surf2"], fg=T["text"],
                 relief="flat", bd=0, width=16,
                 insertbackground=T["text"]).grid(
            row=1, column=3, sticky="ew", ipady=5, ipadx=4)

        # Row 2: Password + Role
        tk.Label(form, text="Password *", font=(T["font"], 9),
                 fg=T["muted"], bg=T["surf"]).grid(row=2, column=0, sticky="e", padx=(0, 6), pady=(8, 0))
        tk.Entry(form, textvariable=self._np, show="*",
                 font=(T["mono"], 10), bg=T["surf2"], fg=T["text"],
                 relief="flat", bd=0, width=16,
                 insertbackground=T["text"]).grid(
            row=2, column=1, sticky="ew", ipady=5, ipadx=4, padx=(0, 18), pady=(8, 0))

        tk.Label(form, text="Role *", font=(T["font"], 9),
                 fg=T["muted"], bg=T["surf"]).grid(row=2, column=2, sticky="e", padx=(0, 6), pady=(8, 0))
        role_cb = ttk.Combobox(form, textvariable=self._nr,
                               values=["admin", "manager", "user"],
                               state="readonly", font=(T["font"], 10), width=14)
        role_cb.grid(row=2, column=3, sticky="ew", ipady=4, pady=(8, 0))

        # ── Buttons
        btn_f = tk.Frame(self, bg=T["bg"])
        btn_f.pack(fill="x", padx=16, pady=(0, 12))

        tk.Button(btn_f, text="  ✔  ADD / UPDATE USER  ",
                  font=(T["mono"], 10, "bold"),
                  bg=T["green"], fg="white", relief="flat",
                  padx=16, pady=8, cursor="hand2",
                  command=self._add).pack(side="left", padx=(0, 10))

        tk.Button(btn_f, text="  🗑  DELETE SELECTED  ",
                  font=(T["font"], 9),
                  bg=T["red"], fg="white", relief="flat",
                  padx=12, pady=8, cursor="hand2",
                  command=self._del).pack(side="left", padx=(0, 10))

        tk.Button(btn_f, text="  ✕  Close  ",
                  font=(T["font"], 9),
                  bg=T["surf2"], fg=T["muted"], relief="flat",
                  padx=12, pady=8, cursor="hand2",
                  command=self.destroy).pack(side="right")

        self._status_lbl = tk.Label(btn_f, text="",
                                    font=(T["font"], 9),
                                    fg=T["green"], bg=T["bg"])
        self._status_lbl.pack(side="left", padx=8)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        for uname, u in self.users.items():
            role = u.get("role", "user")
            tag = role
            badge = {"admin": "[ADMIN]", "manager": "[MANAGER]", "user": "[USER]"}.get(role, role.upper())
            self.tree.insert("", "end",
                             values=(uname, u.get("name", uname), badge),
                             tags=(tag,))
        self.tree.tag_configure("admin",   foreground=T["red"])
        self.tree.tag_configure("manager", foreground=T["gold"])
        self.tree.tag_configure("user",    foreground=T["green"])

    def _on_select(self, *_):
        """Auto-fill username field when a row is selected (for quick password change)."""
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        if vals:
            self._nu.set(str(vals[0]))
            self._nn.set(str(vals[1]))
            # Find role
            uname = str(vals[0]).lower()
            if uname in self.users:
                self._nr.set(self.users[uname].get("role", "user"))
            self._np.set("")   # always clear password

    def _set_status(self, msg, color=None):
        self._status_lbl.config(text=msg, fg=color or T["green"])
        self.after(3000, lambda: self._status_lbl.config(text=""))

    # ── Actions ────────────────────────────────────────────────────────────────
    def _add(self):
        u = self._nu.get().strip().lower()
        n = self._nn.get().strip()
        p = self._np.get().strip()
        r = self._nr.get().strip()

        # Validation
        if not u:
            self._set_status("  ✗  Username is required!", T["red"]); return
        if not p:
            self._set_status("  ✗  Password is required!", T["red"]); return
        if not r:
            self._set_status("  ✗  Please select a Role!", T["red"]); return

        # Always reload from disk first to avoid overwriting other changes
        self.users = auth_load()

        is_new = u not in self.users
        action_label = "Create" if is_new else "Update"

        def _do_add():
            self.users[u] = {"password": _hp(p), "role": r, "name": n or u}
            try:
                _auth_save(self.users)
            except Exception as e:
                self._set_status(f"  ✗  Save failed: {e}", T["red"]); return
            self._refresh()
            self._nu.set("")
            self._nn.set("")
            self._np.set("")
            self._nr.set("user")
            action = "created" if is_new else "updated"
            log_action("admin", f"User {action.title()}", f"User '{u}' was {action} with role {r}.")
            self._set_status(f"  ✓  User '{u}' {action} successfully!", T["green"])
            ProToast(self, "success", f"User {action.title()}",
                     f"User '{u}' has been {action} with role [{r.upper()}].")

        show_confirm(self, f"{action_label} User?",
                     f"{action_label} user '{u}' with role [{r.upper()}]?",
                     on_yes=_do_add)

    def _del(self):
        sel = self.tree.selection()
        if not sel:
            self._set_status("  ✗  Please select a user from the list above.", T["red"])
            return

        vals = self.tree.item(sel[0])["values"]
        if not vals:
            self._set_status("  ✗  Could not read selected row.", T["red"])
            return

        u = str(vals[0]).strip().lower()

        # Always reload from disk first to avoid stale data
        self.users = auth_load()

        # Safety: cannot delete yourself
        if u == str(self.current_user.get("username", "")).strip().lower():
            self._set_status("  ✗  You cannot delete your own account.", T["red"])
            return

        # Safety: must exist in users dict
        if u not in self.users:
            self._set_status(f"  ✗  User '{u}' not found.", T["red"])
            self._refresh()
            return

        # Confirm with professional popup
        def _do_user_delete():
            try:
                del self.users[u]
                _auth_save(self.users)
                self._refresh()
                self._nu.set("")
                self._nn.set("")
                self._np.set("")
                self._nr.set("user")
                self._set_status(f"  ✓  User '{u}' deleted successfully.", T["gold"])
                log_action("admin", "User Deleted", f"User '{u}' was removed.")
                ProToast(self, "success", "User Deleted",
                         f"User '{u}' has been removed from the system.")
            except Exception as e:
                self.users = auth_load()
                self._refresh()
                self._set_status(f"  ✗  Delete failed: {e}", T["red"])

        show_confirm(self, "Delete User?",
                     f"Are you sure you want to delete user '{u}'?\nThis action cannot be undone.",
                     on_yes=_do_user_delete)

import os
from tkcalendar import DateEntry
from tkinter import filedialog
from reports import generate_schedule_pdf, generate_schedule_excel, generate_completed_pdf, generate_completed_excel, generate_new_orders_pdf, generate_new_orders_excel

class ReportManager(tk.Toplevel):
    def __init__(self, parent, orders):
        super().__init__(parent)
        self.title("📅  Generate Reports")
        self.geometry("700x720"); self.configure(bg=T["bg"]); self.resizable(False,False)
        self.orders = orders
        self.weeks = ["All"] + sorted(list(set(o.get("week") for o in self.orders if o.get("week"))))
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=T["surf"], pady=12); hdr.pack(fill="x")
        tk.Label(hdr, text="📅  REPORTS & EXPORTS", font=(T["mono"],12,"bold"), fg=T["accent"], bg=T["surf"]).pack()

        def make_section(title, desc, gen_pdf, gen_excel, prefix):
            f = tk.Frame(self, bg=T["surf2"], pady=10, padx=20); f.pack(fill="x", padx=16, pady=8)
            tk.Label(f, text=title, font=(T["font"],10,"bold"), fg=T["gold"], bg=T["surf2"]).pack(anchor="w")
            tk.Label(f, text=desc, font=(T["font"],8), fg=T["muted"], bg=T["surf2"]).pack(anchor="w", pady=(0,6))
            
            ftype = tk.StringVar(value="Week")
            tf = tk.Frame(f, bg=T["surf2"]); tf.pack(anchor="w", pady=4)
            tk.Radiobutton(tf, text="By Week", variable=ftype, value="Week", bg=T["surf2"], fg=T["text"], selectcolor=T["surf"], font=(T["font"],8), command=lambda: toggle()).pack(side="left")
            tk.Radiobutton(tf, text="By Date Range", variable=ftype, value="Date", bg=T["surf2"], fg=T["text"], selectcolor=T["surf"], font=(T["font"],8), command=lambda: toggle()).pack(side="left")
            
            input_container = tk.Frame(f, bg=T["surf2"]); input_container.pack(fill="x", pady=(0, 4))
            
            w_frame = tk.Frame(input_container, bg=T["surf2"])
            tk.Label(w_frame, text="Select Week:", font=(T["font"],9), fg=T["text"], bg=T["surf2"]).pack(side="left", padx=(0,5))
            w_var = tk.StringVar(value=self.weeks[-1] if len(self.weeks)>1 else "All")
            ttk.Combobox(w_frame, textvariable=w_var, values=self.weeks, state="readonly", width=22).pack(side="left")
            
            d_frame = tk.Frame(input_container, bg=T["surf2"])
            tk.Label(d_frame, text="From:", font=(T["font"],9), fg=T["text"], bg=T["surf2"]).pack(side="left")
            d_start = DateEntry(d_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd-M-yy'); d_start.pack(side="left", padx=5)
            tk.Label(d_frame, text="To:", font=(T["font"],9), fg=T["text"], bg=T["surf2"]).pack(side="left")
            d_end = DateEntry(d_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd-M-yy'); d_end.pack(side="left", padx=5)
            
            def toggle():
                if ftype.get() == "Week":
                    d_frame.forget(); w_frame.pack(fill="x")
                else:
                    w_frame.forget(); d_frame.pack(fill="x")
            toggle()
            
            def get_filtered():
                if ftype.get() == "Week":
                    w = w_var.get()
                    if w == "All": return self.orders, "All Weeks"
                    return [o for o in self.orders if o.get("week") == w], w
                else:
                    s_dt = d_start.get_date()
                    e_dt = d_end.get_date()
                    
                    res = []
                    for o in self.orders:
                        tod = o.get("tod","").strip()
                        if not tod: continue
                        for fmt in ["%d-%b-%y","%d-%b-%Y","%Y-%m-%d"]:
                            try:
                                dt = datetime.strptime(tod, fmt).date()
                                if s_dt <= dt <= e_dt:
                                    res.append(o)
                                break
                            except: pass
                    return res, f"{s_dt.strftime('%d-%b-%y')} to {e_dt.strftime('%d-%b-%y')}"

            def run_export(ext):
                ords, lbl = get_filtered()
                if not ords:
                    ProToast(self, "info", "No Data", "No data found for this selection."); return
                file_types = [("PDF","*.pdf")] if ext==".pdf" else [("Excel","*.xlsx")]
                safe_lbl = lbl.replace(" to ","_").replace(" ","_").replace("/","_")
                path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=file_types, initialfile=f"{prefix}_{safe_lbl}{ext}")
                if path:
                    if ext==".pdf": gen_pdf(ords, lbl, path)
                    else: gen_excel(ords, lbl, path)
                    ProToast(self, "success", "Export Complete", f"{ext[1:].upper()} generated successfully!")
                    os.startfile(path)
            
            r = tk.Frame(f, bg=T["surf2"]); r.pack(fill="x", pady=(8,0))
            tk.Button(r, text="📄 Export PDF", font=(T["font"],9,"bold"), bg="#B22222", fg="white", relief="flat", padx=12, pady=6, cursor="hand2", command=lambda: run_export(".pdf")).pack(side="left", padx=(0,10))
            tk.Button(r, text="📊 Export Excel", font=(T["font"],9,"bold"), bg="#2E8B50", fg="white", relief="flat", padx=12, pady=6, cursor="hand2", command=lambda: run_export(".xlsx")).pack(side="left")
            
        make_section("Weekly Shipping Schedule", "Generates a formatted report for 1st Cut Off and 2nd Cut Off", generate_schedule_pdf, generate_schedule_excel, "Schedule")
        make_section("Completed Shipments Summary", "Summary of all fully shipped orders (Status: Shipped)", generate_completed_pdf, generate_completed_excel, "Completed")
        make_section("New Orders Summary", "List of all received orders within the selected period", generate_new_orders_pdf, generate_new_orders_excel, "NewOrders")

# ── Update Review Dialog ──────────────────────────────────────────────────────
class ReviewUpdatesDialog(tk.Toplevel):
    """A professional Treeview-based dialog to review and approve/reject updates."""
    def __init__(self, parent, updates, on_apply):
        super().__init__(parent)
        self.title("Review Pending Updates")
        self.geometry("1100x680")
        self.configure(bg="#0A0E14")
        self.on_apply = on_apply
        
        # 1. Header (Top)
        hdr = tk.Frame(self, bg="#161B22", pady=15)
        hdr.pack(fill="x", side="top")
        tk.Label(hdr, text="📋 Review Proposed Revisions", font=("Inter", 18, "bold"),
                 bg="#161B22", fg="#FFD700").pack()
        tk.Label(hdr, text=f"The system found {len(updates)} changes. Please review carefully.",
                 font=("Inter", 10), bg="#161B22", fg="#8B949E").pack(pady=4)

        # 2. Footer (Bottom) - Pack this BEFORE the main content to guarantee visibility
        footer = tk.Frame(self, bg="#161B22", pady=15)
        footer.pack(fill="x", side="bottom")
        
        def do_apply():
            self.on_apply(); self.destroy()
            ProToast(parent, "success", "Updated", f"Successfully applied {len(updates)} revisions.")

        tk.Button(footer, text="✅ Apply All Revisions", bg="#238636", fg="white",
                  font=("Inter", 11, "bold"), padx=30, pady=10, relief="flat", cursor="hand2",
                  command=do_apply).pack(side="right", padx=20)
        tk.Button(footer, text="❌ Discard Changes", bg="#30363D", fg="#C9D1D9",
                  font=("Inter", 11), padx=25, pady=10, relief="flat", cursor="hand2",
                  command=self.destroy).pack(side="right", padx=10)

        # 3. Main Content (Middle)
        main_f = tk.Frame(self, bg="#0A0E14", padx=20, pady=10)
        main_f.pack(fill="both", expand=True)

        cols = ("Action", "Order No", "Country", "Field / Details", "Old Value", "New Value")
        self.tree = ttk.Treeview(main_f, columns=cols, show="headings", height=15)
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Review.Treeview", 
                        background="#0A0E14", 
                        foreground="#E6EDF3", 
                        fieldbackground="#0A0E14",
                        rowheight=30)
        style.configure("Review.Treeview.Heading", 
                        background="#21262D", 
                        foreground="#E6EDF3", 
                        font=("Inter", 10, "bold"))
        self.tree.configure(style="Review.Treeview")

        col_w = {"Action": 100, "Order No": 130, "Country": 120, "Field / Details": 150, "Old Value": 220, "New Value": 220}
        for c in cols:
            self.tree.heading(c, text=c, anchor="w")
            self.tree.column(c, width=col_w[c], anchor="w")

        # Scrollbar
        sb = ttk.Scrollbar(main_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Highlighting Tags
        self.tree.tag_configure("update", background="#1A1C0E", foreground="#E7FFAC")
        self.tree.tag_configure("add",    background="#0E1B1B", foreground="#ACFFFE")
        self.tree.tag_configure("remove", background="#1B0E0E", foreground="#FFACAC")

        # Populate
        for up in updates:
            action = up.get("action", "UPDATE").upper()
            v = (action, up["order_no"], up["country"], up["field"], up["old"], up["new"])
            tag = action.lower()
            self.tree.insert("", "end", values=v, tags=(tag,))

        # Finalize
        self.update_idletasks()
        self.transient(parent)
        self.grab_set()
        self.wait_window()

# ── Audit Log Viewer Dialog ───────────────────────────────────────────────────
class AuditLogViewerDialog(tk.Toplevel):
    """A professional dialog to view and search system audit logs."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📜 System Audit Logs")
        self.geometry("1100x700")
        self.configure(bg="#0A0E14")
        
        from database import get_logs
        self.all_logs = get_logs()
        
        # 1. Header (Top)
        hdr = tk.Frame(self, bg="#161B22", pady=15)
        hdr.pack(fill="x", side="top")
        tk.Label(hdr, text="📜 Audit Log Explorer", font=("Inter", 16, "bold"),
                 bg="#161B22", fg="#FFD700").pack(side="left", padx=20)
        
        # Search
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter())
        sf = tk.Frame(hdr, bg="#30363D", padx=1, pady=1)
        sf.pack(side="right", padx=20)
        se = tk.Entry(sf, textvariable=self.search_var, font=("Inter", 10),
                      bg="#0A0E14", fg="#E6EDF3", relief="flat", width=30, insertbackground="#58A6FF")
        se.pack(padx=8, pady=4)
        tk.Label(hdr, text="Search Logs:", font=("Inter", 9), bg="#161B22", fg="#8B949E").pack(side="right")

        # 2. Main Content
        main_f = tk.Frame(self, bg="#0A0E14", padx=20, pady=10)
        main_f.pack(fill="both", expand=True)
        
        cols = ("Time", "User", "Action", "Details")
        self.tree = ttk.Treeview(main_f, columns=cols, show="headings", height=18)
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Audit.Treeview", 
                        background="#0A0E14", 
                        foreground="#E6EDF3", 
                        fieldbackground="#0A0E14",
                        rowheight=28)
        style.configure("Audit.Treeview.Heading", 
                        background="#21262D", 
                        foreground="#E6EDF3", 
                        font=("Inter", 10, "bold"))
        self.tree.configure(style="Audit.Treeview")

        # Column Config
        self.tree.heading("Time", text="Timestamp")
        self.tree.column("Time", width=160, anchor="w")
        self.tree.heading("User", text="User")
        self.tree.column("User", width=120, anchor="w")
        self.tree.heading("Action", text="Action")
        self.tree.column("Action", width=160, anchor="w")
        self.tree.heading("Details", text="Description")
        self.tree.column("Details", width=580, anchor="w")

        sb = ttk.Scrollbar(main_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        
        self.tree.tag_configure("import", foreground="#58A6FF")
        self.tree.tag_configure("edit", foreground="#D29922")
        self.tree.tag_configure("delete", foreground="#F85149")
        
        self._filter()
        self.update_idletasks()
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def _filter(self):
        self.tree.delete(*self.tree.get_children())
        q = self.search_var.get().lower()
        for l in self.all_logs:
            t = str(l.get("timestamp",""))
            u = str(l.get("user",""))
            a = str(l.get("action",""))
            d = str(l.get("details",""))
            
            if q in t.lower() or q in u.lower() or q in a.lower() or q in d.lower():
                tag = ""
                if "Import" in a: tag = "import"
                elif "Edit" in a or "Update" in a: tag = "edit"
                elif "Delete" in a: tag = "delete"
                
                self.tree.insert("", "end", values=(t, u, a, d), tags=(tag,))


class VersionHistoryDialog(tk.Toplevel):
    """A premium dialog to display the system's version history and changelog."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📜 System Version History")
        self.geometry("600x740")
        self.configure(bg=T["bg"])
        self.resizable(False, True)
        self.transient(parent)
        self.grab_set()
        
        self.changelog = self._load_changelog()
        self._build()
        
    def _load_changelog(self):
        try:
            with open(CHANGELOG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _build(self):
        # Header with Version Info
        hdr = tk.Frame(self, bg=T["surf"], pady=24)
        hdr.pack(fill="x")
        
        from config import VERSION
        tk.Label(hdr, text="🧵 GARMENT TRACKER", font=(T["mono"], 10, "bold"),
                 fg=T["accent"], bg=T["surf"]).pack()
        tk.Label(hdr, text=f"v{VERSION} — CHANGELOG", font=(T["font"], 16, "bold"),
                 fg=T["text"], bg=T["surf"]).pack(pady=5)
        tk.Label(hdr, text="Official Release Notes & System Updates", font=(T["font"], 9),
                 fg=T["muted"], bg=T["surf"]).pack()

        # Content Area
        container = tk.Frame(self, bg=T["bg"], padx=20, pady=10)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg=T["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        self.scroll_frame = tk.Frame(canvas, bg=T["bg"])
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=540)
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        add_mouse_wheel(self.scroll_frame, canvas)

        # Render Versions
        for entry in self.changelog:
            self._render_version_card(entry)

        # Footer
        footer = tk.Frame(self, bg=T["surf"], pady=14)
        footer.pack(fill="x", side="bottom")
        btn = tk.Button(footer, text="   CLOSE   ", font=(T["font"], 10, "bold"),
                  bg=T["accent"], fg="white", relief="flat", padx=40, pady=10,
                  cursor="hand2", command=self.destroy)
        btn.pack()
        bind_hover(btn, T["accent"], T["accent2"], "white", "white")

    def _render_version_card(self, entry):
        card = tk.Frame(self.scroll_frame, bg=T["surf2"], padx=20, pady=20)
        card.pack(fill="x", pady=10)
        
        # Version Badge
        v_f = tk.Frame(card, bg=T["accent3"], padx=10, pady=3)
        v_f.pack(side="top", anchor="w")
        tk.Label(v_f, text=f"v{entry['version']}", font=(T["mono"], 9, "bold"),
                 fg="white", bg=T["accent3"]).pack()
        
        # Title & Date
        title_f = tk.Frame(card, bg=T["surf2"])
        title_f.pack(fill="x", pady=(10, 2))
        tk.Label(title_f, text=entry.get("title", "System Update"), font=(T["font"], 13, "bold"),
                 fg=T["gold"], bg=T["surf2"]).pack(side="left")
        tk.Label(card, text=f"Released: {entry.get('date', 'Unknown Date')}", font=(T["mono"], 8),
                 fg=T["muted"], bg=T["surf2"]).pack(anchor="w")
        
        # Divider
        tk.Frame(card, bg=T["border"], height=1).pack(fill="x", pady=14)
        
        # Changes
        for change in entry.get("changes", []):
            cf = tk.Frame(card, bg=T["surf2"])
            cf.pack(fill="x", pady=3)
            tk.Label(cf, text="●", font=(T["font"], 8),
                     fg=T["accent"], bg=T["surf2"]).pack(side="left", anchor="n", pady=3)
            tk.Label(cf, text=change, font=(T["font"], 10),
                     fg=T["text"], bg=T["surf2"], wraplength=440,
                     justify="left").pack(side="left", padx=10, anchor="w")


class UpdateReviewDialog(tk.Toplevel):
    """A professional dialog to review changes before applying a system update."""
    def __init__(self, parent, local_v, remote_v, remote_changelog, on_update):
        super().__init__(parent)
        self.title("🚀 System Update Available")
        self.geometry("640x800")
        self.configure(bg=T["bg"])
        self.resizable(False, True)
        self.transient(parent)
        self.grab_set()
        
        self.local_v = local_v
        self.remote_v = remote_v
        self.remote_changelog = remote_changelog
        self.on_update = on_update
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=T["surf"], pady=24)
        hdr.pack(fill="x")
        
        tk.Label(hdr, text="🧵 GARMENT TRACKER", font=(T["mono"], 10, "bold"),
                 fg=T["accent"], bg=T["surf"]).pack()
        tk.Label(hdr, text="NEW VERSION READY", font=(T["font"], 18, "bold"),
                 fg=T["text"], bg=T["surf"]).pack(pady=5)
        
        # Version Comparison Badge
        v_f = tk.Frame(hdr, bg=T["bg"], padx=16, pady=8)
        v_f.pack(pady=10)
        tk.Label(v_f, text=f"v{self.local_v}", font=(T["mono"], 10),
                 fg=T["muted"], bg=T["bg"]).pack(side="left")
        tk.Label(v_f, text="  →  ", font=(T["mono"], 12, "bold"),
                 fg=T["accent"], bg=T["bg"]).pack(side="left")
        tk.Label(v_f, text=f"v{self.remote_v}", font=(T["mono"], 12, "bold"),
                 fg=T["green"], bg=T["bg"]).pack(side="left")

        # Scrollable Content
        container = tk.Frame(self, bg=T["bg"], padx=20, pady=10)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg=T["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        self.scroll_frame = tk.Frame(canvas, bg=T["bg"])
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=580)
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        add_mouse_wheel(self.scroll_frame, canvas)

        tk.Label(self.scroll_frame, text="RELEASE NOTES:", font=(T["font"], 9, "bold"),
                 fg=T["gold"], bg=T["bg"]).pack(anchor="w", pady=(10, 5))

        # Render relevant remote changelog entries
        # (Assuming they are sorted newest to oldest)
        for entry in self.remote_changelog:
            if entry["version"] == self.local_v: break # Stop when we reach current version
            self._render_version_card(entry)

        # Bottom Actions
        footer = tk.Frame(self, bg=T["surf"], pady=18, padx=24)
        footer.pack(fill="x", side="bottom")
        
        tk.Button(footer, text="   Later   ", font=(T["font"], 10),
                  bg=T["surf3"], fg=T["muted"], relief="flat", padx=20, pady=10,
                  cursor="hand2", command=self.destroy).pack(side="left")
        
        upd_btn = tk.Button(footer, text="   🚀 UPDATE SYSTEM NOW   ", font=(T["font"], 10, "bold"),
                  bg=T["green"], fg="white", relief="flat", padx=30, pady=10,
                  cursor="hand2", command=self._confirm_update)
        upd_btn.pack(side="right")
        bind_hover(upd_btn, T["green"], T["green2"], "white", "white")

    def _render_version_card(self, entry):
        card = tk.Frame(self.scroll_frame, bg=T["surf2"], padx=20, pady=20)
        card.pack(fill="x", pady=8)
        
        tk.Label(card, text=f"v{entry['version']} — {entry.get('title','')}", 
                 font=(T["font"], 11, "bold"), fg=T["text"], bg=T["surf2"]).pack(anchor="w")
        tk.Label(card, text=entry.get('date',''), font=(T["mono"], 8),
                 fg=T["muted"], bg=T["surf2"]).pack(anchor="w", pady=(2, 8))
        
        for change in entry.get("changes", []):
            cf = tk.Frame(card, bg=T["surf2"])
            cf.pack(fill="x", pady=2)
            tk.Label(cf, text="•", font=(T["font"], 8), fg=T["accent"], bg=T["surf2"]).pack(side="left", anchor="n", pady=2)
            tk.Label(cf, text=change, font=(T["font"], 9), fg=T["text"], bg=T["surf2"], 
                     wraplength=480, justify="left").pack(side="left", padx=8, anchor="w")

    def _confirm_update(self):
        self.destroy()
        if self.on_update: self.on_update()
