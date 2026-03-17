# ============================================================
# skills/dream_machine/dreamer.py — Background Goals Engine
# Long-term goals the AI works on during idle time
# ============================================================

import os, json
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit

_GOALS_PATH = os.path.join(config.BASE_DIR, "goals.json")

def _load(): return json.load(open(_GOALS_PATH)) if os.path.isfile(_GOALS_PATH) else {"goals": []}
def _save(data): json.dump(data, open(_GOALS_PATH, "w"), indent=2)

def add_goal(title: str, description: str = "", priority: int = 5) -> dict:
    data = _load()
    goal = {"id": len(data["goals"]) + 1, "title": title, "description": description,
            "priority": priority, "progress": 0, "steps_done": [],
            "created": datetime.now().isoformat(), "status": "active"}
    data["goals"].append(goal)
    _save(data)
    log_audit("DREAM", f"Goal added: {title}")
    return goal

def update_progress(goal_id: int, step: str, progress: int):
    data = _load()
    for g in data["goals"]:
        if g["id"] == goal_id:
            g["steps_done"].append({"step": step, "at": datetime.now().isoformat()})
            g["progress"] = min(progress, 100)
            if progress >= 100: g["status"] = "completed"
            break
    _save(data)

def get_active_goals() -> list:
    return [g for g in _load()["goals"] if g["status"] == "active"]

def format_goals() -> str:
    goals = _load()["goals"]
    if not goals: return "💭 No goals set. Use `/dream add <goal>`"
    lines = ["💭 *Dream Machine — Background Goals*\n"]
    for g in goals:
        bar = "█" * (g["progress"] // 10) + "░" * (10 - g["progress"] // 10)
        status = "🟢" if g["status"] == "active" else "✅"
        lines.append(f"{status} #{g['id']} *{g['title']}*\n   [{bar}] {g['progress']}%")
    return "\n".join(lines)
