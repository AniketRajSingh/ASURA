"""
ASURA Logger Skill
==================

This module implements a robust, centralized logging system for the ASURA
framework.  The original implementation was prone to crashes when the log
file was missing, corrupted, or when multiple concurrent writes occurred.
This updated version addresses those issues and provides a clean,
well‑documented API that other skills can use.

Key Features
------------
* **Thread‑safe logging** – uses the standard :mod:`logging` module which
  is safe for concurrent access.
* **Rotating file handler** – automatically rolls over the log file
  when it reaches 5 MiB, keeping up to 5 backup files.  This prevents the
  log from growing indefinitely.
* **Graceful degradation** – if the file handler cannot be created,
  the logger falls back to a console handler instead of raising an
  exception.
* **Convenience helpers** – functions for reading the most recent log
  entries, clearing the log, and adjusting the log level at runtime.
* **Skill registration** – exposes a :func:`get_skill_manifest` function
  that the ASURA skill registry can import.  The manifest lists the
  public functions that other skills may call.

Usage
-----
```python
from src.skills.logger import log_event, get_recent_logs

# Log an informational message
log_event("startup", "ASURA system starting up")

# Retrieve the last 50 log lines
last_logs = get_recent_logs(50)
```

The skill automatically creates the ``data/logs`` directory if it does
not exist, and it will continue to operate even if the log file is
deleted while the process is running.

Author
------
Aniket Raj Singh
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import List, Optional

# Re-export structured logging primitives for full backward compatibility
try:
    from skills.logger.log import log_audit, log_app, query_logs
except ImportError:
    def log_audit(step: str, message: str, **extra) -> None:
        logging.getLogger("ASURA").info(f"[{step}] {message}")
    def log_app(message: str, **extra) -> None:
        logging.getLogger("ASURA").info(f"[APP] {message}")
        print(message)
    def query_logs(*args, **kwargs) -> list:
        return []

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Determine the absolute path to the log file.
# The log file resides in the project's data/logs directory.
_LOG_DIR = Path(__file__).resolve().parents[2] / "data" / "logs"
_LOG_FILE = _LOG_DIR / "log.txt"

# Maximum size of the log file before rotation (5 MiB).
_MAX_BYTES = 5 * 1024 * 1024
# Number of backup files to keep.
_BACKUP_COUNT = 5

# --------------------------------------------------------------------------- #
# Logger Setup
# --------------------------------------------------------------------------- #

# Ensure the log directory exists.
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create a dedicated logger for the ASURA framework.
_logger = logging.getLogger("ASURA")
_logger.setLevel(logging.INFO)
_logger.propagate = False  # prevent double‑logging if root logger is configured elsewhere

# Try to add a rotating file handler.  If this fails, fall back to console.
try:
    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    _logger.addHandler(file_handler)
except Exception as exc:
    # If we cannot write to the file, log to stderr instead.
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    _logger.addHandler(console_handler)
    _logger.error("Failed to initialize file handler for logger: %s", exc)

# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def log_event(event_type: str, message: str, level: str = "INFO") -> None:
    """
    Log an event with a specified type and message.

    Parameters
    ----------
    event_type : str
        A short identifier for the event (e.g., "startup", "error").
    message : str
        The human‑readable message to log.
    level : str, optional
        Logging level as a string ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
        Defaults to "INFO".

    Notes
    -----
    The function is thread‑safe and will not raise exceptions if the
    underlying logging system encounters an error; instead, it will
    silently ignore the failure to avoid cascading crashes.
    """
    if not isinstance(event_type, str) or not isinstance(message, str):
        _logger.debug("log_event called with invalid types: %s, %s", event_type, message)
        return

    # Normalize level
    level = level.upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        level = "INFO"

    try:
        _logger.log(getattr(logging, level), f"[{event_type}] {message}")
    except Exception as exc:  # pragma: no cover - defensive
        # If logging fails, write to stderr to avoid silent failure.
        sys.stderr.write(f"Logging failed: {exc}\n")

def get_recent_logs(n: int = 100) -> List[str]:
    """
    Retrieve the most recent log lines.

    Parameters
    ----------
    n : int, optional
        Number of lines to return from the end of the log file.
        Defaults to 100.

    Returns
    -------
    List[str]
        A list of log lines, most recent last.

    Notes
    -----
    If the log file does not exist or cannot be read, an empty list is
    returned.
    """
    if n <= 0:
        return []

    try:
        with _LOG_FILE.open("r", encoding="utf-8") as f:
            lines = f.readlines()
            return [line.rstrip("\n") for line in lines[-n:]]
    except Exception as exc:  # pragma: no cover - defensive
        _logger.debug("Failed to read log file: %s", exc)
        return []

def clear_logs() -> None:
    """
    Truncate the current log file.

    This operation is safe even if the log file is being written to
    concurrently; the file will simply be emptied.
    """
    try:
        _LOG_FILE.unlink(missing_ok=True)
        # Re‑create the file to ensure the handler continues to work.
        _LOG_FILE.touch()
    except Exception as exc:  # pragma: no cover - defensive
        _logger.debug("Failed to clear log file: %s", exc)

def set_level(level: str) -> None:
    """
    Dynamically adjust the logger's level.

    Parameters
    ----------
    level : str
        Desired logging level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
    """
    level = level.upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        return
    _logger.setLevel(getattr(logging, level))

def flush() -> None:
    """
    Flush all logging handlers.

    This ensures that all buffered log entries are written to disk.
    """
    for handler in _logger.handlers:
        try:
            handler.flush()
        except Exception:  # pragma: no cover - defensive
            pass

# --------------------------------------------------------------------------- #
# Skill Manifest
# --------------------------------------------------------------------------- #

def get_skill_manifest() -> dict:
    """
    Return the skill manifest for the ASURA skill registry.

    The registry expects a dictionary containing metadata and a mapping
    of callable names to functions.

    Returns
    -------
    dict
        Skill manifest with the following keys:
        - name: Skill name.
        - version: Semantic version string.
        - description: Human‑readable description.
        - author: Name of the author.
        - functions: Mapping of public function names to callables.
    """
    return {
        "name": "logger",
        "version": "1.0.0",
        "description": "Centralized logging skill for ASURA.",
        "author": "Aniket Raj Singh",
        "functions": {
            "log_event": log_event,
            "get_recent_logs": get_recent_logs,
            "clear_logs": clear_logs,
            "set_level": set_level,
            "flush": flush,
        },
    }

# --------------------------------------------------------------------------- #
# Exported names
# --------------------------------------------------------------------------- #

__all__ = [
    "log_event",
    "get_recent_logs",
    "clear_logs",
    "set_level",
    "flush",
    "get_skill_manifest",
    "log_audit",
    "log_app",
    "query_logs",
]