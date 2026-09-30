# ============================================================
# core/unified_memory.py — Unified Sovereign Memory System
#
# Connects all memory layers into a single coherent interface:
# 1. Identity Vault (Permanent Sovereign Facts & Master Profile)
# 2. Working Memory (Active task scratchpad & immediate context)
# 3. Episodic Memory (Experiential history: actions & outcomes)
# 4. Procedural Memory (Learned step-by-step action recipes)
# 5. Knowledge Graph (Semantic entity-relationship network)
# 100% Cross-Platform: pure Python JSON-backed persistence.
# ============================================================

from __future__ import annotations
import os
import json
import time
import threading
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, asdict

from settings import settings as config
from skills.logger import log_audit, log_app


class UnifiedMemory:
    """
    Central Sovereign Memory Controller for ASURA.
    Unifies Identity Vault, Working Memory, Episodic Memory,
    Procedural Memory, and Knowledge Graph into a single recall engine.
    """

    _instance: Optional[UnifiedMemory] = None

    def __new__(cls) -> UnifiedMemory:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._lock = threading.Lock()
        self._memory_dir = getattr(config, "MEMORY_STORE_DIR", os.path.join(config.DATA_DIR, "memory"))
        os.makedirs(self._memory_dir, exist_ok=True)

        # File paths
        self._identity_file = os.path.join(self._memory_dir, "identity.json")
        self._working_file = os.path.join(self._memory_dir, "working_memory.json")
        self._episodic_file = os.path.join(self._memory_dir, "episodic_memory.json")
        self._procedural_file = os.path.join(self._memory_dir, "procedural_memory.json")

        # In-memory caches
        self._identity: Dict[str, Any] = {}
        self._working: Dict[str, Any] = {}
        self._episodes: List[Dict[str, Any]] = []
        self._procedures: Dict[str, Any] = {}

        self._load_all()

    # ─── Load & Save ───────────────────────────────────────────

    def _load_all(self):
        """Load all memory files from disk."""
        with self._lock:
            # 1. Identity Vault
            if os.path.exists(self._identity_file):
                try:
                    with open(self._identity_file, "r", encoding="utf-8") as f:
                        self._identity = json.load(f)
                except Exception:
                    self._identity = {}
            else:
                self._identity = {
                    "master_name": getattr(config, "MASTER_NAME", "Master"),
                    "master_username": getattr(config, "MASTER_USERNAME", None),
                    "created_at": time.time(),
                    "preferences": {},
                    "facts": {},
                }
                self._save_identity()

            # 2. Working Memory
            if os.path.exists(self._working_file):
                try:
                    with open(self._working_file, "r", encoding="utf-8") as f:
                        self._working = json.load(f)
                except Exception:
                    self._working = {}

            # 3. Episodic Memory
            if os.path.exists(self._episodic_file):
                try:
                    with open(self._episodic_file, "r", encoding="utf-8") as f:
                        self._episodes = json.load(f)
                except Exception:
                    self._episodes = []

            # 4. Procedural Memory
            if os.path.exists(self._procedural_file):
                try:
                    with open(self._procedural_file, "r", encoding="utf-8") as f:
                        self._procedures = json.load(f)
                except Exception:
                    self._procedures = {}

    def _save_identity(self):
        with open(self._identity_file, "w", encoding="utf-8") as f:
            json.dump(self._identity, f, indent=2)

    def _save_working(self):
        with open(self._working_file, "w", encoding="utf-8") as f:
            json.dump(self._working, f, indent=2)

    def _save_episodes(self):
        with open(self._episodic_file, "w", encoding="utf-8") as f:
            json.dump(self._episodes, f, indent=2)

    def _save_procedures(self):
        with open(self._procedural_file, "w", encoding="utf-8") as f:
            json.dump(self._procedures, f, indent=2)

    # ─── Layer 1: Identity Vault (Permanent Facts) ─────────────

    def remember_fact(self, key: str, value: Any, category: str = "facts"):
        """Store a permanent fact in the Identity Vault."""
        with self._lock:
            if category not in self._identity:
                self._identity[category] = {}
            self._identity[category][key] = {
                "value": value,
                "updated_at": time.time(),
            }
            self._save_identity()
        log_audit("MEMORY_FACT", f"Stored fact: [{category}] {key} = {value}")

    def recall_facts(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Recall permanent facts from the Identity Vault."""
        with self._lock:
            if category:
                return self._identity.get(category, {})
            return self._identity

    # ─── Layer 2: Working Memory (Scratchpad) ───────────────────

    def set_working(self, key: str, value: Any):
        """Set an active variable in working memory."""
        with self._lock:
            self._working[key] = {
                "value": value,
                "timestamp": time.time(),
            }
            self._save_working()

    def get_working(self, key: str, default: Any = None) -> Any:
        """Get an active variable from working memory."""
        with self._lock:
            entry = self._working.get(key)
            return entry["value"] if entry else default

    def clear_working(self):
        """Clear the working memory scratchpad."""
        with self._lock:
            self._working.clear()
            self._save_working()

    # ─── Layer 3: Episodic Memory (Experiential History) ───────

    def record_episode(self, action: str, context: str, outcome: str, success: bool, metadata: Optional[dict] = None):
        """Record an action and its outcome in episodic memory."""
        entry = {
            "id": f"ep_{int(time.time())}_{len(self._episodes)}",
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "context": context[:300],
            "outcome": outcome[:300],
            "success": success,
            "metadata": metadata or {},
        }
        with self._lock:
            self._episodes.append(entry)
            # Cap episodic log to last 500 episodes
            if len(self._episodes) > 500:
                self._episodes = self._episodes[-500:]
            self._save_episodes()
        log_audit("EPISODIC_RECORD", f"Recorded episode: {action} (Success: {success})")

    def recall_recent_episodes(self, limit: int = 5, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recall recent experiential episodes, optionally filtered by keyword."""
        with self._lock:
            episodes = self._episodes
            if query:
                q_lower = query.lower()
                episodes = [
                    e for e in episodes
                    if q_lower in e["action"].lower() or q_lower in e["context"].lower() or q_lower in e["outcome"].lower()
                ]
            return episodes[-limit:]

    # ─── Layer 4: Procedural Memory (Action Recipes) ───────────

    def store_procedure(self, name: str, steps: List[str], description: str = ""):
        """Store a verified reusable procedure or recipe."""
        with self._lock:
            self._procedures[name] = {
                "name": name,
                "description": description,
                "steps": steps,
                "updated_at": time.time(),
            }
            self._save_procedures()
        log_audit("PROCEDURAL_STORE", f"Stored procedure: {name} ({len(steps)} steps)")

    def recall_procedure(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a learned procedure by name."""
        with self._lock:
            return self._procedures.get(name)

    def list_procedures(self) -> List[str]:
        """List all stored procedural recipes."""
        with self._lock:
            return list(self._procedures.keys())

    # ─── Layer 5: Knowledge Graph Integration ──────────────────

    def query_knowledge_graph(self, node_id: Optional[str] = None) -> Dict[str, Any]:
        """Query connected nodes from the Knowledge Graph."""
        from core.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        if node_id:
            return kg.nodes.get(node_id, {})
        return {"nodes_count": len(kg.nodes), "edges_count": len(kg.edges)}

    # ─── Unified Context Compiler for LLM Calls ────────────────

    def compile_context_for_prompt(self, prompt: str) -> str:
        """
        Compile relevant Identity facts, active working scratchpad,
        and past relevant episodes into a unified context block for call_llm.
        """
        sections = []

        # 1. Master Identity
        facts = self._identity.get("facts", {})
        if facts:
            fact_lines = [f"- {k}: {v['value']}" for k, v in list(facts.items())[:5]]
            sections.append("### Known Master Profile & System Facts:\n" + "\n".join(fact_lines))

        # 2. Active Working Memory
        if self._working:
            work_lines = [f"- {k}: {v['value']}" for k, v in list(self._working.items())[:5]]
            sections.append("### Active Working Memory Scratchpad:\n" + "\n".join(work_lines))

        # 3. Relevant Past Episodes
        relevant_episodes = self.recall_recent_episodes(limit=3, query=prompt[:50] if len(prompt) > 10 else None)
        if relevant_episodes:
            ep_lines = [
                f"- Action: {e['action']} | Outcome: {e['outcome'][:80]} | {'Success' if e['success'] else 'Failed'}"
                for e in relevant_episodes
            ]
            sections.append("### Relevant Past Experiences (Episodic):\n" + "\n".join(ep_lines))

        return "\n\n".join(sections)


# Global singleton instance
unified_memory = UnifiedMemory()
