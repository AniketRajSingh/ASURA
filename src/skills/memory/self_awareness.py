"""
# skills/memory/self_awareness.py — Recursive Self-Documentation Logic
# This skill ensures ASURA "remembers" its own architectural and behavioral standards
# by indexing the documentation suite into the RAG memory pool.
"""

import os
import glob
from settings import settings as config
from skills.logger import log_audit, log_app
from skills.memory.store import store_memory, delete_by_metadata, batch_mode

def index_system_docs():
    """
    Discovers and indexes all key documentation into the RAG store.
    Automates the 'Self-Awareness' loop by ensuring current docs are always recalled.
    """
    log_audit("SELF_AWARENESS", "Starting system documentation indexing cycle")
    
    # 1. Discover docs
    docs_to_index = [
        os.path.join(config.BASE_DIR, "README.md"),
    ]
    
    # Add everything in docs/
    docs_dir = os.path.join(config.BASE_DIR, "docs")
    if os.path.isdir(docs_dir):
        docs_to_index.extend(glob.glob(os.path.join(docs_dir, "*.md")))

    indexed_count = 0
    with batch_mode():
        for doc_path in docs_to_index:
            if os.path.isfile(doc_path):
                try:
                    if index_file(doc_path):
                        indexed_count += 1
                except Exception as e:
                    log_app(f"Self-Awareness: Failed to index {doc_path}: {e}")

    log_audit("SELF_AWARENESS", f"Indexing cycle complete. {indexed_count} documents synchronized.")
    return indexed_count


def index_file(filepath: str) -> bool:
    """
    Indexes a documentation file into the RAG store in semantic chunks.
    Prunes old versions of the same file first.
    """
    filename = os.path.basename(filepath)
    rel_path = os.path.relpath(filepath, config.BASE_DIR)
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
        
    if not content:
        return False

    # Prune old versions to avoid semantic pollution
    delete_by_metadata("source_file", rel_path)
    
    # Simple semantic chunking by headers or double newlines
    # For documentation, we'll try to keep sections together
    chunks = []
    current_chunk = []
    current_size = 0
    MAX_CHUNK_SIZE = 2000 # Characters, roughly 500 tokens
    
    for line in content.split('\n'):
        if (line.startswith('#') or current_size + len(line) > MAX_CHUNK_SIZE) and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = []
            current_size = 0
        
        current_chunk.append(line)
        current_size += len(line)
        
    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    # Index each chunk
    for i, chunk_text in enumerate(chunks):
        if not chunk_text.strip(): continue
        store_memory(
            text=chunk_text,
            metadata={
                "type": "system_docs",
                "source_file": rel_path,
                "chunk": i,
                "total_chunks": len(chunks),
                "title": filename.replace(".md", "").replace("_", " ").title()
            }
        )
    
    log_app(f"Self-Awareness: Indexed {rel_path} in {len(chunks)} chunks")
    return True
