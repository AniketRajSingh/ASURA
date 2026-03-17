# ============================================================
# core/rule_engine.py — Declarative Behavior Rule Engine
#
# Loads YAML rules from src/rules/ and evaluates them against
# system state. Replaces hardcoded thresholds and triggers.
# ============================================================

import os
import time
import json
import threading
from datetime import datetime
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None

from settings import settings as config
from skills.logger import log_audit, log_app

_RULES_DIR = os.path.join(config.SRC_DIR, "rules")
_rules: list[dict] = []
_cooldowns: dict[str, float] = {}  # rule_name -> last_triggered_time
_lock = threading.Lock()


def load_rules() -> list[dict]:
    """Load all YAML rule files from src/rules/."""
    global _rules

    if yaml is None:
        log_app("rule_engine: PyYAML not installed, using built-in rules")
        return []

    rules = []
    if not os.path.isdir(_RULES_DIR):
        return rules

    for fname in sorted(os.listdir(_RULES_DIR)):
        if not fname.endswith((".yaml", ".yml")):
            continue
        fpath = os.path.join(_RULES_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                file_rules = yaml.safe_load(f) or []
            if isinstance(file_rules, list):
                for rule in file_rules:
                    rule["_source"] = fname
                    rules.append(rule)
        except Exception as e:
            log_app(f"rule_engine: Error loading {fname}: {e}")

    _rules = rules
    log_audit("RULES", f"Loaded {len(_rules)} rules from {_RULES_DIR}")
    return _rules


def evaluate_metric_rules(metrics: dict) -> list[dict]:
    """
    Evaluate metric-based rules against current system metrics.

    Args:
        metrics: {"cpu_percent": 45, "memory_percent": 70, "disk_percent": 85}

    Returns:
        List of triggered rule dicts
    """
    if not _rules:
        load_rules()

    triggered = []
    now = time.time()

    for rule in _rules:
        trigger = rule.get("trigger", {})
        if "metric" not in trigger:
            continue

        metric_name = trigger["metric"]
        operator = trigger.get("operator", ">")
        threshold = trigger.get("threshold", 0)
        current_value = metrics.get(metric_name)

        if current_value is None:
            continue

        # Evaluate condition
        fired = False
        if operator == ">" and current_value > threshold:
            fired = True
        elif operator == ">=" and current_value >= threshold:
            fired = True
        elif operator == "<" and current_value < threshold:
            fired = True
        elif operator == "==" and current_value == threshold:
            fired = True

        if not fired:
            continue

        # Check cooldown
        rule_name = rule.get("name", "unnamed")
        cooldown_min = rule.get("cooldown_minutes", 0)
        with _lock:
            last_time = _cooldowns.get(rule_name, 0)
            if (now - last_time) < (cooldown_min * 60):
                continue
            _cooldowns[rule_name] = now

        triggered.append(rule)
        log_audit("RULES", f"Triggered: {rule_name} ({metric_name}={current_value} {operator} {threshold})")

    return triggered


def evaluate_event_rules(event: str) -> list[dict]:
    """
    Evaluate event-based rules (startup, idle, etc).

    Args:
        event: "startup", "idle", "schedule"

    Returns:
        List of triggered rule dicts
    """
    if not _rules:
        load_rules()

    triggered = []
    now = time.time()

    for rule in _rules:
        trigger = rule.get("trigger", {})
        if trigger.get("event") != event:
            continue

        rule_name = rule.get("name", "unnamed")
        cooldown_min = rule.get("cooldown_minutes", 0)

        with _lock:
            last_time = _cooldowns.get(rule_name, 0)
            if cooldown_min > 0 and (now - last_time) < (cooldown_min * 60):
                continue
            _cooldowns[rule_name] = now

        triggered.append(rule)
        log_audit("RULES", f"Event triggered: {rule_name} (event={event})")

    return triggered


def get_rules_summary() -> str:
    """Get a human-readable summary of loaded rules."""
    if not _rules:
        load_rules()

    if not _rules:
        return "No rules loaded."

    lines = [f"📋 Loaded rules ({len(_rules)} total):\n"]
    for rule in _rules:
        name = rule.get("name", "unnamed")
        trigger = rule.get("trigger", {})
        actions = rule.get("actions", [])
        source = rule.get("_source", "?")
        lines.append(f"  • {name} [{source}] → {', '.join(actions)}")

    return "\n".join(lines)


# Load rules on import
load_rules()
