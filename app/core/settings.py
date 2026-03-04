"""
Persist and restore GUI form state across sessions.

Saves to  ~/.theforklooker/settings.json
"""

import json
import os
from pathlib import Path

_DIR = Path.home() / ".theforklooker"
_FILE = _DIR / "settings.json"


def save(data: dict) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load() -> dict:
    if _FILE.exists():
        try:
            with open(_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}
