# src/cli/agent_selector.py — Agent Selection Interface for ASURA CLI
#
# Provides a user-friendly interface for selecting which AI agent/model
# should handle tasks in interactive mode. Supports both built-in agents
# and custom model configurations.

import os
import json


class AgentSelector:
    """
    Manages agent selection for ASURA CLI interactive mode.

    Allows users to select which AI agent/model should process their requests,
    similar to Claude Code's model selector interface.
    """

    # Available agents configuration
    AVAILABLE_AGENTS = {
        "auto": {
            "name": "Auto-Select",
            "type": "automatic",
            "description": "Let ASURA automatically choose the best agent for your task",
        },
        "fast": {
            "name": "Fast",
            "type": "quick",
            "description": "Optimized for speed — best for quick queries and simple tasks",
        },
        "balanced": {
            "name": "Balanced",
            "type": "standard",
            "description": "Good balance of quality and speed — default choice",
        },
        "reasoning": {
            "name": "Reasoning",
            "type": "deep-thinking",
            "description": "Advanced reasoning for complex problem-solving and analysis",
        },
        "coding": {
            "name": "Coding",
            "type": "specialized",
            "description": "Optimized for code generation, debugging, and software tasks",
        },
        "creative": {
            "name": "Creative",
            "type": "generative",
            "description": "Best for creative writing, brainstorming, and content creation",
        },
    }

    def __init__(self, config_path: str = None):
        """Initialize the agent selector."""
        self.selected_agent = "auto"
        self.config_path = config_path or os.path.join(
            os.environ.get("ASURA_DATA_DIR", ""), "agent_preferences.json"
        )
        self._load_preferences()

    def _load_preferences(self):
        """Load saved agent preferences from file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    prefs = json.load(f)
                    saved_agent = prefs.get("selected_agent", "auto")
                    if saved_agent in self.AVAILABLE_AGENTS:
                        self.selected_agent = saved_agent
            except (json.JSONDecodeError, IOError):
                # Invalid or unreadable file — use default
                self.selected_agent = "auto"

    def _save_preferences(self):
        """Save current agent preference to file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump({"selected_agent": self.selected_agent}, f, indent=2)
        except IOError:
            # Silently fail — preferences are optional
            pass

    def get_available_agents(self) -> dict:
        """Return list of available agents."""
        return self.AVAILABLE_AGENTS.copy()

    def select_agent(self, agent_id: str) -> str:
        """
        Select an agent for processing tasks.

        Args:
            agent_id: The ID of the agent to select

        Returns:
            The selected agent ID (or 'auto' if invalid)
        """
        agent_id = agent_id.lower().strip()

        if agent_id in self.AVAILABLE_AGENTS:
            self.selected_agent = agent_id
            self._save_preferences()
            return agent_id

        # Invalid agent — fallback to auto
        print(f"⚠️  Unknown agent '{agent_id}', using 'auto' instead")
        self.selected_agent = "auto"
        return "auto"

    def get_agent_info(self, agent_id: str) -> dict | None:
        """Get information about a specific agent."""
        if agent_id in self.AVAILABLE_AGENTS:
            info = self.AVAILABLE_AGENTS[agent_id].copy()
            info["selected"] = (agent_id == self.selected_agent)
            return info
        return None

    def format_selection_text(self, selected_only: bool = False) -> str:
        """
        Generate formatted text showing agent selection options.

        Args:
            selected_only: If True, only show the currently selected agent

        Returns:
            Formatted string for terminal display
        """
        lines = []
        prefix = "✓" if self.selected_agent == "auto" else ""

        lines.append(f"\n{prefix} \033[36mCurrently Selected:\033[0m  \033[33m{self.selected_agent}\033[0m")

        for agent_id, info in self.AVAILABLE_AGENTS.items():
            if selected_only and agent_id != self.selected_agent:
                continue

            marker = "✓" if agent_id == self.selected_agent else "○"
            agent_type = f"\033[36m{info.get('type', 'unknown')}\033[0m"
            desc = info.get("description", "")[:50] + ("..." if len(info.get("description", "")) > 50 else "")

            lines.append(f"  {marker} \033[33m{agent_id}\033[0m  —  {agent_type}: {desc}")

        return "\n".join(lines)

    def agent_for_task(self, task_prompt: str) -> str:
        """
        Automatically select an agent based on task content.

        Uses simple heuristics to detect task type and choose appropriate agent.

        Args:
            task_prompt: The user's task description

        Returns:
            Suggested agent ID
        """
        prompt_lower = task_prompt.lower()

        # Heuristic rules for automatic selection
        if any(word in prompt_lower for word in ["code", "debug", "function", "class", "module"]):
            return "coding"

        if any(word in prompt_lower for word in ["analyze", "reason", "complex", "calculate", "explain"]):
            return "reasoning"

        if any(word in prompt_lower for word in ["write", "create", "story", "poem", "art"]):
            return "creative"

        if any(word in prompt_lower for word in ["quick", "fast", "simple", "brief", "short"]):
            return "fast"

        # Default to balanced for most tasks
        return "balanced"


def print_agent_options(selector: AgentSelector, selected_only: bool = False):
    """
    Helper function to print agent selection options.

    Args:
        selector: AgentSelector instance
        selected_only: If True, only show current selection
    """
    text = selector.format_selection_text(selected_only)
    print(text)


def get_agent_selector() -> AgentSelector:
    """Get a configured AgentSelector instance for CLI use."""
    return AgentSelector()


if __name__ == "__main__":
    # Demo mode
    selector = AgentSelector()

    print("\n\033[36mASURA CLI — Agent Selector Demo\033[0m\n")
    print_agent_options(selector, selected_only=False)

    print("\n" + "=" * 50)
    print("\nSimulating automatic agent selection:\n")

    test_tasks = [
        "Write a Python function to sort a list",
        "Explain quantum computing in simple terms",
        "Create a poem about the ocean",
        "Quick: what's 2 + 2?",
        "Debug this React component",
    ]

    for task in test_tasks:
        selected = selector.agent_for_task(task)
        marker = "✓" if selected == selector.selected_agent else "○"
        print(f"{marker} Task: {task}")
        print(f"   → Suggested agent: \033[36m{selected}\033[0m\n")

    print("\n\033[32mDemo complete!\033[0m")
