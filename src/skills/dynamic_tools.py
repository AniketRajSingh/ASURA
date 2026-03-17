"""
Dynamic Tools Skill — ASURA
Allows the AI to autonomously create scripts for one-off tasks 
and register them as transient tools in the current session.
"""

import os
import sys
import importlib.util
from core.tool_protocol import register_tool
from skills.logger import log_audit, log_app

TRANSIENT_DIR = "/tmp/asura_transient"
os.makedirs(TRANSIENT_DIR, exist_ok=True)

def create_transient_tool(name: str, code: str, description: str):
    """
    Creates a temporary Python script and registers it as a tool.
    Ideal for complex data transformations or one-off logic.
    """
    safe_name = name.strip().lower().replace(" ", "_")
    file_path = os.path.join(TRANSIENT_DIR, f"{safe_name}.py")
    
    try:
        with open(file_path, "w") as f:
            f.write(code)
        
        # Dynamically load the module
        spec = importlib.util.spec_from_file_location(safe_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check for entry point (handler function)
        if not hasattr(module, "handler"):
            return f"Error: Transient tool must define a 'handler(args)' function."
        
        # Register in tool protocol
        register_tool(
            name=f"tmp_{safe_name}",
            function=module.handler,
            description=f"[Transient] {description}",
            category="transient"
        )
        
        log_audit("DYNAMIC_TOOL", f"Registered transient tool: tmp_{safe_name}")
        return f"SUCCESS: Transient tool 'tmp_{safe_name}' is now active."
        
    except Exception as e:
        log_app(f"Transient tool creation failed: {e}")
        return f"FAILED to create transient tool: {e}"
