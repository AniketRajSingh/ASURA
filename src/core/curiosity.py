import os
import json
import time
import asyncio
from typing import Optional, Dict, Any
from skills.logger import log_audit, log_app
import config

DEFAULT_SUPPORTED_MIMES = [
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "audio/wav", "audio/ogg", "audio/mpeg", "audio/mp3",
    "application/pdf", "text/plain", "text/markdown", "application/json"
]

class CuriosityEngine:
    """
    Sovereign Curiosity Layer:
    Autonomously detects novel inputs (files, complex intents) and triggers 
    capability expansion or architectural research.
    """

    def __init__(self, notify_fn=None):
        self._notify_fn = notify_fn
        self._curiosity_threshold = 0.7
        self._last_discovery = 0
        self._discovery_cooldown = 3600 # 1 hour

    def start(self):
        """Start background curiosity routines if any."""
        log_app("Sovereign Curiosity engine started")
        # Background idle curiosity could be added here in the future
        pass

    async def sense_wonder(self, message: str, metadata: Dict[str, Any], session_id: str) -> Optional[str]:
        """
        Analyze an interaction for 'Discovery Potential'.
        Returns a 'Curiosity Prompt' if something novel is found.
        """
        # 1. Detection: Unknown File Types
        supported_mimes = getattr(config, "SUPPORTED_MIMES", DEFAULT_SUPPORTED_MIMES)
        if metadata.get("file_type") and metadata["file_type"] not in supported_mimes:
            return self._trigger_skill_synthesis(f"Unknown file type received: {metadata['file_type']}", message)

        # 2. Semantic Novelty (Pattern matching for 'how do I', 'can you' for missing tools)
        if any(trigger in message.lower() for trigger in ["can you learn", "implement", "how do you handle"]):
            # Check if this maps to an existing tool
            return self._trigger_architectural_research(message)

        return None

    def _trigger_skill_synthesis(self, reason: str, context: str) -> str:
        log_audit("CURIOSITY", f"Synthesizing curiosity: {reason}")
        return f"""[SOVEREIGN CURIOSITY]
I detected a novel element: {reason}.
My current architecture doesn't have a specialized handler for this.
I'm initiating an autonomous research phase to synthesize a new capability or skill that could handle this optimally. 
What do you think of me evolving this way?"""

    def _trigger_architectural_research(self, context: str) -> str:
        log_audit("CURIOSITY", f"Triggering architectural research for: {context}")
        return f"""[SOVEREIGN EVOLUTION]
You just mentioned a capability I don't yet possess: '{context}'. 
Inspired by the OpenClaw architecture, I'm proposing an autonomous self-update to implement this. 
I'll begin a background analysis of my core modules to find the best integration point."""

curiosity_engine = CuriosityEngine()
