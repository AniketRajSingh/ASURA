# ============================================================
# core/self_recovery.py — Deep Recursive Self-Repair
#
# Spawns a "Ghost" ASURA from a stable snapshot to repair
# the main system's broken core components.
# ============================================================

import os
import shutil
import zipfile
import subprocess
import time
from typing import Optional
from settings import settings as config
from skills.logger import log_audit, log_app

class SelfRecovery:
    """
    Handles the creation and orchestration of a recovery environment.
    """

    def __init__(self):
        self.recovery_root = os.path.join(config.DATA_DIR, "recovery_cache")
        self.backup_dir = config.BACKUP_DIR

    def find_golden_snapshot(self) -> Optional[str]:
        """Find the most recent snapshot that isn't the current broken state."""
        if not os.path.isdir(self.backup_dir):
            return None
        
        snapshots = sorted([
            f for f in os.listdir(self.backup_dir) 
            if f.endswith(".zip")
        ], reverse=True)
        
        return os.path.join(self.backup_dir, snapshots[0]) if snapshots else None

    def prepare_ghost_environment(self, snapshot_path: str):
        """Extract a stable snapshot into the recovery cache."""
        if os.path.exists(self.recovery_root):
            shutil.rmtree(self.recovery_root)
        os.makedirs(self.recovery_root)

        log_app(f"🛠️ Extracting stable ghost from {os.path.basename(snapshot_path)}...")
        with zipfile.ZipFile(snapshot_path, 'r') as zip_ref:
            zip_file_contents = zip_ref.namelist()
            # Most of our snapshots have a top-level dir named after the snapshot
            zip_ref.extractall(self.recovery_root)
            
        log_audit("RECOVERY", f"Ghost environment prepared at {self.recovery_root}")

    def launch_ghost_repair(self, error_msg: str):
        """
        Run a minimal ASURA from the ghost environment to fix the main core.
        """
        log_app("👻 Ghost ASURA rising to repair core...")
        
        # We use the GHOST's code to fix the MAIN project's code
        # Task: Fix the specific error in the main src/ directory
        repair_task = f"Fix this error in the parent directory code: {error_msg}. The parent directory is {config.BASE_DIR}"
        
        # Command to run ghost asura in standalone task mode
        ghost_python = os.path.join(config.BASE_DIR, ".venv", "bin", "python")
        ghost_main = os.path.join(self.recovery_root, "src", "main.py")
        
        # We set PYTHONPATH to the GHOST src
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(self.recovery_root, "src")
        
        try:
            # Ghost runs a single task: Fix the main system
            proc = subprocess.run(
                [ghost_python, ghost_main, "--cli", repair_task],
                cwd=self.recovery_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if proc.returncode == 0:
                log_app("✨ Ghost repair successful. Core integrity restored.")
                log_audit("RECOVERY", "Ghost repair output: " + proc.stdout[:500])
                return True
            else:
                log_app(f"❌ Ghost repair failed: {proc.stderr}")
                log_audit("RECOVERY_ERROR", f"Ghost failure: {proc.stderr}")
                return False
        except Exception as e:
            log_app(f"❌ Ghost launch failed: {e}")
            return False
        # Persistence: We no longer rmtree the recovery root here 
        # so the SelfHealingDaemon can use it for Ghost Restores.

def trigger_deep_recovery(error_msg: str):
    """Entry point for Meta-Healing."""
    recovery = SelfRecovery()
    golden = recovery.find_golden_snapshot()
    
    if not golden:
        log_app("❌ Deep Recovery impossible: No golden snapshots found.")
        return False
        
    recovery.prepare_ghost_environment(golden)
    return recovery.launch_ghost_repair(error_msg)
