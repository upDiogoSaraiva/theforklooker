"""
Main application controller — sidebar navigation + frame switching.
"""

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

    def __init__(self, parent):
        super().__init__(parent, bg=S.BG)
        self._current_page = None
        self._nav_buttons: dict[str, tk.Button] = {}
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

        # Logo / title
        tk.Label(
            sidebar, text="TheFork\nLooker", bg=S.BG_SIDEBAR, fg=S.ACCENT,
            font=S.FONT_TITLE, justify="center",
        ).pack(pady=(S.PAD * 2, S.PAD * 2))

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
        self._frames[name].pack(fill="both", expand=True)
        self._current_page = name

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
