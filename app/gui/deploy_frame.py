"""
Deploy frame — Summary, deploy button, real-time progress log.
"""

import json
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from app.gui import styles as S
from app.core.config_builder import build_config
from app.core.ssh_deployer import SSHDeployer


class DeployFrame(tk.Frame):
    """Deployment screen with progress log."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=S.BG)
        self.app = app
        self._queue: queue.Queue = queue.Queue()
        self._build_ui()

    def _build_ui(self):
        inner = tk.Frame(self, bg=S.BG)
        inner.pack(fill="both", expand=True, padx=S.PAD, pady=S.PAD)

        # --- SUMMARY ---
        tk.Label(
            inner, text="DEPLOYMENT", bg=S.BG, fg=S.ACCENT_BLUE, font=S.FONT_HEADING,
        ).pack(anchor="w", pady=(0, S.PAD_SMALL))

        self.summary_frame = tk.Frame(inner, bg=S.BG_CARD, padx=S.PAD, pady=S.PAD_SMALL)
        self.summary_frame.pack(fill="x")
        self.summary_label = tk.Label(
            self.summary_frame, text="Click 'Refresh Summary' after filling in Setup and Server tabs.",
            bg=S.BG_CARD, fg=S.FG_DIM, font=S.FONT_BODY, justify="left", anchor="w",
        )
        self.summary_label.pack(fill="x")

        # Buttons row
        btn_row = tk.Frame(inner, bg=S.BG)
        btn_row.pack(fill="x", pady=(S.PAD, 0))

        tk.Button(
            btn_row, text="Refresh Summary", bg=S.BG_INPUT, fg=S.FG,
            font=S.FONT_BODY, relief="flat", cursor="hand2", padx=12,
            command=self._refresh_summary,
        ).pack(side="left", padx=(0, S.PAD_SMALL))

        self.deploy_btn = tk.Button(
            btn_row, text="Deploy to VM", bg=S.ACCENT_GREEN, fg=S.BG,
            font=S.FONT_HEADING, relief="flat", cursor="hand2", padx=20,
            command=self._start_deploy,
        )
        self.deploy_btn.pack(side="left")

        # --- PROGRESS LOG ---
        tk.Label(
            inner, text="PROGRESS LOG", bg=S.BG, fg=S.ACCENT_BLUE, font=S.FONT_HEADING,
        ).pack(anchor="w", pady=(S.PAD, S.PAD_SMALL))

        self.log_text = scrolledtext.ScrolledText(
            inner, bg=S.BG_CARD, fg=S.FG, font=S.FONT_MONO,
            relief="flat", height=16, state="disabled",
            insertbackground=S.FG, selectbackground=S.ACCENT_BLUE,
        )
        self.log_text.pack(fill="both", expand=True)

        # Configure tags for colored output
        self.log_text.tag_config("ok", foreground=S.ACCENT_GREEN)
        self.log_text.tag_config("fail", foreground=S.ACCENT_RED)
        self.log_text.tag_config("running", foreground=S.ACCENT_YELLOW)
        self.log_text.tag_config("info", foreground=S.ACCENT_BLUE)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _refresh_summary(self):
        setup = self.app.setup_frame.get_data()
        server = self.app.server_frame.get_data()

        lines = []
        lines.append(f"Restaurant:  {setup.get('name', '?')}  ({setup.get('uuid', '?')[:20]}...)")
        lines.append(f"Watches:     {len(setup.get('watches', []))}")
        lines.append(f"Interval:    {setup.get('interval', '?')} min (offset {setup.get('offset', '?')})")
        lines.append(f"VM:          {server.get('ip', '?')} ({server.get('username', '?')})")
        tg = "ON" if setup.get("telegram_token") else "OFF"
        lines.append(f"Telegram:    {tg}")

        self.summary_label.config(text="\n".join(lines), fg=S.FG)

    # ------------------------------------------------------------------
    # Deploy
    # ------------------------------------------------------------------

    def on_show(self):
        """Called when this tab becomes visible — auto-refresh the summary."""
        self._refresh_summary()

    def _start_deploy(self):
        setup = self.app.setup_frame.get_data()
        server = self.app.server_frame.get_data()

        # Validate
        if not setup.get("uuid"):
            self._log("ERROR: No restaurant UUID set. Go to Setup tab.\n", "fail")
            return
        if not setup.get("watches"):
            self._log("ERROR: No watches defined. Go to Setup tab.\n", "fail")
            return
        if not server.get("ip") or not server.get("key_path"):
            self._log("ERROR: VM IP or SSH key missing. Go to Server tab.\n", "fail")
            return

        # Confirm
        if not messagebox.askyesno(
            "Confirm Deploy",
            "This will restart the monitor on the VM.\n\nContinue?",
        ):
            return

        # Build config
        config_dict = build_config(
            restaurant_uuid=setup["uuid"],
            restaurant_name=setup.get("name", ""),
            watches=setup["watches"],
            telegram_token=setup.get("telegram_token", ""),
            telegram_chat_id=setup.get("telegram_chat_id", ""),
            check_interval=int(setup.get("interval", 10)),
            schedule_offset=int(setup.get("offset", 1)),
        )

        self._log_clear()
        self._log("Config built. Starting deployment...\n\n", "info")
        self.deploy_btn.config(state="disabled")

        deployer = SSHDeployer(
            host=server["ip"],
            username=server.get("username", "ubuntu"),
            key_path=server["key_path"],
            port=int(server.get("port", 22)),
            on_progress=lambda *a: self._queue.put(("progress", a)),
            on_error=lambda msg: self._queue.put(("error", msg)),
            on_complete=lambda: self._queue.put(("done", None)),
        )

        threading.Thread(
            target=deployer.deploy, args=(config_dict,), daemon=True,
        ).start()
        self._poll_queue()

        # Save settings on deploy
        self.app.save_settings()

    def _poll_queue(self):
        try:
            while True:
                msg_type, data = self._queue.get_nowait()
                if msg_type == "progress":
                    step, total, label, status = data
                    icon = {"running": "...", "ok": " OK", "fail": "FAIL"}[status]
                    tag = status
                    line = f"[{step}/{total}] {label}... [{icon}]\n"
                    self._log(line, tag)
                elif msg_type == "error":
                    self._log(f"\nERROR: {data}\n", "fail")
                    self.deploy_btn.config(state="normal")
                    return
                elif msg_type == "done":
                    self._log("\nDEPLOYED SUCCESSFULLY\n", "ok")
                    self._log("Monitor is running. Check Status tab for logs.\n", "info")
                    self.deploy_btn.config(state="normal")
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _log(self, text: str, tag: str = ""):
        self.log_text.config(state="normal")
        if tag:
            self.log_text.insert("end", text, tag)
        else:
            self.log_text.insert("end", text)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _log_clear(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
