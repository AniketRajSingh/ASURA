---
name: time_tracker
description: "Lightweight session-based time tracking for monitoring task duration and generating weekly reports."
entry_point: tracker.py
---

# Time Tracker

Keep track of how much time you spend on different tasks. Logs sessions and generates reports to help monitor productivity.

### 🔧 Tools / Functions
- `start_timer(task: str)`: Start a new timing session for a task.
- `stop_timer(task: str)`: End the session and persist the elapsed time.
- `get_weekly_report()`: Generate a summary of time spent on tasks over the last 7 days.

### 📝 Examples
- "Start timer for 'Refactoring'" -> Begins tracking.
- "Stop timer" -> Saves session and displays duration.

### 🛠️ Requirements
- `time_logs.json` for persistent storage.
