# ============================================================
# core/observability.py — Tool Execution Observability
#
# Tracks timing, token estimates, and execution metrics for
# every tool call. Provides dashboard data and debugging info.
# ============================================================

import time
import threading
from datetime import datetime, timezone
from typing import Optional, Any
from skills.logger import log_audit

# Thread-safe metrics store
_lock = threading.Lock()
_metrics: list[dict] = []
_session_start = time.time()

# Max metrics to keep in memory
MAX_METRICS = 500


class ToolTrace:
    """Context manager for tracing tool execution."""

    def __init__(self, tool_name: str, input_str: str):
        self.tool_name = tool_name
        self.input_str = input_str
        self.start_time = None
        self.end_time = None
        self.duration_ms = 0
        self.success = False
        self.result_size = 0
        self.error = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000)
        self.success = exc_type is None

        if exc_val:
            self.error = str(exc_val)

        # Store metric
        record_metric(
            tool_name=self.tool_name,
            duration_ms=self.duration_ms,
            success=self.success,
            input_size=len(self.input_str),
            output_size=self.result_size,
            error=self.error,
        )

        return False  # Don't suppress exceptions


def record_metric(
    tool_name: str,
    duration_ms: int,
    success: bool,
    input_size: int = 0,
    output_size: int = 0,
    error: Optional[str] = None,
) -> None:
    """Record a tool execution metric."""
    metric = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "duration_ms": duration_ms,
        "success": success,
        "input_size": input_size,
        "output_size": output_size,
        "input_tokens_est": input_size // 4,
        "output_tokens_est": output_size // 4,
        "error": error,
    }

    with _lock:
        _metrics.append(metric)
        if len(_metrics) > MAX_METRICS:
            _metrics.pop(0)


def get_session_stats() -> dict:
    """Get aggregate stats for the current session."""
    with _lock:
        if not _metrics:
            return {"total_calls": 0, "uptime_s": round(time.time() - _session_start)}

        total = len(_metrics)
        successes = sum(1 for m in _metrics if m["success"])
        total_duration = sum(m["duration_ms"] for m in _metrics)
        total_tokens = sum(m["input_tokens_est"] + m["output_tokens_est"] for m in _metrics)

        # Per-tool breakdown
        tools = {}
        for m in _metrics:
            t = m["tool"]
            if t not in tools:
                tools[t] = {"calls": 0, "total_ms": 0, "errors": 0}
            tools[t]["calls"] += 1
            tools[t]["total_ms"] += m["duration_ms"]
            if not m["success"]:
                tools[t]["errors"] += 1

        return {
            "total_calls": total,
            "success_rate": round(successes / total * 100, 1) if total else 0,
            "total_duration_ms": total_duration,
            "avg_duration_ms": round(total_duration / total) if total else 0,
            "total_tokens_est": total_tokens,
            "uptime_s": round(time.time() - _session_start),
            "tools": tools,
        }


def get_recent_traces(n: int = 10) -> list[dict]:
    """Get the N most recent tool traces."""
    with _lock:
        return list(reversed(_metrics[-n:]))


def format_stats() -> str:
    """Format session stats as a readable string."""
    stats = get_session_stats()
    if stats["total_calls"] == 0:
        return "No tool calls recorded yet."

    lines = [
        "📊 Session Observability:",
        f"  Uptime: {stats['uptime_s']}s",
        f"  Tool calls: {stats['total_calls']} ({stats['success_rate']}% success)",
        f"  Avg latency: {stats['avg_duration_ms']}ms",
        f"  Est. tokens: {stats['total_tokens_est']}",
        "",
        "  Per-tool breakdown:",
    ]

    for tool, data in sorted(stats.get("tools", {}).items(), key=lambda x: -x[1]["calls"]):
        avg = round(data["total_ms"] / data["calls"]) if data["calls"] else 0
        err = f" ({data['errors']} errors)" if data["errors"] else ""
        lines.append(f"    • {tool}: {data['calls']}x, avg {avg}ms{err}")

    return "\n".join(lines)
