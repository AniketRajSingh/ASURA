# ============================================================
# skills/calendar_manager/calendar.py — Calendar & Reminders
# ============================================================

import os
import json
from datetime import datetime, timedelta
from settings import settings as config
from skills.logger import log_audit


def _load_events() -> list[dict]:
    if os.path.isfile(config.CALENDAR_PATH):
        try:
            with open(config.CALENDAR_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_events(events: list[dict]):
    with open(config.CALENDAR_PATH, "w") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


def add_event(title: str, when: str, description: str = "",
              remind_minutes: int = 30) -> dict:
    """
    Add a calendar event.
    when: ISO format datetime or natural like '2026-02-28 14:00'
    """
    events = _load_events()
    event_id = max([e.get("id", 0) for e in events], default=0) + 1

    try:
        dt = datetime.fromisoformat(when)
    except ValueError:
        # Try common formats
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"]:
            try:
                dt = datetime.strptime(when, fmt)
                break
            except ValueError:
                continue
        else:
            dt = datetime.now() + timedelta(hours=1)

    event = {
        "id": event_id,
        "title": title,
        "description": description,
        "when": dt.isoformat(),
        "remind_at": (dt - timedelta(minutes=remind_minutes)).isoformat(),
        "reminded": False,
        "created": datetime.now().isoformat(),
    }
    events.append(event)
    _save_events(events)
    log_audit("CALENDAR", f"Added event #{event_id}: {title} at {dt}")
    return event


def remove_event(event_id: int) -> bool:
    events = _load_events()
    before = len(events)
    events = [e for e in events if e["id"] != event_id]
    if len(events) < before:
        _save_events(events)
        return True
    return False


def get_upcoming(hours: int = 24) -> list[dict]:
    """Get events in the next N hours."""
    events = _load_events()
    now = datetime.now()
    cutoff = now + timedelta(hours=hours)
    upcoming = []

    for e in events:
        try:
            dt = datetime.fromisoformat(e["when"])
            if now <= dt <= cutoff:
                upcoming.append(e)
        except (ValueError, KeyError):
            continue

    return sorted(upcoming, key=lambda x: x["when"])


def get_due_reminders() -> list[dict]:
    """Get events whose reminders are due."""
    events = _load_events()
    now = datetime.now()
    due = []

    for e in events:
        if e.get("reminded"):
            continue
        try:
            remind_at = datetime.fromisoformat(e["remind_at"])
            event_time = datetime.fromisoformat(e["when"])
            if remind_at <= now <= event_time:
                due.append(e)
        except (ValueError, KeyError):
            continue

    return due


def mark_reminded(event_id: int):
    events = _load_events()
    for e in events:
        if e["id"] == event_id:
            e["reminded"] = True
            break
    _save_events(events)


def format_calendar_summary() -> str:
    upcoming = get_upcoming(48)
    if not upcoming:
        return "📅 No upcoming events.\nUse `/calendar add <title> <datetime>`"

    lines = [f"📅 *Upcoming Events ({len(upcoming)})*\n"]
    for e in upcoming:
        dt = datetime.fromisoformat(e["when"]).strftime("%b %d %H:%M")
        lines.append(f"  🔹 #{e['id']} *{e['title']}* — {dt}")
        if e.get("description"):
            lines.append(f"    {e['description'][:50]}")
    return "\n".join(lines)
