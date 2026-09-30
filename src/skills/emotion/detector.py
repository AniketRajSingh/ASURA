# ============================================================
# skills/emotion/detector.py — Emotion-Aware Response Engine
# ============================================================

import re
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit


# Emotion patterns
_PATTERNS = {
    "frustrated": {
        "words": {"fix", "broken", "wrong", "annoying", "ugh", "wtf", "stupid", "hate", "damn", "doesn't work"},
        "patterns": [r"!{2,}", r"\?{2,}", r"why (won't|isn't|doesn't|can't)"],
        "signals": ["short messages", "repeated commands", "exclamation marks"],
    },
    "excited": {
        "words": {"amazing", "awesome", "wow", "love", "perfect", "incredible", "fantastic", "yes", "🔥", "🚀", "💯"},
        "patterns": [r"!{1,}", r"let's go"],
        "signals": ["emojis", "exclamation marks", "enthusiastic words"],
    },
    "tired": {
        "words": {"later", "tomorrow", "tired", "sleepy", "night", "enough", "done for now"},
        "patterns": [r"\.{3,}"],
        "signals": ["late night messages", "trailing off", "brief responses"],
    },
    "curious": {
        "words": {"how", "why", "what if", "explain", "tell me", "learn", "understand", "interesting"},
        "patterns": [r"\?"],
        "signals": ["questions", "exploration"],
    },
    "neutral": {
        "words": set(),
        "patterns": [],
        "signals": [],
    },
}


def detect_emotion(message: str) -> dict:
    """
    Detect emotional state from message content + metadata.
    Returns: {"emotion": str, "confidence": float, "signals": [str]}
    """
    msg_lower = message.lower()
    scores = {}
    signals = {}

    for emotion, data in _PATTERNS.items():
        if emotion == "neutral":
            continue

        score = 0
        sigs = []

        # Word matching
        for word in data["words"]:
            if word in msg_lower:
                score += 2
                sigs.append(f"word: {word}")

        # Pattern matching
        for pattern in data["patterns"]:
            if re.search(pattern, message):
                score += 1
                sigs.append(f"pattern match")

        # Time-based signals
        hour = datetime.now().hour
        if emotion == "tired" and (hour >= 23 or hour < 6):
            score += 3
            sigs.append("late night")

        # Message length signals
        if emotion == "frustrated" and len(message) < 20 and any(c in message for c in "!?"):
            score += 2
            sigs.append("terse + punctuation")

        scores[emotion] = score
        signals[emotion] = sigs

    # Pick highest scoring emotion
    if scores:
        best = max(scores, key=scores.get)
        if scores[best] >= 2:
            confidence = min(scores[best] / 8, 1.0)
            log_audit("EMOTION", f"Detected: {best} ({confidence:.0%})")
            return {"emotion": best, "confidence": confidence, "signals": signals[best]}

    return {"emotion": "neutral", "confidence": 0.5, "signals": []}


def get_adaptive_prefix(emotion: str, confidence: float = 1.0) -> str:
    """Get a response style adaptation based on detected emotion."""
    if confidence < 0.4: return ""
    
    adaptations = {
        "frustrated": "I sense some frustration—let's resolve this with precision. ",
        "excited": "Love the momentum! 🚀 ",
        "tired": "Quick and efficient for you— ",
        "curious": "Intriguing direction! ",
        "neutral": "",
    }
    return adaptations.get(emotion, "")


def should_suggest_break(message: str) -> bool:
    """Check if the user should be suggested to take a break."""
    hour = datetime.now().hour
    emotion = detect_emotion(message)
    return (hour >= 1 and hour < 6) or (emotion["emotion"] == "tired" and emotion["confidence"] > 0.6)
