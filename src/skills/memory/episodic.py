# ============================================================
# skills/memory/episodic.py — Episodic Memory Layer
#
# Time-indexed event store: remembers WHAT happened and WHEN.
# Stored as append-only JSONL for efficient sequential access.
# Embeds events in FAISS for semantic search across time.
# ============================================================

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from settings import settings as config
from skills.logger import log_audit

_EPISODES_PATH = os.path.join(config.MEMORY_STORE_DIR, "episodes.jsonl")


def store_episode(
    event: str,
    context: dict = None,
    category: str = "general",
    importance: float = 0.5,
) -> str:
    """
    Record a timestamped event in episodic memory.

    Args:
        event: What happened (human-readable description)
        context: Optional structured data about the event
        category: Event type (e.g., "command", "evolve", "error", "conversation")
        importance: 0.0–1.0, used for memory consolidation/pruning

    Returns:
        Episode ID
    """
    episode = {
        "id": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"),
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "context": context or {},
        "category": category,
        "importance": max(0.0, min(1.0, importance)),
    }

    os.makedirs(os.path.dirname(_EPISODES_PATH), exist_ok=True)
    with open(_EPISODES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(episode, ensure_ascii=False, default=str) + "\n")

    log_audit("EPISODIC", f"Stored: [{category}] {event[:80]}", importance=importance)
    return episode["id"]


def recall_episodes(
    query: str = None,
    category: str = None,
    since: str = None,
    until: str = None,
    min_importance: float = 0.0,
    limit: int = 20,
) -> list[dict]:
    """
    Search episodic memory with optional filters.

    Args:
        query: Text to search for (keyword match)
        category: Filter by category
        since: ISO timestamp — only events after this
        until: ISO timestamp — only events before this
        min_importance: Minimum importance threshold
        limit: Max results (newest first)

    Returns:
        List of episode dicts, newest first.
    """
    if not os.path.isfile(_EPISODES_PATH):
        return []

    episodes = []
    with open(_EPISODES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ep = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Apply filters
            if category and ep.get("category") != category:
                continue
            if since and ep.get("ts", "") < since:
                continue
            if until and ep.get("ts", "") > until:
                continue
            if ep.get("importance", 0) < min_importance:
                continue
            if query:
                q_lower = query.lower()
                text = (ep.get("event", "") + " " + json.dumps(ep.get("context", {}))).lower()
                if q_lower not in text:
                    continue

            episodes.append(ep)

    # Newest first, limited
    return episodes[-limit:][::-1]


def recall_recent(hours: int = 24, limit: int = 10) -> list[dict]:
    """Get episodes from the last N hours."""
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return recall_episodes(since=since, limit=limit)


def get_episode_summary(hours: int = 24) -> str:
    """Get a human-readable summary of recent episodes."""
    episodes = recall_recent(hours=hours, limit=20)
    if not episodes:
        return "No recent episodes recorded."

    lines = [f"Recent activity ({len(episodes)} events in last {hours}h):\n"]
    for ep in episodes:
        ts = ep.get("ts", "?")[:19].replace("T", " ")
        cat = ep.get("category", "?")
        event = ep.get("event", "?")[:80]
        imp = "★" * int(ep.get("importance", 0.5) * 5)
        lines.append(f"  [{ts}] [{cat}] {event} {imp}")

    return "\n".join(lines)


def count_episodes() -> int:
    """Count total stored episodes."""
    if not os.path.isfile(_EPISODES_PATH):
        return 0
    with open(_EPISODES_PATH, "r") as f:
        return sum(1 for line in f if line.strip())
