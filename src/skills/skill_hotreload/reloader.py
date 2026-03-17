# ============================================================
# skills/skill_hotreload/reloader.py — Skill Hot-Reload
# Reload skills without restarting the system
# ============================================================
import importlib, sys
from settings import settings as config
from skills.logger import log_audit

def reload_skill(skill_name: str) -> dict:
    """Hot-reload a skill module without restarting."""
    module_name = f"skills.{skill_name}"
    try:
        if module_name in sys.modules:
            mod = importlib.reload(sys.modules[module_name])
            log_audit("HOTRELOAD", f"Reloaded: {skill_name}")
            return {"success": True, "skill": skill_name}
        else:
            mod = importlib.import_module(module_name)
            log_audit("HOTRELOAD", f"Loaded: {skill_name}")
            return {"success": True, "skill": skill_name}
    except Exception as e:
        log_audit("HOTRELOAD_ERROR", f"Failed: {skill_name}: {e}")
        return {"success": False, "error": str(e)}

def reload_all_skills() -> dict:
    """Reload all skill modules."""
    from skills.skill_registry import discover_skills
    registry = discover_skills()
    results = {}
    for name in registry:
        results[name] = reload_skill(name)
    passed = sum(1 for v in results.values() if v.get("success"))
    log_audit("HOTRELOAD", f"Reloaded: {passed}/{len(results)}")
    return {"total": len(results), "passed": passed, "results": results}
