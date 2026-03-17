# ============================================================
# skills/dashboard/progress_socket.py — Live Task Narration
# ============================================================
import json
import queue
import time
from datetime import datetime
from skills.logger import log_audit

# Global queue for SSE updates
class ProgressManager:
    def __init__(self):
        self.listeners = []
    
    def subscribe(self):
        q = queue.Queue(maxsize=100)
        self.listeners.append(q)
        return q
        
    def unsubscribe(self, q):
        if q in self.listeners:
            self.listeners.remove(q)
            
    def broadcast(self, data):
        for q in self.listeners:
            try: q.put_nowait(data)
            except: pass

progress_manager = ProgressManager()
_progress_queue = queue.Queue(maxsize=100)

def report_progress(task_name: str, status: str, progress: int = 0, summary: str = ""):
    """
    Log and broadcast a progress update for the dashboard to consume.
    """
    update = {
        "timestamp": datetime.now().isoformat(),
        "task": task_name,
        "status": status,
        "progress": progress, # 0-100
        "summary": summary
    }
    
    # Add to in-memory queue for SSE
    if _progress_queue.full():
        try: _progress_queue.get_nowait()
        except: pass
    _progress_queue.put(update)
    progress_manager.broadcast(update)
    
    # Audit trail
    log_audit("PROGRESS", f"[{task_name}] {status} ({progress}%)")

def get_latest_updates():
    """Retrieve all pending updates for the SSE handler."""
    updates = []
    while not _progress_queue.empty():
        updates.append(_progress_queue.get())
    return updates
