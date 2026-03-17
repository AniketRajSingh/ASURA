---
name: conversation
description: "Manages conversation history, context retrieval, and system prompt construction for human-AI interaction."
entry_point: __init__.py
---

# Conversation Manager

The central hub for managing the dialogue between the user and the AI. It handles message history, context pruning, and dynamic system prompt generation.

### 🔧 Tools / Functions
- `add_message(message, role)`: Append a new turn to the conversation history.
- `get_recent_context(limit)`: Retrieve recent messages for LLM context injection.
- `search_history(query)`: Query past conversations using text search.
- `get_history_stats()`: Retrieve statistics on message counts and session duration.
- `get_system_prompt()`: Construct the master system prompt including dynamic personality and project rules.

### 📝 Examples
- "What did I ask you earlier?" -> Searches history for matching queries.

### 🛠️ Requirements
- `history.json` for conversation persistence.
