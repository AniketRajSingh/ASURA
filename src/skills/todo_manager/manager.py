# ============================================================
# core/todo_manager.py — AI-Driven TODO Tracking
# ============================================================

import os
import json
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit, log_app


def _load_todos() -> list[dict]:
    """Load TODOs from disk."""
    from core.state_manager import state
    return state.get_section("todos", [])


def _save_todos(todos: list[dict]):
    """Persist TODOs to disk."""
    from core.state_manager import state
    state.update_section("todos", todos)


def add_todo(
    description: str,
    source: str = "self_updater",
    priority: str = "medium",
    category: str = "improvement",
) -> dict:
    """
    Add a new TODO item.
    Called by the self-updater when it encounters a difficulty
    or thinks something could be improved.

    Args:
        description: What needs to be done
        source: Where this TODO came from (self_updater, user, system)
        priority: low / medium / high / critical
        category: improvement / bugfix / feature / optimization
    """
    todos = _load_todos()

    todo = {
        "id": len(todos) + 1,
        "description": description,
        "source": source,
        "priority": priority,
        "category": category,
        "status": "open",
        "created": datetime.now().isoformat(),
        "completed": None,
    }

    todos.append(todo)
    _save_todos(todos)

    log_audit("TODO", f"Added #{todo['id']}: {description[:80]}")
    log_app(f"TODO added: [{priority}] {description[:60]}")
    return todo


def complete_todo(todo_id: int, result: str = "") -> bool:
    """Mark a TODO as complete with an optional result description."""
    todos = _load_todos()

    for todo in todos:
        if todo["id"] == todo_id:
            todo["status"] = "done"
            todo["completed"] = datetime.now().isoformat()
            todo["result"] = result
            _save_todos(todos)
            log_audit("TODO", f"Completed #{todo_id}: {result[:80]}")
            return True

    return False


def get_open_todos(priority: str = None, category: str = None) -> list[dict]:
    """Get open TODOs, optionally filtered by priority or category."""
    todos = _load_todos()
    open_todos = [t for t in todos if t["status"] == "open"]

    if priority:
        open_todos = [t for t in open_todos if t["priority"] == priority]
    if category:
        open_todos = [t for t in open_todos if t["category"] == category]

    return open_todos


def get_next_todo() -> dict | None:
    """
    Get the highest-priority open TODO for the self-updater to work on.
    Priority order: critical > high > medium > low
    """
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    open_todos = get_open_todos()

    if not open_todos:
        return None

    open_todos.sort(key=lambda t: priority_order.get(t["priority"], 99))
    return open_todos[0]


def format_todos_summary() -> str:
    """Format TODOs as a readable Telegram message."""
    todos = _load_todos()
    open_t = [t for t in todos if t["status"] == "open"]
    done_t = [t for t in todos if t["status"] == "done"]

    lines = [f"📋 **TODOs** ({len(open_t)} open, {len(done_t)} done)\n"]

    if open_t:
        lines.append("**Open:**")
        for t in open_t:
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                t["priority"], "⚪"
            )
            lines.append(f"  {emoji} #{t['id']} [{t['category']}] {t['description'][:60]}")
    else:
        lines.append("✅ No open TODOs!")

    return "\n".join(lines)
