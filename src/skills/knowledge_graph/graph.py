# ============================================================
# skills/knowledge_graph/graph.py — Knowledge Graph
# Structured graph of concepts, relationships, and entities
# ============================================================

import os
import json
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit


def _load_graph() -> dict:
    if os.path.isfile(config.KNOWLEDGE_GRAPH_PATH):
        try:
            with open(config.KNOWLEDGE_GRAPH_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"nodes": {}, "edges": []}


def _save_graph(graph: dict):
    with open(config.KNOWLEDGE_GRAPH_PATH, "w") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)


def add_node(name: str, category: str = "concept", properties: dict = None) -> dict:
    """Add a node (concept, entity, skill, etc.) to the knowledge graph."""
    graph = _load_graph()
    node_id = name.lower().replace(" ", "_")

    node = {
        "id": node_id,
        "name": name,
        "category": category,
        "properties": properties or {},
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
    }
    graph["nodes"][node_id] = node
    _save_graph(graph)
    log_audit("KG", f"Node added: {name} [{category}]")
    return node


def add_edge(from_node: str, to_node: str, relation: str, weight: float = 1.0):
    """Add a relationship between two nodes."""
    graph = _load_graph()
    from_id = from_node.lower().replace(" ", "_")
    to_id = to_node.lower().replace(" ", "_")

    edge = {
        "from": from_id,
        "to": to_id,
        "relation": relation,
        "weight": weight,
        "created": datetime.now().isoformat(),
    }
    graph["edges"].append(edge)
    _save_graph(graph)
    log_audit("KG", f"Edge: {from_node} --[{relation}]--> {to_node}")


def query_node(name: str) -> dict | None:
    """Get a node and its connections."""
    graph = _load_graph()
    node_id = name.lower().replace(" ", "_")
    node = graph["nodes"].get(node_id)

    if not node:
        return None

    # Find connected edges
    connections = []
    for edge in graph["edges"]:
        if edge["from"] == node_id:
            target = graph["nodes"].get(edge["to"], {})
            target_name = target.get("name") or target.get("metadata", {}).get("label") or edge["to"]
            connections.append({"direction": "outgoing", "relation": edge["relation"],
                                "target": target_name})
        elif edge["to"] == node_id:
            source = graph["nodes"].get(edge["from"], {})
            source_name = source.get("name") or source.get("metadata", {}).get("label") or edge["from"]
            connections.append({"direction": "incoming", "relation": edge["relation"],
                                "source": source_name})

    return {**node, "connections": connections}


def search_nodes(query: str, category: str = None) -> list[dict]:
    """Search nodes by name or category."""
    graph = _load_graph()
    query_lower = query.lower()
    results = []

    for nid, node in graph["nodes"].items():
        name = node.get("name") or node.get("metadata", {}).get("label") or nid
        if query_lower in name.lower() or query_lower in nid:
            if category is None or node.get("category") == category:
                results.append(node)

    return results


def get_graph_stats() -> str:
    graph = _load_graph()
    nodes = len(graph.get("nodes", {}))
    edges = len(graph.get("edges", []))

    categories = {}
    for node in graph.get("nodes", {}).values():
        cat = node.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1

    lines = [f"🕸️ *Knowledge Graph*\n", f"Nodes: {nodes} | Edges: {edges}\n"]
    if categories:
        lines.append("*Categories:*")
        for cat, count in sorted(categories.items()):
            lines.append(f"  • {cat}: {count}")
    return "\n".join(lines)


def build_context_from_topic(topic: str) -> str:
    """Build context from the knowledge graph for a given topic."""
    results = search_nodes(topic)
    if not results:
        return ""

    lines = ["Related knowledge:"]
    for node in results[:5]:
        full = query_node(node["name"])
        lines.append(f"- {node['name']} [{node.get('category', '')}]")
        if full and full.get("connections"):
            for conn in full["connections"][:3]:
                if conn["direction"] == "outgoing":
                    lines.append(f"  → {conn['relation']} → {conn['target']}")
                else:
                    lines.append(f"  ← {conn['relation']} ← {conn['source']}")

    return "\n".join(lines)
