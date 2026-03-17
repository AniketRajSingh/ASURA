---
name: emotion
description: "Emotion-aware response engine that detects user sentiment and adapts AI personality and style."
entry_point: detector.py
---

# Emotion Engine

Analyzes user input for emotional signals and provides personality adaptations to make the AI more empathetic and responsive to user state.

### 🔧 Tools / Functions
- `detect_emotion(message: str) -> dict`: Analyzes tone, punctuation, and keywords to identify emotional state.
- `get_adaptive_prefix(emotion: str) -> str`: Returns a contextual prefix to modify the AI's response style.
- `should_suggest_break(message: str) -> bool`: Monitors for fatigue or late-night usage to suggest user rest.

### 📝 Examples
- "Detect emotion in 'This is so frustrating!'" -> Identifies 'frustrated' with high confidence.

### 🛠️ Requirements
- None (Pattern-based detection).
