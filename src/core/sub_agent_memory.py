import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit, log_app

MEMORY_ROOT = os.path.join(config.PROJECT_ROOT, "data", "sub_agent_memory")

class SubAgentMemory:
    """
    Manages isolated memory vaults for sub-agents.
    Each agent has its own JSON-based vault for transient facts, 
    context, and task history.
    """
    
    @staticmethod
    def _get_vault_path(agent_name: str) -> str:
        os.makedirs(MEMORY_ROOT, exist_ok=True)
        return os.path.join(MEMORY_ROOT, f"{agent_name.lower()}_vault.json")

    @staticmethod
    def initialize_vault(agent_name: str, role: str):
        """Initialize a new memory vault for an agent."""
        path = SubAgentMemory._get_vault_path(agent_name)
        data = {
            "agent_name": agent_name,
            "role": role,
            "created_at": datetime.now().isoformat(),
            "facts": [],
            "history": [],
            "metadata": {}
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        log_audit("MEMORY", f"Initialized vault for sub-agent: {agent_name}")

    @staticmethod
    def add_fact(agent_name: str, fact: str):
        """Add a transient fact to an agent's vault."""
        path = SubAgentMemory._get_vault_path(agent_name)
        if not os.path.exists(path):
            SubAgentMemory.initialize_vault(agent_name, "unknown")
            
        with open(path, "r") as f:
            data = json.load(f)
            
        data["facts"].append({
            "fact": fact,
            "timestamp": datetime.now().isoformat()
        })
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def add_history(agent_name: str, task: str, result: str):
        """Add a task outcome to an agent's history."""
        path = SubAgentMemory._get_vault_path(agent_name)
        if not os.path.exists(path):
            SubAgentMemory.initialize_vault(agent_name, "unknown")
            
        with open(path, "r") as f:
            data = json.load(f)
            
        data["history"].append({
            "task": task,
            "result": result[:2000],  # Truncate large results
            "timestamp": datetime.now().isoformat()
        })
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def get_vault(agent_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve the entire memory vault for an agent."""
        path = SubAgentMemory._get_vault_path(agent_name)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    @staticmethod
    def delete_vault(agent_name: str):
        """Permanently delete an agent's memory vault."""
        path = SubAgentMemory._get_vault_path(agent_name)
        if os.path.exists(path):
            os.remove(path)
            log_audit("MEMORY", f"Deleted vault for sub-agent: {agent_name}")

    @staticmethod
    def list_vaults() -> List[str]:
        """List all active sub-agent vaults."""
        if not os.path.exists(MEMORY_ROOT):
            return []
        return [f.replace("_vault.json", "") for f in os.listdir(MEMORY_ROOT) if f.endswith("_vault.json")]
