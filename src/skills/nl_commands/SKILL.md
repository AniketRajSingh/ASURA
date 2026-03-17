---
name: nl_commands
description: "Translates natural language messages into specific internal skill function calls using regex pattern matching."
entry_point: parser.py
---

# Natural Language Commands

A parser that maps human-intent messages (e.g., "check my emails") to specific internal skill function calls. It uses a registry of regex patterns to detect intents and extract relevant arguments.

### 🔧 Tools / Functions
- `parse_intent(message)`: Analyzes a string to find a matching skill and function. Returns a dictionary with match status, skill name, and function name.
- `extract_args(message, intent)`: Processes the raw message to extract arguments for the identified function, stripping common filler words.

### 📝 Examples
- "Check my emails" -> `{"matched": True, "skill": "email_manager", "function": "check_inbox", ...}`
- "Add a todo to buy milk" -> `{"matched": True, "skill": "todo_manager", "function": "add_todo", "needs_args": True, ...}`

### 🛠️ Requirements
- `re` module (standard library)
