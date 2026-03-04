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

    # Set window icon (title bar + taskbar)
    icon_ico = resource_path(os.path.join("assets", "icon.ico"))
    try:
        if os.path.exists(icon_ico):
            root.iconbitmap(default=icon_ico)
    except Exception:
        pass

    # Apply modern dark theme to ttk widgets
    from app.gui.styles import apply_theme
    apply_theme(root)

    # Import here so PyInstaller picks up the dependency chain
    from app.app import App

    # Pass the assets path so App can load the PNG icon for the sidebar
    assets_dir = resource_path("assets")
    app = App(root, assets_dir=assets_dir)
    app.pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
