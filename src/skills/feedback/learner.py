# ============================================================
# skills/feedback/learner.py — Feedback Loop Learning
# Store user feedback and adapt AI behavior over time
# ============================================================

import os
import json
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit


def _load_feedback() -> list[dict]:
    if os.path.isfile(config.FEEDBACK_PATH):
        try:
            with open(config.FEEDBACK_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_feedback(data: list[dict]):
    with open(config.FEEDBACK_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_feedback(context: str, feedback: str, sentiment: str = "neutral"):
    """
    Record user feedback about an AI action.
    sentiment: 'positive' | 'negative' | 'neutral'
    """
    entries = _load_feedback()
    entry = {
        "id": len(entries) + 1,
        "context": context[:200],
        "feedback": feedback,
        "sentiment": sentiment,
        "timestamp": datetime.now().isoformat(),
    }
    entries.append(entry)
    _save_feedback(entries)
    log_audit("FEEDBACK", f"[{sentiment}] {feedback[:80]}")

    # Also store in RAG memory for semantic recall
    try:
        from skills.memory import store_memory
        store_memory(
            f"User feedback ({sentiment}): {feedback}",
            {"type": "feedback", "sentiment": sentiment},
        )
    except Exception:
        pass


def auto_detect_sentiment(message: str) -> str:
    """Detect sentiment from user message keywords."""
    positive = {"good", "great", "nice", "awesome", "perfect", "love", "thanks",
                "excellent", "amazing", "well done", "👍", "❤️", "🔥", "💯"}
    negative = {"bad", "wrong", "terrible", "fix", "broken", "hate", "awful",
                "useless", "stupid", "annoying", "👎", "😡", "🤦"}

    msg_lower = message.lower()
    pos_score = sum(1 for w in positive if w in msg_lower)
    neg_score = sum(1 for w in negative if w in msg_lower)

    if pos_score > neg_score:
        return "positive"
    elif neg_score > pos_score:
        return "negative"
    return "neutral"


def get_learned_preferences() -> str:
    """Extract patterns from feedback to inject into system prompt."""
    entries = _load_feedback()
    if not entries:
        return ""

    positive = [e for e in entries if e["sentiment"] == "positive"]
    negative = [e for e in entries if e["sentiment"] == "negative"]

    lines = []
    if positive:
        lines.append("Things the user likes:")
        for e in positive[-5:]:
            lines.append(f"  - {e['feedback'][:60]}")
    if negative:
        lines.append("Things the user dislikes:")
        for e in negative[-5:]:
            lines.append(f"  - {e['feedback'][:60]}")

    return "\n".join(lines)


def get_feedback_stats() -> str:
    entries = _load_feedback()
    if not entries:
        return "No feedback recorded yet."

    pos = sum(1 for e in entries if e["sentiment"] == "positive")
    neg = sum(1 for e in entries if e["sentiment"] == "negative")
    neu = sum(1 for e in entries if e["sentiment"] == "neutral")

    return (
        f"📊 *Feedback Stats*\n\n"
        f"Total: {len(entries)}\n"
        f"👍 Positive: {pos}\n"
        f"👎 Negative: {neg}\n"
        f"😐 Neutral: {neu}"
    )
