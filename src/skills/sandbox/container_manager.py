# ============================================================
# skills/sandbox/container_manager.py — Headless Virtual Sandbox
#
# Provides isolated virtual desktop & Android sandbox for ASURA:
# 1. Docker/Podman container lifecycle (start, stop, status)
# 2. Headless X11 virtual display (Xvfb :99)
# 3. Isolated ADB server for untrusted mobile automation
# 4. Safe command execution quarantined from host machine
# 100% Cross-Platform: Works on macOS, Linux, and Windows.
# ============================================================

from __future__ import annotations
import os
import shutil
import subprocess
import json
import base64
from typing import Optional, Dict, Any

from settings import settings as config
from skills.logger import log_audit, log_app
from core.consciousness import consciousness


class SandboxManager:
    """
    Manages isolated Docker container with headless virtual display (Xvfb)
    and ADB bridge for zero-risk untrusted autonomous execution.
    """
    CONTAINER_NAME = "asura-sandbox"
    IMAGE_NAME = "asura-sandbox:latest"
    VIRTUAL_DISPLAY = ":99"

    def __init__(self):
        self._docker_bin = shutil.which("docker") or shutil.which("podman")
        self._compose_file = os.path.join(config.PROJECT_ROOT, "docker", "docker-compose.sandbox.yml")

    def is_docker_available(self) -> bool:
        """Check if Docker/Podman daemon is installed and reachable."""
        if not self._docker_bin:
            return False
        try:
            res = subprocess.run([self._docker_bin, "info"], capture_output=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """Inspect the current sandbox container status."""
        docker_ok = self.is_docker_available()
        if not docker_ok:
            return {
                "available": False,
                "running": False,
                "engine": None,
                "virtual_display": self.VIRTUAL_DISPLAY,
                "error": "Docker/Podman daemon is not running or not installed.",
            }

        try:
            cmd = [self._docker_bin, "inspect", "--format", "{{.State.Status}}", self.CONTAINER_NAME]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            status = proc.stdout.strip() if proc.returncode == 0 else "stopped"
            running = status == "running"

            return {
                "available": True,
                "running": running,
                "status": status,
                "container_name": self.CONTAINER_NAME,
                "virtual_display": self.VIRTUAL_DISPLAY,
                "vnc_port": 5900,
                "novnc_port": 6080,
                "adb_port": 5555,
                "engine": os.path.basename(self._docker_bin),
            }
        except Exception as e:
            return {"available": True, "running": False, "error": str(e)}

    def start_sandbox(self, width: int = 1280, height: int = 800) -> Dict[str, Any]:
        """Launch the headless sandbox container."""
        if not self.is_docker_available():
            return {"success": False, "error": "Docker daemon is not available."}

        status = self.get_status()
        if status.get("running"):
            return {"success": True, "message": "Sandbox container is already active.", "status": status}

        consciousness.record_thought("sandbox_start", "Spinning up isolated virtual Xvfb sandbox...", pulse="vigilant")

        try:
            # Check if container exists stopped
            check = subprocess.run([self._docker_bin, "ps", "-a", "-q", "-f", f"name={self.CONTAINER_NAME}"], capture_output=True, text=True)
            if check.stdout.strip():
                # Start existing container
                subprocess.run([self._docker_bin, "start", self.CONTAINER_NAME], check=True, capture_output=True)
            else:
                # Run new container
                run_cmd = [
                    self._docker_bin, "run", "-d",
                    "--name", self.CONTAINER_NAME,
                    "-e", f"RESOLUTION={width}x{height}x24",
                    "-e", f"DISPLAY={self.VIRTUAL_DISPLAY}",
                    "-p", "6080:6080",
                    "-p", "5555:5555",
                    self.IMAGE_NAME
                ]
                subprocess.run(run_cmd, check=True, capture_output=True)

            log_audit("SANDBOX_STARTED", f"Sandbox {self.CONTAINER_NAME} started on display {self.VIRTUAL_DISPLAY}")
            return {"success": True, "status": self.get_status()}
        except Exception as e:
            log_app(f"Failed to start sandbox: {e}")
            return {"success": False, "error": str(e)}

    def stop_sandbox(self) -> Dict[str, Any]:
        """Halt the sandbox container."""
        if not self.is_docker_available():
            return {"success": False, "error": "Docker daemon is not available."}
        try:
            subprocess.run([self._docker_bin, "stop", self.CONTAINER_NAME], capture_output=True, timeout=10)
            log_audit("SANDBOX_STOPPED", f"Sandbox {self.CONTAINER_NAME} halted.")
            return {"success": True, "message": "Sandbox container stopped."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_isolated_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute an untrusted command safely inside the isolated sandbox container.
        Zero access to host filesystem, credentials, or network secrets.
        """
        if not self.is_docker_available():
            return {"success": False, "error": "Docker is not available for isolated execution."}

        status = self.get_status()
        if not status.get("running"):
            start_res = self.start_sandbox()
            if not start_res.get("success"):
                return {"success": False, "error": f"Cannot launch sandbox: {start_res.get('error')}"}

        consciousness.record_thought("sandbox_exec", f"Executing isolated command in sandbox: {command[:60]}", pulse="vigilant")

        try:
            exec_cmd = [self._docker_bin, "exec", self.CONTAINER_NAME, "sh", "-c", command]
            proc = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=timeout)
            return {
                "success": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "isolated": True,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout} seconds."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def capture_sandbox_screen(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Capture the virtual framebuffer display (:99) inside the sandbox.
        """
        dest = output_path or os.path.join(config.PROJECT_ROOT, "data", "sandbox_screen.png")
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        res = self.execute_isolated_command(f"xwd -root -display {self.VIRTUAL_DISPLAY} -silent | convert xwd:- /tmp/screen.png && cat /tmp/screen.png | base64")
        if not res.get("success"):
            return {"success": False, "error": res.get("stderr") or res.get("error")}

        try:
            b64_data = res.get("stdout", "").strip()
            raw_bytes = base64.b64decode(b64_data)
            with open(dest, "wb") as f:
                f.write(raw_bytes)
            return {
                "success": True,
                "path": dest,
                "base64_image": b64_data,
                "display": self.VIRTUAL_DISPLAY,
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to decode sandbox screenshot: {e}"}


# Global singleton instance
sandbox_manager = SandboxManager()
