"""
Main application controller — sidebar navigation + frame switching.
"""

import os
import tkinter as tk

from app.gui import styles as S
from app.gui.setup_frame import SetupFrame
from app.gui.server_frame import ServerFrame
from app.gui.deploy_frame import DeployFrame
from app.gui.status_frame import StatusFrame
from app.core import settings


class App(tk.Frame):
    """Root application frame with sidebar navigation."""

    PAGES = [
        ("Setup", "setup_frame"),
        ("Server", "server_frame"),
        ("Deploy", "deploy_frame"),
        ("Status", "status_frame"),
    ]

    def __init__(self, parent, assets_dir: str = ""):
        super().__init__(parent, bg=S.BG)
        self._assets_dir = assets_dir
        self._current_page = None
        self._nav_buttons: dict[str, tk.Button] = {}
        self._icon_photo = None  # prevent garbage collection
        self._build_ui()
        self._load_settings()
        self._show_page("setup_frame")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Sidebar
        sidebar = tk.Frame(self, bg=S.BG_SIDEBAR, width=S.SIDEBAR_WIDTH)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo icon + title
        logo_frame = tk.Frame(sidebar, bg=S.BG_SIDEBAR)
        logo_frame.pack(pady=(S.PAD * 2, S.PAD * 2))

        icon_png = os.path.join(self._assets_dir, "icon.png")
        if os.path.exists(icon_png):
            self._icon_photo = tk.PhotoImage(file=icon_png)
            tk.Label(
                logo_frame, image=self._icon_photo, bg=S.BG_SIDEBAR,
            ).pack(pady=(0, 8))

        tk.Label(
            logo_frame, text="TheFork\nLooker", bg=S.BG_SIDEBAR, fg=S.ACCENT,
            font=S.FONT_TITLE, justify="center",
        ).pack()

        # Nav buttons
        for label, attr_name in self.PAGES:
            btn = tk.Button(
                sidebar, text=f"  {label}", bg=S.BG_SIDEBAR, fg=S.FG,
                font=S.FONT_BODY, relief="flat", anchor="w",
                padx=S.PAD, pady=S.PAD_SMALL,
                activebackground=S.SIDEBAR_ACTIVE_BG, activeforeground=S.FG_BRIGHT,
                cursor="hand2",
                command=lambda name=attr_name: self._show_page(name),
            )
            btn.pack(fill="x")
            self._nav_buttons[attr_name] = btn

            # Hover effect
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=S.SIDEBAR_HOVER_BG))
            btn.bind("<Leave>", lambda e, b=btn, n=attr_name: b.config(
                bg=S.SIDEBAR_ACTIVE_BG if self._current_page == n else S.BG_SIDEBAR
            ))

        # Save button at bottom of sidebar
        sidebar_bottom = tk.Frame(sidebar, bg=S.BG_SIDEBAR)
        sidebar_bottom.pack(side="bottom", fill="x", pady=S.PAD)
        tk.Button(
            sidebar_bottom, text="Save", bg=S.BG_INPUT, fg=S.FG,
            font=S.FONT_SMALL, relief="flat", cursor="hand2",
            command=self._save_with_feedback,
        ).pack(fill="x", padx=S.PAD)
        self._save_label = tk.Label(
            sidebar_bottom, text="", bg=S.BG_SIDEBAR, fg=S.ACCENT_GREEN, font=S.FONT_SMALL,
        )
        self._save_label.pack()

        # Content area
        self._content = tk.Frame(self, bg=S.BG)
        self._content.pack(side="left", fill="both", expand=True)

        # Create all frames
        self.setup_frame = SetupFrame(self._content, self)
        self.server_frame = ServerFrame(self._content, self)
        self.deploy_frame = DeployFrame(self._content, self)
        self.status_frame = StatusFrame(self._content, self)

        self._frames = {
            "setup_frame": self.setup_frame,
            "server_frame": self.server_frame,
            "deploy_frame": self.deploy_frame,
            "status_frame": self.status_frame,
        }

    def _show_page(self, name: str):
        # Hide all frames
        for frame in self._frames.values():
            frame.pack_forget()

        # Show selected
        frame = self._frames[name]
        frame.pack(fill="both", expand=True)
        self._current_page = name

        # Notify frame it's being shown (for auto-refresh)
        if hasattr(frame, "on_show"):
            frame.on_show()

        # Update nav button styles
        for btn_name, btn in self._nav_buttons.items():
            if btn_name == name:
                btn.config(bg=S.SIDEBAR_ACTIVE_BG, fg=S.FG_BRIGHT)
            else:
                btn.config(bg=S.BG_SIDEBAR, fg=S.FG)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self):
        data = settings.load()
        if not data:
            return
        if "setup" in data:
            self.setup_frame.load_data(data["setup"])
        if "server" in data:
            self.server_frame.load_data(data["server"])

    def save_settings(self):
        data = {
            "setup": self.setup_frame.get_data(),
            "server": self.server_frame.get_data(),
        }
        settings.save(data)

    def _save_with_feedback(self):
        self.save_settings()
        self._save_label.config(text="Saved!", fg=S.ACCENT_GREEN)
        self.after(2000, lambda: self._save_label.config(text=""))
