# ============================================================
# skills/shell_executor/executor.py — Sandboxed Shell Execution
#
# Rules:
#   - Commands inside BASE_DIR → execute freely
#   - Commands outside BASE_DIR or destructive ops → ask master via Telegram
#   - All commands logged to audit.txt
# ============================================================

import os
import asyncio
import shlex
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit, log_app
from core.utils import is_safe_path

# Commands that always require master approval regardless of path
DANGEROUS_COMMANDS = {
    "rm", "rmdir", "sudo", "su", "chmod", "chown",
    "mkfs", "dd", "format", "kill", "killall",
    "shutdown", "reboot", "halt", "poweroff",
    "curl", "wget",  # network ops outside project
}

# Max output to keep in memory
MAX_OUTPUT_CHARS = 10_000


def _is_inside_project(path: str) -> bool:
    """Check if a path is inside the project directory."""
    return is_safe_path(path, config.BASE_DIR)


def _analyze_command(cmd: str) -> dict:
    """
    Analyze a shell command to determine:
    - Whether it's safe to run autonomously
    - What paths it touches
    - Whether it needs master approval
    """
    analysis = {
        "command": cmd,
        "safe": True,
        "reason": "",
        "touches_outside": False,
        "is_destructive": False,
    }

    try:
        parts = shlex.split(cmd)
    except ValueError:
        parts = cmd.split()

    if not parts:
        analysis["safe"] = False
        analysis["reason"] = "Empty command"
        return analysis

    base_cmd = os.path.basename(parts[0])

    # Check for dangerous commands
    if base_cmd in DANGEROUS_COMMANDS:
        analysis["safe"] = False
        analysis["is_destructive"] = True
        analysis["reason"] = f"Dangerous command: {base_cmd}"
        return analysis

    # Check if any arguments reference paths outside project
    for arg in parts[1:]:
        if arg.startswith("/") or arg.startswith("~") or ".." in arg:
            if not _is_inside_project(arg):
                analysis["safe"] = False
                analysis["touches_outside"] = True
                analysis["reason"] = f"Path outside project: {arg}"
                return analysis

    # Pipe chains: check each command
    if "|" in cmd or "&&" in cmd or ";" in cmd:
        # Simple check: ensure no dangerous commands in chain
        for segment in cmd.replace("&&", "|").replace(";", "|").split("|"):
            sub_parts = segment.strip().split()
            if sub_parts and os.path.basename(sub_parts[0]) in DANGEROUS_COMMANDS:
                analysis["safe"] = False
                analysis["is_destructive"] = True
                analysis["reason"] = f"Dangerous command in chain: {sub_parts[0]}"
                return analysis

    return analysis


async def execute(cmd: str, timeout: int = 30) -> dict:
    """
    Execute a shell command inside the project directory (Async).
    Returns dict with: stdout, stderr, returncode, duration.

    Only runs commands that pass safety analysis.
    For unsafe commands, returns the analysis with safe=False.
    """
    analysis = _analyze_command(cmd)

    log_audit("SHELL", f"Command: {cmd}")
    log_audit("SHELL", f"Analysis: safe={analysis['safe']}, reason={analysis.get('reason', 'OK')}")

    if not analysis["safe"]:
        log_audit("SHELL_BLOCKED", f"Blocked: {analysis['reason']}")
        return {
            "success": False,
            "stdout": "",
            "stderr": f"BLOCKED: {analysis['reason']}",
            "returncode": -1,
            "needs_approval": True,
            "analysis": analysis,
        }

    start = datetime.now()

    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=config.BASE_DIR,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=True  # Ensure we create a new process group
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except (asyncio.TimeoutError, TimeoutError):
            try:
                os.killpg(os.getpgid(process.pid), 9)
            except Exception:
                process.kill()
            await process.wait()
            log_audit("SHELL_TIMEOUT", f"Command timed out after {timeout}s")
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Timed out after {timeout}s",
                "returncode": -2,
                "needs_approval": False,
            }

        duration = (datetime.now() - start).total_seconds()

        stdout = stdout_bytes.decode('utf-8', errors='replace')[:MAX_OUTPUT_CHARS] if stdout_bytes else ""
        stderr = stderr_bytes.decode('utf-8', errors='replace')[:MAX_OUTPUT_CHARS] if stderr_bytes else ""

        log_audit("SHELL", f"Exit code: {process.returncode} ({duration:.1f}s)")
        if process.returncode != 0:
            log_audit("SHELL_ERROR", f"stderr: {stderr[:200]}")

        return {
            "success": process.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": process.returncode,
            "duration": duration,
            "needs_approval": False,
        }

    except Exception as e:
        log_audit("SHELL_ERROR", f"Execution error: {e}")
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -3,
            "needs_approval": False,
        }


async def execute_python(code: str, timeout: int = 30) -> dict:
    """Execute a Python snippet in the project context."""
    # Write to temp file and run
    tmp_path = os.path.join(config.BASE_DIR, "_temp_exec.py")
    try:
        with open(tmp_path, "w") as f:
            f.write(code)
        result = await execute(f"python {tmp_path}", timeout=timeout)
        return result
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


async def list_project_files(pattern: str = "*.py") -> str:
    """List files in the project directory matching a pattern."""
    result = await execute(f"find . -name '{pattern}' -not -path './.venv/*' -not -path './__pycache__/*' | sort")
    return result.get("stdout", "")


def read_file(rel_path: str) -> str:
    """Read a file from the project directory."""
    full_path = os.path.join(config.BASE_DIR, rel_path)
    if not _is_inside_project(full_path):
        return f"BLOCKED: {rel_path} is outside project directory"
    if not os.path.isfile(full_path):
        return f"File not found: {rel_path}"
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading {rel_path}: {e}"


def write_file(rel_path: str, content: str) -> bool:
    """Write a file in the project directory."""
    full_path = os.path.join(config.BASE_DIR, rel_path)
    if not _is_inside_project(full_path):
        log_audit("SHELL_BLOCKED", f"Write outside project: {rel_path}")
        return False
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        log_audit("SHELL", f"File written: {rel_path}")
        return True
    except Exception as e:
        log_audit("SHELL_ERROR", f"Write failed: {rel_path}: {e}")
        return False
