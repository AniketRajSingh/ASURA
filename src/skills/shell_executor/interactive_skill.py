# ============================================================
# skills/shell_executor/interactive_skill.py — Cross-Platform Shell
# ============================================================
import os
import subprocess
import threading
import time
from settings import settings as config
from skills.logger import log_audit

class InteractiveShell:
    """
    Manages a long-running shell process with stdin/stdout control.
    Supports Windows (CMD) and POSIX (Sh/Bash).
    """

    def __init__(self, cmd: str):
        self.cmd = cmd
        self.process = None
        self.stdout_lines = []
        self.stderr_lines = []
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        """Start the process across platforms."""
        log_audit("SHELL_INTERACTIVE", f"Starting: {self.cmd}")
        
        # OS-specific shell defaults
        shell_cmd = ["cmd", "/c", self.cmd] if os.name == "nt" else ["/bin/sh", "-c", self.cmd]
        
        try:
            self.process = subprocess.Popen(
                shell_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                cwd=config.BASE_DIR,
                env=os.environ.copy()
            )
            self._running = True
            
            # Start background readers
            threading.Thread(target=self._reader, args=(self.process.stdout, self.stdout_lines), daemon=True).start()
            threading.Thread(target=self._reader, args=(self.process.stderr, self.stderr_lines), daemon=True).start()
            
            return True
        except Exception as e:
            log_audit("SHELL_ERROR", f"Failed to start: {e}")
            return False

    def _reader(self, pipe, storage):
        while self._running:
            line = pipe.readline()
            if not line:
                break
            with self._lock:
                storage.append(line)
                if len(storage) > 1000: storage.pop(0) # Keep last 1000 lines

    def send_input(self, text: str):
        """Send text to stdin."""
        if not self.process or not self._running:
            return False
        try:
            if not text.endswith("\n"): text += "\n"
            self.process.stdin.write(text)
            self.process.stdin.flush()
            log_audit("SHELL_INTERACTIVE", f"Sent Input: {text.strip()}")
            return True
        except Exception as e:
            log_audit("SHELL_ERROR", f"Failed to send input: {e}")
            return False

    def get_output(self, clear: bool = False) -> str:
        """Get accumulated stdout."""
        with self._lock:
            out = "".join(self.stdout_lines)
            if clear: self.stdout_lines = []
            return out

    def get_errors(self, clear: bool = False) -> str:
        """Get accumulated stderr."""
        with self._lock:
            err = "".join(self.stderr_lines)
            if clear: self.stderr_lines = []
            return err

    def stop(self):
        """Gracefully terminate the process."""
        self._running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            log_audit("SHELL_INTERACTIVE", "Stopped process.")

# Active shells registry for multi-turn sessions
_active_sessions = {}

def start_interactive_session(session_id: str, cmd: str) -> bool:
    if session_id in _active_sessions:
        _active_sessions[session_id].stop()
    
    shell = InteractiveShell(cmd)
    if shell.start():
        _active_sessions[session_id] = shell
        return True
    return False

def send_session_input(session_id: str, text: str) -> str:
    if session_id not in _active_sessions:
        return "Session not found."
    
    shell = _active_sessions[session_id]
    shell.send_input(text)
    time.sleep(1) # Give it a second to react
    return shell.get_output()

def get_session_status(session_id: str) -> dict:
    if session_id not in _active_sessions:
        return {"active": False}
    
    shell = _active_sessions[session_id]
    return {
        "active": shell.process.poll() is None,
        "output": shell.get_output(),
        "errors": shell.get_errors()
    }
