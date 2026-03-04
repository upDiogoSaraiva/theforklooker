"""
Paramiko-based SSH/SFTP deployment pipeline for Oracle Cloud VM.

Runs in a background thread and emits progress via callbacks.
Each step is idempotent — safe to re-run after partial failure.
"""

import json
import os
import sys
import time
from typing import Callable

import paramiko


def _resource_path(relative: str) -> str:
    """Resolve path to bundled assets (works both dev and PyInstaller)."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.join(os.path.dirname(__file__), "..")
    return os.path.join(base, relative)


MONITOR_SCRIPT_PATH = os.path.join("assets", "thefork_monitor.py")
REMOTE_DIR = "~/thefork-monitor"


class SSHDeployer:
    """Deploy the TheFork monitor to a remote VM."""

    def __init__(
        self,
        host: str,
        username: str,
        key_path: str,
        port: int = 22,
        on_progress: Callable | None = None,
        on_error: Callable | None = None,
        on_complete: Callable | None = None,
    ):
        self.host = host
        self.username = username
        self.key_path = key_path
        self.port = port
        self._on_progress = on_progress or (lambda *a: None)
        self._on_error = on_error or (lambda msg: None)
        self._on_complete = on_complete or (lambda: None)
        self._client: paramiko.SSHClient | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def test_connection(self) -> tuple[bool, str]:
        """Quick SSH connectivity test. Returns (ok, message)."""
        try:
            client = self._make_client()
            client.connect(
                self.host,
                port=self.port,
                username=self.username,
                pkey=self._load_key(),
                timeout=10,
            )
            _, stdout, _ = client.exec_command("echo ok && uname -a")
            output = stdout.read().decode().strip()
            client.close()
            return True, output
        except Exception as e:
            return False, str(e)

    def deploy(self, config_dict: dict) -> None:
        """Full deployment pipeline. Call from a background thread."""
        steps = [
            ("Connecting to VM", self._step_connect),
            ("Installing system packages", self._step_apt),
            ("Installing Chrome browser", self._step_chrome),
            ("Installing Python packages", self._step_pip),
            ("Creating project directory", self._step_mkdir),
            ("Uploading files", lambda: self._step_upload(config_dict)),
            ("Starting monitor", self._step_start),
        ]
        total = len(steps)

        for i, (label, func) in enumerate(steps, 1):
            self._on_progress(i, total, label, "running")
            try:
                func()
                self._on_progress(i, total, label, "ok")
            except Exception as e:
                self._on_progress(i, total, label, "fail")
                self._on_error(f"Step {i} failed: {e}")
                self._cleanup()
                return

        self._cleanup()
        self._on_complete()

    def fetch_logs(self, lines: int = 50) -> str:
        """Fetch recent monitor logs from the VM."""
        try:
            client = self._make_client()
            client.connect(
                self.host,
                port=self.port,
                username=self.username,
                pkey=self._load_key(),
                timeout=10,
            )
            _, stdout, _ = client.exec_command(
                f"tail -{lines} {REMOTE_DIR}/monitor.log 2>/dev/null || echo 'No log file found'"
            )
            output = stdout.read().decode()
            client.close()
            return output
        except Exception as e:
            return f"Error fetching logs: {e}"

    def restart_monitor(self) -> str:
        """Kill and restart the screen session."""
        try:
            client = self._make_client()
            client.connect(
                self.host,
                port=self.port,
                username=self.username,
                pkey=self._load_key(),
                timeout=10,
            )
            self._run_on(client, "screen -S thefork -X quit 2>/dev/null || true")
            time.sleep(1)
            self._run_on(
                client,
                f"screen -dmS thefork bash -c 'cd {REMOTE_DIR} && python3 thefork_monitor.py 2>&1 | tee monitor.log'",
            )
            time.sleep(2)
            _, stdout, _ = client.exec_command("screen -ls | grep thefork")
            result = stdout.read().decode().strip()
            client.close()
            return f"Restarted. {result}" if result else "Warning: screen session may not have started"
        except Exception as e:
            return f"Error: {e}"

    def stop_monitor(self) -> str:
        """Stop the screen session."""
        try:
            client = self._make_client()
            client.connect(
                self.host,
                port=self.port,
                username=self.username,
                pkey=self._load_key(),
                timeout=10,
            )
            self._run_on(client, "screen -S thefork -X quit 2>/dev/null || true")
            client.close()
            return "Monitor stopped."
        except Exception as e:
            return f"Error: {e}"

    # ------------------------------------------------------------------
    # Deployment steps
    # ------------------------------------------------------------------

    def _step_connect(self):
        self._client = self._make_client()
        self._client.connect(
            self.host,
            port=self.port,
            username=self.username,
            pkey=self._load_key(),
            timeout=15,
        )

    def _step_apt(self):
        self._run(
            "sudo apt-get update -qq "
            "&& sudo apt-get install -y -qq python3 python3-pip screen wget curl > /dev/null 2>&1 "
            "&& echo 'APT_OK'",
            timeout=120,
        )

    def _step_chrome(self):
        # Skip if already installed
        _, stdout, _ = self._client.exec_command("which google-chrome 2>/dev/null")
        if stdout.read().strip():
            return
        self._run(
            "wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb "
            "&& sudo dpkg -i google-chrome-stable_current_amd64.deb 2>/dev/null "
            "|| sudo apt-get -f install -y -qq > /dev/null 2>&1 "
            "&& rm -f google-chrome-stable_current_amd64.deb "
            "&& echo 'CHROME_OK'",
            timeout=120,
        )

    def _step_pip(self):
        self._run(
            "pip3 install --break-system-packages requests playwright 2>&1 | tail -3 "
            "&& python3 -m playwright install chromium 2>&1 | tail -3 "
            "&& echo 'PIP_OK'",
            timeout=180,
        )

    def _step_mkdir(self):
        self._run(f"mkdir -p {REMOTE_DIR}")

    def _step_upload(self, config_dict: dict):
        sftp = self._client.open_sftp()
        remote_dir = REMOTE_DIR.replace("~", f"/home/{self.username}")

        # Upload config.json
        config_json = json.dumps(config_dict, indent=4, ensure_ascii=False)
        with sftp.file(f"{remote_dir}/config.json", "w") as f:
            f.write(config_json)

        # Upload monitor script
        monitor_path = _resource_path(MONITOR_SCRIPT_PATH)
        sftp.put(monitor_path, f"{remote_dir}/thefork_monitor.py")

        sftp.close()

    def _step_start(self):
        # Kill existing
        self._run("screen -S thefork -X quit 2>/dev/null || true", check=False)
        time.sleep(1)

        # Start new session
        self._run(
            f"screen -dmS thefork bash -c 'cd {REMOTE_DIR} && python3 thefork_monitor.py 2>&1 | tee monitor.log'"
        )
        time.sleep(3)

        # Verify
        _, stdout, _ = self._client.exec_command("screen -ls | grep thefork")
        if not stdout.read().strip():
            raise RuntimeError("Screen session did not start — check VM logs")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_client(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    def _load_key(self) -> paramiko.PKey:
        """Load SSH private key, trying RSA then Ed25519 then ECDSA."""
        for cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
            try:
                return cls.from_private_key_file(self.key_path)
            except Exception:
                continue
        raise RuntimeError(f"Could not load SSH key: {self.key_path}")

    def _run(self, cmd: str, timeout: int = 60, check: bool = True) -> str:
        """Execute a command on the connected client."""
        _, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        if check and exit_code != 0:
            err = stderr.read().decode()
            raise RuntimeError(f"exit {exit_code}: {err[:500]}")
        return out

    def _run_on(self, client: paramiko.SSHClient, cmd: str, timeout: int = 30) -> str:
        """Execute a command on a specific client instance."""
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        stdout.channel.recv_exit_status()
        return stdout.read().decode()

    def _cleanup(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
