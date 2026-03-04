"""
TheFork Monitor
===============
Config-driven restaurant availability monitor for TheFork.
Supports multiple watches with different party sizes, meals, and date filters.
Sends alerts via desktop notification and Telegram.

Usage:
    python thefork_monitor.py               # continuous monitoring
    python thefork_monitor.py --once        # single check
    python thefork_monitor.py --verbose     # debug logging

Configuration: config.json (see README.md)
"""

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import date, datetime, timedelta

import requests as http_requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("thefork")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRAPHQL_QUERY = """
query GetAvailabilities($restaurantUuid: ID!, $startDate: String!, $endDate: String!, $partySize: Int, $includeWaitingList: Boolean, $timeslot: Int, $offerUuid: ID) {
  availabilities(
    restaurantUuid: $restaurantUuid
    startDate: $startDate
    endDate: $endDate
    partySize: $partySize
    includeWaitingList: $includeWaitingList
    timeslot: $timeslot
    offerUuid: $offerUuid
  ) {
    date
    hasNormalStock
    offerList
    __typename
  }
}
"""

STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    window.chrome = { runtime: {} };
    const origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (params) =>
        params.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : origQuery(params);
}
"""

JS_FETCH = """
async (payload) => {
    const r = await fetch("/api/graphql", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Apollographql-Client-Name": "widget-front-browser",
            "X-App-Name": "widget-front-browser",
        },
        body: JSON.stringify(payload),
    });
    if (!r.ok) return { status: r.status, body: null };
    return { status: r.status, body: await r.json() };
}
"""

WEEKDAY_NAMES = {
    0: "Segunda", 1: "Terca", 2: "Quarta", 3: "Quinta",
    4: "Sexta", 5: "Sabado", 6: "Domingo",
}

MEAL_LABELS = {"lunch": "almoco", "dinner": "jantar", "any": ""}

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def load_config() -> dict:
    cfg_path = os.path.join(_script_dir(), "config.json")
    if not os.path.exists(cfg_path):
        log.error("config.json not found in %s", _script_dir())
        sys.exit(1)
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Validate essentials
    if "restaurant" not in cfg:
        log.error("config.json missing 'restaurant' section")
        sys.exit(1)
    if not cfg.get("watches"):
        log.error("config.json has no watches defined")
        sys.exit(1)

    return cfg

# ---------------------------------------------------------------------------
# Alerted state (avoid duplicate alerts)
# ---------------------------------------------------------------------------

def _alerted_path():
    return os.path.join(_script_dir(), ".alerted.json")


def load_alerted() -> dict:
    """Load {watch_name: [date, ...]} of already-alerted combos."""
    path = _alerted_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_alerted(alerted: dict):
    with open(_alerted_path(), "w") as f:
        json.dump(alerted, f, indent=2)


def mark_alerted(alerted: dict, watch_name: str, dates: list[str]):
    existing = set(alerted.get(watch_name, []))
    existing.update(dates)
    alerted[watch_name] = sorted(existing)

# ---------------------------------------------------------------------------
# GraphQL helpers
# ---------------------------------------------------------------------------

def _build_payload(restaurant_uuid: str, party_size: int, start_date: str, end_date: str):
    return [{
        "operationName": "GetAvailabilities",
        "query": GRAPHQL_QUERY,
        "variables": {
            "restaurantUuid": restaurant_uuid,
            "startDate": start_date,
            "endDate": end_date,
            "partySize": party_size,
            "includeWaitingList": True,
        },
    }]


def _parse_response(result) -> list | None:
    if result["status"] != 200 or not result["body"]:
        return None
    body = result["body"]
    if isinstance(body, list) and body:
        return body[0].get("data", {}).get("availabilities", [])
    if isinstance(body, dict):
        return body.get("data", {}).get("availabilities", [])
    return []

# ---------------------------------------------------------------------------
# Fetcher — Playwright with stealth
# ---------------------------------------------------------------------------

_headed_mode = False  # set via --headed flag


def fetch_all_party_sizes(restaurant_uuid: str, party_sizes: set[int]) -> dict[int, list]:
    """Fetch availability for each party size using one Playwright session.

    Returns {party_size: [availability_entries]} or empty dict on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright not installed. Run: pip install playwright && python -m playwright install chromium")
        return {}

    today = date.today()
    start = today.strftime("%Y-%m-%d")
    end = (today + timedelta(days=120)).strftime("%Y-%m-%d")
    results: dict[int, list] = {}

    widget_url = f"https://widget.thefork.com/en/{restaurant_uuid}?step=date"

    with sync_playwright() as p:
        # headless=True works on clean IPs (e.g., VM).
        # Use --headed locally if DataDome detects headless mode.
        browser = p.chromium.launch(
            headless=not _headed_mode,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-gpu",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
            locale="en-US",
        )
        context.add_init_script(STEALTH_JS)
        page = context.new_page()

        try:
            # Load page and handle DataDome CAPTCHA with retries
            for attempt in range(3):
                log.info("Loading widget page (attempt %d/3)...", attempt + 1)
                page.goto(widget_url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(3000)

                captcha_frames = [f for f in page.frames if "captcha" in f.url.lower()]
                if not captcha_frames:
                    log.info("Page loaded — no CAPTCHA")
                    break

                log.warning("DataDome CAPTCHA detected — waiting 20s for auto-resolve...")
                page.wait_for_timeout(20000)
                captcha_frames = [f for f in page.frames if "captcha" in f.url.lower()]
                if not captcha_frames:
                    log.info("CAPTCHA resolved")
                    break

                if attempt < 2:
                    log.info("CAPTCHA persists — reloading page...")
                    page.wait_for_timeout(5000)
                else:
                    log.warning("CAPTCHA not resolved after 3 attempts — trying fetch anyway")

            for ps in sorted(party_sizes):
                payload = _build_payload(restaurant_uuid, ps, start, end)
                log.debug("Fetching party_size=%d (%s to %s)...", ps, start, end)

                try:
                    result = page.evaluate(JS_FETCH, payload)
                    avails = _parse_response(result)
                    if avails is not None:
                        results[ps] = avails
                        stock = [a["date"] for a in avails if a.get("hasNormalStock")]
                        log.info("  party_size=%d: %d dates returned, %d with stock", ps, len(avails), len(stock))
                    else:
                        log.warning("  party_size=%d: HTTP %s", ps, result.get("status", "?"))
                        results[ps] = []
                except Exception as e:
                    log.error("  party_size=%d: fetch error — %s", ps, e)
                    results[ps] = []

                # Delay between calls to avoid rate limiting
                if ps != max(party_sizes):
                    time.sleep(4)

        except Exception as e:
            log.error("Playwright session error: %s", e)
        finally:
            browser.close()

    return results

# ---------------------------------------------------------------------------
# Watch evaluation
# ---------------------------------------------------------------------------

def evaluate_watch(watch: dict, availabilities: list) -> list[dict]:
    """Check a watch against availability data.

    Returns list of hits: [{"date": "2026-...", "label": "...", "priority": bool}]
    """
    stock_dates = {a["date"] for a in availabilities if a.get("hasNormalStock")}
    if not stock_dates:
        return []

    hits = []
    target_dates = set()

    if "dates" in watch:
        # Explicit date list
        target_dates = set(watch["dates"])
    elif "weekdays" in watch:
        # Filter by weekday — check all stock dates
        target_weekdays = set(watch["weekdays"])
        for d_str in stock_dates:
            try:
                d = date.fromisoformat(d_str)
                if d.weekday() in target_weekdays:
                    target_dates.add(d_str)
            except ValueError:
                continue

    priority_set = set(watch.get("priority", []))
    meal = watch.get("meal", "any")
    meal_label = MEAL_LABELS.get(meal, meal)
    ps = watch["party_size"]

    for d_str in sorted(target_dates):
        if d_str not in stock_dates:
            continue
        try:
            d = date.fromisoformat(d_str)
        except ValueError:
            continue
        day_name = WEEKDAY_NAMES.get(d.weekday(), "?")
        label = f"{d_str} ({day_name}) — {meal_label} p/{ps}" if meal_label else f"{d_str} ({day_name}) — p/{ps}"
        hits.append({
            "date": d_str,
            "label": label,
            "priority": d_str in priority_set,
        })

    return hits

# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def notify_desktop(title: str, message: str):
    try:
        from plyer import notification
        notification.notify(title=title, message=message[:256], timeout=30)
        log.info("Desktop notification sent")
    except Exception as e:
        log.warning("Desktop notification failed: %s", e)


def notify_telegram(token: str, chat_id: str, message: str):
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        http_requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        log.info("Telegram notification sent")
    except Exception as e:
        log.warning("Telegram failed: %s", e)


def send_alerts(cfg: dict, watch_hits: list[tuple[dict, list[dict]]]):
    """Send alerts for all triggered watches."""
    restaurant = cfg["restaurant"]
    name = restaurant["name"]
    uuid = restaurant["uuid"]
    booking_url = f"https://widget.thefork.com/en/{uuid}?step=date"
    token = cfg.get("telegram_bot_token", "")
    chat_id = cfg.get("telegram_chat_id", "")

    for watch, hits in watch_hits:
        priority_hits = [h for h in hits if h["priority"]]
        normal_hits = [h for h in hits if not h["priority"]]
        all_hits = priority_hits + normal_hits

        # Console
        lines = [
            f"VAGA ENCONTRADA — {name}",
            f"  [{watch['name']}]",
            "",
        ]
        for h in all_hits:
            marker = " ⭐" if h["priority"] else ""
            lines.append(f"  >> {h['label']}{marker}")
        lines.append("")
        lines.append(f"  Reservar: {booking_url}")

        print()
        print("!" * 60)
        print("\n".join(lines))
        print("!" * 60)
        print()

        # Desktop
        notify_desktop(
            f"{name} — VAGA!",
            f"[{watch['name']}] {len(all_hits)} data(s) disponivel(is)!",
        )

        # Telegram
        tg_lines = [
            f"<b>{name} — VAGA!</b>",
            f"<i>{watch['name']}</i>",
            "",
        ]
        for h in all_hits:
            marker = " ⭐" if h["priority"] else ""
            tg_lines.append(f">> {h['label']}{marker}")
        tg_lines.append("")
        tg_lines.append(f"<a href='{booking_url}'>RESERVAR AGORA</a>")
        notify_telegram(token, chat_id, "\n".join(tg_lines))

# ---------------------------------------------------------------------------
# Main check
# ---------------------------------------------------------------------------

def run_once(cfg: dict) -> bool:
    """Run one check cycle. Returns True if any watch triggered."""
    log.info("=" * 50)
    log.info("Running availability check...")

    restaurant = cfg["restaurant"]
    watches = cfg["watches"]

    # Collect unique party sizes needed
    party_sizes = {w["party_size"] for w in watches}
    log.info("Party sizes to query: %s", sorted(party_sizes))

    # Fetch all
    avail_map = fetch_all_party_sizes(restaurant["uuid"], party_sizes)

    if not avail_map:
        log.error("Failed to fetch any data")
        return False

    # Load alert state
    alerted = load_alerted()

    # Evaluate each watch
    triggered: list[tuple[dict, list[dict]]] = []

    for watch in watches:
        ps = watch["party_size"]
        avails = avail_map.get(ps, [])
        hits = evaluate_watch(watch, avails)

        if not hits:
            log.info("  [%s] — no availability", watch["name"])
            continue

        # Filter out already-alerted dates
        already = set(alerted.get(watch["name"], []))
        new_hits = [h for h in hits if h["date"] not in already]

        if not new_hits:
            log.info("  [%s] — %d hit(s) but already alerted", watch["name"], len(hits))
            continue

        log.info("  [%s] — %d NEW hit(s)!", watch["name"], len(new_hits))
        triggered.append((watch, new_hits))

        # Mark as alerted
        mark_alerted(alerted, watch["name"], [h["date"] for h in new_hits])

    # Send alerts
    if triggered:
        send_alerts(cfg, triggered)
        save_alerted(alerted)
        return True

    # Log summary of available dates for context
    for ps, avails in sorted(avail_map.items()):
        stock = [a["date"] for a in avails if a.get("hasNormalStock")]
        if stock:
            log.info("  Available dates for %d people: %s", ps, ", ".join(stock[:8]))
        else:
            log.info("  No availability for %d people in current window", ps)

    save_alerted(alerted)
    return False

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="TheFork availability monitor")
    parser.add_argument("--once", action="store_true", help="Single check and exit")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    parser.add_argument("--headed", action="store_true", help="Run Chrome in headed mode (for local testing)")
    parser.add_argument("--reset-alerts", action="store_true", help="Clear alerted state and exit")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    global _headed_mode
    _headed_mode = args.headed

    cfg = load_config()

    if args.reset_alerts:
        path = _alerted_path()
        if os.path.exists(path):
            os.remove(path)
            log.info("Cleared alerted state")
        else:
            log.info("No alerted state to clear")
        return

    restaurant = cfg["restaurant"]
    interval = cfg.get("check_interval_minutes", 20)
    token = cfg.get("telegram_bot_token", "")

    log.info("TheFork Monitor — %s", restaurant["name"])
    log.info("Watches: %d | Interval: %d min | Telegram: %s",
             len(cfg["watches"]), interval, "ON" if token else "OFF")
    for w in cfg["watches"]:
        dates_info = f"dates={w['dates']}" if "dates" in w else f"weekdays={w.get('weekdays', [])}"
        log.info("  • %s (p/%d, %s, %s)", w["name"], w["party_size"], w.get("meal", "any"), dates_info)

    if args.once:
        found = run_once(cfg)
        sys.exit(0 if found else 1)

    offset_minutes = cfg.get("schedule_offset_minutes", 1)
    interval_secs = interval * 60
    log.info("Continuous monitoring every %d min at :%02d past each window (Ctrl+C to stop)",
             interval, offset_minutes)

    while True:
        try:
            run_once(cfg)
        except KeyboardInterrupt:
            log.info("Stopped by user")
            break
        except Exception as e:
            log.error("Unexpected error: %s", e, exc_info=True)

        # Clock-aligned scheduling: sleep until the next :01, :11, :21, etc.
        now = datetime.now()
        minutes_since_offset = (now.minute - offset_minutes) % interval
        minutes_until_next = interval - minutes_since_offset
        wake = now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_until_next)
        if wake <= now:
            wake += timedelta(minutes=interval)
        sleep_secs = (wake - now).total_seconds()
        log.info("Next check at %s (%.0fs)", wake.strftime("%H:%M:%S"), sleep_secs)

        try:
            time.sleep(sleep_secs)
        except KeyboardInterrupt:
            log.info("Stopped by user")
            break


if __name__ == "__main__":
    main()
