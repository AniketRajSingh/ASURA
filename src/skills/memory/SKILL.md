---
name: memory
description: "Multi-layered RAG memory system featuring semantic (FAISS), episodic, and procedural storage."
entry_point: store.py
---

# Memory Skill

Provides a sophisticated, multi-layered persistent memory system for the AI. It uses FAISS vector stores for semantic retrieval (RAG), a JSONL-based episodic store for timestamped events, and a procedural store for learning successful action chains over time.

### 🔧 Tools / Functions
- `store_memory(text, metadata=None)`: Stores a text chunk in the semantic memory using FAISS embeddings for future recall.
- `recall(query, top_k=5)`: Performs a semantic search across stored memories and returns the most relevant matches.
- `store_episode(event, context=None, category="general", importance=0.5)`: Records a timestamped event in the episodic memory.
- `recall_episodes(query=None, category=None, limit=20)`: Retrieves past events based on keyword, category, or time filters.
- `store_procedure(trigger, action_chain, outcome, success, context=None)`: Records a sequence of actions taken in response to a trigger for future optimization.
- `recall_procedures(situation, min_score=0.3, limit=5)`: Suggests previously successful action chains for a given situation.
- `get_all_memories_summary()`: Generates a high-level summary of all memory layers for system context.

### 📝 Examples
- "Remember that the user's favorite color is blue" -> Stores the fact in semantic memory.
- "What did we do yesterday?" -> Recalls events from episodic memory.
- "How did we fix the last dependency error?" -> Retrieves a successful procedure from procedural memory.

### 🛠️ Requirements
- `faiss-cpu` or `faiss-gpu` library
- `sentence-transformers` or access to an embedding API (e.g., Ollama)
- Persistent storage directory at `config.MEMORY_STORE_DIR`
