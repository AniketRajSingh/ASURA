import os
import ast
import json
import sys
from typing import Dict, List, Any
from core.knowledge_graph import knowledge_graph
from core.declarative_agent_loader import get_agent_loader
from skills.logger import log_audit, log_app
from settings import settings as config

# Standard libraries AND common installed dependencies to ignore in "Broken Edge" checks
KNOWN_LIBS = {
    "os", "sys", "re", "json", "time", "asyncio", "threading", "datetime", 
    "logging", "typing", "pathlib", "subprocess", "shutil", "math", "base64",
    "collections", "queue", "abc", "functools", "traceback", "inspect", "shlex",
    "fastapi", "pydantic", "rich", "httpx", "requests", "psutil", "yaml", "jwt",
    "playwright", "structlog", "faiss", "numpy", "PIL", "wave", "struct", "io",
    "telegram", "uvicorn", "torch", "faster_whisper", "kokoro", "bs4", "hmac", "hashlib"
}

class KnowledgeScanner:
    """
    God-Mode ASURA Knowledge Scanner.
    Optimized with AST caching for near-instant awareness.
    """
    def __init__(self, root_dir: str = None):
        self.root_dir = root_dir or config.SRC_DIR
        self.cache_path = os.path.join(config.DATA_DIR, "scan_cache.json")
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r') as f:
                    return json.load(f)
            except: return {}
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_path, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except: pass

    async def scan_all(self):
        """Perform a full system scan and health probe."""
        log_app("KG: Initiating Absolute Awareness Scan...")
        knowledge_graph.clear()
        
        # 0. Initialize System Hierarchy
        self._init_hierarchy()
        
        # 1. Map High-Level Skills
        self._map_skills()

        # 2. Map Files & Deep Dependencies
        self._scan_directory(self.root_dir)
        
        # 3. Map Specialist Agents
        self._scan_agents()
        
        # 4. Final Verification Phase
        await self.run_health_probes()
        
        knowledge_graph.save()
        self._save_cache()
        log_app("KG: Architectural alignment complete. System is fully self-aware.")

    def _init_hierarchy(self):
        knowledge_graph.add_node("sys_asura", "category", {"label": "ASURA Core"})
        categories = {
            "sys_agents": "Autonomous Specialists",
            "sys_skills": "Functional Capabilities",
            "sys_core": "Architecture Engine",
            "sys_infra": "Support Infrastructure"
        }
        for cid, label in categories.items():
            knowledge_graph.add_node(cid, "category", {"label": label, "parent_id": "sys_asura"})
            knowledge_graph.add_edge("sys_asura", cid, "contains")

    def _map_skills(self):
        """Map each skill folder as a primary node."""
        if not os.path.exists(config.SKILLS_DIR): return
        for entry in os.listdir(config.SKILLS_DIR):
            full_path = os.path.join(config.SKILLS_DIR, entry)
            if os.path.isdir(full_path) and not entry.startswith(("_", ".")):
                skill_id = f"skill:{entry}"
                knowledge_graph.add_node(skill_id, "skill", {
                    "label": self._format_label(entry),
                    "category": "Skills",
                    "parent_id": "sys_skills",
                    "path": os.path.relpath(full_path, config.BASE_DIR)
                })
                knowledge_graph.add_edge("sys_skills", skill_id, "contains")

    def _determine_category(self, rel_path: str) -> tuple[str, str]:
        if rel_path.startswith("src/skills"): return "Skills", "sys_skills"
        if rel_path.startswith("src/core"): return "Utilities", "sys_core"
        if rel_path.startswith("src/agents"): return "Agents", "sys_agents"
        return "System", "sys_infra"

    def _format_label(self, name: str) -> str:
        return name.replace('_', ' ').title()

    def _scan_directory(self, directory: str):
        """Walk directory with mtime-aware skipping for optimized speed."""
        try:
            # Check directory itself first
            dir_mtime = os.path.getmtime(directory)
            dir_cache_key = f"dir:{directory}"
            cached_dir = self.cache.get(dir_cache_key)
            
            # If directory mtime is unchanged, we still need to process its files
            # but we can trust the cache for the deeper AST parts.
            # (Note: on most OS, dir mtime changes if files are added/removed)
        except: pass

        for root, dirs, files in os.walk(directory):
            # Optimization: Filter out ignored directories immediately
            dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
            
            for file in files:
                if file.endswith((".py", ".md")):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, config.BASE_DIR)
                    cat_name, parent_id = self._determine_category(rel_path)
                    
                    # Add node (file or doc)
                    node_type = "file" if file.endswith(".py") else "doc"
                    label = self._format_label(os.path.basename(file).replace(".py", "").replace(".md", ""))
                    
                    knowledge_graph.add_node(rel_path, node_type, {
                        "abs_path": file_path, "category": cat_name, 
                        "parent_id": parent_id, "label": label
                    })
                    knowledge_graph.add_edge(parent_id, rel_path, "contains")
                    
                    # Link to skill if applicable (only if in a subfolder)
                    if "src/skills/" in rel_path:
                        parts = rel_path.split("src/skills/")[1].split("/")
                        if len(parts) > 1:
                            skill_name = parts[0]
                            knowledge_graph.add_edge(f"skill:{skill_name}", rel_path, "implemented_by" if node_type == "file" else "documented_by")
                        else:
                            knowledge_graph.add_edge("sys_skills", rel_path, "contains")

                    if node_type == "file":
                        self._parse_file_ast(file_path, rel_path, cat_name)

    def _parse_file_ast(self, file_path: str, node_id: str, category: str):
        try:
            mtime = os.path.getmtime(file_path)
            cached = self.cache.get(node_id)
            
            if cached and cached.get("mtime") == mtime:
                # Use cached findings
                for imp in cached.get("imports", []):
                    self._add_resolved_edge(node_id, imp)
                for func in cached.get("functions", []):
                    func_id = f"{node_id}:{func}"
                    knowledge_graph.add_node(func_id, "function", {"label": self._format_label(func), "parent_id": node_id})
                    knowledge_graph.add_edge(node_id, func_id, "contains")
                return

            # Parse needed
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            imports = []
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                        self._add_resolved_edge(node_id, alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        self._add_resolved_edge(node_id, node.module)
                
                # Definitions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("_"): continue
                    functions.append(node.name)
                    func_id = f"{node_id}:{node.name}"
                    knowledge_graph.add_node(func_id, "function", {"label": self._format_label(node.name), "parent_id": node_id})
                    knowledge_graph.add_edge(node_id, func_id, "contains")
            
            # Update cache
            self.cache[node_id] = {
                "mtime": mtime,
                "imports": list(set(imports)),
                "functions": list(set(functions))
            }
        except Exception: pass

    def _add_resolved_edge(self, source_id: str, target: str):
        """Resolves module names to actual file paths in the graph."""
        if target in KNOWN_LIBS or target.split(".")[0] in KNOWN_LIBS: return
        
        # Resolve settings/config
        if target in ("settings", "config"):
            knowledge_graph.add_edge(source_id, "src/settings.py", "imports")
            return

        # Map internal modules to src/ paths
        resolved_path = None
        if target.startswith("core."):
            resolved_path = f"src/core/{target[5:].replace('.', '/')}.py"
        elif target.startswith("skills."):
            resolved_path = f"src/skills/{target[7:].replace('.', '/')}.py"
        
        if resolved_path:
            # Check if it's a package or a file
            full_p = os.path.join(config.BASE_DIR, resolved_path)
            if not os.path.exists(full_p):
                pkg_path = resolved_path.replace(".py", "/__init__.py")
                if os.path.exists(os.path.join(config.BASE_DIR, pkg_path)):
                    resolved_path = pkg_path
            
            knowledge_graph.add_edge(source_id, resolved_path, "imports")

    def _scan_agents(self):
        try:
            loader = get_agent_loader()
            loader.load_all()
            for name, agent in loader.agents.items():
                if "Imperative" in agent.config.get("description", ""): continue
                agent_id = f"agent:{name}"
                knowledge_graph.add_node(agent_id, "agent", {"label": self._format_label(name), "parent_id": "sys_agents"})
                knowledge_graph.add_edge("sys_agents", agent_id, "contains")
                
                agent_file = f"src/agents/{name}.md"
                if os.path.exists(os.path.join(config.BASE_DIR, agent_file)):
                    knowledge_graph.add_edge(agent_id, agent_file, "defined_in")
        except Exception: pass

    async def run_health_probes(self):
        for node_id, node in list(knowledge_graph.nodes.items()):
            health = 100
            if node["type"] == "file":
                if not os.path.exists(os.path.join(config.BASE_DIR, node_id)): health = 0
            knowledge_graph.update_health(node_id, health)

knowledge_scanner = KnowledgeScanner()
