# ============================================================
# core/workflow_engine.py — YAML-Driven Workflow Automation
#
# Executes multi-step workflows defined in YAML files.
# Steps run in dependency order with failure handling.
# ============================================================

import os
import json
import time
from datetime import datetime, timezone
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None

from settings import settings as config
from skills.logger import log_audit, log_app

_WORKFLOWS_DIR = os.path.join(config.SRC_DIR, "workflows")


def _load_workflow(name: str) -> Optional[dict]:
    """Load a workflow definition from YAML."""
    if yaml is None:
        return None

    for ext in (".yaml", ".yml"):
        path = os.path.join(_WORKFLOWS_DIR, f"{name}{ext}")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

    return None


def list_workflows() -> str:
    """List all available workflows."""
    if not os.path.isdir(_WORKFLOWS_DIR):
        return "No workflows directory found."

    workflows = []
    for fname in sorted(os.listdir(_WORKFLOWS_DIR)):
        if not fname.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(_WORKFLOWS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                wf = yaml.safe_load(f) if yaml else {}
            name = wf.get("name", fname.rsplit(".", 1)[0])
            desc = wf.get("description", "No description")
            steps = len(wf.get("steps", []))
            workflows.append(f"  • {name} — {desc} ({steps} steps)")
        except Exception:
            workflows.append(f"  • {fname} — (error loading)")

    if not workflows:
        return "No workflows defined yet."

    return "📋 Available Workflows:\n" + "\n".join(workflows)


def run_workflow(name: str) -> dict:
    """
    Execute a named workflow.

    Returns:
        {
            "name": "workflow_name",
            "success": bool,
            "results": {"step_name": {"output": str, "success": bool}},
            "error": str or None,
        }
    """
    wf = _load_workflow(name)
    if not wf:
        return {"name": name, "success": False, "results": {}, "error": f"Workflow '{name}' not found"}

    steps = wf.get("steps", [])
    if not steps:
        return {"name": name, "success": False, "results": {}, "error": "Workflow has no steps"}

    log_audit("WORKFLOW", f"Starting: {name} ({len(steps)} steps)")

    results = {}
    completed = set()

    # Topological execution based on depends_on
    max_iterations = len(steps) * 2  # prevent infinite loops
    iteration = 0

    while len(completed) < len(steps) and iteration < max_iterations:
        iteration += 1
        progress = False

        for step in steps:
            step_name = step.get("name", f"step_{iteration}")
            if step_name in completed:
                continue

            # Check dependencies
            deps = step.get("depends_on", [])
            if not all(d in completed for d in deps):
                continue

            # Check dependency success
            dep_failed = any(
                not results.get(d, {}).get("success", False) for d in deps
            )
            if dep_failed:
                results[step_name] = {
                    "output": "Skipped — dependency failed",
                    "success": False,
                }
                completed.add(step_name)
                progress = True
                continue

            # Execute step
            log_audit("WORKFLOW", f"  Step: {step_name} (tool: {step.get('tool', '?')})")
            try:
                output = _execute_step(step)
                success = "ERROR" not in output.upper() and "FAIL" not in output.upper()
                results[step_name] = {"output": output[:1000], "success": success}

                if not success:
                    on_failure = step.get("on_failure")
                    if on_failure:
                        log_audit("WORKFLOW", f"  Failure handler: {on_failure}")
                        _execute_step({"tool": "shell", "input": on_failure, "name": f"{step_name}_rollback"})

                log_audit("WORKFLOW", f"  {step_name}: {'✅' if success else '❌'}")
            except Exception as e:
                results[step_name] = {"output": f"Exception: {e}", "success": False}
                log_audit("WORKFLOW", f"  {step_name}: ❌ {e}")

            completed.add(step_name)
            progress = True

        if not progress:
            # Deadlock — circular dependencies
            remaining = [s["name"] for s in steps if s.get("name") not in completed]
            for r in remaining:
                results[r] = {"output": "Deadlocked — circular dependency", "success": False}
            break

    all_success = all(r.get("success", False) for r in results.values())
    log_audit("WORKFLOW", f"Completed: {name} ({'✅' if all_success else '❌'})")

    return {
        "name": name,
        "success": all_success,
        "results": results,
        "error": None if all_success else "Some steps failed",
    }


def _execute_step(step: dict) -> str:
    """Execute a single workflow step using the MCP tool protocol."""
    tool = step.get("tool", "shell")
    input_str = step.get("input", "")

    from core.tool_protocol import dispatch
    return dispatch(tool, input_str)
