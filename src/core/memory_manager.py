"""
Sovereign Multi‑Layer Memory Manager
====================================

This module implements a lightweight yet extensible in‑memory and persistent
storage system for an autonomous AI.  It separates short‑term conversation
state (handled elsewhere) from mid‑term episodic memory and a long‑term
*Vault* that stores permanent facts.  The Vault is backed by a JSON file
(`identity.json`) located in the directory configured via
`config.MEMORY_STORE_DIR`.  The module is intentionally self‑contained so
that it can be unit‑tested in isolation.

Key Features
------------

* **Layered Recall** – Queries first hit the Vault, then fall back to an
  optional semantic RAG layer provided by the *skills* package.
* **Smart Fact Management** – When adding a fact the system uses a
  lightweight language‑model prompt to deduplicate, update or merge
  similar entries.
* **Caching** – The Vault is cached in memory to avoid repeated disk I/O.
  Cache invalidation can be forced by callers.
* **Extensible API** – Exposes a clean class API that other skills can
  import (`memory_manager`) without needing to understand the underlying
  persistence details.

Usage Example
-------------

```python
from core.memory_manager import memory_manager

# Store a new fact
await memory_manager.remember_fact("I was born in 1990.")

# Retrieve information
print(await memory_manager.recall("when was I born?"))
```

"""

import os
import json
from settings import settings as config
import asyncio
import fcntl
from typing import List, Dict
from datetime import datetime, timezone
from skills.logger import log_audit, log_app
from core.llm import call_llm


def _get_vault_path() -> str:
    """Return the absolute path to the persistent Vault file."""
    return os.path.join(config.MEMORY_STORE_DIR, "identity.json")


class SovereignMemory:
    """Orchestrates multi‑layer recall and storage."""

    # Atomic locks for thread-safety during parallel access
    _vault_lock = asyncio.Lock()
    _vault_cache = None  # type: Dict | None
    _last_load_time: float = 0

    @classmethod
    def initialize(cls) -> None:
        """Ensure the Vault file exists."""
        path = _get_vault_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump({"master_identity": {}, "permanent_facts": []}, f, indent=2)

    @classmethod
    async def _load_vault(cls, force: bool = False) -> Dict:
        """Load the Vault from disk with caching and async locking."""
        async with cls._vault_lock:
            path = _get_vault_path()
            if not force and cls._vault_cache is not None:
                if os.path.exists(path) and os.path.getmtime(path) <= cls._last_load_time:
                    return cls._vault_cache

            cls.initialize()
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        # Non-blocking check for file lock
                        fcntl.flock(f, fcntl.LOCK_SH)
                        try:
                            cls._vault_cache = json.load(f)
                            cls._last_load_time = os.path.getmtime(path)
                            return cls._vault_cache
                        finally:
                            fcntl.flock(f, fcntl.LOCK_UN)
                except Exception as e:
                    log_app(f"Vault load error: {e}")
            return {"master_identity": {}, "permanent_facts": []}

    @classmethod
    async def _save_vault(cls, data: Dict) -> None:
        """Persist the Vault to disk with async locking."""
        async with cls._vault_lock:
            path = _get_vault_path()
            try:
                with open(path, "w") as f:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    try:
                        json.dump(data, f, indent=2)
                    finally:
                        fcntl.flock(f, fcntl.LOCK_UN)
                cls._vault_cache = data
                cls._last_load_time = datetime.now().timestamp()
            except Exception as e:
                log_app(f"Vault save error: {e}")

    @classmethod
    async def remember_fact(cls, fact: str, category: str = "permanent_facts") -> str:
        """
        Store a fact with smart update logic.
        """
        data = await cls._load_vault()
        facts = data.get("permanent_facts", [])

        # 1. Exact match check (instant)
        if fact in [x["fact"] for x in facts if x["category"] == category]:
            return "Fact already vaulted exactly."

        # 2. Smart comparison via LLM
        relevant_for_check = [f for f in facts if f["category"] == category][-10:]
        if relevant_for_check:
            prompt = f"""
Analyze the NEW FACT against the EXISTING FACTS in the category '{category}'.
NEW FACT: "{fact}"

EXISTING FACTS:
{json.dumps([f["fact"] for f in relevant_for_check], indent=2)}

Decide on the action (return ONLY a JSON object):
- "IGNORE": If the NEW FACT is already present (even if worded differently).
- "REPLACE": If the NEW FACT supersedes an existing fact (e.g., age 23 -> 24). List the text of the fact to REMOVE.
- "APPEND": If the NEW FACT is entirely new.
- "MERGE": If the NEW FACT should be combined with an existing fact. List the text of the fact to MERGE with and the NEW COMBINED text.

JSON FORMAT:
{{"action": "REPLACE|APPEND|IGNORE|MERGE", "target": "old text to remove/merge", "merged_text": "new combined text"}}
"""
            try:
                response = await call_llm(
                    prompt, model=config.OLLAMA_MODEL_FAST, format="json"
                )
                log_app(f"Memory: Smart check response: {response}")
                decision = json.loads(response)

                action = decision.get("action", "APPEND").upper()
                target = decision.get("target")
                merged_text = decision.get("merged_text")

                if action == "IGNORE":
                    return "Fact already covered in vault (Smart Check)."

                if action == "REPLACE" and target:
                    data["permanent_facts"] = [
                        f for f in facts if f["fact"].strip().lower() != target.strip().lower()
                    ]
                    log_app(f"Memory: Replacing '{target}' with '{fact}'")

                if action == "MERGE" and target and merged_text:
                    data["permanent_facts"] = [
                        f for f in facts if f["fact"].strip().lower() != target.strip().lower()
                    ]
                    fact = merged_text
                    log_app(f"Memory: Merging '{target}' -> '{fact}'")
            except Exception as e:
                log_app(f"Memory: Smart check failed ({e}), defaulting to APPEND")

        # 3. Final write
        entry = {
            "fact": fact,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
        }
        data["permanent_facts"].append(entry)
        cls._save_vault(data)

        log_audit("VAULT", f"Vaulted Fact: {fact[:50]}...")
        return "SUCCESS: Fact stored and consolidated in Sovereign Vault."

    @classmethod
    async def recall_observations(cls, query: str = "", limit: int = 5) -> str:
        """Retrieve recent or relevant system diagnostics from the side-store."""
        try:
            obs_file = os.path.join(config.DATA_DIR, "system_observations.json")
            if not os.path.exists(obs_file):
                return ""
            
            with open(obs_file, "r") as f:
                data = json.load(f)
            
            if not query:
                relevant = data[-limit:]
            else:
                q_words = query.lower().split()
                # Simple keyword filtering for observations
                relevant = [
                    obs for obs in data 
                    if any(w in obs["observation"].lower() for w in q_words)
                ][-limit:]
                
            if not relevant:
                # If no keywords match, just return newest
                relevant = data[-3:]

            lines = [f"• [{o['timestamp'].split('T')[1][:5]}] {o['observation']}" for o in relevant]
            return "\n".join(lines) if lines else ""
        except Exception as e:
            log_app(f"Observation recall failed: {e}")
            return ""

    @classmethod
    async def recall(cls, query: str, limit: int = 5) -> str:
        """
        Perform a tiered recall:
        1. Search the Sovereign Vault (cached).
        2. Query the Architectural Knowledge Graph (GraphRAG).
        3. Search Episodic Memory (semantic RAG).
        """
        # 1. Vault search (Personal Identity)
        vault_findings: List[str] = []
        data = await cls._load_vault()
        query_lower = query.lower()
        
        # ... (vault search logic remains similar but optimized)
        for item in data.get("permanent_facts", []):
            if query_lower in item["fact"].lower():
                vault_findings.append(f"• [VAULT] {item['fact']}")

        # 2. Knowledge Graph Query (Architecture / File System)
        kg_findings: List[str] = []
        try:
            from core.knowledge_graph import knowledge_graph
            # Smart architectural query
            nodes = knowledge_graph.query_nodes(query)
            for nid, nmeta in nodes[:limit]:
                kg_findings.append(f"• [ARCH] {nmeta.get('label', nid)} ({nmeta.get('type')}): path={nid}")
                # Auto-pull neighbors for context
                neighbors = knowledge_graph.get_neighbors(nid)
                if neighbors:
                    kg_findings.append(f"  └─ Connected to: {', '.join([str(n) for n in neighbors[:3]])}")
        except Exception as e:
            log_app(f"KG recall failed: {e}")

        # 3. Episodic recall (semantic)
        rag_findings: List[str] = []
        try:
            from skills.memory.store import recall as episodic_recall
            results = episodic_recall(query, top_k=limit)
            for r in results:
                snippet = r["text"]
                if not any(snippet[:50] in v for v in vault_findings):
                    rag_findings.append(f"• [EPISODIC] {snippet}")
        except Exception as e:
            log_app(f"RAG recall skipped: {e}")

        # Combine results
        combined: List[str] = []
        if vault_findings:
            combined.append("=== SOVEREIGN VAULT ===")
            combined.extend(vault_findings[:5])
        if kg_findings:
            combined.append("=== ARCHITECTURAL CONTEXT (GraphRAG) ===")
            combined.extend(kg_findings)
        if rag_findings:
            combined.append("=== EPISODIC RECALL ===")
            combined.extend(rag_findings[:limit])

        return "\n".join(combined) if combined else "No relevant memories found."


# Public instance used by other modules
memory_manager = SovereignMemory()