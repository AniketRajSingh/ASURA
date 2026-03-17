---
name: sub_agent_manager
description: "Manager for spawning, commanding, and inspecting specialized sub-agents with isolated memory vaults."
entry_point: manager.py
---

# Sub-Agent Manager

Lifecycle management for specialized sub-agents. Allows ASURA to delegate tasks to personas with isolated memory and focused roles.

### 🔧 Tools / Functions
- `spawn_subagent(name, role, persistent)`: Create a new specialized agent.
- `run_subagent_task(name, task)`: Direct a sub-agent to perform a specific action.
- `list_subagents()`: Show all active and dormant sub-agents.
- `inspect_subagent_memory(name)`: View the internal memory vault of an agent.
- `kill_subagent(name)`: Terminate an agent and optionally purge its memory.

### 📝 Examples
- "Spawn a security auditor agent" -> Creates a new persona for specialized tasks.
- "Ask the auditor to check this script" -> Executes task via the sub-agent.

### 🛠️ Requirements
- `SubAgentMemory` core module.
