# ============================================================
# core/declarative_agent_loader.py — Declarative Agent System
#
# Loads agent definitions from markdown files with YAML frontmatter.
# Features a Self-Learning Hybrid Intent System.
# ============================================================

import os
import re
import yaml
import json
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from settings import settings as config


class DeclarativeAgent:
    """Represents an agent loaded from a markdown definition file."""

    def __init__(self, name: str, config: dict, content: str):
        self.name = name
        self.config = config
        self.content = content
        self._trigger_patterns: List[re.Pattern] = []
        self.model = config.get("model", "inherit")
        self._parse_triggers()

    def _parse_triggers(self):
        example_pattern = r'<example>\s*\nContext:\s*(.*?)\n\nuser:\s*(.*?)\n\nassistant:\s*(.*?)\n\s*</example>'
        examples = re.findall(example_pattern, self.content, re.DOTALL)
        for context, user_query, response in examples:
            pattern = f"({re.escape(user_query.lower())})"
            try:
                self._trigger_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error: pass

    def should_trigger(self, query: str) -> bool:
        query_lower = query.lower()
        return any(pattern.search(query_lower) for pattern in self._trigger_patterns)

    def get_description(self) -> str:
        desc = self.config.get("description", f"Agent {self.name}")
        return desc.strip() if desc else f"Agent {self.name}"


class AgentLoader:
    """Loads agents and provides self-learning hybrid intent recognition."""

    KEYWORD_ROUTING = {
        "bug_hunter": ["bug", "fix", "error", "crash", "traceback", "debug", "broken", "syntax"],
        "explorer": ["map", "relationship", "diagram", "where is", "find file", "structure", "architecture"],
        "reviewer": ["audit", "security", "vulnerability", "check code", "review", "quality", "clean"],
        "validator": ["sync", "verify", "health", "knowledge graph", "correct", "check changes"],
        "asura_spawner": ["spawn", "create agent", "multi-agent", "parallel", "delegate"],
        "asura_despawner": ["kill agent", "terminate", "cleanup agents", "stop specialist"],
        "interactive_agent": ["chat", "hello", "who are you", "help", "talk"]
    }

    def __init__(self, agent_dirs: List[str] = None):
        self.agent_dirs = agent_dirs or ["src/agents", "src/skills"]
        self.agents: Dict[str, DeclarativeAgent] = {}
        self.cache_path = os.path.join(config.DATA_DIR, "intent_cache.json")
        self._learned_cache: Dict[str, str] = self._load_cache()

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r") as f:
                    return json.load(f)
            except Exception: pass
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_path, "w") as f:
                json.dump(self._learned_cache, f, indent=2)
        except Exception: pass

    def load_all(self):
        for agent_dir in self.agent_dirs:
            path = Path(agent_dir)
            if not path.exists(): continue
            for md_file in path.glob("**/*.md"):
                if md_file.name.startswith("_") or md_file.name == ".gitkeep": continue
                self._load_declarative_agent(md_file)
            for py_file in path.glob("**/*.py"):
                if py_file.name.startswith("_") or py_file.name == "__init__.py": continue
                self._register_py_agent(path / py_file, agent_dir)
        return list(self.agents.keys())

    def _load_declarative_agent(self, file_path: Path):
        try:
            content = file_path.read_text()
            fm = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
            if not fm: return
            conf = yaml.safe_load(fm.group(1)) or {}
            name = conf.get("name") or file_path.stem.replace("-", "_")
            self.agents[name] = DeclarativeAgent(name, conf, content)
        except Exception: pass

    def _register_py_agent(self, file_path: Path, base_dir: str):
        name = file_path.stem
        self.agents[name] = DeclarativeAgent(name=name, config={"description": "Imperative"}, content="")

    def get_agent(self, name: str) -> Optional[DeclarativeAgent]:
        return self.agents.get(name)

    async def find_agent_for_query_async(self, query: str) -> str:
        """
        Self-Learning Intent Recognition.
        Level 0: Learned Cache (Learns from previous LLM decisions)
        Level 1: Keywords
        Level 2: Heuristics
        Level 3: 0.8B LLM (Updates Cache on success)
        """
        from skills.logger import log_audit
        query_norm = re.sub(r'\W+', ' ', query.lower()).strip()

        # 0. 🧠 LEVEL 0: Learned Cache
        if query_norm in self._learned_cache:
            agent_id = self._learned_cache[query_norm]
            log_audit("INTENT", f"Learned Cache Hit: {agent_id}")
            return agent_id

        # 1. 🚀 LEVEL 1: High-Speed Keyword Match
        for agent_id, keywords in self.KEYWORD_ROUTING.items():
            if any(k in query_norm for k in keywords):
                log_audit("INTENT", f"Keyword Match: {agent_id}")
                return agent_id

        # 2. 🤖 LEVEL 3: 0.8B LLM Pass (with strict timeout)
        from core.llm import call_llm
        from core.model_manager import model_manager
        import asyncio
        
        agent_names = list(self.agents.keys())
        prompt = f"[INST] Select agent for: \"{query[:200]}\"\nChoices: {agent_names}\nRespond with ONLY name.[/INST]"

        try:
            fast_model = model_manager.get_model_for_task("fast")
            from skills.logger import log_app
            log_app(f"DEBUG: Intent recognition Level 3 starting (Model: {fast_model})...")
            
            # Force a strict timeout for intent recognition
            response = await asyncio.wait_for(
                call_llm(prompt, model=fast_model, temperature=0.0),
                timeout=5.0
            )
            
            selected = response.strip().lower().split()[0].replace(".", "").replace("'", "")
            
            if selected in self.agents:
                # 🎓 LEARN: Store successful mapping
                self._learned_cache[query_norm] = selected
                self._save_cache()
                log_audit("INTENT", f"Learned NEW Intent: {query_norm} -> {selected}")
                return selected
        except asyncio.TimeoutError:
            log_app("DEBUG: Intent recognition timed out after 5s. Falling back.")
        except Exception as e:
            log_app(f"DEBUG: Intent recognition failed: {e}")
        
        return "asura_spawner" # Default fallback

        return "interactive_agent"

    def get_all_agents_info(self) -> List[dict]:
        return [{"name": a.name, "description": a.get_description()[:100]} for a in self.agents.values()]


_loader_instance: Optional[AgentLoader] = None

def get_agent_loader() -> AgentLoader:
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = AgentLoader()
    return _loader_instance

def init_declarative_agents():
    return get_agent_loader().load_all()
