---
name: habit_tracker
description: "Habit and pattern recognition. Logs events, detects peak usage hours/days, and provides proactive insights."
entry_point: tracker.py
---

# Habit Tracker

Tracks and analyzes user interaction patterns within the ASURA ecosystem. It identifies peak usage times and common actions to provide proactive suggestions and insights into system usage.

### 🔧 Tools / Functions
- `log_event(event_type, details)`: Log a usage event with timestamp, hour, and day metadata.
- `get_patterns()`: Analyze logged events to find peak hours, peak days, and top actions.
- `get_proactive_insight()`: Generate a text insight if the current time matches peak activity patterns.
- `format_habits()`: Generate a human-readable Markdown summary of habit patterns.

### 📝 Examples
- "Show my usage patterns" -> Displays peak hours and most frequent actions.
- "What's my most active day?" -> "Your peak day is Wednesday."

### 🛠️ Requirements
- None (Uses local `usage_patterns.json` for storage)
