import os
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from config import T, COLUMNS, COL_KEYS, STATUS_OPTIONS, COUNTRY_CUTOFF, DEFAULT_COUNTRY_CUTOFF, can, bind_hover, SHIPPED_DONE, VERSION
from database import (db_load, db_save, auth_load, auth_verify,
                       load_remembered, save_remembered, clear_remembered,
                       backup_on_close, backup_manual, stop_scheduled_backup,
                       get_backup_info, BACKUP_DIR, log_action)
from logic import calculate_row, auto_first_last
from pdf_handler import extract_hm_records
from export import export_excel
from dashboard import DashboardFrame
from dialogs import RowEditor, BulkEditor, CutoffManager, UserManager, ReportManager, FactoryMerchantManager, AdvancedSearchDialog, ProToast, show_confirm, ReviewUpdatesDialog, AuditLogViewerDialog, VersionHistoryDialog, UpdateReviewDialog
from settings import SettingsDialog, load_settings
from updater import check_for_updates, perform_git_update


def apply_global_style():
    """Apply premium navy dark theme — MUST be called before building any widget."""
    s = ttk.Style()
    s.theme_use("clam")
    s.configure(".",
                background=T["surf2"], foreground=T["text"],
                troughcolor=T["bg"], bordercolor=T["border"],
                darkcolor=T["surf"], lightcolor=T["surf3"],
                focuscolor=T["accent"])
    s.configure("TFrame",       background=T["bg"])
    s.configure("TLabel",       background=T["bg"], foreground=T["text"])
    s.configure("TButton",      background=T["surf3"], foreground=T["text"],
                relief="flat", borderwidth=0, padding=4)
    s.configure("TEntry",       background=T["surf3"], foreground=T["text"],
                fieldbackground=T["surf3"], insertcolor=T["accent"])
    s.configure("TCheckbutton", background=T["bg"], foreground=T["text"])
    s.configure("TCombobox",
                fieldbackground=T["surf3"], background=T["surf3"],
                foreground=T["text"], arrowcolor=T["muted"],
                selectbackground=T["surf3"], selectforeground=T["text"])
    s.map("TCombobox",
          fieldbackground=[("readonly", T["surf3"])],
          selectbackground=[("readonly", T["surf3"])],
          selectforeground=[("readonly", T["text"])],
          foreground=[("readonly", T["text"])])
    s.configure("TScrollbar",
                background=T["surf3"], troughcolor=T["bg"],
                arrowcolor=T["border"], bordercolor=T["border"], width=10)
    s.map("TScrollbar",
          background=[("active", T["accent"]), ("!active", T["surf4"])])
    # Main Treeview
    s.configure("Main.Treeview",
                background=T["surf2"], foreground=T["text"],
                fieldbackground=T["surf2"], rowheight=30,
                font=(T["font"], 10))
    s.configure("Main.Treeview.Heading",
                background=T["surf3"], foreground=T["muted"],
                font=(T["font"], 10, "bold"), relief="flat", borderwidth=0)
    s.map("Main.Treeview",
          background=[("selected", T["accent3"])],
          foreground=[("selected", "white")])
    s.map("Main.Treeview.Heading",
          background=[("active", T["surf4"])])


def _mk_btn(parent, text, bg, fg, cmd, hover_bg=None, font_size=10, padx=14, pady=6):
    """Reusable modern flat button with hover."""
    hbg = hover_bg or bg
    b = tk.Button(parent, text=text, font=(T["font"], font_size, "bold"),
                  bg=bg, fg=fg, relief="flat", bd=0,
                  padx=padx, pady=pady, cursor="hand2",
                  activebackground=hbg, activeforeground=fg, command=cmd)
    bind_hover(b, bg, hbg, fg, fg)
    return b


def show_confirm(parent, title, message, on_yes, on_no=None):
    """Shortcut for confirmation dialogs with Yes/No buttons."""
    ProToast(parent, "confirm", title, message, on_yes=on_yes, on_no=on_no)


def styled_entry(parent, textvariable, width=22, show=""):
    """A bordered entry widget with dark background."""
    f = tk.Frame(parent, bg=T["border"], padx=1, pady=1)
    e = tk.Entry(f, textvariable=textvariable, show=show,
                 font=(T["font"], 10), bg=T["surf3"], fg=T["text"],
                 relief="flat", bd=0, insertbackground=T["accent"],
                 width=width, highlightthickness=0)
    e.pack(padx=8, pady=6)
    e.bind("<FocusIn>",  lambda ev, fr=f: fr.config(bg=T["accent"]))
    e.bind("<FocusOut>", lambda ev, fr=f: fr.config(bg=T["border"]))
    return f, e


# ─────────────────────────────────────────────────────────────────────────────
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Garment Tracker  —  Sign In")
        self.geometry("460x540")
        self.resizable(False, False)
        self.configure(bg=T["bg"])
        apply_global_style()
        self.users = auth_load()
        self.settings = load_settings()
        self.logged_in = None
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        ru, rp = load_remembered()
        if ru and rp:
            self._uv.set(ru); self._pv.set(rp); self.remember_var.set(True)

    def _build(self):
        # Top accent gradient bar
        top = tk.Frame(self, bg=T["accent"], height=5)
        top.pack(fill="x")

        # Header
        hdr = tk.Frame(self, bg=T["bg"], pady=30)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🧵  GARMENT TRACKER",
                 font=(T["mono"], 18, "bold"), fg=T["text"], bg=T["bg"]).pack()
        tk.Label(hdr, text="Tasniah Fabrics Ltd  ·  Masco Group",
                 font=(T["font"], 9), fg=T["muted"], bg=T["bg"]).pack(pady=(4, 0))

        # Thin divider
        tk.Frame(self, bg=T["border"], height=1).pack(fill="x", padx=30)

        # Card - Modern 'Glass' look
        card = tk.Frame(self, bg=T["surf"], padx=40, pady=32)
        card.pack(fill="x", padx=30, pady=28)

        self._uv = tk.StringVar()
        self._pv = tk.StringVar()
        for lbl, var, show in [("USERNAME", self._uv, ""), ("PASSWORD", self._pv, "•")]:
            tk.Label(card, text=lbl, font=(T["font"], 9, "bold"),
                     fg=T["accent"], bg=T["surf"], anchor="w").pack(fill="x", pady=(12, 4))
            fr, ent = styled_entry(card, var, width=28, show=show if show != "•" else "*")
            fr.pack(fill="x")
            if show != "":
                ent.bind("<Return>", lambda _: self._login())

        self.remember_var = tk.BooleanVar(value=False)
        tk.Checkbutton(card, text="  Remember me", variable=self.remember_var,
                       font=(T["font"], 9), fg=T["muted"], bg=T["surf"],
                       activebackground=T["surf"], activeforeground=T["text"],
                       selectcolor=T["surf2"], relief="flat").pack(anchor="w", pady=(14, 0))

        self._err = tk.StringVar()
        tk.Label(self, textvariable=self._err, font=(T["font"], 9),
                 fg=T["red"], bg=T["bg"]).pack(pady=(0, 4))

        # Login button — full width accent
        btn_f = tk.Frame(self, bg=T["bg"])
        btn_f.pack(fill="x", padx=30)
        btn = tk.Button(btn_f, text="SIGN IN  →",
                        font=(T["font"], 12, "bold"),
                        bg=T["accent"], fg="white", relief="flat", bd=0,
                        pady=12, cursor="hand2",
                        activebackground=T["accent2"], activeforeground="white",
                        command=self._login)
        btn.pack(fill="x")
        bind_hover(btn, T["accent"], T["accent2"], "white", "white")

        if self.settings.get("show_default_creds", True):
            tk.Label(self, text="Default credentials:  admin / admin123",
                     font=(T["font"], 8), fg=T["dim"], bg=T["bg"]).pack(pady=(12, 0))

    def _login(self):
        u = self._uv.get().strip(); p = self._pv.get().strip()
        r = auth_verify(u, p, self.users)
        if r:
            if self.remember_var.get(): save_remembered(u, p)
            else: clear_remembered()
            
            # Hide default creds for future runs
            if self.settings.get("show_default_creds"):
                from settings import save_settings
                self.settings["show_default_creds"] = False
                save_settings(self.settings)
                
            self.logged_in = {"username": u, **r}; self.destroy()
        else:
            self._err.set("⚠  Invalid username or password")


# ─────────────────────────────────────────────────────────────────────────────
class MainApp(tk.Tk):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.title("Garment Order Tracking System — Tasniah Fabrics Ltd")
        self.geometry("1480x840"); self.minsize(1100, 640)
        self.configure(bg=T["bg"])
        apply_global_style()          # ← FIRST, before any widget
        self.db = db_load()
        raw_orders = self.db.get("orders", [])
        self._orders = auto_first_last(raw_orders)
        self._recent_changes = {} # {(order_no, country, colour, style, key): timestamp}
        saved_co = self.db.get("country_cutoff", {})
        if saved_co: COUNTRY_CUTOFF.clear(); COUNTRY_CUTOFF.update(saved_co)
        else: self.db["country_cutoff"] = dict(DEFAULT_COUNTRY_CUTOFF)
        self._sel_all = tk.BooleanVar(value=False)
        self.adv_filters  = {}
        self.app_settings = load_settings()   # company name, export dir, logo
        self._build()
        self._show_dashboard()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Version Check
        last_v = self.app_settings.get("last_version", "1.0.0")
        if last_v != VERSION:
            self.after(2000, self._show_version_history)
            from settings import save_settings
            self.app_settings["last_version"] = VERSION
            save_settings(self.app_settings)

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        # Top accent bar
        tk.Frame(self, bg=T["accent"], height=3).pack(fill="x")
        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=T["surf"], height=58)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        lf = tk.Frame(hdr, bg=T["surf"]); lf.pack(side="left", padx=18, fill="y")
        tk.Label(lf, text="\U0001f9f5  GARMENT TRACKER",
                 font=(T["mono"], 14, "bold"), fg=T["text"], bg=T["surf"]).pack(side="left", pady=18)
        tk.Label(lf, text="  \u00b7  Tasniah Fabrics Ltd",
                 font=(T["font"], 8), fg=T["muted"], bg=T["surf"]).pack(side="left")
        
        # Version Link
        v_btn = tk.Button(lf, text=f"v{VERSION}", font=(T["mono"], 8, "bold"),
                          fg=T["accent"], bg=T["surf"], relief="flat", bd=0,
                          cursor="hand2", command=self._show_version_history)
        v_btn.pack(side="left", padx=12)
        bind_hover(v_btn, T["surf"], T["surf2"], T["accent"], "white")
        # Right: user badge chip
        role = self.current_user["role"]
        ri_col = {"admin": T["red"], "manager": T["gold"], "user": T["green"]}.get(role, T["muted"])
        badge_f = tk.Frame(hdr, bg=T["surf3"], padx=20)
        badge_f.pack(side="right", padx=18, fill="y")
        tk.Label(badge_f, text="\u25cf", font=(T["font"], 14), fg=ri_col, bg=T["surf3"]).pack(side="left", padx=(0, 10), pady=18)
        tk.Label(badge_f, text=f"{self.current_user['name']}",
                 font=(T["font"], 10, "bold"), fg=T["text"], bg=T["surf3"]).pack(side="left")
        tk.Label(badge_f, text=f"  [{role.upper()}]",
                 font=(T["font"], 9), fg=T["muted"], bg=T["surf3"]).pack(side="left")

        # ── Nav bar ───────────────────────────────────────────────────────────
        nav_f = tk.Frame(self, bg=T["surf"], height=42)
        nav_f.pack(fill="x"); nav_f.pack_propagate(False)
        tk.Frame(nav_f, bg=T["accent"], width=4).pack(side="left", fill="y")
        nav_items = [
            ("Dashboard",    "\U0001f4ca", self._show_dashboard,      None),
            ("Order List",   "\U0001f4cb", self._show_orders,         None),
            ("Import PDF",   "\u2b07",     self._import_pdf,          "import_pdf"),
            ("Import Excel", "\u2b07",     self._import_excel,        "import_pdf"),
            ("Template",     "\u229e",     self._download_template,   "import_pdf"),
            ("Cut Off",      "\u29bf",     self._open_cutoff_mgr,     "manage_cutoff"),
            ("Fact/Merch",   "\u229e",     self._open_fact_merch,     "manage_cutoff"),
            ("Reports",      "\u22a1",     self._open_reports,        "export"),
            ("Backup",       "\U0001f4be", self._open_backup_manager, None),
            ("Settings",     "\u2699",     self._open_settings,       "manage_users"),
            ("Users",        "\u2295",     self._open_users,          "manage_users"),
            ("Logout",       "\u2297",     self._logout,              None),
        ]
        self._nav_buttons = {}
        for label, icon, cmd, perm in nav_items:
            if perm and not can(self.current_user, perm): continue
            is_logout = (label == "Logout")
            nbg    = T["surf"]
            nfg    = T["red"]    if is_logout else T["muted"]
            nhov   = T["red_bg"] if is_logout else T["nav_hover"]
            nfghov = T["red"]    if is_logout else T["text"]
            b = tk.Button(nav_f, text=f"  {icon}  {label}  ",
                          font=(T["font"], 9, "bold"),
                          bg=nbg, fg=nfg, relief="flat", bd=0,
                          padx=4, pady=0, cursor="hand2",
                          activebackground=nhov, activeforeground=nfghov,
                          command=cmd)
            b.pack(side="left", fill="y")
            bind_hover(b, nbg, nhov, nfg, nfghov)
            self._nav_buttons[label] = b

        tk.Frame(self, bg=T["border"], height=1).pack(fill="x")
        # ── Content area ─────────────────────────────────────────────────────
        self.main_container = tk.Frame(self, bg=T["bg"])
        self.main_container.pack(fill="both", expand=True)
        self.dashboard_view = DashboardFrame(
            self.main_container, self._orders, on_close=self._show_orders)
        self.orders_view = tk.Frame(self.main_container, bg=T["bg"])
        self._build_orders_view(self.orders_view)

    def _set_active_nav(self, label):
        for lbl, btn in self._nav_buttons.items():
            is_logout = (lbl == "Logout")
            if lbl == label:
                btn.config(bg=T["accent3"], fg="white")
                btn.unbind("<Enter>"); btn.unbind("<Leave>")
            else:
                nbg = T["surf"]
                nfg = T["red"] if is_logout else T["muted"]
                nhov = T["red_bg"] if is_logout else T["nav_hover"]
                nfghov = T["red"] if is_logout else T["text"]
                btn.config(bg=nbg, fg=nfg)
                bind_hover(btn, nbg, nhov, nfg, nfghov)

    def _show_dashboard(self):
        self._set_active_nav("Dashboard")
        self.orders_view.pack_forget()
        self.dashboard_view.update_data(self._orders)
        self.dashboard_view.pack(fill="both", expand=True)

    def _show_orders(self):
        self._set_active_nav("Order List")
        self.dashboard_view.pack_forget()
        self.orders_view.pack(fill="both", expand=True)
        self._refresh_table()

    # ── Orders view ───────────────────────────────────────────────────────────
    def _build_orders_view(self, parent):
        # Toolbar
        tb = tk.Frame(parent, bg=T["surf"], pady=6)
        tb.pack(fill="x", padx=0, pady=0)
        tk.Frame(parent, bg=T["border"], height=1).pack(fill="x")

        b_add = _mk_btn(tb, "\uff0b  Add Row", T["green"], "white", self._add_row, T["green2"])
        b_add.pack(side="left", padx=(8, 4))

        tk.Checkbutton(tb, text=" Select All", variable=self._sel_all,
                       font=(T["font"], 9), fg=T["text"], bg=T["surf"],
                       activebackground=T["surf"], selectcolor=T["surf2"],
                       relief="flat", command=self._toggle_all).pack(side="left", padx=(2, 6))

        tk.Frame(tb, bg=T["border"], width=1).pack(side="left", fill="y", pady=6)

        # Search box
        tk.Label(tb, text="\U0001f50d", font=(T["font"], 10),
                 fg=T["muted"], bg=T["surf"]).pack(side="left", padx=(10, 2))
        self._sv = tk.StringVar()
        self._sv.trace_add("write", lambda *_: self._apply_filter())
        sf = tk.Frame(tb, bg=T["border"], padx=1, pady=1)
        sf.pack(side="left", padx=4)
        se = tk.Entry(sf, textvariable=self._sv,
                      font=(T["mono"], 9), bg=T["surf3"], fg=T["text"],
                      relief="flat", bd=0, insertbackground=T["accent"], width=24)
        se.pack(padx=8, pady=4)
        se.bind("<FocusIn>",  lambda e, f=sf: f.config(bg=T["accent"]))
        se.bind("<FocusOut>", lambda e, f=sf: f.config(bg=T["border"]))

        self._adv_btn = _mk_btn(tb, "\u2699  Adv Filter", T["surf3"], T["gold"],
                          self._open_adv_search, T["surf4"], pady=5)
        self._adv_btn.pack(side="left", padx=(2, 10))

        tk.Frame(tb, bg=T["border"], width=1).pack(side="left", fill="y", pady=6)

        tk.Label(tb, text="Status", font=(T["font"], 8),
                 fg=T["muted"], bg=T["surf"]).pack(side="left", padx=(8, 3))
        self._stf = tk.StringVar(value="All")
        ttk.Combobox(tb, textvariable=self._stf,
                     values=["All"] + STATUS_OPTIONS[1:],
                     state="readonly", width=13,
                     font=(T["font"], 9)).pack(side="left", padx=3)
        self._stf.trace_add("write", lambda *_: self._apply_filter())

        tk.Label(tb, text="Country", font=(T["font"], 8),
                 fg=T["muted"], bg=T["surf"]).pack(side="left", padx=(8, 3))
        self._ctf = tk.StringVar(value="All")
        self._ct_cb = ttk.Combobox(tb, textvariable=self._ctf,
                                   values=["All"] + sorted(COUNTRY_CUTOFF.keys()),
                                   state="readonly", width=7,
                                   font=(T["font"], 9))
        self._ct_cb.pack(side="left", padx=3)
        self._ctf.trace_add("write", lambda *_: self._apply_filter())

        # Right-side action buttons
        self._cnt_lbl = tk.Label(tb, text="", font=(T["mono"], 8, "bold"),
                                  fg=T["blue"], bg=T["surf"])
        self._cnt_lbl.pack(side="right", padx=(4, 14))
        for txt, cmd, bg_, hov_, fgc in [
            ("\u2715  Delete",    self._delete_sel, T["red_bg"],  T["red"],  T["red"]),
            ("\u270e  Bulk Edit", self._bulk_edit,  T["blue_bg"], T["blue"], T["blue"]),
            ("\u270e  Edit",      self._edit_row,   T["blue_bg"], T["blue"], T["blue"]),
        ]:
            b = tk.Button(tb, text=txt, font=(T["font"], 8, "bold"),
                          bg=bg_, fg=fgc, relief="flat", padx=10, pady=5,
                          cursor="hand2", command=cmd,
                          activebackground=hov_, activeforeground="white")
            b.pack(side="right", padx=2)
            bind_hover(b, bg_, hov_, fgc, "white")

        # Selection info bar
        sb2 = tk.Frame(parent, bg=T["surf3"], height=24)
        sb2.pack(fill="x", padx=6); sb2.pack_propagate(False)
        self._sel_lbl = tk.Label(sb2, text="", font=(T["font"], 8),
                                  fg=T["accent"], bg=T["surf3"])
        self._sel_lbl.pack(side="left", padx=12, pady=4)

        # Table
        tf = tk.Frame(parent, bg=T["bg"])
        tf.pack(fill="both", expand=True, padx=6, pady=(2, 0))
        self.tree = ttk.Treeview(tf, columns=COL_KEYS, show="headings",
                                  style="Main.Treeview", selectmode="extended")
        for col in COLUMNS:
            self.tree.heading(col["key"], text=col["label"],
                              command=lambda k=col["key"]: self._sort(k))
            self.tree.column(col["key"], width=col["width"], minwidth=50,
                             anchor="center" if col["type"] in
                             ("calc", "pdf_auto", "auto_co", "auto_fl") else "w")
        ys = ttk.Scrollbar(tf, orient="vertical",   command=self.tree.yview)
        xs = ttk.Scrollbar(tf, orient="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        xs.pack(side="bottom", fill="x"); ys.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _: self._edit_row())
        self.tree.bind("<<TreeviewSelect>>", self._on_sel)

        # Mousewheel support
        def _on_mousewheel(event):
            self.tree.yview_scroll(int(-1*(event.delta/120)), "units")
        self.tree.bind("<MouseWheel>", _on_mousewheel)

        # Status tags — navy palette
        # Status tags — robust visibility
        self.tree.tag_configure("shipped",   background="#1B4D2E", foreground="#A5F3BC") # Light Green Tint
        self.tree.tag_configure("pending",   background="#1A1200", foreground="#F59E0B")
        self.tree.tag_configure("first",     background="#0A1530", foreground="#60A5FA")
        self.tree.tag_configure("last",      background="#160A24", foreground="#C084FC")
        self.tree.tag_configure("cancelled", background="#4D1B1B", foreground="#F3A5A5") # Light Red Tint
        self.tree.tag_configure("overdue",   background="#330000", foreground="#FF9999") # Darker Red for Overdue
        self.tree.tag_configure("air_row",   background="#280A00", foreground="#FB923C")
        self.tree.tag_configure("recently_updated", background="#21262D", foreground="#FFD700")

        # Status bar
        sbar = tk.Frame(parent, bg=T["surf"], height=28)
        sbar.pack(fill="x"); sbar.pack_propagate(False)
        tk.Frame(sbar, bg=T["accent"], width=3).pack(side="left", fill="y")
        self._stv = tk.StringVar(value="Ready")
        tk.Label(sbar, textvariable=self._stv,
                 font=(T["mono"], 8), fg=T["muted"],
                 bg=T["surf"]).pack(side="left", padx=12, pady=5)
        tk.Label(sbar, text="TASNIAH FABRICS LTD  \u00b7  MASCO GROUP",
                 font=(T["font"], 7), fg=T["dim"],
                 bg=T["surf"]).pack(side="right", padx=12)
        self._sort_col = None; self._sort_asc = True
        
        # Load settings & alerts
        self.after(1000, self._check_shipment_alerts)

    def _check_shipment_alerts(self):
        """Proactively notify admin about upcoming and OVERDUE shipments."""
        reminder_days = self.app_settings.get("reminder_days", 7)
        now = datetime.now()
        upcoming = []
        overdue = []
        
        for o in self._orders:
            if o.get("shipped_status") in (SHIPPED_DONE, "Cancelled"): continue
            tod_str = o.get("tod", "")
            if not tod_str: continue
            
            dt = None
            for fmt in ["%d-%b-%y","%d-%b-%Y","%Y-%m-%d"]:
                try: dt = datetime.strptime(tod_str, fmt); break
                except: pass
            
            if dt:
                diff = (dt - now).days
                if diff < 0:
                    overdue.append(f"• {o.get('order_no')} ({o.get('country')}) — Delayed by {abs(diff)} days")
                elif 0 <= diff <= reminder_days:
                    upcoming.append(f"• {o.get('order_no')} ({o.get('country')}) — Due in {diff} days")
        
        if overdue or upcoming:
            title = f"🔔 {len(overdue) + len(upcoming)} Shipment Alerts"
            msg = ""
            if overdue:
                msg += f"⚠️ OVERDUE SHIPMENTS ({len(overdue)}):\n"
                msg += "\n".join(overdue[:5])
                if len(overdue) > 5: msg += f"\n... and {len(overdue)-5} more."
                msg += "\n\n"
            
            if upcoming:
                msg += f"📅 UPCOMING (Next {reminder_days} days):\n"
                msg += "\n".join(upcoming[:5])
                if len(upcoming) > 5: msg += f"\n... and {len(upcoming)-5} more."
            
            # Show professional alert
            ProToast(self, "warning", title, msg)

    # ── Table helpers ─────────────────────────────────────────────────────────
    def _on_sel(self, *_):
        n = len(self.tree.selection())
        self._sel_lbl.config(text="" if n == 0 else
            "1 row selected" if n == 1 else
            f"{n} rows selected  ·  Bulk Edit or Delete")

    def _toggle_all(self):
        if self._sel_all.get(): self.tree.selection_set(self.tree.get_children())
        else: self.tree.selection_remove(self.tree.get_children())
        self._on_sel()

    def _get_sel(self):
        out = []
        for item in self.tree.selection():
            vals = self.tree.item(item)["values"]
            out.append((item, {k: (str(v) if v else "") for k, v in zip(COL_KEYS, vals)}))
        return out

    def _find_idx(self, row):
        return next((i for i, o in enumerate(self._orders)
                     if o.get("order_no") == row.get("order_no")
                     and o.get("country") == row.get("country")
                     and o.get("colour")  == row.get("colour")
                     and o.get("style_name") == row.get("style_name")), None)

    def _refresh_table(self, orders=None):
        if orders is None: orders = self._orders
        self.tree.delete(*self.tree.get_children())
        import time
        from datetime import datetime
        now_ts = time.time()
        now_dt = datetime.now()
        for o in orders:
            vals = []; is_air = False; is_recent = False; is_overdue = False
            for k in COL_KEYS:
                v = o.get(k, "")
                # Visual Highlight Logic
                ck = (o.get("order_no"), o.get("country"), o.get("colour"), o.get("style_name"), k)
                if ck in self._recent_changes:
                    if now_ts - self._recent_changes[ck] < 600: # 10 mins
                        is_recent = True
                    else:
                        try: del self._recent_changes[ck]
                        except: pass

                if k == "ship_mode" and str(v).strip().upper() == "AIR":
                    v = "✈ AIR"; is_air = True
                elif k == "ship_mode" and str(v).strip().upper() == "SEA":
                    v = "⛴ SEA"
                elif k == "short_excess" and str(v).strip():
                    try:
                        num = int(str(v).replace(",", ""))
                        if num < 0: v = f"▼ {v}"
                        elif num > 0: v = f"▲ +{v}" if not str(v).startswith("+") else f"▲ {v}"
                    except: pass
                vals.append(v)
            
            # Delay Alert Highlighting
            st = o.get("shipped_status", "")
            if st not in (SHIPPED_DONE, "Cancelled"):
                tod_str = o.get("tod", "")
                if tod_str:
                    for fmt in ["%d-%b-%y","%d-%b-%Y","%Y-%m-%d"]:
                        try:
                            dt = datetime.strptime(tod_str, fmt)
                            if dt < now_dt: is_overdue = True
                            break
                        except: pass

            # Apply Multiple Tags
            tags = []
            tag = {"Shipped": "shipped", "Pending": "pending",
                   "1st Shipment": "first", "Last Shipment": "last",
                   "Cancelled": "cancelled"}.get(st, "")
            if tag: tags.append(tag)
            if is_overdue: tags.append("overdue")
            if is_air: tags.append("air_row")
            if is_recent: tags.append("recently_updated")
            
            self.tree.insert("", "end", values=vals, tags=tuple(tags))
        tot = len(self._orders); shown = len(orders)
        self._cnt_lbl.config(text=f"{shown} / {tot} rows")
        self._stv.set(f"Total: {tot} records  |  Shown: {shown}")
        self._sel_all.set(False)

    def _apply_filter(self):
        q   = self._sv.get().strip().lower()
        sf  = self._stf.get()
        cf  = self._ctf.get()
        f   = self._orders

        # Quick status dropdown
        if sf and sf != "All":
            f = [o for o in f if o.get("shipped_status", "") == sf]

        # Quick country dropdown
        if cf and cf != "All":
            f = [o for o in f if o.get("country", "").upper() == cf]

        # Advanced: multi-select status
        adv_statuses = self.adv_filters.get("statuses") or []
        if adv_statuses:
            f = [o for o in f if o.get("shipped_status", "Pending") in adv_statuses]

        # Advanced: colour
        adv_c = self.adv_filters.get("colour")
        if adv_c: f = [o for o in f if o.get("colour", "") == adv_c]

        # Advanced: season
        adv_s = self.adv_filters.get("season")
        if adv_s: f = [o for o in f if o.get("season", "") == adv_s]

        # Advanced: country (from adv panel, overrides quick-select)
        adv_ct = self.adv_filters.get("country")
        if adv_ct: f = [o for o in f if o.get("country", "").upper() == adv_ct.upper()]

        # Advanced: date range (ToD)
        if self.adv_filters.get("use_date"):
            from datetime import datetime
            s_dt = self.adv_filters["start_date"]
            e_dt = self.adv_filters["end_date"]
            res  = []
            for o in f:
                tod = o.get("tod", "").strip()
                if not tod: continue
                for fmt in ["%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d"]:
                    try:
                        dt = datetime.strptime(tod, fmt).date()
                        if s_dt <= dt <= e_dt: res.append(o)
                        break
                    except: pass
            f = res

        # Text search (all columns)
        if q:
            f = [o for o in f if any(q in str(v).lower() for v in o.values())]

        self._refresh_table(f)

    def _open_adv_search(self):
        colors    = set(o.get("colour",  "") for o in self._orders if o.get("colour"))
        seasons   = set(o.get("season",  "") for o in self._orders if o.get("season"))
        countries = set(o.get("country", "") for o in self._orders if o.get("country"))
        def on_apply(filters):
            self.adv_filters = filters
            # Update Adv Filter button to show active count
            n = sum([
                bool(filters.get("statuses")),
                bool(filters.get("colour")),
                bool(filters.get("season")),
                bool(filters.get("country")),
                bool(filters.get("use_date")),
            ])
            self._adv_btn.config(
                text=(f"\u2699  Adv Filter  [●{n}]" if n else "\u2699  Adv Filter"),
                fg=T["red"] if n else T["gold"]
            )
            self._apply_filter()
        AdvancedSearchDialog(self, colors, seasons, countries, self.adv_filters, on_apply)

    def _sort(self, col):
        self._sort_asc = not self._sort_asc if self._sort_col == col else True
        self._sort_col = col
        self._orders.sort(key=lambda o: str(o.get(col, "")), reverse=not self._sort_asc)
        self._apply_filter()

    # ── Import/Export ─────────────────────────────────────────────────────────
    def _import_pdf(self):
        bd = filedialog.askopenfilename(title="Country Breakdown PDF", filetypes=[("PDF", "*.pdf")])
        if not bd: return
        po = filedialog.askopenfilename(title="Purchase Order PDF", filetypes=[("PDF", "*.pdf")])
        if not po: return
        self._stv.set("⏳  Extracting PDF…"); self.update()
        def worker():
            try:
                from datetime import datetime
                records = extract_hm_records(bd, po)
                self._process_import_batch(records, "PDF")
            except Exception as e:
                self.after(0, lambda: ProToast(self, "error", "PDF Error", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _process_import_batch(self, records, source_type):
        from datetime import datetime
        added = updated = skipped = removed = 0
        proposed_changes = []
        temp_orders = [dict(o) for o in self._orders]
        
        # 1. Identify which orders are being touched by this import
        imported_order_nos = set(str(r.get("order_no", "")).strip() for r in records if r.get("order_no"))
        
        # 2. Track which existing rows for these orders are matched
        matched_existing_indices = set()
        
        for rec in records:
            idx = self._find_idx(rec)
            if idx is not None:
                matched_existing_indices.add(idx)
                existing = temp_orders[idx]
                if existing.get("shipped_status") in SHIPPED_DONE:
                    skipped += 1; continue
                
                diffs = []
                for k, new_v in rec.items():
                    if k in ("date_added", "added_by", "cut_off", "first_last", "week"): continue
                    if k in COL_KEYS:
                        old_v = str(existing.get(k,"")).strip()
                        v_str = str(new_v).strip()
                        if not v_str: continue # Skip empty incoming values
                        
                        try:
                            if float(v_str.replace(",","")) == float(old_v.replace(",","")): continue
                        except: pass
                        
                        if v_str.lower() != old_v.lower():
                            diffs.append((k, old_v, v_str))
                
                if diffs:
                    for k, old_v, new_v in diffs:
                        # Find human label for the field
                        lbl = next((c["label"] for c in COLUMNS if c["key"] == k), k)
                        proposed_changes.append({
                            "action": "UPDATE", "order_no": existing.get("order_no"),
                            "country": existing.get("country"), "field": lbl,
                            "old": old_v, "new": new_v, "idx": idx, "field_key": k
                        })
                else:
                    skipped += 1
            else:
                # Proposed Addition
                proposed_changes.append({
                    "action": "ADD", "order_no": rec.get("order_no"),
                    "country": rec.get("country"), "field": "New Row",
                    "old": "(N/A)", "new": "[INSERT]", "rec": rec
                })

        # 3. Identify existing rows for imported orders that were NOT in the new source
        # This handles the "Revised Order" case where a country might be removed.
        for i, o in enumerate(temp_orders):
            ono = str(o.get("order_no", "")).strip()
            if ono in imported_order_nos and i not in matched_existing_indices:
                # If it's not shipped, suggest removal
                if o.get("shipped_status") not in SHIPPED_DONE:
                    proposed_changes.append({
                        "action": "REMOVE", "order_no": o.get("order_no"),
                        "country": o.get("country"), "field": "Obsolete Row",
                        "old": "Existing in DB", "new": "[DELETE]", "idx": i
                    })

        def apply_final(final_orders, a, u, s, r):
            self._orders = auto_first_last(final_orders)
            self._save_db()
            self._apply_filter()
            # Custom status for revisions
            status_msg = f"✓ {a} added · {u} updated · {r} removed"
            self._stv.set(status_msg)
            if hasattr(self, "dashboard_view"): self.dashboard_view.update_data(self._orders)
            msg = f"{a} new record(s) added.\n{u} record(s) updated with revisions.\n{r} record(s) removed (obsolete).\n{s} record(s) skipped/no change."
            ProToast(self, "success", "Import & Review Complete", msg)

        if proposed_changes:
            def show_review():
                def on_apply():
                    u_count = 0; a_count = 0; r_count = 0
                    indices_to_remove = set()
                    
                    # We must process ADDs first or handle removals carefully
                    # Process Updates and Additions first
                    for ch in proposed_changes:
                        act = ch["action"]
                        if act == "UPDATE":
                            idx = ch["idx"]
                            fld = ch["field_key"]
                            temp_orders[idx][fld] = ch["new"]
                            temp_orders[idx] = calculate_row(temp_orders[idx])
                            self._record_change(temp_orders[idx], fld)
                            u_count += 1
                        elif act == "ADD":
                            rec = ch["rec"]
                            rec["date_added"] = datetime.now().strftime("%d-%b-%Y")
                            rec["added_by"]   = self.current_user["username"]
                            temp_orders.append(rec)
                            for k in COL_KEYS: self._record_change(rec, k)
                            a_count += 1
                        elif act == "REMOVE":
                            indices_to_remove.add(ch["idx"])
                            r_count += 1
                    
                    # Apply removals (in reverse to preserve indices)
                    final_orders = []
                    for i, o in enumerate(temp_orders):
                        if i not in indices_to_remove:
                            final_orders.append(o)
                    
                    log_action(self.current_user["username"], f"Import Sync ({source_type})",
                               f"Synced revision: {a_count} adds, {u_count} updates, {r_count} removals.")
                    apply_final(final_orders, a_count, u_count, skipped, r_count)
                
                ReviewUpdatesDialog(self, proposed_changes, on_apply=on_apply)
            self.after(0, show_review)
        else:
            self.after(0, lambda: apply_final(temp_orders, 0, 0, skipped, 0))


    def _record_change(self, row, key):
        """Record the timestamp of a change for visual highlighting."""
        import time
        ck = (row.get("order_no"), row.get("country"), row.get("colour"), row.get("style_name"), key)
        self._recent_changes[ck] = time.time()
        # Schedule a refresh to clear the highlight in 10 mins
        self.after(600000, self._apply_filter)

    def _find_idx(self, row):
        """Find the index of an order in self._orders based on order_no, country, and colour."""
        def _fmt(v): return str(v or "").strip().lower()
        
        on = _fmt(row.get("order_no"))
        ct = _fmt(row.get("country"))
        cl = _fmt(row.get("colour"))
        
        if not on or not ct: return None
        
        # Step 1: Find all potential candidates by Order No + Country
        candidates = []
        for i, o in enumerate(self._orders):
            if _fmt(o.get("order_no")) == on and _fmt(o.get("country")) == ct:
                candidates.append((i, o))
        
        if not candidates: return None
        
        # Step 2: Try exact colour match among candidates
        for i, o in candidates:
            if _fmt(o.get("colour")) == cl:
                return i
                
        # Step 3: Try fuzzy colour match among candidates
        # (Check if one colour string is contained in the other)
        for i, o in candidates:
            o_cl = _fmt(o.get("colour"))
            if cl and o_cl:
                if cl in o_cl or o_cl in cl:
                    return i
        
        # Step 4: If there is only ONE candidate and colour is empty/vague in source, match it
        if len(candidates) == 1 and not cl:
            return candidates[0][0]
            
        return None

    def _done_import(self, added, updated, skipped):
        self._apply_filter()
        self._stv.set(f"✓ {added} added · {updated} updated · {skipped} skipped")
        if hasattr(self, "dashboard_view"): self.dashboard_view.update_data(self._orders)
        msg = f"{added} new record(s) added.\n{updated} record(s) updated with revisions.\n{skipped} duplicate(s) skipped."
        ProToast(self, "success", "Import Complete", msg)

    def _download_template(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
            initialfile="Order_Import_Template.xlsx", title="Save Excel Template",
            filetypes=[("Excel", "*.xlsx")])
        if not path: return
        try:
            import pandas as pd
            pd.DataFrame(columns=[c["label"] for c in COLUMNS]).to_excel(path, index=False)
            self._stv.set("✓  Template saved")
            ProToast(self, "success", "Template Saved", f"Template saved to:\n{path}")
        except Exception as e:
            ProToast(self, "error", "Template Error", f"Failed: {e}")

    def _import_excel(self):
        f = filedialog.askopenfilename(title="Import Excel", filetypes=[("Excel", "*.xlsx *.xls")])
        if not f: return
        self._stv.set("⏳  Importing Excel…"); self.update()
        def worker():
            try:
                import pandas as pd
                df = pd.read_excel(f); records = []
                for _, row in df.iterrows():
                    d = {k: "" for k in COL_KEYS}
                    row_dict = {str(k).strip().lower(): v for k, v in row.items()}
                    for ec, val in row_dict.items():
                        if pd.isna(val): continue
                        v = str(val).strip()
                        if not v: continue
                        if   "order no" in ec or "o/n" in ec: d["order_no"] = v
                        elif "style" in ec:      d["style_name"] = v
                        elif "color" in ec or "colour" in ec: d["colour"] = v
                        elif "country" in ec:    d["country"] = v
                        elif "tod" in ec:        d["tod"] = v
                        elif "qty" in ec and ("order" in ec or "ord" in ec) and "pcs" not in ec: d["order_qty_set"] = v
                        elif "qty" in ec and "ship" in ec and "pcs" not in ec: d["ship_qty_set"] = v
                        elif "short" in ec or "excess" in ec: d["short_excess"] = v
                        elif "ship mode" in ec or "mode" in ec: d["ship_mode"] = v
                        elif "season" in ec:     d["season"] = v
                        elif "status" in ec:     d["shipped_status"] = v
                        elif "week" in ec:       d["week"] = v
                        elif "factory" in ec:    d["factory_merch"] = v
                        elif "merch" in ec and "hm" in ec: d["hm_merch"] = v
                        elif "cut" in ec:        d["cut_off"] = v
                    if d.get("order_no") and d.get("country"): records.append(d)
                self._process_import_batch(records, "Excel")
            except Exception as e:
                self.after(0, lambda: ProToast(self, "error", "Excel Error", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def _add_row(self):
        if not can(self.current_user, "add_row"):
            ProToast(self, "warning", "Permission Denied", "You do not have permission to add rows."); return
        
        # Collect unique values for searchable dropdowns
        countries = sorted(list(set(str(o.get("country", "")) for o in self._orders if o.get("country"))))
        colors    = sorted(list(set(str(o.get("colour", "")) for o in self._orders if o.get("colour"))))
        seasons   = sorted(list(set(str(o.get("season", "")) for o in self._orders if o.get("season"))))

        def on_save(row):
            self._orders.append(row); self._orders = auto_first_last(self._orders)
            self._save_db(); self._apply_filter()
            log_action(self.current_user["username"], "Add Row", f"Added Order {row.get('order_no')} ({row.get('country')})")
            if hasattr(self, "dashboard_view"): self.dashboard_view.update_data(self._orders)
        
        RowEditor(self, {k: "" for k in COL_KEYS}, "Add New Row", on_save, self.current_user, 
                  self.db.get("factory_merchants", []), countries, colors, seasons)

    def _edit_row(self):
        sel = self.tree.selection()
        if not sel: ProToast(self, "info", "No Selection", "Please select a row to edit."); return
        if len(sel) > 1: ProToast(self, "info", "Multiple Rows", "For single edit, select one row.\nFor multiple rows, use Bulk Edit."); return
        vals = self.tree.item(sel[0])["values"]
        row  = {k: (str(v) if v else "") for k, v in zip(COL_KEYS, vals)}
        idx  = self._find_idx(row)
        if idx is None: return

        # Collect unique values for searchable dropdowns
        countries = sorted(list(set(str(o.get("country", "")) for o in self._orders if o.get("country"))))
        colors    = sorted(list(set(str(o.get("colour", "")) for o in self._orders if o.get("colour"))))
        seasons   = sorted(list(set(str(o.get("season", "")) for o in self._orders if o.get("season"))))

        def on_save(updated):
            self._orders[idx] = updated; self._orders = auto_first_last(self._orders)
            self._save_db(); self._apply_filter()
            log_action(self.current_user["username"], "Edit Row", f"Updated Order {updated.get('order_no')} ({updated.get('country')})")
            if hasattr(self, "dashboard_view"): self.dashboard_view.update_data(self._orders)
        
        RowEditor(self, self._orders[idx], "Edit Row", on_save, self.current_user, 
                  self.db.get("factory_merchants", []), countries, colors, seasons)

    def _bulk_edit(self):
        sel = self._get_sel()
        if not sel: ProToast(self, "info", "No Selection", "Please select at least one row to bulk edit."); return
        pairs = []
        for _, row in sel:
            idx = self._find_idx(row)
            if idx is not None: pairs.append((idx, self._orders[idx]))
        if not pairs: return
        def on_save(updated):
            for (idx, _), nr in zip(pairs, updated): self._orders[idx] = nr
            self._orders = auto_first_last(self._orders)
            self._save_db(); self._apply_filter()
            self._stv.set(f"✓  {len(updated)} rows updated")
            if hasattr(self, "dashboard_view"): self.dashboard_view.update_data(self._orders)
        BulkEditor(self, [r for _, r in pairs], on_save, self.db.get("factory_merchants", []))

    def _delete_sel(self):
        if not can(self.current_user, "delete_row"):
            ProToast(self, "warning", "Permission Denied", "You do not have delete permission."); return
        sel = self._get_sel()
        if not sel: ProToast(self, "info", "No Selection", "Please select at least one row to delete."); return
        n = len(sel)
        def _do_delete():
            keys = {(r.get("order_no",""),r.get("country",""),r.get("colour","")) for _,r in sel}
            self._orders = [o for o in self._orders
                            if (o.get("order_no",""),o.get("country",""),o.get("colour","")) not in keys]
            self._orders = auto_first_last(self._orders)
            self._save_db(); self._apply_filter()
            self._stv.set(f"✓  {n} rows deleted")
            log_action(self.current_user["username"], "Delete Rows", f"Deleted {n} rows.")
            if hasattr(self, "dashboard_view"): self.dashboard_view.update_data(self._orders)
            ProToast(self, "success", "Deleted", f"{n} row(s) deleted successfully.")
        show_confirm(self, "Delete Rows?",
                     f"This will permanently delete {n} row(s).\nThis action cannot be undone.",
                     on_yes=_do_delete)

    def _open_reports(self):  ReportManager(self, self._orders)

    def _open_cutoff_mgr(self):
        if not can(self.current_user, "manage_cutoff"):
            ProToast(self, "warning", "Permission Denied", "You do not have permission to manage cut-off."); return
        def on_save(new_co):
            COUNTRY_CUTOFF.clear(); COUNTRY_CUTOFF.update(new_co)
            self.db["country_cutoff"] = dict(new_co)
            self._ct_cb.configure(values=["All"] + sorted(COUNTRY_CUTOFF.keys()))
            self._orders = [calculate_row(o) for o in self._orders]
            self._save_db(); self._apply_filter()
            self._stv.set(f"✓  Cut Off updated ({len(new_co)} countries)")
        CutoffManager(self, COUNTRY_CUTOFF, on_save)

    def _open_fact_merch(self):
        def on_save(new_db): self.db = new_db; self._save_db()
        FactoryMerchantManager(self, self.db, on_save)

    def _save_db(self):
        self.db["orders"] = self._orders
        self.db["country_cutoff"] = dict(COUNTRY_CUTOFF)
        db_save(self.db)

    def _open_users(self):
        if not can(self.current_user, "manage_users"):
            ProToast(self, "warning", "Access Restricted", "This feature is available to Admins only."); return
        UserManager(self, self.current_user)

    # ── Settings ──────────────────────────────────────────────────────────────
    def _open_settings(self):
        if not can(self.current_user, "manage_users"):
            ProToast(self, "warning", "Access Restricted", "This feature is available to Admins only."); return
        def on_saved(s):
            self.app_settings = s
            # Update title bar with new company name
            self.title(
                f"Garment Order Tracking System \u2014 {s.get('company_name','')}")
        SettingsDialog(self, on_saved=on_saved)

    def _open_backup_manager(self):
        win = tk.Toplevel(self)
        win.title("\U0001f4be  Backup Manager")
        win.geometry("520x540"); win.configure(bg=T["bg"])
        win.resizable(False, False); win.grab_set()
        tk.Frame(win, bg=T["accent"], height=3).pack(fill="x")
        hdr = tk.Frame(win, bg=T["surf"]); hdr.pack(fill="x")
        tk.Frame(hdr, bg=T["accent"], width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="  \U0001f4be  BACKUP MANAGER",
                 font=(T["mono"], 11, "bold"), fg=T["text"],
                 bg=T["surf"]).pack(side="left", pady=12, padx=6)
        tk.Frame(win, bg=T["border"], height=1).pack(fill="x")

        body = tk.Frame(win, bg=T["bg"], padx=24, pady=14)
        body.pack(fill="both", expand=True)

        info = get_backup_info()
        rows = [
            ("daily",    "\U0001f4c5  Daily Backups",      T["gold"]),
            ("on_close", "\U0001f6aa  On-Close Backups",   T["blue"]),
            ("manual",   "\u270d  Manual Backups",          T["teal"]),
        ]
        for key, title, col in rows:
            d = info.get(key, {"count": 0, "latest": "\u2014"})
            card = tk.Frame(body, bg=T["surf2"], padx=16, pady=10)
            card.pack(fill="x", pady=3)
            row_f = tk.Frame(card, bg=T["surf2"]); row_f.pack(fill="x")
            tk.Label(row_f, text=title, font=(T["font"], 9, "bold"),
                     fg=col, bg=T["surf2"]).pack(side="left")
            tk.Label(row_f, text=f"{d['count']} copies",
                     font=(T["mono"], 8, "bold"), fg=T["text"],
                     bg=T["surf2"]).pack(side="right")
            tk.Label(card, text=f"  Latest: {d['latest']}",
                     font=(T["mono"], 8), fg=T["muted"],
                     bg=T["surf2"]).pack(anchor="w")

        tk.Frame(body, bg=T["border"], height=1).pack(fill="x", pady=8)
        
        admin_f = tk.Frame(body, bg=T["bg"])
        admin_f.pack(fill="x", pady=5)
        _mk_btn(admin_f, "👤 User Management", T["surf3"], T["text"],
                lambda: UserManager(self)).pack(side="left", padx=5)
        _mk_btn(admin_f, "📜 Audit Logs", T["surf3"], T["text"],
                lambda: AuditLogViewerDialog(self)).pack(side="left", padx=5)

        tk.Label(body, text=f"  Folder:  {BACKUP_DIR}",
                 font=(T["font"], 8), fg=T["dim"], bg=T["bg"],
                 wraplength=460, justify="left").pack(anchor="w")

        note_f = tk.Frame(body, bg=T["gold_bg"], padx=12, pady=8)
        note_f.pack(fill="x", pady=(10, 0))
        tk.Label(note_f,
                 text="\u2139  Daily: once per day at startup  |  "
                      "On-Close: every exit  |  Hourly: every 60 min (bg)",
                 font=(T["font"], 8), fg=T["gold"],
                 bg=T["gold_bg"], justify="left").pack(anchor="w")

        bot = tk.Frame(win, bg=T["surf"], pady=10); bot.pack(fill="x")
        self._bk_status = tk.StringVar(value="")
        tk.Label(bot, textvariable=self._bk_status,
                 font=(T["font"], 8), fg=T["green"],
                 bg=T["surf"]).pack(side="left", padx=16)

        def do_manual():
            p = backup_manual()
            self._bk_status.set(
                f"\u2705 Saved: {os.path.basename(p)}" if p else "\u26a0 Backup failed")

        def open_folder():
            import subprocess
            subprocess.Popen(f'explorer "{BACKUP_DIR}"')

        _mk_btn(bot, "\U0001f4c2  Open Folder", T["surf3"], T["text"],
                open_folder, T["surf4"], font_size=9).pack(side="right", padx=4)
        _mk_btn(bot, "\U0001f4be  Backup Now", T["accent"], "white",
                do_manual, T["accent2"], font_size=9).pack(side="right", padx=10)

    def _show_version_history(self):
        """Open the professional version history (changelog) dialog."""
        VersionHistoryDialog(self)

    def _logout(self):
        """Confirm and logout from the current session."""
        if show_confirm(self, "Confirm Logout", "Are you sure you want to log out?"):
            # Close the main window. 
            # Note: In the current __main__ structure, this will exit the app.
            self.destroy()

    # ── Close / Logout ─────────────────────────────────────────────────────────
    def _on_close(self):
        self._stv.set("\u29d6  Saving backup\u2026"); self.update()
        stop_scheduled_backup()
        backup_on_close()
        self.destroy()


    def _prompt_update(self, remote_v, remote_cl):
        """Show the professional review dialog before updating."""
        def on_update():
            self._stv.set("⏳ Updating system...")
            def worker():
                success, output = perform_git_update()
                if success:
                    self.after(0, lambda: ProToast(self, "success", "Update Successful", 
                                                   "System updated successfully. Please restart the application to apply changes."))
                    self.after(0, lambda: self._stv.set(f"✓ Updated to v{remote_v} (Restart required)"))
                else:
                    self.after(0, lambda: ProToast(self, "error", "Update Failed", output))
                    self.after(0, lambda: self._stv.set("⚠ Update failed"))
            
            threading.Thread(target=worker, daemon=True).start()

        UpdateReviewDialog(self, VERSION, remote_v, remote_cl, on_update=on_update)


if __name__ == "__main__":
    login = LoginWindow()
    login.mainloop()
    if login.logged_in:
        app = MainApp(login.logged_in)
        app.mainloop()