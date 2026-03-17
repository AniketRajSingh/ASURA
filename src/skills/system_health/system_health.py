# src/skills/system_health/system_health.py

"""
system_health
==============

This lightweight skill provides a concise, human‑readable report of the
system’s health metrics.  It reports CPU usage, memory usage, disk usage,
and uptime.  The information is gathered via :mod:`psutil` and returned as
a formatted string.

The module exposes a single :func:`run` function which can be invoked by
the skill registry.  All operations are wrapped in robust error handling
and are logged with :func:`core.logger.log_app` for normal operation and
:func:`core.logger.log_audit` for error conditions.

The module imports :mod:`config` and :mod:`core.logger` to conform to the
project’s import conventions and to allow future extensions that may
utilise configuration values.

"""

import time
import platform
import psutil

# Project imports
from settings import settings as config
from skills.logger import log_audit, log_app


__all__ = ["run"]


def _bytes_to_gb(byte_count: int) -> float:
    """
    Convert a byte count to gigabytes.

    Parameters
    ----------
    byte_count : int
        Size in bytes.

    Returns
    -------
    float
        Size in gigabytes, rounded to one decimal place.
    """
    return round(byte_count / (1024 ** 3), 1)


def _format_uptime(seconds: float) -> str:
    """
    Format uptime from seconds to a human‑readable string.

    Parameters
    ----------
    seconds : float
        Uptime in seconds.

    Returns
    -------
    str
        Uptime formatted as ``Xd Xh Xm Xs``.
    """
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def run() -> str:
    """
    Generate a system health report.

    The report includes:
    * CPU usage percentage
    * Memory usage percentage and total/used GB
    * Disk usage percentage and total/used GB
    * System uptime

    Returns
    -------
    str
        Human‑readable system health summary.
    """
    try:
        log_app("Collecting system health metrics")

        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory
        mem = psutil.virtual_memory()
        mem_used_gb = _bytes_to_gb(mem.used)
        mem_total_gb = _bytes_to_gb(mem.total)
        mem_percent = mem.percent

        # Disk (root partition)
        disk = psutil.disk_usage("/")
        disk_used_gb = _bytes_to_gb(disk.used)
        disk_total_gb = _bytes_to_gb(disk.total)
        disk_percent = disk.percent

        # Uptime
        uptime_seconds = time.time() - psutil.boot_time()
        uptime_str = _format_uptime(uptime_seconds)

        # Build report
        report = (
            f"CPU Usage: {cpu_percent:.1f}%\n"
            f"Memory: {mem_percent:.1f}% used "
            f"({mem_used_gb:.1f} GB / {mem_total_gb:.1f} GB)\n"
            f"Disk: {disk_percent:.1f}% used "
            f"({disk_used_gb:.1f} GB / {disk_total_gb:.1f} GB)\n"
            f"Uptime: {uptime_str}"
        )

        log_app("System health report generated")
        return report

    except Exception as exc:  # pragma: no cover
        log_audit(f"Error generating system health report: {exc}")
        return "Error: Unable to retrieve system health metrics."


if __name__ == "__main__":  # pragma: no cover
    print(run())