# ============================================================
# core/handoff.py — Autonomous Agent Handoff Protocol
#
# Enables agents to delegate tasks to more appropriate 
# specialists during a reasoning loop.
# ============================================================

from typing import Optional, Tuple
from skills.logger import log_audit, log_app

def detect_handoff_need(thought: str, current_agent: str) -> Optional[str]:
    """
    Analyze a thought step to see if the agent is requesting a handoff.
    
    Expected thought patterns:
    - "I am the wrong agent for this, use bug_hunter"
    - "Delegate this to the archistar"
    - "Handoff to validator"
    """
    import re
    thought_lower = thought.lower()
    
    # Simple regex for handoff detection
    # Pattern: (delegate|handoff|use agent|switch to) [agent_name]
    patterns = [
        r"(?:delegate|handoff|use agent|switch to|better handled by) (?:the )?([a-z0-9_-]+)",
        r"i am (?:the )?wrong agent.*?use ([a-z0-9_-]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, thought_lower)
        if match:
            target_agent = match.group(1).strip()
            if target_agent != current_agent:
                return target_agent
                
    return None

async def perform_handoff(task: str, target_agent: str, context: str = "") -> Tuple[str, str]:
    """
    Execute a handoff by re-routing the task to the new agent.
    """
    log_audit("HANDOFF", f"Rerouting task to {target_agent}")
    log_app(f"🔄 Autonomous Handoff: {target_agent} taking over...")
    
    from skills.ai_content.generator import chat
    
    # We provide the context of the previous agent's failure or finding
    handoff_context = f"PREVIOUS AGENT CONTEXT: {context}\n\nTASK: {task}"
    
    # Call the new agent
    reply, _ = await chat(task, history=[{"role": "system", "content": context}, {"role": "user", "content": task}], agent_name=target_agent)
    
    return reply, target_agent

def create_handoff(err_msg: str, tb: str, target_file: str, attempts: int):
    """
    Create a persistent handoff record for a bug that the self-healing system
    could not fix autonomously after multiple attempts.
    """
    import json
    import os
    from datetime import datetime, timezone
    from settings import settings as config

    handoff_dir = os.path.join(config.DATA_DIR, "handoffs")
    os.makedirs(handoff_dir, exist_ok=True)

    handoff_id = f"bug_{int(datetime.now(timezone.utc).timestamp())}"
    path = os.path.join(handoff_dir, f"{handoff_id}.json")

    data = {
        "id": handoff_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": err_msg,
        "traceback": tb,
        "target_file": target_file,
        "attempts": attempts,
        "status": "pending"
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    log_audit("HANDOFF", f"Created bug handoff: {path}")
    return path
