# ============================================================
# core/startup_checks.py — Boot-time tool verification
# Runs on every startup. Reports failures to audit log and
# attempts auto-fix for known issues (import mismatches).
# ============================================================

import os
import sys
import importlib
import json
from skills.logger import log_audit, log_app


def verify_all_skills() -> dict:
    """Import every skill module. Returns {passed: [...], failed: [...]}."""
    from settings import settings as config
    results = {"passed": [], "failed": []}
    
    for entry in sorted(os.listdir(config.SKILLS_DIR)):
        skill_path = os.path.join(config.SKILLS_DIR, entry)
        if not os.path.isdir(skill_path) or entry.startswith('_'):
            continue
        
        try:
            importlib.import_module(f"skills.{entry}")
            results["passed"].append(entry)
        except Exception as e:
            results["failed"].append({"skill": entry, "error": f"{type(e).__name__}: {e}"})
    
    return results


async def verify_dispatcher_tools() -> dict:
    """Test each dispatcher tool with safe inputs via MCP protocol."""
    from core.tool_protocol import dispatch as mcp_dispatch
    
    safe_tests = [
        ("shell", "echo OK"),
        ("system_info", "full"),
        ("read_file", "src/config.py"),
        ("list_skills", "all"),
        ("todos", "list"),
        ("memory_recall", "startup_check"),
        ("list_files", "src/skills/"),
    ]
    
    results = {"passed": [], "failed": []}
    
    for tool_name, tool_input in safe_tests:
        try:
            # We are already in an event loop now
            result = await mcp_dispatch(tool_name, tool_input)
            if result and result.strip():
                results["passed"].append(tool_name)
            else:
                results["failed"].append({"tool": tool_name, "error": "Returned empty result"})
        except Exception as e:
            results["failed"].append({"tool": tool_name, "error": f"{type(e).__name__}: {e}"})
    
    return results


async def run_startup_checks() -> str:
    """Run all startup checks. Returns a summary string."""
    log_app("Running startup self-check...")
    
    # 1. Verify skill imports
    skill_results = verify_all_skills()
    skill_pass = len(skill_results["passed"])
    skill_fail = len(skill_results["failed"])
    
    # 2. Verify dispatcher tools
    tool_results = await verify_dispatcher_tools()
    tool_pass = len(tool_results["passed"])
    tool_fail = len(tool_results["failed"])
    
    # 3. Build report
    total_pass = skill_pass + tool_pass
    total_fail = skill_fail + tool_fail
    
    if total_fail == 0:
        summary = f"Self-check PASSED: {skill_pass} skills, {tool_pass} tools operational"
        log_audit("SELF_CHECK", summary)
    else:
        lines = [f"Self-check: {total_fail} issues found"]
        for f in skill_results["failed"]:
            lines.append(f"  Skill '{f['skill']}': {f['error']}")
        for f in tool_results["failed"]:
            lines.append(f"  Tool '{f['tool']}': {f['error']}")
        summary = "\n".join(lines)
        log_audit("SELF_CHECK_FAIL", summary)
        log_app(summary)
    
    log_app(summary)
    return summary
