---
name: feature_tracker
description: "Feature evolution tracker. Registers capabilities, detects when a new skill can replace an old one, and tracks upgrade history."
entry_point: tracker.py
---

# Feature Tracker

Manages the lifecycle and evolution of features within ASURA. It maintains a registry of capabilities and uses LLM-based reasoning to suggest upgrades or replacements for existing implementations based on efficiency and performance.

### 🔧 Tools / Functions
- `register_feature(name, category, capability, implementation, version)`: Register a new feature or skill capability.
- `check_for_upgrades()`: Analyze active features and check for better local/lightweight alternatives using LLM.
- `apply_replacement(old_name, new_name, reason)`: Mark a feature as deprecated/replaced and track the upgrade.
- `get_active_features()`: Retrieve a list of all currently active system features.
- `format_tracker_summary()`: Generate a formatted summary of active features and upgrade history.

### 📝 Examples
- "Register the new RAG skill" -> Adds 'rag_memory' to the feature registry.
- "Check for feature upgrades" -> LLM suggests replacing 'gTTS' with 'Kokoro' for better quality.

### 🛠️ Requirements
- `requests`
- `ollama` (configured in `config.py` for upgrade analysis)
