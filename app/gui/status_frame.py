"""
Status frame — View remote logs, restart/stop monitor.
"""

import threading
import tkinter as tk
from tkinter import scrolledtext

from app.gui import styles as S
from app.core.ssh_deployer import SSHDeployer


class StatusFrame(tk.Frame):
    """Post-deployment monitor management screen."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=S.BG)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        inner = tk.Frame(self, bg=S.BG)
        inner.pack(fill="both", expand=True, padx=S.PAD, pady=S.PAD)

        tk.Label(
            inner, text="MONITOR STATUS", bg=S.BG, fg=S.ACCENT_BLUE, font=S.FONT_HEADING,
        ).pack(anchor="w", pady=(0, S.PAD))

        # Buttons
        btn_row = tk.Frame(inner, bg=S.BG)
        btn_row.pack(fill="x", pady=(0, S.PAD))

        self.refresh_btn = tk.Button(
            btn_row, text="Refresh Logs", bg=S.ACCENT_BLUE, fg=S.BG,
            font=S.FONT_BODY, relief="flat", cursor="hand2", padx=12,
            command=self._refresh_logs,
        )
        self.refresh_btn.pack(side="left", padx=(0, S.PAD_SMALL))

        self.restart_btn = tk.Button(
            btn_row, text="Restart Monitor", bg=S.ACCENT_YELLOW, fg=S.BG,
            font=S.FONT_BODY, relief="flat", cursor="hand2", padx=12,
            command=self._restart_monitor,
        )
        self.restart_btn.pack(side="left", padx=(0, S.PAD_SMALL))

        self.stop_btn = tk.Button(
            btn_row, text="Stop Monitor", bg=S.ACCENT_RED, fg=S.BG,
            font=S.FONT_BODY, relief="flat", cursor="hand2", padx=12,
            command=self._stop_monitor,
        )
        self.stop_btn.pack(side="left")

        self.status_label = tk.Label(
            inner, text="", bg=S.BG, fg=S.FG_DIM, font=S.FONT_SMALL,
        )
        self.status_label.pack(anchor="w", pady=(0, S.PAD_SMALL))

        # Log viewer
        tk.Label(
            inner, text="REMOTE LOGS", bg=S.BG, fg=S.FG_DIM, font=S.FONT_SMALL,
        ).pack(anchor="w", pady=(0, 4))

        self.log_text = scrolledtext.ScrolledText(
            inner, bg=S.BG_CARD, fg=S.FG, font=S.FONT_MONO,
            relief="flat", height=20, state="disabled",
            insertbackground=S.FG, selectbackground=S.ACCENT_BLUE,
        )
        self.log_text.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _get_deployer(self) -> SSHDeployer | None:
        server = self.app.server_frame.get_data()
        if not server.get("ip") or not server.get("key_path"):
            self.status_label.config(text="Set VM details in Server tab first", fg=S.ACCENT_YELLOW)
            return None
        return SSHDeployer(
            host=server["ip"],
            username=server.get("username", "ubuntu"),
            key_path=server["key_path"],
            port=int(server.get("port", 22)),
        )

    def _refresh_logs(self):
        deployer = self._get_deployer()
        if not deployer:
            return

        self.refresh_btn.config(state="disabled")
        self.status_label.config(text="Fetching logs...", fg=S.ACCENT_YELLOW)

        def _run():
            logs = deployer.fetch_logs(lines=50)
            self.after(0, lambda: self._show_logs(logs))

        threading.Thread(target=_run, daemon=True).start()

    def _show_logs(self, logs: str):
        self.refresh_btn.config(state="normal")
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", logs)
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.status_label.config(text="Logs refreshed", fg=S.ACCENT_GREEN)

    def _restart_monitor(self):
        deployer = self._get_deployer()
        if not deployer:
            return

        self.restart_btn.config(state="disabled")
        self.status_label.config(text="Restarting monitor...", fg=S.ACCENT_YELLOW)

        def _run():
            result = deployer.restart_monitor()
            self.after(0, lambda: self._show_action_result(result, self.restart_btn))

        threading.Thread(target=_run, daemon=True).start()

    def _stop_monitor(self):
        deployer = self._get_deployer()
        if not deployer:
            return

        self.stop_btn.config(state="disabled")
        self.status_label.config(text="Stopping monitor...", fg=S.ACCENT_YELLOW)

        def _run():
            result = deployer.stop_monitor()
            self.after(0, lambda: self._show_action_result(result, self.stop_btn))

        threading.Thread(target=_run, daemon=True).start()

    def _show_action_result(self, msg: str, btn: tk.Button):
        btn.config(state="normal")
        is_error = msg.lower().startswith("error")
        self.status_label.config(
            text=msg[:100],
            fg=S.ACCENT_RED if is_error else S.ACCENT_GREEN,
        )
