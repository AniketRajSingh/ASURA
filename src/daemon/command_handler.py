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
            # Create logs dir if not exists
            log_dir = PROJECT_ROOT / "data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "asura_core.log"
            
            # Re-launch using root run.py with managed bot flag
            env = os.environ.copy()
            env["ASURA_MANAGED_BOT"] = "true"
            
            # Open log file in append mode
            with open(log_file, "a") as f:
                # We use Popen with start_new_session to decouple it
                subprocess.Popen(
                    [sys.executable, "run.py", "start"], 
                    cwd=str(PROJECT_ROOT), 
                    env=env, 
                    stdout=f, 
                    stderr=f, 
                    start_new_session=True
                )
            logger.info(f"✅ Core restart triggered. Logs: {log_file}")
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
