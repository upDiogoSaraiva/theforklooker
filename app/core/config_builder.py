"""
Builds the config.json dict that thefork_monitor.py expects.
"""


def build_config(
    restaurant_uuid: str,
    restaurant_name: str,
    watches: list[dict],
    telegram_token: str = "",
    telegram_chat_id: str = "",
    check_interval: int = 10,
    schedule_offset: int = 1,
) -> dict:
    """Build config dict matching thefork_monitor.py format.

    Each watch in *watches* should have:
        name       – str
        party_size – int
        meal       – "lunch" | "dinner" | "any"
        dates      – list[str]  (YYYY-MM-DD)
        priority   – list[str]  (optional)
    """
    cfg: dict = {}

    if telegram_token and telegram_chat_id:
        cfg["telegram_bot_token"] = telegram_token
        cfg["telegram_chat_id"] = telegram_chat_id

    cfg["restaurant"] = {
        "uuid": restaurant_uuid,
        "name": restaurant_name,
    }

    cfg["check_interval_minutes"] = check_interval
    cfg["schedule_offset_minutes"] = schedule_offset

    cfg["watches"] = []
    for w in watches:
        entry: dict = {
            "name": w["name"],
            "party_size": int(w["party_size"]),
            "meal": w.get("meal", "any"),
            "dates": sorted(w["dates"]),
        }
        if w.get("priority"):
            entry["priority"] = sorted(w["priority"])
        cfg["watches"].append(entry)

    return cfg
