"""
TheFork URL parsing and UUID resolution.

Accepts three input formats:
  1. Restaurant page URL:  https://www.thefork.com/restaurant/o-velho-eurico-r770451
  2. Widget URL:           https://widget.thefork.com/en/999d3391-...-4090?step=date
  3. Bare UUID:            999d3391-000e-42f1-b7bf-ce987f2f4090
"""

import re
from urllib.parse import urlparse

UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I
)
SLUG_RE = re.compile(r"/restaurant/([^/?#]+-r(\d+))")
WIDGET_RE = re.compile(r"widget\.thefork\.com/\w+/([0-9a-f-]{36})")


def parse_thefork_input(user_input: str) -> dict:
    """Parse user input and extract restaurant identifiers.

    Returns dict with keys:
        uuid         – str | None  (direct UUID if found)
        numeric_id   – str | None  (numeric ID from slug, e.g. "770451")
        slug         – str | None  (full slug, e.g. "o-velho-eurico-r770451")
        source       – str         ("widget_url", "thefork_url", "uuid", "unknown")
    """
    text = user_input.strip()
    if not text:
        return _empty("unknown")

    # 1. Widget URL with UUID
    widget_match = WIDGET_RE.search(text)
    if widget_match:
        return {
            "uuid": widget_match.group(1),
            "numeric_id": None,
            "slug": None,
            "source": "widget_url",
        }

    # 2. Bare UUID
    if UUID_RE.fullmatch(text):
        return {
            "uuid": text.lower(),
            "numeric_id": None,
            "slug": None,
            "source": "uuid",
        }

    # 3. TheFork restaurant URL  (…/restaurant/slug-rNNNNN)
    slug_match = SLUG_RE.search(text)
    if slug_match:
        slug_full = slug_match.group(1)
        numeric_id = slug_match.group(2)
        return {
            "uuid": None,
            "numeric_id": numeric_id,
            "slug": slug_full,
            "source": "thefork_url",
        }

    # 4. Maybe just a numeric ID?
    if text.isdigit():
        return {
            "uuid": None,
            "numeric_id": text,
            "slug": None,
            "source": "numeric_id",
        }

    return _empty("unknown")


def resolve_uuid_from_numeric_id(numeric_id: str) -> str | None:
    """Try to resolve UUID from TheFork numeric restaurant ID.

    Attempts a lightweight API call. Returns None on failure.
    """
    try:
        import urllib.request
        import json

        url = f"https://api.thefork.com/restaurants/{numeric_id}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            uuid = data.get("uuid") or data.get("id_restaurant_uuid")
            if uuid and UUID_RE.match(uuid):
                return uuid
    except Exception:
        pass
    return None


def _empty(source: str) -> dict:
    return {"uuid": None, "numeric_id": None, "slug": None, "source": source}
