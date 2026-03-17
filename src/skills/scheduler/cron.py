# ============================================================
# skills/scheduler/cron.py — Cron-Style Task Scheduler
# Persist arbitrary recurring tasks to schedules.json
# ============================================================

import os
import json
import time
import threading
from datetime import datetime, timedelta
from settings import settings as config
from skills.logger import log_audit, log_app


def _load_schedules() -> list[dict]:
    from core.state_manager import state
    return state.get_section("calendar", [])


def _save_schedules(schedules: list[dict]):
    from core.state_manager import state
    state.update_section("calendar", schedules)


def add_schedule(name: str, action: str, interval_minutes: int = 60,
                 action_type: str = "shell", enabled: bool = True) -> dict:
    """
    Add a recurring scheduled task.
    action_type: 'shell' | 'python' | 'notify' | 'evolve'
    """
    schedules = _load_schedules()
    task_id = max([s.get("id", 0) for s in schedules], default=0) + 1

    task = {
        "id": task_id,
        "name": name,
        "action": action,
        "action_type": action_type,
        "interval_minutes": interval_minutes,
        "enabled": enabled,
        "last_run": None,
        "next_run": datetime.now().isoformat(),
        "run_count": 0,
        "created": datetime.now().isoformat(),
    }
    schedules.append(task)
    _save_schedules(schedules)
    log_audit("SCHEDULER", f"Added: #{task_id} '{name}' every {interval_minutes}m")
    return task


def remove_schedule(task_id: int) -> bool:
    schedules = _load_schedules()
    before = len(schedules)
    schedules = [s for s in schedules if s["id"] != task_id]
    if len(schedules) < before:
        _save_schedules(schedules)
        log_audit("SCHEDULER", f"Removed: #{task_id}")
        return True
    return False


def toggle_schedule(task_id: int) -> bool:
    schedules = _load_schedules()
    for s in schedules:
        if s["id"] == task_id:
            s["enabled"] = not s["enabled"]
            _save_schedules(schedules)
            return True
    return False


def list_schedules() -> list[dict]:
    return _load_schedules()


def format_schedules_summary() -> str:
    schedules = _load_schedules()
    if not schedules:
        return "📅 No scheduled tasks.\nUse `/schedule add <name> <interval_mins> <action>`"

    lines = [f"📅 *Scheduled Tasks ({len(schedules)})*\n"]
    for s in schedules:
        status = "✅" if s["enabled"] else "⏸️"
        lines.append(
            f"{status} #{s['id']} *{s['name']}*\n"
            f"   Every {s['interval_minutes']}m | Runs: {s['run_count']} | "
            f"`{s['action_type']}: {s['action'][:40]}`"
        )
    return "\n".join(lines)


def get_due_tasks() -> list[dict]:
    """Get tasks that are due to run."""
    schedules = _load_schedules()
    now = datetime.now()
    due = []

    for s in schedules:
        if not s["enabled"]:
            continue
        next_run = datetime.fromisoformat(s["next_run"]) if s.get("next_run") else now
        if now >= next_run:
            due.append(s)

    return due


def mark_task_run(task_id: int):
    """Mark a task as just-run, advance next_run."""
    schedules = _load_schedules()
    for s in schedules:
        if s["id"] == task_id:
            s["last_run"] = datetime.now().isoformat()
            s["next_run"] = (datetime.now() + timedelta(minutes=s["interval_minutes"])).isoformat()
            s["run_count"] = s.get("run_count", 0) + 1
            break
    _save_schedules(schedules)


class SchedulerDaemon:
    """Background daemon that checks and executes scheduled tasks."""

    def __init__(self, notify_fn=None):
        self._notify_fn = notify_fn
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()
        log_app("Scheduler daemon started")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            time.sleep(60)  # Check every minute
            if not self._running:
                break
            try:
                self._process_due()
            except Exception as e:
                log_app(f"Scheduler error: {e}")

    def _process_due(self):
        due = get_due_tasks()
        for task in due:
            try:
                log_audit("SCHEDULER", f"Executing: #{task['id']} '{task['name']}'")
                result = self._execute_task(task)
                mark_task_run(task["id"])

                if self._notify_fn and result:
                    msg = f"<b>📅 Scheduled: {task['name']}</b>\n\n{result[:500]}"
                    self._notify_fn(msg)

            except Exception as e:
                log_audit("SCHEDULER_ERROR", f"Task #{task['id']} failed: {e}")
                mark_task_run(task["id"])  # Still advance to avoid infinite retries

    def _execute_task(self, task: dict) -> str:
        action_type = task.get("action_type", "shell")
        action = task["action"]

        if action_type == "shell":
            from skills.shell_executor import execute
            import asyncio
            # Scheduler runs in a sync thread, so we use asyncio.run
            result = asyncio.run(execute(action))
            return result.get("stdout", "") or result.get("stderr", "")

        elif action_type == "python":
            from skills.shell_executor import execute_python
            import asyncio
            result = asyncio.run(execute_python(action))
            return result.get("stdout", "") or result.get("stderr", "")

        elif action_type == "notify":
            return action  # Just return the message itself

        elif action_type == "evolve":
            from core.self_updater import SelfUpdater
            result = SelfUpdater().evolve()
            return f"{'✅' if result['success'] else '❌'} {result.get('summary', '')}"

        return f"Unknown action_type: {action_type}"
