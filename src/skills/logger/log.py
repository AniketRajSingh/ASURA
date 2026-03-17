"""
Structured Logging Skill.

This module provides high-performance, semi-structured logging for the ASURA system.
It maintain both human-readable text logs (audit.txt, log.txt) and JSONL files for 
programmatic querying (audit.jsonl).

Main Functions:
- log_audit: Secure, background logging for sensitive events.
- log_app: User-visible lifecycle logging with console output.
- query_logs: Retrieve and filter structured logs.
"""

import os
import json
import threading
from datetime import datetime, timezone
import structlog

from settings import settings as config

_lock = threading.Lock()

# ─── Configure structlog ──────────────────────────────────
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

_jsonl_path = os.path.join(
    os.path.dirname(config.AUDIT_LOG_PATH), "audit.jsonl"
)


def _write(filepath: str, entry: str) -> None:
    """Thread-safe append to a log file."""
    with _lock:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)


def _write_jsonl(event: dict) -> None:
    """Thread-safe append to the structured JSONL log."""
    line = json.dumps(event, ensure_ascii=False, default=str) + "\n"
    with _lock:
        with open(_jsonl_path, "a", encoding="utf-8") as f:
            f.write(line)


def log_audit(step: str, message: str, **extra) -> None:
    """
    Append to audit.txt + audit.jsonl — for security-relevant events.
    Does NOT print to console (background noise).

    Extra keyword arguments are added as structured fields.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Legacy text format
    entry = f"[{ts}] [{step}] {message}\n"
    _write(config.AUDIT_LOG_PATH, entry)

    # Structured JSON
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": "info",
        "step": step,
        "msg": message,
        **extra,
    }
    _write_jsonl(event)


def log_app(message: str, **extra) -> None:
    """
    Append to log.txt AND print to console.
    For user-visible lifecycle events.

    Extra keyword arguments are added as structured fields.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Legacy text format
    entry = f"[{ts}] {message}\n"
    _write(config.APP_LOG_PATH, entry)

    # Structured JSON
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": "info",
        "step": "APP",
        "msg": message,
        **extra,
    }
    _write_jsonl(event)

    # Console output (human-readable)
    print(message)


def query_logs(step: str = None, since: str = None, limit: int = 50) -> list[dict]:
    """
    Query structured logs from audit.jsonl.

    Args:
        step: Filter by step (e.g., "SELF_UPDATE", "COMMAND")
        since: ISO timestamp — only return events after this time
        limit: Max events to return (newest first)

    Returns:
        List of event dicts, newest first
    """
    if not os.path.isfile(_jsonl_path):
        return []

    events = []
    with open(_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if step and event.get("step") != step:
                continue
            if since and event.get("ts", "") < since:
                continue
            events.append(event)

    # Return newest first, limited
    return events[-limit:][::-1]
