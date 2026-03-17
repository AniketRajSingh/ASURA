import os
import re
import datetime
import json
from pathlib import Path
from typing import List

from settings import settings as config
from skills.logger import log_audit, log_app


# Regular expression to match common timestamp formats at the beginning of a line
TIMESTAMP_REGEX = re.compile(
    r"""^
    (?P<timestamp>
        \d{4}-\d{2}-\d{2}          # YYYY-MM-DD
        (?:[ T]
            \d{2}:\d{2}:\d{2}      # HH:MM:SS
            (?:\.\d+)?            # optional fractional seconds
        )?
    )
    """,
    re.VERBOSE,
)


def _parse_timestamp(line: str) -> datetime.datetime | None:
    """Extract a datetime object from the beginning of a log line."""
    match = TIMESTAMP_REGEX.match(line)
    if not match:
        return None
    ts_str = match.group("timestamp")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def _clean_text_file(file_path: Path, cutoff: datetime.datetime) -> int:
    """Prune old entries from a text log file."""
    if not file_path.exists():
        return 0

    # Max size check: if > 100MB, force truncate to last 10k lines regardless of date
    if file_path.stat().st_size > 100 * 1024 * 1024:
        log_audit("CLEANUP", f"File {file_path.name} is too large (>100MB). Force truncating.")
        with file_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        kept = lines[-10000:]
        with file_path.open("w", encoding="utf-8") as f:
            f.writelines(kept)
        return len(lines) - len(kept)

    try:
        with file_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as exc:
        log_app(f"Error reading {file_path}: {exc}")
        return 0

    kept_lines: List[str] = []
    removed = 0

    for line in lines:
        ts = _parse_timestamp(line)
        if ts and ts < cutoff:
            removed += 1
            continue
        kept_lines.append(line)

    with file_path.open("w", encoding="utf-8") as f:
        f.writelines(kept_lines)
    
    return removed


def _clean_jsonl_file(file_path: Path, cutoff: datetime.datetime) -> int:
    """Prune old entries from a JSONL log file."""
    if not file_path.exists():
        return 0

    if file_path.stat().st_size > 100 * 1024 * 1024:
        # Emergency truncation
        with file_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        kept = lines[-5000:] # JSON lines are heavier
        with file_path.open("w", encoding="utf-8") as f:
            f.writelines(kept)
        return len(lines) - len(kept)

    removed = 0
    kept_lines = []
    
    try:
        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line)
                    ts_str = event.get("ts", "")
                    # structlog typical format: 2024-03-02T12:34:56.789Z
                    ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    if ts < cutoff:
                        removed += 1
                        continue
                except (ValueError, json.JSONDecodeError):
                    pass
                kept_lines.append(line)
    except Exception as e:
        log_app(f"Error cleaning JSONL {file_path}: {e}")
        return 0

    with file_path.open("w", encoding="utf-8") as f:
        f.writelines(kept_lines)
    
    return removed


class LogCleanupSkill:
    """Prunes old log entries to prevent storage bloat."""

    def __init__(self, days: int | None = None):
        self.retention_days = days or getattr(config, "LOG_RETENTION_DAYS", 7)

    def run(self) -> None:
        """Prune logs based on retention settings."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=self.retention_days)
        logs_dir = Path(config.DATA_DIR) / "logs"
        if not logs_dir.exists():
            return

        # Text logs
        for fname in ["audit.txt", "log.txt"]:
            count = _clean_text_file(logs_dir / fname, cutoff)
            if count > 0:
                log_audit("CLEANUP", f"Removed {count} rows from {fname}")

        # JSONL logs
        for fname in ["audit.jsonl"]:
            count = _clean_jsonl_file(logs_dir / fname, cutoff)
            if count > 0:
                log_audit("CLEANUP", f"Removed {count} rows from {fname}")


if __name__ == "__main__":
    LogCleanupSkill().run()