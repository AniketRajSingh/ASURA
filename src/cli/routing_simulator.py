"""
routing_simulator.py — Query-to-Agent Routing Simulation

Simulates ASURA's agent routing logic to determine which agent would handle a query.
Shows pattern matches, confidence scores, and allows explicit override.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MatchResult:
    """Represents a matching agent for a query."""
    name: str
    description: str
    model: str
    confidence: float  # 0.0 to 1.0
    matched_patterns: List[str]
    capabilities: set

    def format_score(self) -> str:
        """Format confidence score with emoji indicator."""
        if self.confidence >= 0.85:
            return f"🎯 {self.confidence:.0%}"
        elif self.confidence >= 0.6:
            return f"✅ {self.confidence:.0%}"
        elif self.confidence >= 0.4:
            return f"ℹ️ {self.confidence:.0%}"
        else:
            return f"❓ {self.confidence:.0%}"


class RoutingSimulator:
    """
    Simulates ASURA's agent routing to predict which agent would handle a query.

    Uses the same pattern matching logic as declarative_agent_loader.py but provides
    detailed feedback about matches and confidence levels.
    """

    def __init__(self, capability_manager):
        self.capability_manager = capability_manager
        self._agent_info: Dict[str, dict] = {}
        self._patterns: Dict[str, List[re.Pattern]] = {}

    def load_agents(self, agent_dirs: List[str] = None) -> int:
        """
        Load agent definitions from directories.

        Args:
            agent_dirs: List of directories to scan (defaults to ["src/agents", "src/skills"])

        Returns:
            Number of agents loaded
        """
        dirs = agent_dirs or ["src/agents", "src/skills"]
        loaded = 0

        for agent_dir in dirs:
            path = Path(agent_dir)
            if not path.exists():
                continue

            for md_file in path.glob("**/*.md"):
                if md_file.name.startswith("_") or md_file.name == ".gitkeep":
                    continue

                content = md_file.read_text()
                info, patterns = self._parse_agent_file(md_file, content)

                if info:
                    name = info['name']
                    self._agent_info[name] = info
                    self._patterns[name] = patterns
                    loaded += 1

        return loaded

    def _parse_agent_file(self, file_path: Path, content: str) -> Tuple[Optional[dict], List[re.Pattern]]:
        """Parse a single agent markdown file."""
        import yaml

        # Extract YAML frontmatter
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        if not frontmatter_match:
            return None, []

        try:
            config = yaml.safe_load(frontmatter_match.group(1)) or {}
        except Exception:
            return None, []

        name = config.get("name") or file_path.stem.replace("-", "_")
        model = config.get("model", "inherit")
        description = config.get("description", f"Agent {name}")

        # Extract trigger patterns from examples
        patterns = self._extract_trigger_patterns(content)

        # Get capabilities for this agent
        capabilities = self.capability_manager.get_agent_capabilities(name)

        return {
            'name': name,
            'model': model,
            'description': description.strip() if description else f"Agent {name}",
            'capabilities': capabilities,
            'file_path': str(file_path)
        }, patterns

    def _extract_trigger_patterns(self, content: str) -> List[re.Pattern]:
        """Extract trigger patterns from agent examples."""
        patterns = []

        # Look for <example> blocks
        example_pattern = r'<example>\s*\nContext:\s*(.*?)\n\nuser:\s*(.*?)\n\nassistant:\s*(.*?)\n\s*</example>'
        examples = re.findall(example_pattern, content, re.DOTALL)

        for context, user_query, response in examples:
            # Use the specific example query as trigger pattern
            pattern_text = f"({re.escape(user_query.lower())})"
            try:
                patterns.append(re.compile(pattern_text, re.IGNORECASE))
            except re.error:
                pass

        return patterns

    def simulate_routing(self, query: str) -> List[MatchResult]:
        """
        Simulate agent routing for a given query.

        Args:
            query: User query to route

        Returns:
            List of matching agents sorted by confidence (highest first)
        """
        results = []
        query_lower = query.lower()
        keywords = self._extract_query_keywords(query_lower)

        for name, agent_info in self._agent_info.items():
            patterns = self._patterns.get(name, [])

            # Calculate confidence based on multiple factors
            pattern_match = 0.0
            matched_patterns = []

            # Factor 1: Trigger pattern matching (40% weight)
            for pattern in patterns:
                if pattern.search(query_lower):
                    pattern_match += 0.25
                    matched_patterns.append(f"'{pattern.pattern}'")
                    break

            if not patterns or pattern_match > 0:
                # No specific triggers means agent handles all queries
                if not patterns:
                    pattern_match = 0.15

            # Factor 2: Capability keyword matching (40% weight)
            capability_score = self._calculate_capability_match(agent_info, keywords, query_lower)

            # Factor 3: Semantic relevance (20% weight) - simplified version
            semantic_score = self._calculate_semantic_relevance(query_lower, agent_info)

            # Weighted score
            total_score = (pattern_match * 0.4) + (capability_score * 0.4) + (semantic_score * 0.2)

            if pattern_match > 0 or capability_score > 0 or not patterns:
                results.append(MatchResult(
                    name=name,
                    description=agent_info['description'],
                    model=agent_info['model'],
                    confidence=min(total_score, 1.0),
                    matched_patterns=matched_patterns if matched_patterns else ["Keyword match"],
                    capabilities=agent_info['capabilities']
                ))

        # Sort by confidence descending
        results.sort(key=lambda x: -x.confidence)
        return results

    def _extract_query_keywords(self, query_lower: str) -> List[str]:
        """Extract meaningful keywords from a query."""
        import re
        words = re.findall(r'\b[a-z]+\b', query_lower)
        return [w for w in words if len(w) > 3]

    def _calculate_capability_match(self, agent_info: dict, keywords: List[str], query: str) -> float:
        """Calculate capability-based matching score."""
        capabilities = agent_info.get('capabilities', {'general'})
        score = 0.0

        # Check if keywords match any of agent's capabilities
        for cap in capabilities:
            cap_lower = cap.lower()
            # Direct keyword match
            for kw in keywords:
                if re.search(rf'\b{kw}\b', cap_lower) or re.search(rf'\b{cap_lower}\b', kw):
                    score += 0.3

        # Also check query against taxonomy directly
        from .capability_manager import CapabilityManager
        for keyword in keywords:
            if keyword in CapabilityManager.KEYWORD_TO_CAPABILITY:
                expected_cap = CapabilityManager.KEYWORD_TO_CAPABILITY[keyword]
                if any(expected_cap in cap or cap in expected_cap for cap in capabilities):
                    score += 0.2

        return min(score, 1.0)

    def _calculate_semantic_relevance(self, query: str, agent_info: dict) -> float:
        """Simple semantic relevance using keyword overlap."""
        # Extract key terms from description
        desc = agent_info['description'].lower()
        desc_words = set(re.findall(r'\b[a-z]+\b', desc))

        # Query words that appear in description
        query_words = set(re.findall(r'\b[a-z]+\b', query))

        if not desc_words or not query_words:
            return 0.1  # Low relevance but not zero

        overlap = len(desc_words & query_words)
        max_overlap = max(len(desc_words), len(query_words))

        return (overlap / max_overlap) * 0.2 if max_overlap > 0 else 0.1

    def get_best_match(self, query: str) -> Optional[MatchResult]:
        """Get the single best matching agent for a query."""
        results = self.simulate_routing(query)
        return results[0] if results else None

    def suggest_agent_for_query(self, query: str) -> str:
        """Generate a human-readable suggestion for agent selection."""
        match = self.get_best_match(query)
        if not match:
            return "No specific agent suggested - use default routing"

        suggestions = [
            f"🎯 Best Match: **{match.name}** (confidence: {match.format_score()})",
            "",
            f"   Description: {match.description}",
            f"   Model: {match.model}",
            f"   Capabilities: {', '.join(match.capabilities)}",
        ]

        if len(match.matched_patterns) > 0:
            suggestions.append(f"   Matched patterns: {' | '.join(match.matched_patterns[:3])}")

        return "\n".join(suggestions)


# Singleton instance
_routing_simulator: Optional[RoutingSimulator] = None


def get_routing_simulator() -> RoutingSimulator:
    """Get or create the global routing simulator."""
    global _routing_simulator
    from .capability_manager import get_capability_manager
    if _routing_simulator is None:
        _routing_simulator = RoutingSimulator(get_capability_manager())
        _routing_simulator.load_agents()
    return _routing_simulator
