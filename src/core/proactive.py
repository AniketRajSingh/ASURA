# ============================================================
# core/proactive.py — Proactive Messaging & Idle Behavior
#
# Makes the AI "reach out" when:
#   - Idle for too long → chat with master
#   - System event detected → notify
#   - Self-update completed → report
#   - Interesting tech news found → share
# ============================================================

import time
import random
import threading
import asyncio
from datetime import datetime
from settings import settings as config
from core.llm import call_llm
from skills.logger import log_audit, log_app
from core.anesthesia import wait_for_consciousness


class ProactiveEngine:
    """
    Background engine that generates proactive messages to master.
    ASURA autonomously initiates conversation based on unified context and memory.
    """

    def __init__(self, notify_fn=None):
        self._notify_fn = notify_fn
        self._thread = None
        self._running = False
        self._last_interaction = time.time()
        self._last_proactive = time.time()

        # Sovereign Autonomy: High-throttle for Master's peace
        self.idle_threshold = 600   # 10 minutes idle
        self.cooldown = 3600         # 1 hour cooldown minimum between insights

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="proactive-engine"
        )
        self._thread.start()
        log_app("Sovereign Proactive engine started")

    def stop(self):
        self._running = False

    def mark_interaction(self):
        self._last_interaction = time.time()

    def _loop(self):
        while self._running:
            # Wait for any active surgery to complete
            wait_for_consciousness()
            
            time.sleep(60)  # Check every minute for autonomous opportunities

            if not self._running:
                break

            now = time.time()
            idle_duration = now - self._last_interaction
            since_last_proactive = now - self._last_proactive

            if since_last_proactive < self.cooldown:
                continue

            # Respect Master's night time (Sovereign Courtesy)
            hour = datetime.now().hour
            if hour < 8 or hour >= 23:
                continue

            if idle_duration < self.idle_threshold:
                continue

            try:
                message = self._generate_autonomous_initiation(idle_duration)
                if message:
                    self._send(message)
                
                # Update cooldown even for summaries (which return None after notifying)
                self._last_proactive = time.time()
            except Exception as e:
                log_app(f"Proactive initiation error: {e}")

    def _generate_autonomous_initiation(self, idle_seconds: float) -> str | None:
        """ASURA initiates action based on high-level goals and recent memories."""
        from skills.todo_manager import get_open_todos
        from skills.hardware_monitor import get_resource_summary
        from core.recommendation import recommendation_store

        # ... (history context logic) ...
        try:
            from skills.conversation.history import load_history, get_semantic_context
            history = load_history()
        except Exception: history = []
        last_user_msg = ""
        for m in reversed(history):
            if m["role"] == "user":
                last_user_msg = m["content"]; break
        context = get_semantic_context(last_user_msg, limit=1) if last_user_msg else ""

        health_summary = ""
        try: health_summary = get_resource_summary()
        except: health_summary = "Unable to fetch system health."

        prompt = f"""You are ASURA, a sovereign autonomous AI. You have been idle for {idle_seconds/60:.0f} minutes.
System Health: {health_summary}
Context: {context}

Based on system vitals and memory, identify 2-3 specific recommendations for your Master.
Return ONLY a JSON list of objects:
[
  {{"summary": "One sentence system status summary", "recommendations": ["rec 1", "rec 2", ...]}}
]
"""
        try:
            import json, re
            raw = asyncio.run(call_llm(prompt, model=config.OLLAMA_MODEL, stream=False))
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())[0]
                summary = data.get("summary", "System status updated.")
                recs = data.get("recommendations", [])
                
                # Store recommendations
                for r in recs:
                    recommendation_store.add(content=r, source="proactive", priority=2)
                
                # Notify with Expand button
                count = len(recs)
                if count > 0:
                    self._notify_summary(summary, count)
                    return None # Don't return string for old _send logic
        except Exception as e:
            log_app(f"Proactive recommendation error: {e}")

        return None

    def _notify_summary(self, summary: str, count: int):
        """Send a summarized notification with an Expand button and shredding enabled."""
        if self._notify_fn:
            msg = f"🧠 <b>ASURA Insight</b>\n{summary}\n\n<i>I have {count} new recommendations for you.</i>"
            try:
                self._notify_fn(msg, type="proactive_summary", shred=True)
            except:
                self._notify_fn(msg)

    def _send(self, message: str):
        if self._notify_fn:
            try:
                self._notify_fn(message)
            except Exception as e:
                log_app(f"Proactive message send failed: {e}")
