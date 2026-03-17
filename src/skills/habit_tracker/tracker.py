# ============================================================
# skills/habit_tracker/tracker.py — Habit & Pattern Recognition
# ============================================================
import os, json
from datetime import datetime, timedelta
from collections import Counter
from settings import settings as config
from skills.logger import log_audit

_PATH = os.path.join(config.BASE_DIR, "usage_patterns.json")

def _load(): return json.load(open(_PATH)) if os.path.isfile(_PATH) else {"events": []}
def _save(d): json.dump(d, open(_PATH, "w"), indent=2)

def log_event(event_type: str, details: str = ""):
    data = _load()
    data["events"].append({"type": event_type, "details": details,
                            "hour": datetime.now().hour, "day": datetime.now().strftime("%A"),
                            "ts": datetime.now().isoformat()})
    if len(data["events"]) > 500: data["events"] = data["events"][-500:]
    _save(data)

def get_patterns() -> dict:
    data = _load()
    events = data.get("events", [])
    if not events: return {}
    hours = Counter(e["hour"] for e in events)
    days = Counter(e["day"] for e in events)
    types = Counter(e["type"] for e in events)
    peak_hour = hours.most_common(1)[0] if hours else (0, 0)
    peak_day = days.most_common(1)[0] if days else ("?", 0)
    return {"peak_hour": peak_hour[0], "peak_day": peak_day[0],
            "top_actions": types.most_common(5), "total_events": len(events)}

def get_proactive_insight() -> str:
    p = get_patterns()
    if not p: return ""
    insights = []
    hour = datetime.now().hour
    if hour == p.get("peak_hour"):
        insights.append(f"📊 This is your peak activity hour ({hour}:00)")
    return " | ".join(insights)

def format_habits() -> str:
    p = get_patterns()
    if not p: return "📊 Not enough data yet for pattern analysis."
    lines = [f"📊 *Habit Patterns*\n", f"Peak hour: {p['peak_hour']}:00 | Peak day: {p['peak_day']}",
             f"Total events: {p['total_events']}", "\n*Top actions:*"]
    for action, count in p.get("top_actions", []):
        lines.append(f"  • {action}: {count}x")
    return "\n".join(lines)
