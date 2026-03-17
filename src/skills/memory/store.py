# ============================================================
# core/memory.py — RAG Persistent Memory
# Adapted from faculty-llm-iiitd/scripts/update_db.py
# Uses FAISS vector store + sentence embeddings for recall.
# ============================================================

import os
import json
import hashlib
from datetime import datetime
from typing import Optional, Any
import threading
from settings import settings as config
from skills.logger import log_audit, log_app

_MEMORY_LOCK = threading.Lock()

# ─── Lazy-loaded heavy imports ──────────────────────────────
_index = None
_documents = []
_embed_model = None
_DOCS_PATH = os.path.join(config.MEMORY_STORE_DIR, "documents.json")
_INDEX_PATH = os.path.join(config.MEMORY_STORE_DIR, "faiss.index")
_BATCH_MODE = False
_NEEDS_REBUILD = False
MAX_MEMORIES = 1000  # Prevent unbounded growth


def _rebuild_index():
    """Rebuild the FAISS index from the documents list."""
    global _index
    if not _documents:
        return

    import faiss
    import numpy as np

    log_app(f"Memory: rebuilding index for {len(_documents)} documents...")
    temp_index = None
    
    # Work on a copy of documents to avoid "dictionary changed size"
    with _MEMORY_LOCK:
        docs_copy = list(_documents)
    
    for doc in docs_copy:
        # Use cached embedding if available
        embedding = None
        if "embedding" in doc:
            embedding = np.array(doc["embedding"], dtype=np.float32)
        else:
            embedding = _get_embedding(doc["text"])
            if embedding is not None:
                doc["embedding"] = embedding.tolist() # Cache as list for JSON
        
        if embedding is not None:
            if temp_index is None:
                dim = len(embedding)
                temp_index = faiss.IndexFlatIP(dim)
            
            # Normalize for cosine similarity
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            temp_index.add(np.array([embedding]))
    
    _save_store() # Final save to persist any new embeddings
    
    _index = temp_index
    if _index:
        faiss.write_index(_index, _INDEX_PATH)
        log_app(f"Memory: index rebuilt with {_index.ntotal} vectors")


def _load_store():
    """Load the FAISS index and document store from disk."""
    global _index, _documents

    # Load documents
    if os.path.isfile(_DOCS_PATH):
        with open(_DOCS_PATH, "r", encoding="utf-8") as f:
            _documents = json.load(f)
    else:
        _documents = []

    # Load FAISS index
    if os.path.isfile(_INDEX_PATH):
        try:
            import faiss
            _index = faiss.read_index(_INDEX_PATH)
            log_app(f"Memory: loaded {_index.ntotal} vectors from FAISS index")
        except Exception as e:
            log_app(f"Memory: failed to load FAISS index: {e}, will rebuild if documents exist")
            _index = None
    else:
        _index = None

    # Rebuild index if missing but documents exist
    if _index is None and _documents:
        log_app(f"Memory: FAISS index missing or failed, rebuilding from {len(_documents)} documents...")
        _rebuild_index()


def _save_store():
    """Persist documents and FAISS index to disk."""
    os.makedirs(config.MEMORY_STORE_DIR, exist_ok=True)

    with open(_DOCS_PATH, "w", encoding="utf-8") as f:
        json.dump(_documents, f, indent=2, ensure_ascii=False)

    if _index is not None:
        try:
            import faiss
            faiss.write_index(_index, _INDEX_PATH)
        except ImportError:
            pass


def _get_embedding(text: str, retries: int = 3):
    """
    Get embedding vector using Ollama's nomic-embed-text model.
    Includes retries and backoff for high-concurrency safety.
    """
    import time
    for attempt in range(retries):
        try:
            import requests
            import numpy as np
            
            host_ip = config.OLLAMA_BASE_URL.split("//")[-1].split(":")[0]
            embedding_url = f"http://{host_ip}:11434/api/embed"
            
            resp = requests.post(
                embedding_url,
                json={"model": "nomic-embed-text", "input": text},
                timeout=30
            )
            resp.raise_for_status()
            embeddings = resp.json().get("embeddings", [])
            if embeddings:
                return np.array(embeddings[0], dtype=np.float32)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1 * (attempt + 1)) # Exponential backoff
                continue
            log_app(f"Memory: Ollama embedding failed after {retries} attempts: {e}")
    
    return None


def initialize():
    """Initialize the memory store. Call once at startup."""
    log_audit("MEMORY", "Initializing persistent memory store")
    with _MEMORY_LOCK:
        _load_store()
    log_audit("MEMORY", f"Memory initialized with {len(_documents)} documents")


def store_memory(text: str, metadata: Optional[dict] = None) -> str:
    """
    Store a text chunk in persistent memory with optional metadata.
    Returns the document ID (hash).
    """
    global _index, _documents

    if not _documents:
        with _MEMORY_LOCK:
            _load_store()

    doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]

    # Check for duplicates
    for doc in _documents:
        if doc["id"] == doc_id:
            log_app(f"Memory: duplicate document skipped — {doc_id}")
            return doc_id

    doc = {
        "id": doc_id,
        "text": text,
        "metadata": metadata or {},
        "timestamp": datetime.now().isoformat(),
    }
    with _MEMORY_LOCK:
        _documents.append(doc)
        
        # Enforce limit
        if len(_documents) > MAX_MEMORIES:
            _documents = _documents[-MAX_MEMORIES:]
            _NEEDS_REBUILD = True

    # Add to FAISS index if available (OFFLOADED TO BACKGROUND if not in batch mode)
    if _BATCH_MODE:
        # In batch mode, we handle embedding synchronously or defer it
        # but _index.add might be expensive. For now, since we have caching,
        # we'll just skip the bg thread and let _rebuild_index handle it at the end.
        _NEEDS_REBUILD = True
    else:
        def _bg_embed():
            try:
                embedding = _get_embedding(text)
                if embedding is not None:
                    import faiss
                    import numpy as np
                    global _index
                    with _MEMORY_LOCK:
                        if _index is None:
                            dim = len(embedding)
                            _index = faiss.IndexFlatIP(dim)
                        norm = np.linalg.norm(embedding)
                        if norm > 0:
                            embedding = embedding / norm
                        _index.add(np.array([embedding]))
                    doc["embedding"] = embedding.tolist() # Cache it!
                    _save_store()
                    log_audit("MEMORY", f"Background indexing complete for {doc_id}")
            except Exception as e:
                log_app(f"Memory: Background embedding failed: {e}")

        import threading
        threading.Thread(target=_bg_embed, daemon=True).start()

    log_audit("MEMORY", f"Stored document {doc_id} (Indexing offloaded)")
    return doc_id


def recall(query: str, top_k: int = 5) -> list[dict]:
    """
    Semantic search across stored memories.
    Returns top_k most relevant documents.
    """
    if not _documents:
        _load_store()

    if not _documents:
        return []

    embedding = _get_embedding(query)

    # FAISS path
    if embedding is not None and _index is not None and _index.ntotal > 0:
        try:
            import numpy as np

            # Normalize query
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            k = min(top_k, _index.ntotal)
            # Guard: dimension mismatch causes AssertionError in FAISS C++
            if _index.d != len(embedding):
                log_app(f"Memory: FAISS dimension mismatch (index={_index.d}, embed={len(embedding)}), using keyword fallback")
                raise AssertionError("dimension mismatch")
            with _MEMORY_LOCK:
                scores, indices = _index.search(np.array([embedding]), k)

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if 0 <= idx < len(_documents):
                    doc = _documents[idx].copy()
                    doc["score"] = float(score)
                    results.append(doc)

            log_audit("MEMORY", f"Recall: {len(results)} results for '{query[:50]}...'")
            return results
        except Exception as e:
            log_app(f"Memory: FAISS search error: {type(e).__name__}: {e}")

    # Fallback: simple keyword matching
    query_lower = query.lower()
    scored = []
    for doc in _documents:
        text_lower = doc["text"].lower()
        # Count keyword overlaps
        score = sum(1 for word in query_lower.split() if word in text_lower)
        if score > 0:
            d = doc.copy()
            d["score"] = score
            scored.append(d)

    scored.sort(key=lambda x: x["score"], reverse=True)
    results = scored[:top_k]
    log_audit("MEMORY", f"Recall (keyword fallback): {len(results)} results")
    return results


def store_update_log(update_summary: str) -> str:
    """Store a self-update event in memory for learning."""
    return store_memory(
        text=update_summary,
        metadata={"type": "self_update", "timestamp": datetime.now().isoformat()},
    )


def get_all_memories_summary() -> str:
    """Get a brief summary of all stored memories (for self-updater context)."""
    if not _documents:
        _load_store()

    if not _documents:
        return "No memories stored yet."

    lines = [f"Total memories: {len(_documents)}\n"]
    for doc in _documents[-10:]:  # Last 10 entries
        snippet = doc["text"][:80].replace("\n", " ")
        meta_type = doc.get("metadata", {}).get("type", "general")
        lines.append(f"  [{meta_type}] {snippet}...")

    return "\n".join(lines)


def list_all(limit: int = 50) -> list[dict]:
    """Retrieve the most recent documents for the dashboard view."""
    if not _documents:
        _load_store()
    return _documents[-limit:]
def get_memory_store():
    """Returns the internal document list for the dashboard."""
    if not _documents:
        _load_store()
    return _documents


def get_freshness_score() -> float:
    """Calculate intelligence freshness based on recent activity."""
    if not _documents:
        return 0.0
    try:
        # Base score 94%, bonus for recent memories
        latest = datetime.fromisoformat(_documents[-1]["timestamp"])
        diff = datetime.now() - latest
        if diff.days == 0:
            return min(100.0, 94.0 + (max(0, 6 - (diff.seconds // 3600)) * 1.0))
    except:
        pass
    return 94.0


def prune_memories(filter_fn) -> int:
    """
    Remove memories that match the filter function.
    filter_fn(doc) -> bool
    Returns the number of removed documents.
    """
    global _documents, _index, _NEEDS_REBUILD
    before = len(_documents)
    _documents = [d for d in _documents if not filter_fn(d)]
    
    removed = before - len(_documents)
    if removed > 0:
        log_audit("MEMORY", f"Pruned {removed} memories")
        _save_store()
        if _BATCH_MODE:
            _NEEDS_REBUILD = True
        else:
            _rebuild_index()
    return removed


class batch_mode:
    """Context manager to defer index rebuilding during multiple mutations."""
    def __enter__(self):
        global _BATCH_MODE
        _BATCH_MODE = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _BATCH_MODE, _NEEDS_REBUILD
        _BATCH_MODE = False
        if _NEEDS_REBUILD:
            _rebuild_index()
            _NEEDS_REBUILD = False


def delete_by_metadata(key: str, value: Any) -> int:
    """Convenience helper to delete memories by metadata key/value match."""
    return prune_memories(lambda d: d.get("metadata", {}).get(key) == value)


def surgery_cleanup():
    """Remove corrupted or invalid memories (e.g., from format specifier bug)."""
    return prune_memories(lambda d: "Invalid format specifier" in d["text"])
