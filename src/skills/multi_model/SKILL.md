---
name: multi_model
description: "Task-aware LLM manager for dynamic model selection and capability-based routing."
entry_point: manager.py
---

# Multi-Model Manager

Orchestrates the use of multiple LLM models based on the task at hand (e.g., using a large model for reasoning and a small one for planning).

### 🔧 Tools / Functions
- `get_model(task_type)`: Determine the assigned model for a specific task (chat, vision, coding).
- `generate(prompt, task_type)`: Execute a generation request using the appropriate model.
- `list_available_models()`: Check which models are currently reachable on the provider.
- `format_models_summary()`: Display a map of task-to-model assignments and their availability.

### 📝 Examples
- "Switch to a faster model" -> Adjusts routing via ModelManager.
- "Show configured models" -> Displays the model registry status.

### 🛠️ Requirements
- `model_manager` core module.
- Active LLM provider (Ollama, Groq, or SGLang).
