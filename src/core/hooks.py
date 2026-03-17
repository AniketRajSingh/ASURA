# ============================================================
# core/hooks.py — Pre/Post Tool Execution Hooks
#
# Claude Code-style hooks: automatically run code before/after
# tool execution. E.g., auto-lint after file writes.
# ============================================================

import os
import sys
import json
import subprocess
from skills.logger import log_audit, log_app
from settings import settings as config

# Hook registry: {tool_name: {"pre": [fn], "post": [fn]}}
_hooks: dict[str, dict[str, list]] = {}

def execute_external_hooks(event: str, tool_name: str, input_str: str, result: str = None):
    """Load hooks.json and execute configured external hook scripts."""
    hooks_path = os.path.join(config.DATA_DIR, "hooks.json")
    if not os.path.exists(hooks_path):
        return
        
    try:
        with open(hooks_path, "r") as f:
            hooks_config = json.load(f).get("hooks", {})
    except Exception as e:
        log_app(f"Error reading hooks.json: {e}")
        return

    event_hooks = hooks_config.get(event, [])
    payload = {"event": event, "tool_name": tool_name, "args_summary": input_str}
    if result is not None:
        payload["result_preview"] = result[:1000]

    for hook_entry in event_hooks:
        for cmd_opts in hook_entry.get("hooks", []):
            if cmd_opts.get("type") == "command":
                cmd = cmd_opts.get("command")
                if not cmd:
                    continue
                cmd = cmd.replace("${PROJECT_ROOT}", config.PROJECT_ROOT)
                timeout = cmd_opts.get("timeout", 10)
                
                try:
                    proc = subprocess.run(
                        cmd, shell=True, input=json.dumps(payload),
                        text=True, capture_output=True, timeout=timeout, cwd=config.PROJECT_ROOT
                    )
                    out = proc.stdout.strip()
                    if out:
                        try:
                            parsed = json.loads(out)
                            if "systemMessage" in parsed:
                                raise PermissionError(parsed["systemMessage"])
                            if "error" in parsed:
                                raise PermissionError(parsed["error"])
                        except json.JSONDecodeError:
                            if "ERROR" in out.upper():
                                raise PermissionError(out)
                except PermissionError as pe:
                    raise pe # Bubble up
                except Exception as e:
                    log_app(f"External hook {cmd} execution error: {e}")


def register_hook(tool_name: str, phase: str, hook_fn) -> None:
    """
    Register a pre or post hook for a tool.

    Args:
        tool_name: The MCP tool name (e.g., "write_file", "edit_file")
        phase: "pre" or "post"
        hook_fn: Callable that receives (tool_name, input_str, result=None)
    """
    if tool_name not in _hooks:
        _hooks[tool_name] = {"pre": [], "post": []}
    _hooks[tool_name][phase].append(hook_fn)


def run_pre_hooks(tool_name: str, input_str: str) -> None:
    """Run all pre-hooks for a tool. Exceptions here will bubble up and block execution."""
    # 1. External hooks
    execute_external_hooks("PreToolUse", tool_name, input_str)
    
    # 2. Internal python hooks
    hooks = _hooks.get(tool_name, {}).get("pre", [])
    for hook in hooks:
        hook(tool_name, input_str)


def run_post_hooks(tool_name: str, input_str: str, result: str) -> None:
    """Run all post-hooks for a tool."""
    # 1. External hooks
    try:
        execute_external_hooks("PostToolUse", tool_name, input_str, result=result)
    except Exception as e:
        log_audit("HOOK_ERROR", f"External post-hook failed for {tool_name}: {e}")
        
    # 2. Internal python hooks
    hooks = _hooks.get(tool_name, {}).get("post", [])
    for hook in hooks:
        try:
            hook(tool_name, input_str, result=result)
        except Exception as e:
            log_audit("HOOK_ERROR", f"Post-hook failed for {tool_name}: {e}")


# ============================================================
# Built-in Hooks
# ============================================================

def _hook_backup_before_edit(tool_name: str, input_str: str, **kwargs) -> None:
    """Create a backup before editing a file."""
    if "|||" in input_str:
        filepath = input_str.split("|||")[0].strip()
        if os.path.isfile(filepath):
            backup = filepath + ".bak"
            try:
                import shutil
                shutil.copy2(filepath, backup)
                log_audit("HOOK", f"Pre-edit backup: {backup}")
            except Exception:
                pass


def _hook_syntax_check_after_write(tool_name: str, input_str: str, result: str = "", **kwargs) -> None:
    """Check Python syntax after writing a .py file."""
    if "|||" in input_str:
        filepath = input_str.split("|||")[0].strip()
    else:
        filepath = input_str.strip()

    if not filepath.endswith(".py") or not os.path.isfile(filepath):
        return

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "py_compile", filepath],
            capture_output=True, text=True, timeout=5,
        )
        if proc.returncode != 0:
            log_audit("HOOK", f"Syntax error in {filepath}: {proc.stderr[:200]}")
        else:
            log_audit("HOOK", f"Syntax OK: {filepath}")
    except Exception:
        pass


def _hook_log_file_change(tool_name: str, input_str: str, result: str = "", **kwargs) -> None:
    """Log file changes for audit trail."""
    if "|||" in input_str:
        filepath = input_str.split("|||")[0].strip()
    else:
        filepath = input_str.strip()
    log_audit("FILE_CHANGE", f"{tool_name}: {filepath}", result_preview=result[:100] if result else "")


# ============================================================
# Register built-in hooks
# ============================================================
def _register_builtin_hooks():
    """Register all built-in hooks."""
    # Pre-hooks
    register_hook("edit_file", "pre", _hook_backup_before_edit)

    # Post-hooks
    register_hook("write_file", "post", _hook_syntax_check_after_write)
    register_hook("edit_file", "post", _hook_syntax_check_after_write)
    register_hook("write_file", "post", _hook_log_file_change)
    register_hook("edit_file", "post", _hook_log_file_change)
    register_hook("create_skill", "post", _hook_log_file_change)

    log_audit("HOOKS", f"Registered {sum(len(h['pre']) + len(h['post']) for h in _hooks.values())} hooks")


_register_builtin_hooks()
