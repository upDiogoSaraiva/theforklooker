"""
TheFork Looker — Entry point.
"""

import os
import sys
import tkinter as tk


def resource_path(relative: str) -> str:
    """Resolve path for PyInstaller bundled assets."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(__file__), relative)


def main():
    root = tk.Tk()
    root.title("TheFork Looker")
    root.geometry("950x680")
    root.minsize(850, 600)
    root.configure(bg="#1e1e2e")

    # Set icon if available
    try:
        icon_path = resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    # Import here so PyInstaller picks up the dependency chain
    from app.app import App

    app = App(root)
    app.pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
