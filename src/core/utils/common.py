# ============================================================
# core/utils/common.py — System-Wide Utility Functions
# ============================================================

import os
import re
import json
import datetime
import logging
from typing import Optional

# Import project specific modules
try:
    from settings import settings as config
except ImportError:
    config = None

try:
    from skills.logger import log_audit, log_app
except ImportError:
    def log_audit(category, message): print(f"[AUDIT][{category}] {message}")
    def log_app(message): print(f"[APP] {message}")

__all__ = [
    "get_current_timestamp",
    "format_timestamp",
    "generate_filename",
    "generate_backup_filename",
    "sanitize_filename",
    "is_safe_path",
    "find_project_root",
    "extract_json",
]


def find_project_root(start_path: str = None) -> str:
    """
    Find the project root by looking for a marker file.
    """
    # Check if settings already has it
    try:
        from settings import settings
        return settings.PROJECT_ROOT
    except (ImportError, AttributeError):
        pass

    curr = os.path.abspath(start_path or os.getcwd())
    while curr != os.path.dirname(curr):
        if any(os.path.exists(os.path.join(curr, m)) for m in [".git", "pyproject.toml", "asura.md"]):
            return curr
        curr = os.path.dirname(curr)
    return os.getcwd()


def get_current_timestamp(format_str: str | None = None) -> str:
    """Return the current datetime formatted as a string."""
    try:
        fmt = format_str or getattr(config, "TIMESTAMP_FORMAT", "%Y-%m-%d_%H-%M-%S")
        return datetime.datetime.now().strftime(fmt)
    except Exception:
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def format_timestamp(dt: datetime.datetime, format_str: str | None = None) -> str:
    """Format a given datetime object into a string."""
    try:
        fmt = format_str or getattr(config, "TIMESTAMP_FORMAT", "%Y-%m-%d_%H-%M-%S")
        return dt.strftime(fmt)
    except Exception:
        return dt.strftime("%Y-%m-%d_%H-%M-%S")


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be safe for use as a filename."""
    base = os.path.basename(name)
    sanitized = re.sub(r"[<>:\"/\\|?*\s]+", "_", base)
    return sanitized[:255]


def generate_filename(
    base_name: str,
    extension: str = "",
    suffix: str = "",
    timestamp_format: str | None = None,
) -> str:
    """Generate a consistent filename with timestamp."""
    timestamp = get_current_timestamp(timestamp_format)
    parts = [sanitize_filename(base_name)]
    if suffix:
        parts.append(sanitize_filename(suffix))
    parts.append(timestamp)

    filename = "_".join(parts)
    if extension:
        filename = f"{filename}.{extension.lstrip('.')}"
    return filename


def generate_backup_filename(file_path: str) -> str:
    """Produce a backup filename."""
    dir_name, original = os.path.split(file_path)
    name, ext = os.path.splitext(original)
    backup_name = generate_filename(name, ext.lstrip("."), suffix="backup")
    return os.path.join(dir_name, backup_name)


def is_safe_path(path: str, base_dir: str | None = None) -> bool:
    """Check if a path is safe and stays within the intended base directory."""
    try:
        # Use PROJECT_ROOT from config if available, otherwise find it
        if base_dir:
            base = os.path.abspath(base_dir)
        elif config and hasattr(config, "PROJECT_ROOT"):
            base = os.path.abspath(config.PROJECT_ROOT)
        else:
            base = os.path.abspath(find_project_root())
            
        if os.path.isabs(path):
            return os.path.abspath(path).startswith(base)
        
        resolved = os.path.abspath(os.path.join(base, path))
        return resolved.startswith(base)
    except Exception:
        return False


def extract_json(text: str) -> dict | list | None:
    """
    Robustly extract JSON object or list from LLM response text.
    Handles markdown blocks and stray text.
    """
    if not text:
        return None
    
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find JSON block (object or list)
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        raw_match = match.group()
        try:
            return json.loads(raw_match)
        except json.JSONDecodeError:
            # Try cleaning common markdown noise
            cleaned = raw_match.replace("```json", "").replace("```", "").strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
    return None
