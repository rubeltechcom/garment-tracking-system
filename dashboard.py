import tkinter as tk
from tkinter import ttk
from config import T, bind_hover
from logic import build_analytics


class DashboardFrame(tk.Frame):
    def __init__(self, parent, orders, on_close=None):
        super().__init__(parent, bg=T["bg"])
        self._orders  = orders
        self._ana     = build_analytics(orders)
        self.on_close = on_close
        self._build()

    def update_data(self, orders):
        self._orders = orders
        self._ana = build_analytics(orders)
        for w in self.winfo_children():
            w.destroy()
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        # ── Dashboard header ─────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=T["surf"], height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=T["accent"], width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="  \U0001f4ca  ANALYTICS DASHBOARD",
                 font=(T["mono"], 10, "bold"), fg=T["text"],
                 bg=T["surf"]).pack(side="left", padx=6)
        tk.Label(hdr, text="Scroll for Trends & Distribution",
                 font=(T["font"], 8), fg=T["muted"],
                 bg=T["surf"]).pack(side="left", padx=4)

        if self.on_close:
            btn = tk.Button(hdr, text="Order List  \u203a",
                            font=(T["font"], 9, "bold"),
                            bg=T["accent"], fg="white",
                            relief="flat", padx=14, pady=0,
                            cursor="hand2", command=self.on_close,
                            activebackground=T["accent2"], activeforeground="white")
            btn.pack(side="right", padx=14, pady=8, fill="y")
            bind_hover(btn, T["accent"], T["accent2"], "white", "white")

        # Thin separator
        tk.Frame(self, bg=T["border"], height=1).pack(fill="x")

        # ── Scrollable Canvas Body ───────────────────────────────────────────
        canvas = tk.Canvas(self, bg=T["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        self.scroll_body = tk.Frame(canvas, bg=T["bg"])
        self.scroll_body.bind("<Configure>", 
                              lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Ensure scroll region is updated when contents change
        canvas.create_window((0, 0), window=self.scroll_body, anchor="nw")
        
        # Auto-resize scrollable frame width to match canvas
        def _on_canvas_resize(event):
            canvas.itemconfig(canvas.create_window((0,0), window=self.scroll_body, anchor="nw"), width=event.width)
        canvas.bind("<Configure>", _on_canvas_resize)

        # ── KPI row ──────────────────────────────────────────────────────────
        self._build_kpi_row(self.scroll_body)

        # Thin separator
        tk.Frame(self.scroll_body, bg=T["border"], height=1).pack(fill="x")

        # ── Body panels ──────────────────────────────────────────────────────
        body = tk.Frame(self.scroll_body, bg=T["bg"])
        body.pack(fill="both", expand=True, padx=10, pady=8)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        lp = tk.Frame(body, bg=T["surf2"])
        lp.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        rp = tk.Frame(body, bg=T["surf2"])
        rp.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self._build_style_panel(lp)
        self._build_order_panel(rp)

        # ── Visual Analytics Section (Trend & Distribution) ──────────────────
        viz_f = tk.Frame(self.scroll_body, bg=T["bg"])
        viz_f.pack(fill="x", padx=10, pady=(0, 10))
        viz_f.columnconfigure(0, weight=3) # Trend
        viz_f.columnconfigure(1, weight=2) # Distribution

        tp = tk.Frame(viz_f, bg=T["surf2"], height=260)
        tp.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        tp.pack_propagate(False)
        self._build_trend_chart(tp)

        dp = tk.Frame(viz_f, bg=T["surf2"], height=260)
        dp.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        dp.pack_propagate(False)
        self._build_distribution_panel(dp)

    def _build_trend_chart(self, parent):
        self._panel_header(parent, "SHIPMENT TRENDS (LAST 6 MONTHS)", "#2DD4BF", "\U0001f4c8")
        
        from datetime import datetime, timedelta
        now = datetime.now()
        # Get last 6 months keys
        six_months = []
        for i in range(5, -1, -1):
            dt = now - timedelta(days=i*30)
            six_months.append(dt.strftime("%Y-%m"))
            
        trends = {m: {"label": datetime.strptime(m, "%Y-%m").strftime("%b-%y"), "qty": 0} for m in six_months}
        
        for o in self._orders:
            if o.get("shipped_status") == "Shipped":
                tod = o.get("tod", "")
                try:
                    dt = datetime.strptime(tod, "%d-%b-%y")
                    m_key = dt.strftime("%Y-%m")
                    if m_key in trends:
                        qty_str = str(o.get("ship_qty_set", "0")).replace(",", "")
                        trends[m_key]["qty"] += int(float(qty_str or 0))
                except: continue
        
        chart_f = tk.Frame(parent, bg=T["surf2"])
        chart_f.pack(fill="both", expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(chart_f, bg=T["surf2"], highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        self.update_idletasks()
        W = canvas.winfo_width() or 450
        H = canvas.winfo_height() or 160
        
        data = [trends[m] for m in six_months]
        max_q = max(d["qty"] for d in data) if data and any(d["qty"] for d in data) else 1
        
        bar_w = (W - 80) // len(data) if data else 50
        x = 50
        for d in data:
            bh = (d["qty"] / max_q) * (H - 50)
            # Bar
            canvas.create_rectangle(x, H-25-bh, x+bar_w-15, H-25, fill="#2DD4BF", outline="")
            # Label
            canvas.create_text(x + (bar_w-15)//2, H-12, text=d["label"], font=(T["font"], 7), fill=T["muted"])
            # Value
            canvas.create_text(x + (bar_w-15)//2, H-25-bh-10, text=f"{d['qty']:,}", font=(T["mono"], 7, "bold"), fill=T["text"])
            x += bar_w

    def _build_distribution_panel(self, parent):
        self._panel_header(parent, "TOP COUNTRIES (DISTRIBUTION)", T["blue"], "\U0001f310")
        
        # Calculate distribution
        dist = {}
        for o in self._orders:
            c = o.get("country", "Unknown") or "Unknown"
            dist[c] = dist.get(c, 0) + 1
            
        top_5 = sorted(dist.items(), key=lambda x: x[1], reverse=True)[:5]
        total = sum(dist.values()) or 1
        
        chart_f = tk.Frame(parent, bg=T["surf2"])
        chart_f.pack(fill="both", expand=True, padx=15, pady=10)
        
        SIZE = 140
        canvas = tk.Canvas(chart_f, width=SIZE, height=SIZE, bg=T["surf2"], highlightthickness=0)
        canvas.pack(side="left")
        
        # Donut Chart
        colors = [T["blue"], T["teal"], T["gold"], T["green"], T["red"]]
        start = 90
        pad, ring = 10, 18
        x0, y0, x1, y1 = pad, pad, SIZE-pad, SIZE-pad
        cx, cy = SIZE//2, SIZE//2
        
        canvas.create_oval(x0, y0, x1, y1, outline=T["surf4"], width=ring)
        
        legend_f = tk.Frame(chart_f, bg=T["surf2"])
        legend_f.pack(side="left", fill="both", expand=True, padx=10)
        
        for i, (name, count) in enumerate(top_5):
            col = colors[i % len(colors)]
            extent = -(count / total * 360)
            canvas.create_arc(x0, y0, x1, y1, start=start, extent=extent, outline=col, width=ring, style="arc")
            start += extent
            
            # Legend
            row = tk.Frame(legend_f, bg=T["surf2"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text="●", fg=col, bg=T["surf2"], font=(T["font"], 8)).pack(side="left")
            tk.Label(row, text=f" {name}", fg=T["text"], bg=T["surf2"], font=(T["font"], 7, "bold")).pack(side="left")
            tk.Label(row, text=f" {int(count/total*100)}%", fg=T["muted"], bg=T["surf2"], font=(T["mono"], 7)).pack(side="right")
        
        canvas.create_text(cx, cy, text=f"{total}", font=(T["mono"], 12, "bold"), fill=T["text"])
        canvas.create_text(cx, cy+14, text="Orders", font=(T["font"], 6), fill=T["muted"])

    # ── KPI row ───────────────────────────────────────────────────────────────
    def _build_kpi_row(self, parent):
        a = self._ana
        total     = len(self._orders)
        n_styles  = len(a["styles"])
        n_orders  = len(a["orders"])
        shipped   = sum(1 for o in self._orders if o.get("shipped_status", "") == "Shipped")
        pending   = sum(1 for o in self._orders
                        if o.get("shipped_status", "") in
                        ("", "Pending", "1st Shipment", "Last Shipment"))
        cancelled = sum(1 for o in self._orders if o.get("shipped_status", "") == "Cancelled")
        closed    = sum(1 for od in a["orders"].values()
                        if od["rows_pending"] == 0
                        and (od["rows_shipped"] + od["rows_cancelled"]) > 0)
        new_ords  = sum(1 for od in a["orders"].values()
                        if od["rows_shipped"] == 0 and od["rows_cancelled"] == 0
                        and od["rows_pending"] > 0
                        and all((o.get("shipped_status", "") or "") in ("", "Pending")
                                for o in od["rows"]))
        pct = int(shipped / total * 100) if total else 0

        row_f = tk.Frame(parent, bg=T["bg"])
        row_f.pack(fill="x", padx=10, pady=8)

        # ── Shipping progress card — Circular Donut ───────────────────────
        prog_card = tk.Frame(row_f, bg=T["surf2"], padx=14, pady=14)
        prog_card.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Header
        top = tk.Frame(prog_card, bg=T["surf2"])
        top.pack(fill="x")
        tk.Label(top, text="SHIPPING PROGRESS",
                 font=(T["font"], 8, "bold"), fg=T["muted"],
                 bg=T["surf2"]).pack(side="left")
        pct_col = T["green"] if pct >= 60 else T["gold"] if pct >= 30 else T["red"]
        tk.Label(top, text=f"{shipped}/{total} entries",
                 font=(T["mono"], 8), fg=T["muted"],
                 bg=T["surf2"]).pack(side="right")

        # Canvas donut layout
        donut_row = tk.Frame(prog_card, bg=T["surf2"])
        donut_row.pack(fill="both", expand=True, pady=(4, 0))

        SIZE = 170
        canvas = tk.Canvas(donut_row, width=SIZE, height=SIZE,
                           bg=T["surf2"], highlightthickness=0)
        canvas.pack(side="left", padx=(10, 14))

        # Donut parameters
        pad, ring = 10, 22
        x0, y0 = pad, pad
        x1, y1 = SIZE - pad, SIZE - pad
        cx, cy = SIZE // 2, SIZE // 2

        # Track ring (background)
        canvas.create_oval(x0, y0, x1, y1, outline=T["surf4"], width=ring)

        # Draw arcs — segments list: (label, count, color)
        segments = [
            ("Shipped",   shipped,   T["green"]),
            ("Pending",   pending,   T["gold"]),
            ("Cancelled", cancelled, T["red"]),
        ]
        arc_ids = []
        start = 90  # start from top (12 o'clock)
        for label, count, color in segments:
            if total == 0 or count == 0:
                arc_ids.append((None, label, count, color))
                continue
            extent = -(count / total * 360)
            aid = canvas.create_arc(x0, y0, x1, y1,
                                    start=start, extent=extent,
                                    outline=color, width=ring, style="arc")
            arc_ids.append((aid, label, count, color))
            start += extent

        # Center percentage text
        canvas.create_text(cx, cy - 8, text=f"{pct}%",
                           font=(T["mono"], 22, "bold"), fill=pct_col)
        canvas.create_text(cx, cy + 16, text="Completed",
                           font=(T["font"], 8), fill=T["muted"])

        # ── Hover tooltip for donut segments ──────────────────────────────
        tooltip_win = None

        def _show_tip(event, label, count, color):
            nonlocal tooltip_win
            _hide_tip()
            p = (count / total * 100) if total else 0
            tooltip_win = tw = tk.Toplevel(canvas)
            tw.wm_overrideredirect(True)
            tw.attributes("-topmost", True)
            tw.configure(bg=T["border"])
            inner = tk.Frame(tw, bg=T["surf"], padx=12, pady=8)
            inner.pack(padx=1, pady=1)
            tk.Label(inner, text=f"● {label}", font=(T["font"], 9, "bold"),
                     fg=color, bg=T["surf"]).pack(anchor="w")
            tk.Label(inner, text=f"Quantity:  {count}",
                     font=(T["mono"], 9), fg=T["text"], bg=T["surf"]).pack(anchor="w", pady=(2,0))
            tk.Label(inner, text=f"Percentage:  {p:.1f}%",
                     font=(T["mono"], 9), fg=T["text"], bg=T["surf"]).pack(anchor="w")
            tw.geometry(f"+{event.x_root+14}+{event.y_root+10}")

        def _hide_tip(*_):
            nonlocal tooltip_win
            if tooltip_win:
                tooltip_win.destroy()
                tooltip_win = None

        for aid, label, count, color in arc_ids:
            if aid is None:
                continue
            canvas.tag_bind(aid, "<Enter>",
                            lambda e, l=label, c=count, co=color: _show_tip(e, l, c, co))
            canvas.tag_bind(aid, "<Motion>",
                            lambda e, l=label, c=count, co=color: _show_tip(e, l, c, co))
            canvas.tag_bind(aid, "<Leave>", _hide_tip)
        canvas.bind("<Leave>", _hide_tip)

        # ── Right side: legend chips + mini stats ─────────────────────────
        info_f = tk.Frame(donut_row, bg=T["surf2"])
        info_f.pack(side="left", fill="both", expand=True, padx=(0, 6))

        for label, count, color in segments:
            p = (count / total * 100) if total else 0
            row = tk.Frame(info_f, bg=T["surf3"], padx=12, pady=7)
            row.pack(fill="x", pady=2)
            tk.Label(row, text="●", font=(T["font"], 10),
                     fg=color, bg=T["surf3"]).pack(side="left")
            tk.Label(row, text=f"  {label}",
                     font=(T["font"], 9, "bold"), fg=T["text"],
                     bg=T["surf3"]).pack(side="left")
            tk.Label(row, text=f"{p:.1f}%",
                     font=(T["mono"], 9, "bold"), fg=color,
                     bg=T["surf3"]).pack(side="right")
            tk.Label(row, text=f"{count}  ·  ",
                     font=(T["mono"], 8), fg=T["muted"],
                     bg=T["surf3"]).pack(side="right")

        # ── Stat cards grid ────────────────────────────────────────────────
        cards_f = tk.Frame(row_f, bg=T["bg"])
        cards_f.pack(side="left", fill="both", expand=True, padx=(5, 0))

        cards = [
            ("STYLES",        n_styles,  T["gold"],   T["gold_bg"],   "\U0001f3a8"),
            ("ORDERS",        n_orders,  T["blue"],   T["blue_bg"],   "\U0001f4e6"),
            ("CLOSED ORDERS", closed,    T["green"],  T["green_bg"],  "\U0001f512"),
            ("NEW ORDERS",    new_ords,  T["teal"],   T["surf3"],     "\u2726"),
        ]
        cards_f.columnconfigure(0, weight=1)
        cards_f.columnconfigure(1, weight=1)
        cards_f.rowconfigure(0, weight=1)
        cards_f.rowconfigure(1, weight=1)

        for i, (title, val, color, bg_col, icon) in enumerate(cards):
            r, c = divmod(i, 2)
            outer = tk.Frame(cards_f, bg=T["border"], padx=1, pady=1)
            outer.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
            cf = tk.Frame(outer, bg=bg_col, padx=16, pady=12)
            cf.pack(fill="both", expand=True)

            top_row = tk.Frame(cf, bg=bg_col)
            top_row.pack(fill="x")
            tk.Label(top_row, text=icon, font=(T["font"], 11),
                     fg=color, bg=bg_col).pack(side="left")
            tk.Label(top_row, text=f"  {title}",
                     font=(T["font"], 7, "bold"), fg=T["muted"],
                     bg=bg_col).pack(side="left", pady=(3, 0))
            tk.Label(cf, text=str(val),
                     font=(T["mono"], 24, "bold"), fg=color,
                     bg=bg_col).pack(anchor="w", pady=(4, 0))

    # ── Treeview builder ──────────────────────────────────────────────────────
    def _make_tree(self, parent, style_name, cols, headers, widths):
        s = ttk.Style()
        s.configure(f"{style_name}.Treeview",
                    background=T["surf2"], foreground=T["text"],
                    fieldbackground=T["surf2"], rowheight=26,
                    font=(T["mono"], 8))
        s.configure(f"{style_name}.Treeview.Heading",
                    background=T["surf3"], foreground=T["muted"],
                    font=(T["font"], 8, "bold"), relief="flat")
        s.map(f"{style_name}.Treeview",
              background=[("selected", T["accent3"])],
              foreground=[("selected", "white")])

        tree = ttk.Treeview(parent, columns=cols, show="headings",
                            style=f"{style_name}.Treeview")
        for c in cols:
            tree.heading(c, text=headers[c])
            tree.column(c, width=widths[c],
                        anchor="w" if c in ("style", "ono", "sty") else "center")
        tree.tag_configure("closed", foreground="#22C55E")
        tree.tag_configure("new",    foreground="#60A5FA")
        tree.tag_configure("active", foreground="#F59E0B")

        ys = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y", pady=(0, 0))
        tree.pack(fill="both", expand=True, padx=(0, 0), pady=(0, 0))
        return tree

    def _panel_header(self, parent, text, color, icon=""):
        hf = tk.Frame(parent, bg=T["surf3"], pady=10)
        hf.pack(fill="x")
        tk.Frame(hf, bg=color, width=4).pack(side="left", fill="y")
        tk.Label(hf, text=f"  {icon}  {text}" if icon else f"  {text}",
                 font=(T["font"], 9, "bold"),
                 fg=color, bg=T["surf3"]).pack(side="left", padx=6)

    # ── Styles panel ──────────────────────────────────────────────────────────
    def _build_style_panel(self, parent):
        self._panel_header(parent, "STYLES", T["gold"], "\U0001f3a8")
        cols    = ("style", "orders", "oq", "shipped", "pending", "state")
        headers = {"style": "Style Name", "orders": "Orders", "oq": "Order Qty",
                   "shipped": "Shipped", "pending": "Pending", "state": "State"}
        widths  = {"style": 180, "orders": 60, "oq": 82,
                   "shipped": 68, "pending": 68, "state": 80}
        self.sty_tree = self._make_tree(parent, "ST", cols, headers, widths)
        self.sty_tree.bind("<<TreeviewSelect>>", self._on_style_click)

        for sn, sd in sorted(self._ana["styles"].items()):
            sp = sd["rows_shipped"]
            pe = sd["rows_pending"]
            ca = sd["rows_cancelled"]
            total = sp + pe + ca
            if total == 0 or (sp == 0 and ca == 0): tag = "new";    state = "New"
            elif pe == 0:                             tag = "closed"; state = "Closed"
            else:                                     tag = "active"; state = "Active"
            self.sty_tree.insert("", "end",
                values=(sn, len(sd["order_nos"]), sd["total_oq"], sp, pe, state),
                tags=(tag,))

    # ── Orders panel ─────────────────────────────────────────────────────────
    def _build_order_panel(self, parent):
        self._panel_header(parent, "ORDERS", T["blue"], "\U0001f4e6")
        cols    = ("ono", "sty", "oq", "shipped", "pending", "state")
        headers = {"ono": "Order No", "sty": "Style", "oq": "Ord Qty",
                   "shipped": "Shipped", "pending": "Pending", "state": "State"}
        widths  = {"ono": 115, "sty": 160, "oq": 75,
                   "shipped": 68, "pending": 68, "state": 80}
        self.ord_tree = self._make_tree(parent, "OR", cols, headers, widths)
        self.ord_tree.bind("<<TreeviewSelect>>", self._on_order_click)

        for ono, od in sorted(self._ana["orders"].items()):
            sp = od["rows_shipped"]
            pe = od["rows_pending"]
            ca = od["rows_cancelled"]
            total = sp + pe + ca
            if total == 0 or (sp == 0 and ca == 0): tag = "new";    state = "New"
            elif pe == 0:                             tag = "closed"; state = "Closed"
            else:                                     tag = "active"; state = "Active"
            self.ord_tree.insert("", "end",
                values=(ono, od["style_name"], od["total_oq"], sp, pe, state),
                tags=(tag,))

    # ── Detail popup ──────────────────────────────────────────────────────────
    def _render_detail(self, title: str, rows: list, extra_info: str = ""):
        popup = tk.Toplevel(self)
        popup.title(title)
        popup.geometry("1000x460")
        popup.configure(bg=T["bg"])
        popup.transient(self.winfo_toplevel())

        # Accent top bar
        tk.Frame(popup, bg=T["accent"], height=3).pack(fill="x")

        # Header
        th = tk.Frame(popup, bg=T["surf2"])
        th.pack(fill="x", padx=0, pady=0)
        tk.Frame(th, bg=T["accent"], width=4).pack(side="left", fill="y")
        tk.Label(th, text=f"  {title}",
                 font=(T["font"], 11, "bold"),
                 fg=T["text"], bg=T["surf2"]).pack(side="left", pady=12, padx=6)
        if extra_info:
            tk.Label(th, text=f"  {extra_info}",
                     font=(T["font"], 8), fg=T["muted"],
                     bg=T["surf2"]).pack(side="left")

        # Summary badges
        total     = len(rows)
        shipped   = sum(1 for r in rows if r.get("shipped_status", "") == "Shipped")
        pending   = sum(1 for r in rows if r.get("shipped_status", "") not in ("Shipped", "Cancelled"))
        cancelled = sum(1 for r in rows if r.get("shipped_status", "") == "Cancelled")

        bf = tk.Frame(popup, bg=T["surf3"])
        bf.pack(fill="x")
        for lbl, col, bg_ in [
            (f"  Total Entries: {total}",    T["muted"],  T["surf3"]),
            (f"  \u2713 Shipped: {shipped}",  T["green"],  T["green_bg"]),
            (f"  \u29d6 Pending: {pending}",  T["gold"],   T["gold_bg"]),
            (f"  \u2715 Cancelled: {cancelled}", T["red"], T["red_bg"]),
        ]:
            chip = tk.Frame(bf, bg=bg_, padx=10, pady=5)
            chip.pack(side="left", padx=2, pady=4)
            tk.Label(chip, text=lbl, font=(T["font"], 8, "bold"),
                     fg=col, bg=bg_).pack()

        # Detail table
        s = ttk.Style()
        s.configure("DT.Treeview",
                    background=T["surf2"], foreground=T["text"],
                    fieldbackground=T["surf2"], rowheight=24,
                    font=(T["mono"], 8))
        s.configure("DT.Treeview.Heading",
                    background=T["surf3"], foreground=T["muted"],
                    font=(T["font"], 8, "bold"), relief="flat")
        s.map("DT.Treeview",
              background=[("selected", T["accent3"])],
              foreground=[("selected", "white")])

        dcols = ("order_no", "colour", "country", "tod", "order_qty_set",
                 "ship_qty_set", "short_excess", "first_last",
                 "week", "cut_off", "status")
        dlbls = {"order_no": "Order No", "colour": "Colour", "country": "Ctry",
                 "tod": "ToD", "order_qty_set": "Ord Qty",
                 "ship_qty_set": "Ship Qty", "short_excess": "Short/Exc",
                 "first_last": "1ST & Last", "week": "Week",
                 "cut_off": "Cut Off", "status": "Status"}
        dw    = {"order_no": 105, "colour": 140, "country": 52, "tod": 85,
                 "order_qty_set": 70, "ship_qty_set": 70, "short_excess": 70,
                 "first_last": 90, "week": 62, "cut_off": 56, "status": 100}

        tf = tk.Frame(popup, bg=T["bg"])
        tf.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        dt = ttk.Treeview(tf, columns=dcols, show="headings", style="DT.Treeview")
        for c in dcols:
            dt.heading(c, text=dlbls[c])
            dt.column(c, width=dw[c], anchor="center")
        xs = ttk.Scrollbar(tf, orient="horizontal", command=dt.xview)
        ys = ttk.Scrollbar(tf, orient="vertical",   command=dt.yview)
        dt.configure(xscrollcommand=xs.set, yscrollcommand=ys.set)
        xs.pack(side="bottom", fill="x")
        ys.pack(side="right",  fill="y")
        dt.pack(fill="both", expand=True)
        dt.tag_configure("shipped",   foreground="#22C55E")
        dt.tag_configure("pending",   foreground="#F59E0B")
        dt.tag_configure("cancelled", foreground="#F87171")

        for o in sorted(rows, key=lambda x: (x.get("country", ""), x.get("colour", ""))):
            st  = o.get("shipped_status", "") or "Pending"
            tag = ("shipped" if st == "Shipped" else
                   "cancelled" if st == "Cancelled" else "pending")
            dt.insert("", "end", tags=(tag,), values=(
                o.get("order_no",      ""),
                o.get("colour",        ""),
                o.get("country",       ""),
                o.get("tod",           ""),
                o.get("order_qty_set", "") or "\u2014",
                o.get("ship_qty_set",  "") or "\u2014",
                o.get("short_excess",  "") or "\u2014",
                o.get("first_last",    "") or "\u2014",
                o.get("week",          "") or "\u2014",
                o.get("cut_off",       "") or "\u2014",
                st,
            ))

    # ── Click handlers ────────────────────────────────────────────────────────
    def _on_style_click(self, *_):
        sel = self.sty_tree.selection()
        if not sel: return
        sn   = str(self.sty_tree.item(sel[0])["values"][0])
        sd   = self._ana["styles"].get(sn, {})
        rows = sd.get("rows", [])
        pc   = sorted(set(o.get("country", "") for o in rows
                          if o.get("shipped_status", "") not in ("Shipped", "Cancelled")))
        extra = f"\u00b7  Pending countries: {', '.join(pc) or 'None'}"
        self._render_detail(f"\U0001f3a8  Style: {sn}", rows, extra)

    def _on_order_click(self, *_):
        sel = self.ord_tree.selection()
        if not sel: return
        ono   = str(self.ord_tree.item(sel[0])["values"][0])
        od    = self._ana["orders"].get(ono, {})
        rows  = od.get("rows", [])
        pc    = sorted(set(od.get("countries_pending", [])))
        extra = f"\u00b7  Pending: {', '.join(pc) or 'None'}"
        self._render_detail(f"\U0001f4e6  Order: {ono}  [{od.get('style_name', '')}]", rows, extra)
