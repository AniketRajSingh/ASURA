# ============================================================
# skills/time_tracker/tracker.py — Time Tracking
# ============================================================
import os, json, time
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit

_PATH = os.path.join(config.BASE_DIR, "time_logs.json")
_active = {}

def _load(): return json.load(open(_PATH)) if os.path.isfile(_PATH) else {"sessions": []}
def _save(d): json.dump(d, open(_PATH, "w"), indent=2)

def start_timer(task: str) -> str:
    _active[task] = time.time()
    log_audit("TIMER", f"Started: {task}")
    return f"⏱️ Timer started: {task}"

def stop_timer(task: str) -> str:
    if task not in _active: return f"No timer for: {task}"
    elapsed = time.time() - _active.pop(task)
    data = _load()
    data["sessions"].append({"task": task, "seconds": elapsed, "date": datetime.now().isoformat()})
    _save(data)
    m, s = divmod(int(elapsed), 60)
    log_audit("TIMER", f"Stopped: {task} ({m}m {s}s)")
    return f"⏱️ {task}: {m}m {s}s"

def get_weekly_report() -> str:
    data = _load()
    sessions = data.get("sessions", [])[-50:]
    if not sessions: return "⏱️ No time tracked yet."
    total = sum(s["seconds"] for s in sessions)
    by_task = {}
    for s in sessions:
        by_task[s["task"]] = by_task.get(s["task"], 0) + s["seconds"]
    lines = ["⏱️ *Time Report*\n"]
    for task, secs in sorted(by_task.items(), key=lambda x: -x[1]):
        m = int(secs / 60)
        lines.append(f"  • {task}: {m}m")
    lines.append(f"\n*Total: {int(total/60)}m*")
    return "\n".join(lines)
