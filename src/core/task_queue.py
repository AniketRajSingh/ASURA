# ============================================================
# core/task_queue.py — Priority Task Queue
# Background tasks processed without overloading the system.
# Integrates with SovereignAuthority to prevent sleep during tasks.
# ============================================================

import queue
import threading
import time
from datetime import datetime
from skills.logger import log_audit, log_app


class TaskItem:
    """A queued task with priority and metadata."""
    def __init__(self, name: str, func, args=(), kwargs=None,
                 priority: int = 5, callback=None):
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority  # 0=highest, 9=lowest
        self.callback = callback
        self.created = datetime.now()
        self.status = "queued"
        self.result = None
        self.error = None

    def __lt__(self, other):
        return self.priority < other.priority


class TaskQueue:
    """
    Background task processor with:
    - Priority queue (0=highest, 9=lowest)
    - Concurrency limit
    - Resource-aware execution (checks governor)
    - Progress tracking
    - Sovereign Power Management (stays awake during active tasks)
    """

    def __init__(self, max_workers: int = 2, notify_fn=None):
        self._queue = queue.PriorityQueue()
        self._workers = []
        self._max_workers = max_workers
        self._running = False
        self._notify_fn = notify_fn
        self._active_tasks: list[TaskItem] = []
        self._completed: list[TaskItem] = []
        self._lock = threading.Lock()
        
        # ── Power Management ────────────
        try:
            from core.sovereignty import get_authority
            self._authority = get_authority()
        except ImportError:
            self._authority = None

    def start(self):
        self._running = True
        for i in range(self._max_workers):
            t = threading.Thread(
                target=self._worker, daemon=True, name=f"task-worker-{i}"
            )
            self._workers.append(t)
            t.start()
        
        # ─── Recommendation Poller ────────────
        t_poller = threading.Thread(
            target=self._recommendation_poller, daemon=True, name="rec-poller"
        )
        t_poller.start()
        
        log_app(f"Task queue started ({self._max_workers} workers + Poller)")

    def _recommendation_poller(self):
        """Periodically poll the RecommendationStore for approved tasks."""
        while self._running:
            try:
                from core.recommendation import recommendation_store
                from core.reasoning import think
                import asyncio
                
                approved = recommendation_store.get_approved()
                for rec in approved:
                    # Submit to queue
                    # We use a wrapper to run the async think() in the worker thread
                    def _think_task(task_content, rec_id):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            res = loop.run_until_complete(think(task_content))
                            recommendation_store.update_status(rec_id, "done")
                            return res.get("conclusion", "Task complete.")
                        finally:
                            loop.close()

                    self.submit(
                        name=f"Autonomous: {rec.content[:30]}",
                        func=_think_task,
                        args=(rec.content, rec.id),
                        priority=7 # Lower priority for background tasks
                    )
                    # Mark as executing so we don't re-submit
                    recommendation_store.update_status(rec.id, "executing")
                    
            except Exception as e:
                log_app(f"Rec-Poller error: {e}")
            
            time.sleep(60) # Poll every minute

    def stop(self):
        self._running = False
        if self._authority:
            self._authority.release_lock()

    def submit(self, name: str, func, args=(), kwargs=None,
               priority: int = 5, callback=None) -> TaskItem:
        """Submit a task to the background queue."""
        task = TaskItem(name, func, args, kwargs, priority, callback)
        self._queue.put(task)
        log_audit("QUEUE", f"Submitted: [{priority}] {name}")
        
        # Ensure system stays awake when tasks are queued
        if self._authority:
            self._authority.stay_awake()
            
        return task

    def _worker(self):
        while self._running:
            try:
                task = self._queue.get(timeout=5)
            except queue.Empty:
                # Check if we should release power lock
                if self.is_empty() and self._authority:
                    self._authority.release_lock()
                continue

            # Engage power lock if not already active
            if self._authority:
                self._authority.stay_awake()

            # Check resource governor before executing
            try:
                from core.resource_governor import get_governor
                gov = get_governor()
                can, reason = gov.can_proceed("task")
                if not can:
                    # Re-queue with delay
                    log_audit("QUEUE", f"Delayed: {task.name} — {reason}")
                    time.sleep(10)
                    self._queue.put(task)
                    continue
            except ImportError:
                pass

            # Execute
            task.status = "running"
            with self._lock:
                self._active_tasks.append(task)

            try:
                log_audit("QUEUE", f"Running: {task.name}")
                task.result = task.func(*task.args, **task.kwargs)
                task.status = "done"
                log_audit("QUEUE", f"Done: {task.name}")

                if task.callback:
                    try:
                        task.callback(task)
                    except Exception:
                        pass

            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                log_audit("QUEUE_ERROR", f"Failed: {task.name} — {e}")

            finally:
                with self._lock:
                    if task in self._active_tasks:
                        self._active_tasks.remove(task)
                    self._completed.append(task)
                    # Keep last 50
                    if len(self._completed) > 50:
                        self._completed = self._completed[-50:]
                
                # Check if this was the last task
                if self.is_empty() and self._authority:
                    self._authority.release_lock()

    def get_status(self) -> str:
        """Format queue status for display."""
        pending = self._queue.qsize()
        active = len(self._active_tasks)
        done = len(self._completed)
        failed = sum(1 for t in self._completed if t.status == "failed")

        lines = [
            f"📋 *Task Queue*\n",
            f"Pending: {pending} | Active: {active} | Done: {done} | Failed: {failed}",
        ]

        if self._active_tasks:
            lines.append("\n*Active:*")
            for t in self._active_tasks:
                lines.append(f"  ⏳ {t.name}")

        recent = [t for t in self._completed[-5:]]
        if recent:
            lines.append("\n*Recent:*")
            for t in reversed(recent):
                emoji = "✅" if t.status == "done" else "❌"
                lines.append(f"  {emoji} {t.name}")

        return "\n".join(lines)

    def is_empty(self) -> bool:
        """Returns True if no tasks are pending or active."""
        return self._queue.empty() and len(self._active_tasks) == 0

    def add_sub_tasks(self, parent_name: str, sub_tasks_data: list[dict]):
        """
        Dynamically append sub-tasks to the registry based on findings.
        Expects [{'name': '...', 'func': ..., 'args': ...}, ...]
        """
        for data in sub_tasks_data:
            name = f"[{parent_name}] {data['name']}"
            self.submit(
                name=name,
                func=data['func'],
                args=data.get('args', ()),
                kwargs=data.get('kwargs', {}),
                priority=data.get('priority', 6)
            )
        log_audit("QUEUE", f"Dynamically added {len(sub_tasks_data)} sub-tasks for {parent_name}")


# ─── Singleton ───────────────────────────────────────────────
_queue_instance: TaskQueue = None

def get_task_queue() -> TaskQueue:
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = TaskQueue()
    return _queue_instance
