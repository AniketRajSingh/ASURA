---
name: dream_machine
description: "Long-term background goals engine for managing and tracking AI autonomous tasks during idle time."
entry_point: dreamer.py
---

# Dream Machine

A background execution engine for long-term goals. It allows the AI to track progress on complex tasks that persist across sessions.

### 🔧 Tools / Functions
- `add_goal(title: str, description: str = "", priority: int = 5) -> dict`: Add a new long-term goal.
- `update_progress(goal_id: int, step: str, progress: int)`: Mark a step as done and update the percentage of completion.
- `get_active_goals() -> list`: Retrieve all goals currently in "active" status.
- `format_goals() -> str`: Generate a formatted summary with progress bars for TUI/Telegram display.

### 📝 Examples
- "Add a goal to learn Rust" -> Initializes a new goal in the dream machine.
- "Show my active dreams" -> Displays a list of goals with progress status.

### 🛠️ Requirements
- `goals.json` in the data directory for persistence.
