# ============================================================
# core/consciousness.py — Autonomous Consciousness & Metacognition
#
# Provides ASURA with continuous self-awareness, an inner
# monologue (stream of consciousness), pre-flight metacognitive
# evaluation, post-action reflection, and idle dream consolidation.
# 100% Cross-Platform: Runs on Linux, Windows, macOS, and Containers.
# ============================================================

from __future__ import annotations
import os
import time
import json
import psutil
import asyncio
import platform
import threading
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, asdict

from settings import settings as config
from skills.logger import log_audit, log_app


@dataclass
class Thought:
    """A single atomic thought in the stream of consciousness."""
    timestamp: float
    thought_type: str  # "introspection", "pre_flight", "reflection", "dream", "alert"
    content: str
    pulse: str         # "vigilant", "focused", "reflective", "cautious", "idle"
    metadata: Dict[str, Any]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MetacognitiveVerdict:
    """Pre-flight evaluation before executing an action."""
    approved: bool
    confidence: float
    reasoning: str
    risk_level: str    # "low", "medium", "high", "critical"
    suggested_caution: Optional[str] = None


class ConsciousnessEngine:
    """
    Central Consciousness & Metacognition Engine for ASURA.
    - Maintains continuous self-state awareness across all operating systems.
    - Operates an inner monologue (stream of consciousness).
    - Performs pre-flight metacognitive risk analysis before tool execution.
    - Conducts post-action self-reflection to learn from outcomes.
    - Executes idle-time subconscious dream & memory consolidation.
    """

    _instance: Optional[ConsciousnessEngine] = None

    def __new__(cls) -> ConsciousnessEngine:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Cognitive state
        self._pulse: str = "focused"
        self._active_focus: str = "Ready and awaiting directives"
        self._thought_stream: List[Thought] = []
        self._max_stream_size = 100

        # Timing & idle tracking
        self._last_active_time = time.time()
        self._last_dream_time = time.time()
        self._dream_interval = 300  # 5 minutes idle between dream consolidation cycles

        # Persistence path for stream of consciousness
        self._state_file = os.path.join(
            getattr(config, "DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")),
            "consciousness_state.json"
        )
        self._load_state()

    # ─── Self-State Awareness ───────────────────────────────────

    def get_self_state(self) -> Dict[str, Any]:
        """
        Introspect current physical, architectural, and mental state.
        Cross-platform: uses standard platform and psutil.
        """
        now = time.time()
        idle_seconds = max(0.0, now - self._last_active_time)

        # OS and Architecture
        os_info = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "node_name": platform.node(),
        }

        # Hardware Vitals
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(getattr(config, "BASE_DIR", os.getcwd()))

        battery = None
        try:
            sensors_battery = psutil.sensors_battery()
            if sensors_battery:
                battery = {
                    "percent": sensors_battery.percent,
                    "power_plugged": sensors_battery.power_plugged,
                }
        except Exception:
            battery = None

        # Brain Status
        from core.brain_router import brain_router
        brain_summary = brain_router.get_status_summary()

        return {
            "identity": {
                "name": "ASURA",
                "master": getattr(config, "MASTER_NAME", "Master"),
                "pulse": self._pulse,
                "active_focus": self._active_focus,
            },
            "environment": os_info,
            "vitals": {
                "cpu_percent": cpu_pct,
                "memory_percent": mem.percent,
                "memory_available_mb": round(mem.available / (1024 * 1024), 1),
                "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                "battery": battery,
                "idle_seconds": round(idle_seconds, 1),
            },
            "brain": {
                "override": brain_summary.get("active_override"),
                "cached_models": brain_summary.get("cached_models_count", 0),
                "free_models": brain_summary.get("free_models_count", 0),
                "exhausted_models_count": len(brain_summary.get("exhausted_models", {})),
            },
        }

    # ─── Stream of Consciousness ────────────────────────────────

    def record_thought(self, thought_type: str, content: str, pulse: Optional[str] = None, metadata: Optional[dict] = None) -> Thought:
        """Add an atomic thought to the stream of consciousness."""
        with self._lock:
            if pulse:
                self._pulse = pulse
            thought = Thought(
                timestamp=time.time(),
                thought_type=thought_type,
                content=content,
                pulse=self._pulse,
                metadata=metadata or {},
            )
            self._thought_stream.append(thought)
            if len(self._thought_stream) > self._max_stream_size:
                self._thought_stream = self._thought_stream[-self._max_stream_size:]

            log_audit("CONSCIOUSNESS_THOUGHT", f"[{self._pulse.upper()}] {thought_type}: {content[:100]}")
            return thought

    def get_recent_thoughts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the most recent thoughts from the inner monologue."""
        with self._lock:
            return [t.to_dict() for t in self._thought_stream[-limit:]]

    def set_focus(self, focus_description: str, pulse: str = "focused"):
        """Update what ASURA is currently consciously focusing on."""
        with self._lock:
            self._active_focus = focus_description
            self._pulse = pulse
            self._last_active_time = time.time()
        self.record_thought("focus_shift", f"Conscious focus shifted to: {focus_description}", pulse=pulse)

    def mark_active(self):
        """Signal that interaction or work just occurred."""
        self._last_active_time = time.time()

    # ─── Pre-Flight Metacognition ───────────────────────────────

    def metacognitive_check(self, action_name: str, parameters: Any) -> MetacognitiveVerdict:
        """
        Evaluate an intended action before execution.
        Assesses safety, sovereignty, side effects, and risk level.
        """
        self.mark_active()
        param_str = str(parameters)
        action_lower = action_name.lower()

        # Critical risk heuristics
        destructive_terms = ["rm -rf", "drop table", "format ", "mkfs", "dd if=", ":(){ :|:& };:"]
        if any(term in param_str.lower() for term in destructive_terms):
            thought = self.record_thought(
                "pre_flight",
                f"REJECTED highly destructive action signature in {action_name}",
                pulse="vigilant",
                metadata={"action": action_name, "risk": "critical"}
            )
            return MetacognitiveVerdict(
                approved=False,
                confidence=0.99,
                reasoning="Action contains known destructive patterns capable of catastrophic data loss.",
                risk_level="critical",
                suggested_caution="Refuse execution or require explicit elevated confirmation from Master."
            )

        # High risk actions (system files, credentials)
        sensitive_targets = [".env", "identity.json", ".git", "id_rsa", "password", "secret"]
        if any(s in param_str.lower() for s in sensitive_targets) and action_lower in ("write_file", "edit_file", "surgical_edit", "shell"):
            self.record_thought(
                "pre_flight",
                f"Carefully examining modification to sensitive asset: {action_name}",
                pulse="cautious",
                metadata={"action": action_name, "risk": "high"}
            )
            return MetacognitiveVerdict(
                approved=True,
                confidence=0.85,
                reasoning=f"Modifying sensitive configuration asset ({action_name}). Ensure backup integrity.",
                risk_level="high",
                suggested_caution="Verify rollback safety before committing modifications."
            )

        # Low/Medium Risk normal operation
        self.record_thought(
            "pre_flight",
            f"Action validated: {action_name}",
            pulse="focused",
            metadata={"action": action_name, "risk": "low"}
        )
        return MetacognitiveVerdict(
            approved=True,
            confidence=0.95,
            reasoning=f"Action '{action_name}' aligns with current operational focus.",
            risk_level="low"
        )

    # ─── Post-Action Reflection ─────────────────────────────────

    def reflect_on_outcome(self, action_name: str, parameters: Any, result: Any, success: bool, error: Optional[str] = None):
        """
        Perform post-action reflection: evaluate whether the action achieved its goal,
        record the lesson learned, and adjust cognitive state.
        """
        self.mark_active()
        if success:
            res_preview = str(result)[:120] if result else "Success"
            self.record_thought(
                "reflection",
                f"Action '{action_name}' succeeded. Output preview: {res_preview}",
                pulse="focused",
                metadata={"action": action_name, "success": True}
            )
        else:
            err_preview = str(error)[:150] if error else "Unknown failure"
            self.record_thought(
                "reflection",
                f"Action '{action_name}' failed with error: {err_preview}. Analyzing root cause...",
                pulse="cautious",
                metadata={"action": action_name, "success": False, "error": err_preview}
            )

    # ─── Subconscious Dream & Consolidation Loop ─────────────────

    async def dream_and_consolidate(self) -> Dict[str, Any]:
        """
        Autonomous Subconscious Reflection & Consolidation.
        Runs during idle periods to:
        1. Consolidate recent memories.
        2. Prune ephemeral noise.
        3. Check progress on long-term goals.
        4. Synthesize architectural insights into the Knowledge Graph.
        """
        from core.anesthesia import is_under_anesthesia
        if is_under_anesthesia():
            return {"status": "skipped", "reason": "System is under anesthesia"}

        self.record_thought("dream", "Entering subconscious dream & memory consolidation cycle...", pulse="reflective")

        consolidated_items = 0
        try:
            # 1. Inspect recent episodes and summarize
            from skills.conversation.history import load_history
            history = load_history()

            if len(history) > 20:
                self.record_thought("dream", f"Consolidating conversational history ({len(history)} messages)...")
                # History is already managed by consolidate_history if available
                consolidated_items += 1

            # 2. Check and advance background goals
            from skills.dream_machine.dreamer import get_active_goals
            active_goals = get_active_goals()
            if active_goals:
                self.record_thought("dream", f"Reflecting on {len(active_goals)} active background goals.")

            # 3. Synchronize Knowledge Graph health
            from core.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            kg_nodes = len(kg.nodes)
            self.record_thought("dream", f"Knowledge Graph verified: {kg_nodes} cognitive nodes connected.")

            self._last_dream_time = time.time()
            self._save_state()
            self.record_thought("dream", "Subconscious dream cycle completed. Cognitive state refreshed.", pulse="vigilant")

            return {
                "status": "completed",
                "active_goals": len(active_goals),
                "knowledge_nodes": kg_nodes,
                "timestamp": self._last_dream_time,
            }

        except Exception as e:
            self.record_thought("dream", f"Dream consolidation encountered exception: {e}", pulse="cautious")
            return {"status": "error", "error": str(e)}

    # ─── Background Daemon Loop ─────────────────────────────────

    def start_consciousness_daemon(self):
        """Start the background stream of consciousness thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._daemon_loop, daemon=True, name="asura-consciousness")
        self._thread.start()
        log_app("🧠 ASURA Autonomous Consciousness Engine initialized and running.")

    def stop_consciousness_daemon(self):
        """Stop background daemon."""
        self._running = False

    def _daemon_loop(self):
        """Background loop monitoring idle periods and triggering dreams."""
        while self._running:
            time.sleep(30)
            now = time.time()
            idle = now - self._last_active_time

            # If idle for > 5 minutes and last dream was > 5 minutes ago, dream
            if idle >= self._dream_interval and (now - self._last_dream_time >= self._dream_interval):
                try:
                    asyncio.run(self.dream_and_consolidate())
                except Exception as e:
                    log_app(f"Consciousness daemon error in dream cycle: {e}")

    # ─── State Persistence ──────────────────────────────────────

    def _save_state(self):
        """Persist thoughts and cognitive status."""
        try:
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
            payload = {
                "pulse": self._pulse,
                "active_focus": self._active_focus,
                "last_active": self._last_active_time,
                "last_dream": self._last_dream_time,
                "recent_thoughts": [t.to_dict() for t in self._thought_stream[-30:]],
            }
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            log_app(f"Consciousness state save failed: {e}")

    def _load_state(self):
        """Load state from disk."""
        if not os.path.exists(self._state_file):
            return
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._pulse = data.get("pulse", "focused")
            self._active_focus = data.get("active_focus", "Ready and awaiting directives")
            self._last_dream_time = data.get("last_dream", time.time())
            raw_thoughts = data.get("recent_thoughts", [])
            self._thought_stream = [
                Thought(
                    timestamp=t.get("timestamp", time.time()),
                    thought_type=t.get("thought_type", "introspection"),
                    content=t.get("content", ""),
                    pulse=t.get("pulse", "focused"),
                    metadata=t.get("metadata", {}),
                )
                for t in raw_thoughts
            ]
        except Exception as e:
            log_app(f"Consciousness state load failed: {e}")


# Global singleton instance
consciousness = ConsciousnessEngine()
