"""
widgets.py — Shared UI helper functions.

Centralises button/entry builders and other small UI primitives that
were previously duplicated across garment_tracker.py, dialogs.py and
settings.py.  Import from here instead of redefining locally.
"""
import tkinter as tk
from tkinter import ttk
from config import T, bind_hover


def mk_btn(parent, text, bg, fg, cmd,
           hover_bg=None, font_size=10, padx=14, pady=6) -> tk.Button:
    """Reusable modern flat button with hover highlight."""
    hbg = hover_bg or bg
    b = tk.Button(
        parent, text=text,
        font=(T["font"], font_size, "bold"),
        bg=bg, fg=fg, relief="flat", bd=0,
        padx=padx, pady=pady, cursor="hand2",
        activebackground=hbg, activeforeground=fg,
        command=cmd,
    )
    bind_hover(b, bg, hbg, fg, fg)
    return b


def mk_entry(parent, textvariable, width=30, show="") -> tk.Entry:
    """Single-line entry with dark theme styling."""
    return tk.Entry(
        parent, textvariable=textvariable,
        font=(T["mono"], 9), bg=T["surf3"], fg=T["text"],
        relief="flat", bd=0, width=width, show=show,
        insertbackground=T["text"],
    )


def styled_entry(parent, textvariable, width=22, show=""):
    """
    Bordered entry widget (accent glow on focus).
    Returns (frame, entry) — pack/grid the frame, interact with the entry.
    """
    f = tk.Frame(parent, bg=T["border"], padx=1, pady=1)
    e = tk.Entry(
        f, textvariable=textvariable, show=show,
        font=(T["font"], 10), bg=T["surf3"], fg=T["text"],
        relief="flat", bd=0, insertbackground=T["accent"],
        width=width, highlightthickness=0,
    )
    e.pack(padx=8, pady=6)
    e.bind("<FocusIn>",  lambda ev, fr=f: fr.config(bg=T["accent"]))
    e.bind("<FocusOut>", lambda ev, fr=f: fr.config(bg=T["border"]))
    return f, e


def show_confirm(parent, title, message, on_yes, on_no=None):
    """
    Show a ProToast confirmation dialog.
    Import ProToast lazily to avoid a circular import.
    """
    from dialogs import ProToast
    ProToast(parent, "confirm", title, message, on_yes=on_yes, on_no=on_no)


def add_mousewheel(widget, canvas):
    """Bind mousewheel scrolling on `canvas` to the given widget subtree."""
    def _scroll(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind(w):
        w.bind("<MouseWheel>", _scroll)
        for child in w.winfo_children():
            _bind(child)

    _bind(widget)
    canvas.bind("<MouseWheel>", _scroll)
