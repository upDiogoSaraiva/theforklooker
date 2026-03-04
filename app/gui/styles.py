"""
Shared style constants and ttk theme setup for a modern dark GUI.
"""

import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Catppuccin Mocha palette
# ---------------------------------------------------------------------------

BG = "#1e1e2e"
BG_SIDEBAR = "#11111b"
BG_CARD = "#313244"
BG_INPUT = "#45475a"
FG = "#cdd6f4"
FG_DIM = "#6c7086"
FG_BRIGHT = "#ffffff"
ACCENT = "#f38ba8"
ACCENT_GREEN = "#a6e3a1"
ACCENT_YELLOW = "#f9e2af"
ACCENT_RED = "#f38ba8"
ACCENT_BLUE = "#89b4fa"
BORDER = "#45475a"

# Sidebar
SIDEBAR_ACTIVE_BG = "#313244"
SIDEBAR_HOVER_BG = "#1e1e2e"

# Fonts
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_HEADING = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO = ("Cascadia Code", 9)

# Dimensions
PAD = 20
PAD_SMALL = 10
SIDEBAR_WIDTH = 170
INPUT_WIDTH = 45


def apply_theme(root: tk.Tk):
    """Apply a modern dark theme to ttk widgets."""
    style = ttk.Style(root)
    style.theme_use("clam")

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground=BG_INPUT,
        background=BG_INPUT,
        foreground=FG,
        arrowcolor=FG,
        borderwidth=0,
        relief="flat",
    )
    style.map("TCombobox",
        fieldbackground=[("readonly", BG_INPUT)],
        selectbackground=[("readonly", BG_INPUT)],
        selectforeground=[("readonly", FG)],
    )

    # Scrollbar
    style.configure(
        "Vertical.TScrollbar",
        background=BG_CARD,
        troughcolor=BG,
        borderwidth=0,
        arrowcolor=FG_DIM,
    )
    style.map("Vertical.TScrollbar",
        background=[("active", ACCENT_BLUE)],
    )
