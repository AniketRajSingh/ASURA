"""
capability_manager.py — Agent Capability Management

Manages capability tags for agents, allowing filtering and search across the agent ecosystem.
Provides fuzzy matching and keyword-based discovery.
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path


class CapabilityManager:
    """
    Manages capability tags for ASURA agents.

    Each agent can have multiple capabilities that define its expertise.
    Supports fuzzy matching and keyword-based discovery.
    """

    # Standard capability taxonomy
    CAPABILITY_TAXONOMY = {
        "code_navigation": ["find", "search", "explore", "locate", "navigate", "scan"],
        "security_review": ["security", "vulnerability", "audit", "review", "analyze", "check"],
        "file_operations": ["create", "write", "save", "generate", "produce", "make"],
        "analysis": ["analyze", "examine", "investigate", "evaluate", "assess", "inspect"],
        "refactoring": ["refactor", "rewrite", "improve", "optimize", "clean up", "restructure"],
        "documentation": ["document", "docstring", "comment", "readme", "explain", "describe"],
        "testing": ["test", "verify", "validate", "check", "assert", "unit test"],
        "debugging": ["debug", "troubleshoot", "fix", "resolve", "diagnose", "issue"],
        "maintenance": ["cleanup", "delete", "remove", "terminate", "kill", "destroy"],
        "learning": ["learn", "discover", "understand", "explore", "investigate"],
        "automation": ["automate", "script", "workflow", "pipeline", "batch", "schedule"],
    }

    # Reverse mapping: keyword -> capabilities
    KEYWORD_TO_CAPABILITY = {}
    for cap, keywords in CAPABILITY_TAXONOMY.items():
        for kw in keywords:
            KEYWORD_TO_CAPABILITY[kw.lower()] = cap

    def __init__(self):
        self._agent_capabilities: Dict[str, Set[str]] = {}
        self._loaded_files: Set[Path] = set()

    def scan_and_register_agents(self, agents_dir: str = "src/agents") -> None:
        """
        Scan agent directories and auto-discover capabilities from content.

        Extracts capability indicators from agent definitions including:
        - YAML frontmatter description and purpose sections
        - <example> blocks showing usage patterns
        - Common action verbs in instructions

        Args:
            agents_dir: Path to directory containing agent .md files
        """
        agents_path = Path(agents_dir)
        if not agents_path.exists():
            return

        for md_file in agents_path.glob("**/*.md"):
            if md_file.name.startswith("_") or md_file.name == ".gitkeep":
                continue

            capabilities = self._extract_capabilities_from_content(md_file.read_text())
            agent_name = md_file.stem.replace("-", "_")
            self.register_agent_capabilities(agent_name, capabilities)
            self._loaded_files.add(md_file)

    def _extract_capabilities_from_content(self, content: str) -> Set[str]:
        """
        Extract capability tags from agent definition content.

        Analysis steps:
        1. Match known capability keywords in description/purpose sections
        2. Identify action verbs that indicate functionality
        3. Cross-reference with taxonomy for normalization

        Args:
            content: Full text of agent .md file

        Returns:
            Set of capability tag names
        """
        capabilities = set()

        # Normalize content for analysis
        text_lower = content.lower()

        # First pass: direct keyword matching against taxonomy
        for keyword, capability in self.KEYWORD_TO_CAPABILITY.items():
            if re.search(rf'\b{keyword}\b', text_lower):
                capabilities.add(capability)

        # Second pass: extract explicit tags if present (e.g., #tag in content)
        tag_pattern = r'#([a-z][a-z0-9_-]+)'
        tags_found = re.findall(tag_pattern, content)
        for tag in tags_found:
            capabilities.add(tag.replace("_", "-"))

        # Third pass: analyze example contexts to infer additional capabilities
        examples = self._extract_examples(content)
        capabilities.update(self._infer_capabilities_from_examples(examples))

        return capabilities if capabilities else {"general"}

    def _extract_examples(self, content: str) -> List[Tuple[str, str]]:
        """Extract (context, query) pairs from <example> blocks."""
        examples = []
        pattern = r'<example>\s*\nContext:\s*(.*?)\n\nuser:\s*(.*?)\n\s*</example>'
        matches = re.findall(pattern, content, re.DOTALL)
        for context, user_query in matches:
            examples.append((context.lower(), user_query.lower()))
        return examples

    def _infer_capabilities_from_examples(self, examples: List[Tuple[str, str]]) -> Set[str]:
        """Infer capabilities from example usage patterns."""
        inferred = set()

        for context, query in examples:
            # Check if query contains capability keywords
            for keyword, capability in self.KEYWORD_TO_CAPABILITY.items():
                if re.search(rf'\b{keyword}\b', query):
                    inferred.add(capability)

        return inferred

    def register_agent_capabilities(self, agent_name: str, capabilities: Set[str]) -> None:
        """Manually register capabilities for an agent."""
        self._agent_capabilities[agent_name] = set(capabilities)

    def get_agent_capabilities(self, agent_name: str) -> Set[str]:
        """Get all capabilities for a specific agent."""
        return self._agent_capabilities.get(agent_name, {"general"})

    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find all agents that support a given capability."""
        matching = []
        search_cap = capability.lower().replace("_", "-")

        for agent_name, caps in self._agent_capabilities.items():
            if any(cap.lower() == search_cap or capability.lower() in cap
                   for cap in caps):
                matching.append(agent_name)

        return sorted(matching)

    def find_agents_by_keywords(self, keywords: List[str]) -> Dict[str, int]:
        """
        Find agents that match given keywords, ranked by relevance score.

        Args:
            keywords: List of search keywords (can be capability names or action words)

        Returns:
            Dict mapping agent_name to relevance score (number of matching keywords)
        """
        results: Dict[str, int] = {}
        keywords_lower = [k.lower() for k in keywords]

        for agent_name, capabilities in self._agent_capabilities.items():
            score = 0

            # Check exact capability matches
            for cap in capabilities:
                if any(kw == cap or kw in cap or cap in kw
                       for kw in keywords_lower):
                    score += 2

            # Check keyword overlap
            for kw in keywords_lower:
                if any(re.search(rf'\b{kw}\b', cap.lower()) for cap in capabilities):
                    score += 1

            if score > 0:
                results[agent_name] = score

        return dict(sorted(results.items(), key=lambda x: -x[1]))

    def get_all_capabilities(self) -> List[str]:
        """Get list of all known capabilities from taxonomy."""
        return sorted(self.CAPABILITY_TAXONOMY.keys()) + \
               [tag.replace("_", "-") for caps in self.CAPABILITY_TAXONOMY.values()
                for tag in set(caps)]

    def suggest_capabilities_for_query(self, query: str) -> List[str]:
        """Suggest relevant capabilities based on user query."""
        keywords = self._extract_keywords_from_query(query)
        return sorted(
            {cap for keyword in keywords
             if (cap := self.KEYWORD_TO_CAPABILITY.get(keyword))
             },
            key=lambda x: -len(x)
        )

    def _extract_keywords_from_query(self, query: str) -> List[str]:
        """Extract meaningful keywords from a query."""
        words = re.findall(r'\b[a-z]+\b', query.lower())
        return [w for w in words if w in self.KEYWORD_TO_CAPABILITY]


# Singleton instance
_capability_manager: Optional[CapabilityManager] = None


def get_capability_manager() -> CapabilityManager:
    """Get or create the global capability manager."""
    global _capability_manager
    if _capability_manager is None:
        _capability_manager = CapabilityManager()
        # Auto-scan agents on first access
        _capability_manager.scan_and_register_agents("src/agents")
    return _capability_manager
