"""
Command Handler for ASURA Daemon
"""
import subprocess
import time
import os
import sys
from pathlib import Path
from .logger import logger
from .config import PROJECT_ROOT

class CommandHandler:
    def __init__(self, stop_script: Path, run_script: Path):
        self.stop_script = stop_script
        self.run_script = run_script
        
    def execute_command(self, command: list[str]) -> bool:
        logger.info(f"Executing: {' '.join(command)}")
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(PROJECT_ROOT)
            )
            if result.returncode != 0:
                logger.error(f"Command failed with code {result.returncode}: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return False
    
    def restart_asura(self) -> bool:
        logger.info("🔄 Initiating ASURA Restart Sequence...")
        
        # 1. Stop Core
        # Calling stop.py directly (assumes python is on path)
        if not self.execute_command([sys.executable, "stop.py", "--core"]):
            logger.warning("Core stop failed or no processes found.")
        
        time.sleep(1)
        
        # 2. Start Core in background
        try:
            # Re-launch using root run.py with managed bot flag
            env = os.environ.copy()
            env["ASURA_MANAGED_BOT"] = "true"
            subprocess.Popen([sys.executable, "run.py", "start"], cwd=str(PROJECT_ROOT), env=env, start_new_session=True)
            logger.info("✅ Core restart triggered.")
            return True
        except Exception as e:
            logger.error(f"Failed to launch Core: {e}")
            return False

    def handle_command(self, text: str) -> str:
        cmd = text.strip().lower()
        if cmd == '/restart':
            success = self.restart_asura()
            return "🔄 Restart sequence initiated." if success else "❌ Restart failed."
        elif cmd == '/stop':
            success = self.execute_command([sys.executable, "stop.py", "--core"])
            return "🛑 Core system stopped. (Daemon remains active)" if success else "❌ Stop failed."
        elif cmd == '/status':
            return "🟢 ASURA Daemon is operational."
        return ""
