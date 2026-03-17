# ============================================================
# skills/memory/procedural.py — Procedural Memory Layer
#
# Learned patterns: records trigger→action chains that worked.
# When the AI faces a similar situation, it recalls what
# sequence of tools/actions led to success in the past.
# ============================================================

import os
import json
from datetime import datetime, timezone
from typing import Optional

from settings import settings as config
from skills.logger import log_audit

_PROCEDURES_PATH = os.path.join(config.MEMORY_STORE_DIR, "procedures.json")
_procedures: list[dict] = []
_loaded = False


def _load():
    """Load procedures from disk."""
    global _procedures, _loaded
    if _loaded:
        return
    if os.path.isfile(_PROCEDURES_PATH):
        try:
            with open(_PROCEDURES_PATH, "r", encoding="utf-8") as f:
                _procedures = json.load(f)
        except (json.JSONDecodeError, IOError):
            _procedures = []
    _loaded = True


def _save():
    """Persist procedures to disk."""
    os.makedirs(os.path.dirname(_PROCEDURES_PATH), exist_ok=True)
    with open(_PROCEDURES_PATH, "w", encoding="utf-8") as f:
        json.dump(_procedures, f, indent=2, ensure_ascii=False, default=str)


def store_procedure(
    trigger: str,
    action_chain: list[str],
    outcome: str,
    success: bool,
    context: dict = None,
) -> str:
    """
    Record a learned procedure (trigger → actions → outcome).

    Args:
        trigger: The situation / user request that triggered this chain
        action_chain: Ordered list of tool calls that were executed
        outcome: What happened as a result
        success: Whether it achieved the desired goal
        context: Optional metadata

    Returns:
        Procedure ID
    """
    _load()

    proc_id = f"proc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"

    # Check for similar existing procedure and update success rate
    for existing in _procedures:
        if _triggers_match(existing["trigger"], trigger):
            # Update existing procedure's success rate
            existing["executions"] += 1
            if success:
                existing["successes"] += 1
            existing["success_rate"] = existing["successes"] / existing["executions"]
            existing["last_used"] = datetime.now(timezone.utc).isoformat()
            if success and len(action_chain) < len(existing.get("action_chain", [])):
                # Found a shorter successful path — update
                existing["action_chain"] = action_chain
                existing["outcome"] = outcome
            _save()
            log_audit("PROCEDURAL", f"Updated procedure: {existing['id']} (rate: {existing['success_rate']:.0%})")
            return existing["id"]

    # New procedure
    procedure = {
        "id": proc_id,
        "trigger": trigger,
        "action_chain": action_chain,
        "outcome": outcome,
        "success": success,
        "executions": 1,
        "successes": 1 if success else 0,
        "success_rate": 1.0 if success else 0.0,
        "context": context or {},
        "created": datetime.now(timezone.utc).isoformat(),
        "last_used": datetime.now(timezone.utc).isoformat(),
    }

    _procedures.append(procedure)
    _save()
    log_audit("PROCEDURAL", f"Stored new procedure: {trigger[:60]} -> {len(action_chain)} actions")
    return proc_id


def recall_procedures(
    situation: str,
    min_score: float = 0.3,
    limit: int = 5,
) -> list[dict]:
    """
    Find procedures using a simplified semantic overlap score.
    Uses Jaccard similarity between word sets after basic normalization.
    """
    _load()
    if not _procedures:
        return []

    scored = []
    # Normalize situation: remove punctuation, lowercase
    s_norm = re.sub(r'[^\w\s]', '', situation.lower())
    s_words = set(s_norm.split())

    for proc in _procedures:
        if proc.get("success_rate", 0) < 0.2: # Don't recall consistent failures
            continue
            
        t_norm = re.sub(r'[^\w\s]', '', proc["trigger"].lower())
        t_words = set(t_norm.split())
        
        # Jaccard similarity + success weighting
        intersection = s_words.intersection(t_words)
        union = s_words.union(t_words)
        
        if not union: continue
        
        similarity = len(intersection) / len(union)
        # Weight by success rate to prioritize proven procedures
        score = similarity * (0.5 + 0.5 * proc.get("success_rate", 1.0))
        
        if score >= min_score:
            scored.append((score, proc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [proc for _, proc in scored[:limit]]


def get_procedures_summary() -> str:
    """Get a human-readable summary of all learned procedures."""
    _load()

    if not _procedures:
        return "No learned procedures yet."

    lines = [f"Learned procedures ({len(_procedures)} total):\n"]
    for proc in sorted(_procedures, key=lambda p: p.get("success_rate", 0), reverse=True)[:10]:
        rate = proc.get("success_rate", 0)
        trigger = proc["trigger"][:50]
        n_actions = len(proc.get("action_chain", []))
        execs = proc.get("executions", 0)
        lines.append(f"  [{rate:.0%}] {trigger} -> {n_actions} steps ({execs} runs)")

    return "\n".join(lines)


def _triggers_match(t1: str, t2: str) -> bool:
    """Check if two triggers are essentially the same (strict threshold)."""
    w1 = set(re.sub(r'[^\w\s]', '', t1.lower()).split())
    w2 = set(re.sub(r'[^\w\s]', '', t2.lower()).split())
    if not w1 or not w2: return False
    
    intersection = w1.intersection(w2)
    union = w1.union(w2)
    return (len(intersection) / len(union)) > 0.7


def count_procedures() -> int:
    """Count total stored procedures."""
    _load()
    return len(_procedures)
