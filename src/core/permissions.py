# ============================================================
# core/permissions.py — Granular Permissions Framework
#
# Claude Code-style per-path, per-tool access control.
# Replaces the binary PROTECTED_FILES + needs_approval approach.
# ============================================================

import os
import re
from settings import settings as config
from skills.logger import log_audit

# Default permission rules (can be overridden by ASURA.md or settings)
_rules: list[dict] = [
    # High-risk: always block
    {"action": "deny", "tool": "shell", "pattern": r"rm\s+(-rf?)\s+/(?!tmp)", "reason": "Destructive rm on root paths"},
    {"action": "deny", "tool": "shell", "pattern": r"mkfs|fdisk|dd\s+if=", "reason": "Disk-level operations"},
    {"action": "deny", "tool": "shell", "pattern": r"chmod\s+777", "reason": "Insecure permissions"},
    {"action": "deny", "tool": "shell", "pattern": r"curl.*\|\s*(?:bash|sh)", "reason": "Pipe to shell"},
    {"action": "deny", "tool": "write_file", "path": "/etc/*", "reason": "System config"},
    {"action": "deny", "tool": "write_file", "path": "/usr/*", "reason": "System binaries"},
    {"action": "deny", "tool": "edit_file", "path": "*/core/self_updater.py", "reason": "Protected: self-updater"},

    # Medium-risk: require approval (logged, but allowed)
    {"action": "warn", "tool": "shell", "pattern": r"pip\s+install", "reason": "Package installation"},
    {"action": "warn", "tool": "shell", "pattern": r"git\s+push", "reason": "Git push"},
    {"action": "warn", "tool": "shell", "pattern": r"systemctl|service\s+", "reason": "Service management"},

    # Allow everything else
    {"action": "allow", "tool": "*", "reason": "Default allow"},
]


def check_permission(tool_name: str, input_str: str) -> tuple[bool, str]:
    """
    Check if a tool invocation is permitted.

    Args:
        tool_name: The MCP tool name
        input_str: The tool's input string

    Returns:
        (allowed: bool, reason: str)
        If denied, reason explains why.
        If warned, logs but still allows.
    """
    for rule in _rules:
        # Check tool match
        rule_tool = rule.get("tool", "*")
        if rule_tool != "*" and rule_tool != tool_name:
            continue

        # Check pattern match (for shell commands, content)
        pattern = rule.get("pattern")
        if pattern:
            if not re.search(pattern, input_str):
                continue

        # Check path match (for file operations)
        path = rule.get("path")
        if path:
            # Extract file path from input
            file_path = input_str.split("|||")[0].strip() if "|||" in input_str else input_str.strip()
            if not _path_matches(file_path, path):
                continue

        # Rule matched
        action = rule.get("action", "allow")
        reason = rule.get("reason", "No reason")

        if action == "deny":
            log_audit("PERMISSION", f"DENIED: {tool_name}({input_str[:60]}) — {reason}")
            return False, f"BLOCKED: {reason}"

        elif action == "warn":
            log_audit("PERMISSION", f"WARNED: {tool_name}({input_str[:60]}) — {reason}")
            # Allow but log warning
            return True, f"WARNING: {reason}"

        elif action == "allow":
            return True, "OK"

    return True, "OK"


def add_rule(action: str, tool: str = "*", pattern: str = None,
             path: str = None, reason: str = "") -> None:
    """Add a new permission rule at the top of the rule list (highest priority)."""
    rule = {"action": action, "tool": tool, "reason": reason}
    if pattern:
        rule["pattern"] = pattern
    if path:
        rule["path"] = path
    _rules.insert(0, rule)  # Insert at top for highest priority
    log_audit("PERMISSION", f"Added rule: {action} {tool} — {reason}")


def get_rules_summary() -> str:
    """Return a formatted summary of all permission rules."""
    lines = ["🔐 Permission Rules:\n"]
    for r in _rules:
        action = r.get("action", "?").upper()
        tool = r.get("tool", "*")
        pattern = r.get("pattern", "")
        path = r.get("path", "")
        reason = r.get("reason", "")
        target = pattern or path or "all"
        lines.append(f"  {'🚫' if action == 'DENY' else '⚠️' if action == 'WARN' else '✅'} [{action}] {tool}: {target} — {reason}")
    return "\n".join(lines)


def _path_matches(file_path: str, pattern: str) -> bool:
    """Check if a file path matches a glob-like pattern."""
    import fnmatch
    # Normalize paths
    file_path = os.path.abspath(file_path) if file_path and not file_path.startswith("*") else file_path
    return fnmatch.fnmatch(file_path, pattern)
