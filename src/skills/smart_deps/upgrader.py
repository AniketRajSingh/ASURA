# ============================================================
# skills/smart_deps/upgrader.py — Smart Dependency Upgrader
# Auto-detect outdated deps, suggest upgrades
# ============================================================
import subprocess, json
from settings import settings as config
from skills.logger import log_audit

def check_outdated() -> list[dict]:
    try:
        result = subprocess.run(["pip", "list", "--outdated", "--format=json"],
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except: pass
    return []

def upgrade_package(name: str) -> bool:
    result = subprocess.run(["pip", "install", "--upgrade", name],
                            capture_output=True, text=True, timeout=120)
    log_audit("DEPS", f"Upgrade {name}: {'OK' if result.returncode == 0 else 'FAIL'}")
    return result.returncode == 0

def format_deps_report() -> str:
    outdated = check_outdated()
    if not outdated: return "📦 All dependencies up to date."
    lines = [f"📦 *Outdated Dependencies ({len(outdated)})*\n"]
    for d in outdated[:15]:
        lines.append(f"  • `{d['name']}` {d.get('version', '?')} → {d.get('latest_version', '?')}")
    return "\n".join(lines)
