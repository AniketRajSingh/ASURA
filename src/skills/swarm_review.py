# ============================================================
# skills/swarm_review.py — Multi-Agent PR Review Workflow
#
# Launches parallel LLM instances loaded from declarative
# Markdown agents to evaluate a codebase or set of files,
# simulating Claude Code's pr-review-toolkit plugin.
# ============================================================

import asyncio
from skills.logger import log_audit, log_app
from core.llm import call_llm
from core.declarative_agent_loader import get_agent_loader
from settings import settings as config

async def spawn_agent(agent_name: str, target_code: str, filename: str) -> dict:
    loader = get_agent_loader()
    agent = loader.get_agent(agent_name)
    if not agent:
        log_app(f"Swarm: Agent '{agent_name}' not found.")
        return {"agent": agent_name, "error": f"Agent {agent_name} missing."}

    # Format the prompt exactly how Claude Code does it, using the markdown body
    prompt = f"""{agent.content}

Please review the following file: `{filename}`

[OBSERVATION]
{target_code}
[/OBSERVATION]

Present your findings clearly using Markdown lists and headers. If you find no issues, state that explicitly.
"""
    
    # We use OLLAMA_MODEL_FAST for swarm reviews to keep things snappy, or OLLAMA_MODEL
    # let's use the default model for deep code reasoning.
    try:
        # In ASURA, call_llm expects the user message. We can prepend the system prompt if needed,
        # but placing it all in the user prompt is fine for single-shot evaluations.
        response = await call_llm(prompt, model=config.OLLAMA_MODEL, stream=False)
        return {"agent": agent.name, "result": response}
    except Exception as e:
        return {"agent": agent.name, "error": str(e)}

async def run_swarm_review(target_code: str, filename: str, agents: list[str] = None) -> str:
    """
    Runs a parallel swarm review on a particular file/diff.
    If no agents are specified, runs all available markdown agents.
    """
    loader = get_agent_loader()
    if not agents:
        agents = loader.load_all()
        if not agents:
            return "❌ Swarm Review Failed: No agents found in src/agents/."
    
    log_audit("SWARM", f"Launching {len(agents)} parallel agents to review {filename}")
    
    # Create an async task for each agent
    tasks = [spawn_agent(agent, target_code, filename) for agent in agents]
    
    # Run them simultaneously
    results = await asyncio.gather(*tasks)
    
    # Aggregate into a master report
    report = f"# 🐝 Swarm Review Report for `{filename}`\n"
    report += f"**Agents Deployed:** {', '.join(agents)}\n\n"
    
    for res in results:
        agent_name = res.get("agent", "Unknown")
        report += f"## 🤖 Agent: {agent_name}\n"
        if "error" in res:
            report += f"⚠️ **Failed:** {res['error']}\n\n"
        else:
            report += f"{res['result']}\n\n"
            
        report += "---\n\n"
        
    return report

# Backward Compatibility Aliases
async def review_code(code: str) -> str:
    """Old entry point for code review, now routes to Swarm Review."""
    return await run_swarm_review(code, "snippet.py")

async def review_file(filepath: str) -> str:
    """Old entry point for file review, now routes to Swarm Review."""
    if not os.path.exists(filepath):
        return f"File not found: {filepath}"
    with open(filepath, "r") as f:
        code = f.read()
    return await run_swarm_review(code, os.path.basename(filepath))

# For synchronous wrapper skills/cli use
def run_swarm_review_sync(target_code: str, filename: str, agents: list[str] = None) -> str:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
             import nest_asyncio
             nest_asyncio.apply()
        return asyncio.run(run_swarm_review(target_code, filename, agents))
    except Exception:
        return asyncio.run(run_swarm_review(target_code, filename, agents))
