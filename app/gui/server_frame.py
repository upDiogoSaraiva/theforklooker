"""
Server frame — Oracle VM connection settings.
"""

import threading
import tkinter as tk
from tkinter import filedialog

from app.gui import styles as S
from app.core.ssh_deployer import SSHDeployer


class ServerFrame(tk.Frame):
    """Oracle Cloud VM connection configuration."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=S.BG)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        inner = tk.Frame(self, bg=S.BG)
        inner.pack(fill="both", expand=True, padx=S.PAD, pady=S.PAD)

        # --- ORACLE CLOUD VM ---
        tk.Label(
            inner, text="ORACLE CLOUD VM", bg=S.BG, fg=S.ACCENT_BLUE, font=S.FONT_HEADING,
        ).pack(anchor="w", pady=(0, S.PAD))

        card = tk.Frame(inner, bg=S.BG_CARD, padx=S.PAD, pady=S.PAD)
        card.pack(fill="x")

        # IP Address
        tk.Label(card, text="VM IP Address:", bg=S.BG_CARD, fg=S.FG, font=S.FONT_BODY).pack(anchor="w")
        self.ip_var = tk.StringVar()
        tk.Entry(
            card, textvariable=self.ip_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_MONO, relief="flat", width=S.INPUT_WIDTH,
        ).pack(fill="x", pady=(2, S.PAD_SMALL))

        # Username + Port row
        row = tk.Frame(card, bg=S.BG_CARD)
        row.pack(fill="x", pady=(0, S.PAD_SMALL))

        col_user = tk.Frame(row, bg=S.BG_CARD)
        col_user.pack(side="left", fill="x", expand=True, padx=(0, S.PAD_SMALL))
        tk.Label(col_user, text="SSH Username:", bg=S.BG_CARD, fg=S.FG, font=S.FONT_BODY).pack(anchor="w")
        self.user_var = tk.StringVar(value="ubuntu")
        tk.Entry(
            col_user, textvariable=self.user_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_BODY, relief="flat", width=15,
        ).pack(fill="x", pady=2)

        col_port = tk.Frame(row, bg=S.BG_CARD)
        col_port.pack(side="left")
        tk.Label(col_port, text="SSH Port:", bg=S.BG_CARD, fg=S.FG, font=S.FONT_BODY).pack(anchor="w")
        self.port_var = tk.StringVar(value="22")
        tk.Entry(
            col_port, textvariable=self.port_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_BODY, relief="flat", width=6,
        ).pack(fill="x", pady=2)

        # SSH Key
        tk.Label(card, text="SSH Private Key:", bg=S.BG_CARD, fg=S.FG, font=S.FONT_BODY).pack(anchor="w")
        key_row = tk.Frame(card, bg=S.BG_CARD)
        key_row.pack(fill="x", pady=(2, S.PAD_SMALL))

        self.key_var = tk.StringVar()
        tk.Entry(
            key_row, textvariable=self.key_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_MONO, relief="flat",
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(
            key_row, text="Browse", bg=S.BG_INPUT, fg=S.FG,
            font=S.FONT_SMALL, relief="flat", cursor="hand2",
            command=self._browse_key,
        ).pack(side="right")

        # --- TEST CONNECTION ---
        test_row = tk.Frame(inner, bg=S.BG)
        test_row.pack(fill="x", pady=(S.PAD, 0))

        self.test_btn = tk.Button(
            test_row, text="Test Connection", bg=S.ACCENT_BLUE, fg=S.BG,
            font=S.FONT_BODY, relief="flat", cursor="hand2", padx=16,
            command=self._test_connection,
        )
        self.test_btn.pack(side="left")

        self.test_status = tk.Label(
            test_row, text="Not tested", bg=S.BG, fg=S.FG_DIM, font=S.FONT_BODY,
        )
        self.test_status.pack(side="left", padx=S.PAD)

        # Info box
        info = tk.Frame(inner, bg=S.BG_CARD, padx=S.PAD, pady=S.PAD)
        info.pack(fill="x", pady=(S.PAD, 0))
        tk.Label(
            info,
            text=(
                "Need an Oracle Cloud VM?\n\n"
                "1. Create a free account at cloud.oracle.com\n"
                "2. Launch an Always Free VM (Ubuntu, ARM or AMD)\n"
                "3. Download the SSH private key during creation\n"
                "4. Open port 22 in the VM's security list\n\n"
                "See the README for a detailed setup guide."
            ),
            bg=S.BG_CARD, fg=S.FG_DIM, font=S.FONT_SMALL,
            justify="left", wraplength=500,
        ).pack(anchor="w")

    def _browse_key(self):
        path = filedialog.askopenfilename(
            title="Select SSH Private Key",
            filetypes=[
                ("SSH Keys", "*.pem *.key"),
                ("All Files", "*.*"),
            ],
        )
        if path:
            self.key_var.set(path)

    def _test_connection(self):
        ip = self.ip_var.get().strip()
        user = self.user_var.get().strip()
        key = self.key_var.get().strip()
        port = int(self.port_var.get() or 22)

        if not ip or not key:
            self.test_status.config(text="Fill in IP and key first", fg=S.ACCENT_YELLOW)
            return

        self.test_btn.config(state="disabled")
        self.test_status.config(text="Connecting...", fg=S.ACCENT_YELLOW)

        def _run():
            deployer = SSHDeployer(host=ip, username=user, key_path=key, port=port)
            ok, msg = deployer.test_connection()
            self.after(0, lambda: self._show_test_result(ok, msg))

        threading.Thread(target=_run, daemon=True).start()

    def _show_test_result(self, ok: bool, msg: str):
        self.test_btn.config(state="normal")
        if ok:
            self.test_status.config(text=f"Connected: {msg[:60]}", fg=S.ACCENT_GREEN)
        else:
            self.test_status.config(text=f"Failed: {msg[:80]}", fg=S.ACCENT_RED)

    # ------------------------------------------------------------------
    # Data getters / setters
    # ------------------------------------------------------------------

    def get_data(self) -> dict:
        return {
            "ip": self.ip_var.get().strip(),
            "username": self.user_var.get().strip(),
            "port": self.port_var.get().strip(),
            "key_path": self.key_var.get().strip(),
        }

    def load_data(self, data: dict):
        self.ip_var.set(data.get("ip", ""))
        self.user_var.set(data.get("username", "ubuntu"))
        self.port_var.set(data.get("port", "22"))
        self.key_var.set(data.get("key_path", ""))
