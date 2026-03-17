---
name: graceful_mode
description: "Graceful degradation system. Caches responses and queues tasks when offline, auto-processing them when services return."
entry_point: offline.py
---

# Graceful Mode

Ensures ASURA remains functional during connectivity issues or service outages. It provides a local response cache for LLM queries and a task queue for operations that require online services, automatically processing them when the system detects restored connectivity.

### 🔧 Tools / Functions
- `cache_response(prompt_key, response)`: Store an LLM response locally for future offline hits.
- `get_cached(prompt_key)`: Retrieve a previously cached response based on the prompt.
- `queue_for_later(task, args)`: Queue a task (e.g., an API call) for execution when the system is back online.
- `process_offline_queue()`: Attempt to execute all queued tasks if services (like Ollama) are available.
- `get_offline_status()`: Get a summary of cached responses and queued tasks.

### 📝 Examples
- "Is the LLM down?" -> System provides cached responses for common queries.
- "Queue this email for later" -> Task is added to `offline_queue.json`.

### 🛠️ Requirements
- None (Uses local `response_cache.json` and `offline_queue.json` for persistence)
