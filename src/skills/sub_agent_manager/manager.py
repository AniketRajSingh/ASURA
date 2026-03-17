import os
import json
import asyncio
from settings import settings as config
from core.sub_agent_memory import SubAgentMemory
from skills.logger import log_audit, log_app
from core.llm import call_llm

# Keep track of active sub-agents in-memory for the current session
_active_agents = {}

async def spawn_subagent(name: str, role: str, persistent: bool = False):
    """
    Spawns a new sub-agent with its own memory vault.
    
    Args:
        name: Unique name for the agent
        role: Description of its purpose
        persistent: Whether it should persist across sessions
    """
    log_audit("SUB_AGENT", f"Spawning agent: {name} (Role: {role})")
    SubAgentMemory.initialize_vault(name, role)
    _active_agents[name] = {
        "name": name,
        "role": role,
        "persistent": persistent,
        "status": "idle"
    }
    return f"Sub-agent '{name}' successfully spawned."

async def list_subagents() -> str:
    """List all active sub-agents."""
    active = list(_active_agents.keys())
    saved = SubAgentMemory.list_vaults()
    
    lines = ["📋 Sub-Agents:"]
    for name in set(active + saved):
        status = "Active" if name in _active_agents else "Sleeping"
        role = _active_agents.get(name, {}).get("role", "Unknown")
        lines.append(f"  • {name} [{status}] - {role}")
    
    return "\n".join(lines) if len(lines) > 1 else "No sub-agents found."

async def kill_subagent(name: str) -> str:
    """Terminates and optionally cleans up an agent."""
    if name in _active_agents:
        del _active_agents[name]
        # For non-persistent agents, delete vault too
        SubAgentMemory.delete_vault(name)
        log_audit("SUB_AGENT", f"Killed agent: {name}")
        return f"Sub-agent '{name}' terminated and memory purged."
    return f"Sub-agent '{name}' not found."

async def inspect_subagent_memory(name: str) -> str:
    """Read a sub-agent's local memory vault."""
    vault = SubAgentMemory.get_vault(name)
    if not vault:
        return f"No memory vault found for agent: {name}"
    return json.dumps(vault, indent=2)

async def run_subagent_task(name: str, task: str) -> str:
    """Execute a task using a sub-agent's perspective."""
    if name not in _active_agents:
        # Try to reactivate from vault
        vault = SubAgentMemory.get_vault(name)
        if not vault:
            return f"Agent {name} not found and no vault exists."
        _active_agents[name] = {
            "name": name,
            "role": vault["role"],
            "persistent": True,
            "status": "idle"
        }

    agent = _active_agents[name]
    agent["status"] = "working"
    log_audit("SUB_AGENT", f"Agent '{name}' starting task: {task[:50]}")

    # Build agent prompt — prioritize declarative definitions
    system_prompt = f"You are {name}, a specialized sub-agent for ASURA.\nRole: {agent['role']}\nTask: {task}"
    
    try:
        from core.declarative_agent_loader import get_agent_loader, init_declarative_agents
        init_declarative_agents()
        loader = get_agent_loader()
        # Look for a declarative agent with this name (lowercase)
        decl_agent = loader.get_agent(name.lower())
        if decl_agent:
            log_audit("SUB_AGENT", f"Using declarative persona for {name}")
            system_prompt = f"{decl_agent.content}\n\n[CURRENT TASK]: {task}"
    except Exception as e:
        log_audit("SUB_AGENT_WARN", f"Could not load declarative persona: {e}")
    
    try:
        # In a real system, we'd pass history here
        result = await call_llm(task, system_prompt=system_prompt)
        SubAgentMemory.add_history(name, task, result)
        agent["status"] = "idle"
        return f"Result from {name}:\n{result}"
    except Exception as e:
        agent["status"] = "error"
        return f"Task failed for agent {name}: {e}"

async def _register_agent_tools():
    """Register tools into the MCP-Lite tool protocol."""
    from core.tool_protocol import register_tool
    
    register_tool(
        "spawn_subagent", 
        spawn_subagent, 
        "Create a new sub-agent with isolated memory. JSON: {name, role, persistent}",
        {"type": "object", "properties": {"name": {"type": "string"}, "role": {"type": "string"}}},
        category="agent_management"
    )
    
    register_tool(
        "list_subagents",
        list_subagents,
        "List all active and sleeping sub-agents.",
        {},
        category="agent_management"
    )

    register_tool(
        "kill_subagent",
        kill_subagent,
        "Terminate a sub-agent and purge its memory. JSON: {name}",
        {"type": "object", "properties": {"name": {"type": "string"}}},
        category="agent_management"
    )

    register_tool(
        "inspect_subagent_memory",
        inspect_subagent_memory,
        "Read the local memory vault of a sub-agent. JSON: {name}",
        {"type": "object", "properties": {"name": {"type": "string"}}},
        category="agent_management"
    )

    register_tool(
        "run_subagent_task",
        run_subagent_task,
        "Give a specific task to a sub-agent. JSON: {name, task}",
        {"type": "object", "properties": {"name": {"type": "string"}, "task": {"type": "string"}}},
        category="agent_management"
    )

    async def delete_agent_definition(name: str) -> str:
        """Deletes a declarative agent's .md definition file."""
        path = os.path.join("src/agents", f"{name.lower()}.md")
        if os.path.exists(path):
            os.remove(path)
            log_audit("SUB_AGENT", f"Deleted agent definition: {name}")
            return f"Agent definition '{name}' deleted from src/agents/."
        return f"Agent definition '{name}' not found."

    register_tool(
        "delete_agent_definition",
        delete_agent_definition,
        "Permanently delete an agent's declarative .md file. JSON: {name}",
        {"type": "object", "properties": {"name": {"type": "string"}}},
        category="agent_management"
    )

log_app("Sub-Agent Manager initialized.")
# Register tools lazily or when a loop is available
try:
    asyncio.get_running_loop().create_task(_register_agent_tools())
except RuntimeError:
    # No loop running at import time (common in tests/CLI)
    pass
