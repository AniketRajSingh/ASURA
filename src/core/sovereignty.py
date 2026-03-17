# ============================================================
# core/sovereignty.py — Cross-Platform Anti-Sleep Protocol
# ============================================================

import os
import sys
import platform
import subprocess
import threading
import time
from skills.logger import log_audit, log_app

class SovereignAuthority:
    """
    Manages system power states to ensure ASURA stays awake during active cycles.
    Supports macOS, Linux, and Windows.
    """

    def __init__(self):
        self.os_type = platform.system().lower()
        self._lock_process = None
        self._active = False
        self._thread = None

    def stay_awake(self):
        """Prevent system from sleeping (Non-blocking)."""
        if self._active:
            return
        
        self._active = True
        log_app(f"Sovereign Power Lock engaged ({self.os_type})")
        
        # ── Start Jiggler Thread ────────────
        self._jiggler_active = True
        self._thread = threading.Thread(target=self._jiggler_loop, daemon=True)
        self._thread.start()

        if self.os_type == "darwin":
            # macOS: Use caffeinate
            try:
                self._lock_process = subprocess.Popen(["caffeinate", "-i"])
                log_audit("POWER", "macOS sleep prevented via caffeinate")
            except Exception as e:
                log_app(f"Failed to start caffeinate: {e}")

        elif self.os_type == "linux":
            # Linux: Use systemd-inhibit if available
            try:
                self._lock_process = subprocess.Popen([
                    "systemd-inhibit", 
                    "--why=ASURA Autonomous Cycle", 
                    "--who=ASURA", 
                    "--mode=block", 
                    "sleep", "infinity"
                ])
                log_audit("POWER", "Linux sleep prevented via systemd-inhibit")
            except Exception:
                log_app("systemd-inhibit not found, Linux sleep prevention limited")

        elif self.os_type == "windows":
            # Windows: Use SetThreadExecutionState via ctypes
            try:
                import ctypes
                # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED | ES_DISPLAY_REQUIRED
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000001 | 0x00000001 | 0x00000040 | 0x00000002)
                log_audit("POWER", "Windows sleep prevented via SetThreadExecutionState")
            except Exception as e:
                log_app(f"Windows Power Lock failed: {e}")

    def _jiggler_loop(self):
        """Periodically simulate activity to trick OS power management."""
        import pyautogui
        # Disable pyautogui fail-safe for this background task
        pyautogui.FAILSAFE = False
        
        log_app("🖱️ Activity Jiggler active.")
        while self._jiggler_active:
            try:
                # Move mouse by 1 pixel and back
                pyautogui.moveRel(1, 0, duration=0.1)
                pyautogui.moveRel(-1, 0, duration=0.1)
                # Or press an innocuous key like shift
                # pyautogui.press('shift')
            except Exception: pass
            time.sleep(120) # Every 2 minutes

    def release_lock(self):
        """Allow system to sleep again."""
        if not self._active:
            return
            
        log_app("Sovereign Power Lock released")
        self._active = False
        self._jiggler_active = False
        
        if self._lock_process:
            self._lock_process.terminate()
            self._lock_process = None
        
        if self.os_type == "windows":
            try:
                import ctypes
                # Reset to continuous
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            except Exception:
                pass

    def purge_memory(self):
        """Wipe all persistent state for a fresh start."""
        import shutil
        from settings import settings as config
        log_audit("SOVEREIGN_COMMAND", "Executing CORE_MEMORY_PURGE")
        
        files_to_delete = [
            config.CHAT_HISTORY_PATH,
            config.KNOWLEDGE_GRAPH_PATH,
            config.FEEDBACK_PATH,
            config.CALENDAR_PATH,
            config.TODO_PATH,
            os.path.join(config.DATA_DIR, "logs", "audit.txt"),
            os.path.join(config.DATA_DIR, "logs", "log.txt"),
        ]
        
        dirs_to_clear = [
            config.MEMORY_STORE_DIR,
            config.UPDATE_HISTORY_DIR,
            config.BACKUP_DIR,
            config.DRAFTS_DIR,
        ]

        for f in files_to_delete:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception as e:
                    log_app(f"Failed to remove {f}: {e}")

        for d in dirs_to_clear:
            if os.path.exists(d):
                try:
                    shutil.rmtree(d)
                    os.makedirs(d, exist_ok=True)
                except Exception as e:
                    log_app(f"Failed to clear {d}: {e}")

        log_app("Consciousness reset complete. Fresh start initiated.")
        return "Memory Core Purged. Re-initializing..."

    def hibernate(self):
        """Gracefully shut down the entire system service."""
        log_audit("SOVEREIGN_COMMAND", "Initiating system-wide hibernation")
        self.release_lock()
        
        # Give logs a moment to flush
        time.sleep(1)
        
        # Kill the current process tree
        # This will be caught by the Guardian Drive which should notice the 'HIBERNATE' intent
        # (We could write a flag to data/hibernate.flag)
        from settings import settings as config
        DATA_DIR = config.DATA_DIR
        with open(os.path.join(DATA_DIR, "hibernate.flag"), "w") as f:
            f.write(str(time.time()))
            
        os._exit(0)

# Global singleton
_authority = SovereignAuthority()

def get_authority():
    return _authority
