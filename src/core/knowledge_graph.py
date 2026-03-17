import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from skills.logger import log_audit, log_app
from settings import settings as config

class KnowledgeGraph:
    """
    Sovereign Knowledge Graph for ASURA.
    Maps units (nodes) and relationships (edges) to provide architectural self-awareness.
    """
    def __init__(self):
        self.path = os.path.join(config.DATA_DIR, "knowledge_graph.json")
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, str]] = []
        self.load()

    def load(self):
        """Load graph from persistent storage."""
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    self.nodes = data.get("nodes", {})
                    self.edges = data.get("edges", [])
            except Exception as e:
                log_app(f"KG: Load error: {e}")

    def save(self):
        """Persist graph to storage."""
        try:
            with open(self.path, 'w') as f:
                json.dump({"nodes": self.nodes, "edges": self.edges}, f, indent=2)
        except Exception as e:
            log_app(f"KG: Save error: {e}")

    def add_node(self, node_id: str, node_type: str, metadata: Dict[str, Any] = None):
        """Add or update a node in the graph."""
        existing = self.nodes.get(node_id, {})
        category = metadata.get("category", "Uncategorized") if metadata else "Uncategorized"
            
        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "category": category, # e.g. Agents, Skills, Utilities, Infra
            "parent_id": metadata.get("parent_id") if metadata else None,
            "metadata": metadata or {},
            "health": existing.get("health", 100),  # Preserve old health if exists
            "last_probed": datetime.now(timezone.utc).isoformat()
        }

    def add_edge(self, source: str, target: str, relationship: str):
        """Add a directed edge between nodes."""
        # Avoid duplicate edges
        if not any(e for e in self.edges if e["source"] == source and e["target"] == target and e["type"] == relationship):
            self.edges.append({
                "source": source,
                "target": target,
                "type": relationship
            })

    def update_health(self, node_id: str, health: int):
        """Update health status of a node and propagate up."""
        if node_id in self.nodes:
            self.nodes[node_id]["health"] = health
            self.nodes[node_id]["last_probed"] = datetime.now(timezone.utc).isoformat()
            
            # Simple recursive propagation up to parent
            parent_id = self.nodes[node_id].get("parent_id")
            if parent_id and parent_id in self.nodes:
                self._recalculate_parent_health(parent_id)

    def _recalculate_parent_health(self, parent_id: str):
        """Calculate parent health based on worst child health."""
        children = [n for n in self.nodes.values() if n.get("parent_id") == parent_id]
        if children:
            worst_health = min(c.get("health", 100) for c in children)
            self.nodes[parent_id]["health"] = worst_health
            
            # Propagate further up
            grandparent_id = self.nodes[parent_id].get("parent_id")
            if grandparent_id and grandparent_id in self.nodes:
                self._recalculate_parent_health(grandparent_id)

    def get_neighbors(self, node_id: str) -> List[str]:
        """Find all outgoing neighbors of a node."""
        return [e["target"] for e in self.edges if e["source"] == node_id]

    def query_nodes(self, query: str) -> List[Tuple[str, dict]]:
        """
        Search for nodes matching a query based on label, ID, or category.
        Returns a list of (node_id, metadata) tuples.
        """
        query_lower = query.lower()
        results = []
        
        for nid, nmeta in self.nodes.items():
            label = nmeta.get("metadata", {}).get("label", "").lower()
            category = nmeta.get("category", "").lower()
            
            # Match on ID, Label, or Category
            if query_lower in nid.lower() or query_lower in label or query_lower in category:
                results.append((nid, nmeta))
                
        return results

    def clear(self):
        """Wipe the graph (used before a full re-scan)."""
        self.nodes = {}
        self.edges = []
        self.save()

# Global KG instance
knowledge_graph = KnowledgeGraph()
