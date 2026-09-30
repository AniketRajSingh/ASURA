import os
import json
import logging
from typing import Any, Dict, Optional
from settings import settings as config

logger = logging.getLogger(__name__)

class StateManager:
    """Manages the consolidated state.json file for all AI persistent generic data."""
    def __init__(self, path: Optional[str] = None):
        self.path = path or config.STATE_PATH
        self._ensure_exists()

    def _ensure_exists(self):
        if not os.path.exists(self.path):
            self.save({
                "todos": [],
                "rbac": {},
                "feedback": [],
                "calendar": []
            })
            logger.info("Initializing unified state.json")
    
    def load(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state.json: {e}")
            return {"todos": [], "rbac": {}, "feedback": [], "calendar": []}

    def save(self, data: Dict[str, Any]):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state.json: {e}")

    def get_section(self, key: str, default: Any = None) -> Any:
        data = self.load()
        return data.get(key, default)

    def update_section(self, key: str, value: Any):
        data = self.load()
        data[key] = value
        self.save(data)

# Singleton instance
state = StateManager()


def get_state_manager() -> StateManager:
    """Return singleton state manager."""
    return state


def update_env(updates: dict):
    """
    Write updated key-value pairs to .env and hot-patch the live config module.
    Called by the dashboard Settings page when the user clicks Save.
    """
    from settings import settings as cfg

    env_path = os.path.join(cfg.ENGINE_HOME, ".env")

    # Read current .env
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            env_lines = f.readlines()

    env_dict = {}
    for line in env_lines:
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env_dict[k.strip()] = v.strip()

    # Apply updates
    for ui_key, value in updates.items():
        if isinstance(value, (dict, list)):
            continue # Skip trying to save complex objects to .env for now, or use json.dumps
        if value is None:
            value = ""
        
        # Update live config
        if hasattr(cfg, ui_key):
            setattr(cfg, ui_key, value)
            
        # Update env dict (prefer ASURA_ prefix for standard settings)
        env_var = f"ASURA_{ui_key}" if not ui_key.startswith("ASURA_") else ui_key
        # For some things that are also standard without prefix
        if ui_key in ["TELEGRAM_BOT_TOKEN", "MASTER_NAME"]:
            env_var = ui_key
            
        env_dict[env_var] = str(value)

    # Write .env back
    with open(env_path, "w") as f:
        for k, v in env_dict.items():
            f.write(f"{k}={v}\n")

    logger.info(f"Settings updated: {list(updates.keys())}")
