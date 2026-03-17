---
name: knowledge_graph
description: "Maintains a structured graph of concepts, entities, and their relationships for context retrieval."
entry_point: graph.py
---

# Knowledge Graph Skill

Manages a persistent knowledge base structured as a directed graph. It allows for the creation of nodes (representing entities or concepts) and edges (representing relationships), enabling complex context retrieval and reasoning support for the system.

### 🔧 Tools / Functions
- `add_node(name, category="concept", properties=None)`: Adds a new node to the knowledge graph with optional properties.
- `add_edge(from_node, to_node, relation, weight=1.0)`: Creates a directed relationship between two existing nodes.
- `query_node(name)`: Retrieves detailed information about a specific node, including its incoming and outgoing connections.
- `search_nodes(query, category=None)`: Searches for nodes by name or category matching the provided query.
- `get_graph_stats()`: Returns a formatted summary of the number of nodes, edges, and category distributions.
- `build_context_from_topic(topic)`: Generates a text-based context string from the graph related to a specific topic for LLM use.

### 📝 Examples
- "Add a concept node for 'Machine Learning'" -> Creates a new node in the graph.
- "Link 'Python' to 'Programming Language' with relation 'is a'" -> Creates an edge between the two nodes.
- "Show stats for the knowledge graph" -> Displays the current count of nodes and edges.

### 🛠️ Requirements
- Persistent storage at `config.KNOWLEDGE_GRAPH_PATH`
