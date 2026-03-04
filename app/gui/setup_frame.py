"""
Setup frame — Restaurant URL, watches, Telegram, check interval.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from app.gui import styles as S
from app.core.url_parser import parse_thefork_input, resolve_uuid_from_numeric_id


class SetupFrame(tk.Frame):
    """Restaurant and watch configuration screen."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=S.BG)
        self.app = app
        self._watches: list[dict] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Scrollable canvas
        canvas = tk.Canvas(self, bg=S.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self._inner = tk.Frame(canvas, bg=S.BG)
        self._inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=S.PAD, pady=S.PAD)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel scrolling
        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        inner = self._inner

        # --- RESTAURANT SECTION ---
        self._section_label(inner, "RESTAURANT")

        row = tk.Frame(inner, bg=S.BG)
        row.pack(fill="x", pady=(0, S.PAD_SMALL))
        tk.Label(row, text="TheFork URL:", bg=S.BG, fg=S.FG, font=S.FONT_BODY).pack(anchor="w")
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(
            row, textvariable=self.url_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_BODY, relief="flat", width=S.INPUT_WIDTH,
        )
        self.url_entry.pack(fill="x", pady=2)
        self.url_var.trace_add("write", self._on_url_change)

        self.url_status = tk.Label(row, text="", bg=S.BG, fg=S.FG_DIM, font=S.FONT_SMALL)
        self.url_status.pack(anchor="w")

        # UUID + Name
        row2 = tk.Frame(inner, bg=S.BG)
        row2.pack(fill="x", pady=(0, S.PAD_SMALL))

        col_uuid = tk.Frame(row2, bg=S.BG)
        col_uuid.pack(side="left", fill="x", expand=True, padx=(0, S.PAD_SMALL))
        tk.Label(col_uuid, text="UUID:", bg=S.BG, fg=S.FG, font=S.FONT_BODY).pack(anchor="w")
        self.uuid_var = tk.StringVar()
        tk.Entry(
            col_uuid, textvariable=self.uuid_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_MONO, relief="flat", width=38,
        ).pack(fill="x", pady=2)

        col_name = tk.Frame(row2, bg=S.BG)
        col_name.pack(side="left", fill="x", expand=True)
        tk.Label(col_name, text="Restaurant Name:", bg=S.BG, fg=S.FG, font=S.FONT_BODY).pack(anchor="w")
        self.name_var = tk.StringVar()
        tk.Entry(
            col_name, textvariable=self.name_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_BODY, relief="flat", width=25,
        ).pack(fill="x", pady=2)

        # --- WATCHES SECTION ---
        self._section_label(inner, "WATCHES")
        self.watches_frame = tk.Frame(inner, bg=S.BG)
        self.watches_frame.pack(fill="x")

        btn_add = tk.Button(
            inner, text="+ Add Watch", bg=S.ACCENT_BLUE, fg=S.BG,
            font=S.FONT_BODY, relief="flat", cursor="hand2",
            command=self._add_watch_ui,
        )
        btn_add.pack(anchor="w", pady=(S.PAD_SMALL, S.PAD))

        # --- NOTIFICATIONS SECTION ---
        self._section_label(inner, "NOTIFICATIONS (optional)")

        tg_frame = tk.Frame(inner, bg=S.BG)
        tg_frame.pack(fill="x", pady=(0, S.PAD_SMALL))

        col_token = tk.Frame(tg_frame, bg=S.BG)
        col_token.pack(side="left", fill="x", expand=True, padx=(0, S.PAD_SMALL))
        tk.Label(col_token, text="Telegram Bot Token:", bg=S.BG, fg=S.FG, font=S.FONT_BODY).pack(anchor="w")
        self.tg_token_var = tk.StringVar()
        tk.Entry(
            col_token, textvariable=self.tg_token_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_MONO, relief="flat", width=35,
        ).pack(fill="x", pady=2)

        col_chat = tk.Frame(tg_frame, bg=S.BG)
        col_chat.pack(side="left", fill="x", expand=True)
        tk.Label(col_chat, text="Telegram Chat ID:", bg=S.BG, fg=S.FG, font=S.FONT_BODY).pack(anchor="w")
        self.tg_chat_var = tk.StringVar()
        tk.Entry(
            col_chat, textvariable=self.tg_chat_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_MONO, relief="flat", width=15,
        ).pack(fill="x", pady=2)

        # --- INTERVAL SECTION ---
        self._section_label(inner, "CHECK INTERVAL")

        int_frame = tk.Frame(inner, bg=S.BG)
        int_frame.pack(fill="x", pady=(0, S.PAD))

        tk.Label(int_frame, text="Every", bg=S.BG, fg=S.FG, font=S.FONT_BODY).pack(side="left")
        self.interval_var = tk.StringVar(value="10")
        tk.Entry(
            int_frame, textvariable=self.interval_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_BODY, relief="flat", width=4,
        ).pack(side="left", padx=4)
        tk.Label(int_frame, text="minutes, offset", bg=S.BG, fg=S.FG, font=S.FONT_BODY).pack(side="left")
        self.offset_var = tk.StringVar(value="1")
        tk.Entry(
            int_frame, textvariable=self.offset_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_BODY, relief="flat", width=4,
        ).pack(side="left", padx=4)
        tk.Label(int_frame, text="min past each window", bg=S.BG, fg=S.FG_DIM, font=S.FONT_SMALL).pack(side="left")

    # ------------------------------------------------------------------
    # Watch management
    # ------------------------------------------------------------------

    def _add_watch_ui(self, data: dict | None = None):
        idx = len(self._watches)
        watch_data = data or {"name": "", "party_size": "6", "meal": "dinner", "dates": "", "priority": ""}
        self._watches.append(watch_data)

        card = tk.Frame(self.watches_frame, bg=S.BG_CARD, padx=S.PAD_SMALL, pady=S.PAD_SMALL)
        card.pack(fill="x", pady=(0, S.PAD_SMALL))
        watch_data["_card"] = card

        # Row 1: name + remove button
        r1 = tk.Frame(card, bg=S.BG_CARD)
        r1.pack(fill="x")
        tk.Label(r1, text="Name:", bg=S.BG_CARD, fg=S.FG_DIM, font=S.FONT_SMALL).pack(side="left")
        name_var = tk.StringVar(value=watch_data["name"])
        watch_data["name_var"] = name_var
        tk.Entry(
            r1, textvariable=name_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_BODY, relief="flat", width=30,
        ).pack(side="left", padx=4, fill="x", expand=True)

        remove_btn = tk.Button(
            r1, text="X", bg=S.ACCENT_RED, fg=S.BG, font=S.FONT_SMALL,
            relief="flat", width=3, cursor="hand2",
            command=lambda c=card, w=watch_data: self._remove_watch(c, w),
        )
        remove_btn.pack(side="right")

        # Row 2: party size + meal
        r2 = tk.Frame(card, bg=S.BG_CARD)
        r2.pack(fill="x", pady=(4, 0))

        tk.Label(r2, text="Party size:", bg=S.BG_CARD, fg=S.FG_DIM, font=S.FONT_SMALL).pack(side="left")
        ps_var = tk.StringVar(value=watch_data["party_size"])
        watch_data["ps_var"] = ps_var
        ps_combo = ttk.Combobox(r2, textvariable=ps_var, values=[str(i) for i in range(1, 21)], width=4, state="readonly")
        ps_combo.pack(side="left", padx=4)

        tk.Label(r2, text="Meal:", bg=S.BG_CARD, fg=S.FG_DIM, font=S.FONT_SMALL).pack(side="left", padx=(12, 0))
        meal_var = tk.StringVar(value=watch_data["meal"])
        watch_data["meal_var"] = meal_var
        meal_combo = ttk.Combobox(r2, textvariable=meal_var, values=["any", "lunch", "dinner"], width=8, state="readonly")
        meal_combo.pack(side="left", padx=4)

        # Row 3: dates
        r3 = tk.Frame(card, bg=S.BG_CARD)
        r3.pack(fill="x", pady=(4, 0))
        tk.Label(r3, text="Dates (YYYY-MM-DD, comma-separated):", bg=S.BG_CARD, fg=S.FG_DIM, font=S.FONT_SMALL).pack(anchor="w")
        dates_var = tk.StringVar(value=watch_data["dates"])
        watch_data["dates_var"] = dates_var
        tk.Entry(
            r3, textvariable=dates_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_MONO, relief="flat",
        ).pack(fill="x", pady=2)

        # Row 4: priority
        r4 = tk.Frame(card, bg=S.BG_CARD)
        r4.pack(fill="x", pady=(4, 0))
        tk.Label(r4, text="Priority dates (optional, comma-separated):", bg=S.BG_CARD, fg=S.FG_DIM, font=S.FONT_SMALL).pack(anchor="w")
        prio_var = tk.StringVar(value=watch_data["priority"])
        watch_data["prio_var"] = prio_var
        tk.Entry(
            r4, textvariable=prio_var, bg=S.BG_INPUT, fg=S.FG,
            insertbackground=S.FG, font=S.FONT_MONO, relief="flat",
        ).pack(fill="x", pady=2)

    def _remove_watch(self, card: tk.Frame, watch_data: dict):
        card.destroy()
        if watch_data in self._watches:
            self._watches.remove(watch_data)

    # ------------------------------------------------------------------
    # URL auto-parsing
    # ------------------------------------------------------------------

    def _on_url_change(self, *_args):
        url = self.url_var.get().strip()
        if not url:
            self.url_status.config(text="", fg=S.FG_DIM)
            return

        parsed = parse_thefork_input(url)

        if parsed["uuid"]:
            self.uuid_var.set(parsed["uuid"])
            self.url_status.config(text=f"UUID found ({parsed['source']})", fg=S.ACCENT_GREEN)
        elif parsed["numeric_id"]:
            self.url_status.config(text=f"Resolving UUID from ID {parsed['numeric_id']}...", fg=S.ACCENT_YELLOW)
            self.after(100, lambda: self._try_resolve(parsed["numeric_id"]))
        else:
            self.url_status.config(text="Could not parse URL — try pasting the widget URL", fg=S.ACCENT_RED)

    def _try_resolve(self, numeric_id: str):
        uuid = resolve_uuid_from_numeric_id(numeric_id)
        if uuid:
            self.uuid_var.set(uuid)
            self.url_status.config(text="UUID resolved from API", fg=S.ACCENT_GREEN)
        else:
            self.url_status.config(
                text="Could not resolve UUID — paste the widget URL or enter UUID manually",
                fg=S.ACCENT_YELLOW,
            )

    # ------------------------------------------------------------------
    # Data getters
    # ------------------------------------------------------------------

    def get_data(self) -> dict:
        """Collect all form data."""
        watches = []
        for w in self._watches:
            dates_raw = w.get("dates_var", tk.StringVar()).get()
            prio_raw = w.get("prio_var", tk.StringVar()).get()
            dates = [d.strip() for d in dates_raw.split(",") if d.strip()]
            prio = [d.strip() for d in prio_raw.split(",") if d.strip()]
            watches.append({
                "name": w.get("name_var", tk.StringVar()).get(),
                "party_size": w.get("ps_var", tk.StringVar()).get(),
                "meal": w.get("meal_var", tk.StringVar()).get(),
                "dates": dates,
                "priority": prio,
            })

        return {
            "url": self.url_var.get(),
            "uuid": self.uuid_var.get(),
            "name": self.name_var.get(),
            "watches": watches,
            "telegram_token": self.tg_token_var.get(),
            "telegram_chat_id": self.tg_chat_var.get(),
            "interval": self.interval_var.get(),
            "offset": self.offset_var.get(),
        }

    def load_data(self, data: dict):
        """Populate form from saved settings."""
        self.url_var.set(data.get("url", ""))
        self.uuid_var.set(data.get("uuid", ""))
        self.name_var.set(data.get("name", ""))
        self.tg_token_var.set(data.get("telegram_token", ""))
        self.tg_chat_var.set(data.get("telegram_chat_id", ""))
        self.interval_var.set(data.get("interval", "10"))
        self.offset_var.set(data.get("offset", "1"))

        for w in data.get("watches", []):
            self._add_watch_ui({
                "name": w.get("name", ""),
                "party_size": str(w.get("party_size", "6")),
                "meal": w.get("meal", "dinner"),
                "dates": ", ".join(w.get("dates", [])),
                "priority": ", ".join(w.get("priority", [])),
            })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _section_label(self, parent, text):
        tk.Label(
            parent, text=text, bg=S.BG, fg=S.ACCENT_BLUE,
            font=S.FONT_HEADING,
        ).pack(anchor="w", pady=(S.PAD, S.PAD_SMALL))
