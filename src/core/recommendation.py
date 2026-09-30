# ============================================================
# core/recommendation.py — Unified Recommendation & Task Store
# ============================================================

import os
import uuid
import time
from typing import List, Dict, Optional
from core.state_manager import state
from skills.logger import log_audit, log_app

class Recommendation:
    def __init__(self, content: str, source: str = "system", priority: int = 1, 
                 autonomous: bool = False, metadata: Dict = None, 
                 id: str = None, status: str = "pending", **kwargs):
        self.id = id or str(uuid.uuid4())[:8]
        self.content = content
        self.source = source
        self.priority = priority # 1 (Low) to 5 (Critical)
        self.autonomous = autonomous
        self.status = status # pending, approved, executing, done, dismissed
        self.metadata = metadata or {}
        self.created_at = kwargs.get("created_at") or time.time()

    def to_dict(self):
        return self.__dict__

class RecommendationStore:
    def __init__(self):
        self._section = "recommendations"
        self._ensure_init()

    def _ensure_init(self):
        current_state = state.get_section(self._section)
        if current_state is None:
            state.update_section(self._section, {"items": []})

    def add(self, content: str, source: str = "proactive", priority: int = 1, 
            autonomous: bool = False, metadata: Dict = None) -> Recommendation:
        rec = Recommendation(content, source, priority, autonomous, metadata)
        items = state.get_section(self._section).get("items", [])
        items.append(rec.to_dict())
        state.update_section(self._section, {"items": items})
        log_audit("RECOMMENDATION_ADD", f"Source: {source} | Content: {content[:50]}")
        return rec

    def get_pending(self) -> List[Recommendation]:
        items = state.get_section(self._section).get("items", [])
        return [Recommendation(**i) for i in items if i["status"] == "pending"]

    def get_approved(self) -> List[Recommendation]:
        items = state.get_section(self._section).get("items", [])
        return [Recommendation(**i) for i in items if i["status"] == "approved"]

    def update_status(self, id: str, status: str):
        items = state.get_section(self._section).get("items", [])
        updated = False
        for i in items:
            if i["id"] == id:
                i["status"] = status
                updated = True
                break
        if updated:
            state.update_section(self._section, {"items": items})

    def update_content(self, id: str, content: str):
        items = state.get_section(self._section).get("items", [])
        updated = False
        for i in items:
            if i["id"] == id:
                i["content"] = content
                updated = True
                break
        if updated:
            state.update_section(self._section, {"items": items})

    def remove(self, id: str):
        items = state.get_section(self._section).get("items", [])
        items = [i for i in items if i["id"] != id]
        state.update_section(self._section, {"items": items})

    def clear_all(self, status: Optional[str] = None):
        """Clear all recommendations, or only those with a specific status."""
        if status:
            items = state.get_section(self._section).get("items", [])
            items = [i for i in items if i["status"] != status]
            state.update_section(self._section, {"items": items})
        else:
            state.update_section(self._section, {"items": []})
        log_audit("RECOMMENDATION_CLEAR", f"Cleared recommendations (status={status})")

# Global singleton
recommendation_store = RecommendationStore()
