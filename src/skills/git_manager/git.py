# ============================================================
# skills/git_manager/git.py — Git Integration Skill
# Auto-commit, branch management, diff review, PR support
# ============================================================

import os
import subprocess
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit


def _git(cmd: str) -> dict:
    """Run a git command in the project directory (Cross-Platform)."""
    import shlex
    try:
        # Avoid shell=True for cross-platform safety and command injection protection
        # Split cmd responsibly, keeping quoted parts intact if any
        full_cmd = ["git"] + shlex.split(cmd)
        
        result = subprocess.run(
            full_cmd, shell=False, capture_output=True, text=True,
            cwd=config.BASE_DIR, timeout=30,
        )
        return {"success": result.returncode == 0,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e)}


def init_repo() -> bool:
    if not os.path.isdir(os.path.join(config.BASE_DIR, ".git")):
        result = _git("init")
        if result["success"]:
            _git('config user.name "ASURA AI"')
            _git('config user.email "tf@ai.local"')
            log_audit("GIT", "Repository initialized")
        return result["success"]
    return True


def status() -> str:
    result = _git("status --porcelain")
    return result["stdout"] if result["success"] else result["stderr"]


def diff(staged: bool = False) -> str:
    flag = "--staged" if staged else ""
    result = _git(f"diff {flag}")
    return result["stdout"][:5000] if result["success"] else result["stderr"]


def auto_commit(message: str = None) -> bool:
    if not message:
        message = f"[ASURA AI] Auto-commit {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    _git("add -A")
    result = _git(f'commit -m "{message}"')
    if result["success"]:
        log_audit("GIT", f"Committed: {message}")
    return result["success"]


def create_branch(name: str) -> bool:
    result = _git(f"checkout -b {name}")
    log_audit("GIT", f"Branch: {name}")
    return result["success"]


def switch_branch(name: str) -> bool:
    return _git(f"checkout {name}")["success"]


def log(n: int = 10) -> str:
    result = _git(f"log --oneline -n {n}")
    return result["stdout"] if result["success"] else "No commits yet"


def format_git_summary() -> str:
    s = status()
    l = log(5)
    branch = _git("branch --show-current")["stdout"] or "unknown"
    changed = len(s.strip().split("\n")) if s.strip() else 0

    return (
        f"🔀 *Git Status*\n\n"
        f"Branch: `{branch}`\n"
        f"Changed files: {changed}\n\n"
        f"*Recent commits:*\n```\n{l}\n```"
    )
