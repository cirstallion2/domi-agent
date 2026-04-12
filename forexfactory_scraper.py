"""
DOMI -- Layer 1: Perception (Macro News Filter)
forexfactory_scraper.py

Scrapes ForexFactory economic calendar for High-impact events.
DOMI uses this to KILL or FLAG signals that are near news events.

Logic:
  - If a High-impact event is within the next 30 minutes: KILL signal
  - If a High-impact event occurred in the last 15 minutes: FLAG signal
  - Otherwise: signal passes through clean

No API key needed -- uses public calendar RSS/HTML.
"""

import requests
import json
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET


FF_RSS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

IMPACT_RANK = {"High": 3, "Medium": 2, "Low": 1, "Holiday": 0}


def fetch_forexfactory_events(cfg: dict) -> list[dict]:
    """
    Fetch this week's ForexFactory events from their public JSON feed.
    Returns list of dicts with: title, country, date, impact, forecast, previous
    Filters to High-impact only by default.
    """
    ff_cfg = cfg.get("forexfactory", {})
    if not ff_cfg.get("enabled", True):
        return []

    impact_filter = set(ff_cfg.get("impact_filter", ["High"]))
    currency_filter = set(ff_cfg.get("currencies", ["USD", "EUR", "JPY", "XAU"]))

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; DOMI-Agent/1.0)"
        }
        resp = requests.get(FF_RSS_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        events_raw = resp.json()

        filtered = []
        for ev in events_raw:
            impact  = ev.get("impact", "")
            country = ev.get("country", "")

            if impact not in impact_filter:
                continue
            if currency_filter and country not in currency_filter:
                continue

            # Parse datetime -- FF uses format: "01-13-2026T08:30:00-0500"
            date_str = ev.get("date", "")
            try:
                dt = datetime.strptime(date_str, "%m-%d-%YT%H:%M:%S%z")
                dt_utc = dt.astimezone(timezone.utc)
            except Exception:
                dt_utc = None

            filtered.append({
                "title":    ev.get("title", ""),
                "country":  country,
                "impact":   impact,
                "datetime": dt_utc,
                "forecast": ev.get("forecast", ""),
                "previous": ev.get("previous", ""),
            })

        print(f"[FOREXFACTORY] {len(filtered)} high-impact events this week")
        return filtered

    except Exception as e:
        print(f"[FOREXFACTORY ERROR] {e}")
        return []


def check_news_window(events: list[dict], cfg: dict) -> dict:
    """
    Check if current time is in a danger window around any High-impact event.

    Returns:
      {
        "kill":   bool,   -- True = kill all signals now
        "flag":   bool,   -- True = warn but allow (event just passed)
        "reason": str,    -- Human readable reason
        "events": list    -- Upcoming events in window
      }
    """
    ff_cfg = cfg.get("forexfactory", {})
    buffer_min = ff_cfg.get("pre_event_buffer_minutes", 30)
    kill_on_high = ff_cfg.get("kill_signal_on_high_impact", True)

    now = datetime.now(timezone.utc)
    upcoming = []
    recent   = []

    for ev in events:
        dt = ev.get("datetime")
        if dt is None:
            continue

        delta = (dt - now).total_seconds() / 60   # minutes until event

        if 0 < delta <= buffer_min:
            upcoming.append({**ev, "minutes_away": round(delta, 1)})
        elif -15 <= delta <= 0:
            recent.append({**ev, "minutes_ago": round(abs(delta), 1)})

    if upcoming and kill_on_high:
        names = ", ".join([f"{e['country']} {e['title']} ({e['minutes_away']}m)" for e in upcoming])
        return {
            "kill":   True,
            "flag":   False,
            "reason": f"HIGH IMPACT EVENT APPROACHING: {names}",
            "events": upcoming,
        }

    if recent:
        names = ", ".join([f"{e['country']} {e['title']} ({e['minutes_ago']}m ago)" for e in recent])
        return {
            "kill":   False,
            "flag":   True,
            "reason": f"HIGH IMPACT EVENT JUST RELEASED: {names} -- volatility risk",
            "events": recent,
        }

    return {
        "kill":   False,
        "flag":   False,
        "reason": "No high-impact events in window. Clear to scan.",
        "events": [],
    }


def format_upcoming_events(events: list[dict], limit: int = 5) -> str:
    """Format upcoming events for inclusion in DOMI briefing."""
    from datetime import timezone
    now = datetime.now(timezone.utc)

    upcoming = [
        e for e in events
        if e.get("datetime") and e["datetime"] > now
    ]
    upcoming.sort(key=lambda e: e["datetime"])

    if not upcoming:
        return "No high-impact events scheduled."

    lines = []
    for ev in upcoming[:limit]:
        dt_local = ev["datetime"].strftime("%a %H:%M UTC")
        lines.append(f"  [{ev['country']}] {ev['title']} -- {dt_local} ({ev['impact']})")

    return "\n".join(lines)


if __name__ == "__main__":
    with open("config/watchlist.json") as f:
        cfg = json.load(f)

    events = fetch_forexfactory_events(cfg)
    status = check_news_window(events, cfg)

    print(f"\nNews Window Status:")
    print(f"  Kill:   {status['kill']}")
    print(f"  Flag:   {status['flag']}")
    print(f"  Reason: {status['reason']}")
    print(f"\nUpcoming Events:\n{format_upcoming_events(events)}")
