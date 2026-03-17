---
name: todo_manager
description: "AI-driven TODO tracking system for managing improvements, bugfixes, and features."
entry_point: manager.py
---

# TODO Manager

A task tracking system designed for both users and the AI's self-improvement cycle. Supports priorities, categories, and completion tracking.

### 🔧 Tools / Functions
- `add_todo(description, source, priority, category)`: Create a new task.
- `complete_todo(todo_id, result)`: Mark a task as done with a summary of the outcome.
- `get_open_todos(priority, category)`: List tasks based on filters.
- `get_next_todo()`: Retrieve the highest priority task for the AI to work on.
- `format_todos_summary()`: Get a formatted status report of all tasks.

### 📝 Examples
- "Add a TODO to fix the login bug" -> Creates a high-priority bugfix task.
- "Show my tasks" -> Displays the current TODO list.

### 🛠️ Requirements
- `state_manager` for persistent task storage.
