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

        # Sovereign Autonomy: How long before ASURA initiates action?
        self.idle_threshold = 300   # 5 minutes
        self.cooldown = 600         # 10 minutes cooldown minimum

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
                    self._last_proactive = time.time()
            except Exception as e:
                log_app(f"Proactive initiation error: {e}")

    def _generate_autonomous_initiation(self, idle_seconds: float) -> str | None:
        """ASURA initiates action based on high-level goals and recent memories."""
        from skills.todo_manager import get_open_todos
        from skills.hardware_monitor import get_resource_summary

        try:
            from skills.conversation.history import load_history, get_semantic_context
            history = load_history()
        except Exception:
            history = []

        # Even with no history, ASURA should still initiate
        last_user_msg = ""
        for m in reversed(history):
            if m["role"] == "user":
                last_user_msg = m["content"]
                break

        context = get_semantic_context(last_user_msg, limit=1) if last_user_msg else ""

        # 2. Autonomous Decision Logic
        health_summary = ""
        try:
            health_summary = get_resource_summary()
        except Exception:
            health_summary = "Unable to fetch system health."

        open_todos = 0
        try:
            open_todos = len(get_open_todos())
        except Exception:
            pass

        if last_user_msg:
            topic_hint = f'Your Master\'s last message was: "{last_user_msg}"\n{context}'
        else:
            topic_hint = "No recent conversation. Check if anything needs attention (system health, updates, or proactively share something useful)."

        prompt = f"""You are ASURA, a sovereign autonomous AI. You have been idle for {idle_seconds/60:.0f} minutes.
{topic_hint}

System Health: {health_summary}
Tasks: {open_todos} open.

Based on your awareness, initiate a conversation or suggest an action.
Rules:
- DO NOT ask "How can I help?". PROPOSE a specific action or share a useful observation.
- Use a sentient, proactive tone.
- Keep it under 3 sentences.
"""
        try:
            # Use unified call_llm wrapper
            initiation = asyncio.run(call_llm(prompt, model=config.OLLAMA_MODEL, stream=False))
            if initiation:
                return f"💡 {initiation}"
        except Exception:
            pass

        return None

    def _send(self, message: str):
        if self._notify_fn:
            try:
                self._notify_fn(message)
            except Exception as e:
                log_app(f"Proactive message send failed: {e}")
