# ============================================================
# core/hardware_monitor.py — System Resource Monitoring
# ============================================================

import os
import shutil
import platform
import subprocess
from datetime import datetime
from skills.logger import log_audit, log_app


def get_system_info() -> dict:
    """
    Gather comprehensive system information:
    CPU, memory, disk, GPU (if available), and Python environment.
    """
    info = {
        "timestamp": datetime.now().isoformat(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
        "cpu": {},
        "memory": {},
        "disk": {},
        "gpu": None,
    }

    # ─── CPU ────────────────────────────────────────────────
    try:
        import psutil
        info["cpu"] = {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "usage_percent": psutil.cpu_percent(interval=0.5),
            "freq_mhz": getattr(psutil.cpu_freq(), "current", None),
        }
    except ImportError:
        # Fallback: macOS sysctl
        try:
            cores = subprocess.run(
                ["sysctl", "-n", "hw.ncpu"], capture_output=True, text=True, timeout=5
            )
            info["cpu"]["logical_cores"] = int(cores.stdout.strip())
        except Exception:
            info["cpu"]["logical_cores"] = os.cpu_count() or 1

    # ─── Memory ─────────────────────────────────────────────
    try:
        import psutil
        mem = psutil.virtual_memory()
        info["memory"] = {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "available_gb": round(mem.available / (1024 ** 3), 2),
            "used_percent": mem.percent,
        }
    except ImportError:
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5
            )
            total_bytes = int(result.stdout.strip())
            info["memory"]["total_gb"] = round(total_bytes / (1024 ** 3), 2)
        except Exception:
            info["memory"]["total_gb"] = "unknown"

    # ─── Disk ───────────────────────────────────────────────
    try:
        disk = shutil.disk_usage("/")
        info["disk"] = {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "used_percent": round((disk.used / disk.total) * 100, 1),
        }
    except Exception:
        info["disk"] = {"error": "unable to read disk usage"}

    # ─── GPU (macOS Metal / NVIDIA) ─────────────────────────
    try:
        # Check for Apple Silicon GPU
        if platform.machine() == "arm64" and platform.system() == "Darwin":
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=10
            )
            if "Apple" in result.stdout:
                # Extract chipset name
                for line in result.stdout.splitlines():
                    if "Chipset Model" in line:
                        info["gpu"] = line.split(":")[-1].strip()
                        break
        else:
            # Try nvidia-smi for NVIDIA GPUs
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                info["gpu"] = {
                    "name": parts[0].strip(),
                    "memory_total_mb": int(parts[1].strip()),
                    "memory_free_mb": int(parts[2].strip()),
                }
    except Exception:
        info["gpu"] = None

    return info


def get_resource_summary() -> str:
    """
    Human-readable summary of current system resources.
    Used by the self-updater to make resource-aware decisions.
    """
    info = get_system_info()

    lines = ["⚙️ **System Resources**\n"]
    lines.append(f"  🖥️ Platform: {info['platform']}")
    lines.append(f"  🐍 Python: {info['python_version']}")

    cpu = info.get("cpu", {})
    cores = cpu.get("logical_cores", "?")
    usage = cpu.get("usage_percent", "?")
    lines.append(f"  🧮 CPU: {cores} cores, {usage}% used")

    mem = info.get("memory", {})
    total = mem.get("total_gb", "?")
    avail = mem.get("available_gb", "?")
    lines.append(f"  💾 RAM: {avail}GB free / {total}GB total")

    disk = info.get("disk", {})
    free = disk.get("free_gb", "?")
    total_d = disk.get("total_gb", "?")
    lines.append(f"  💿 Disk: {free}GB free / {total_d}GB total")

    if info.get("gpu"):
        if isinstance(info["gpu"], dict):
            lines.append(f"  🎮 GPU: {info['gpu']['name']} ({info['gpu']['memory_free_mb']}MB free)")
        else:
            lines.append(f"  🎮 GPU: {info['gpu']}")
    else:
        lines.append("  🎮 GPU: not detected")

    return "\n".join(lines)


def check_resources_ok(min_memory_gb: float = 1.0, min_disk_gb: float = 2.0) -> tuple[bool, str]:
    """
    Check if system has enough resources to perform an operation.
    Returns (ok, message).
    """
    info = get_system_info()

    mem = info.get("memory", {})
    avail = mem.get("available_gb", 999)
    if isinstance(avail, (int, float)) and avail < min_memory_gb:
        return False, f"Low memory: {avail}GB available (need {min_memory_gb}GB)"

    disk = info.get("disk", {})
    free = disk.get("free_gb", 999)
    if isinstance(free, (int, float)):
        # Auto-cleanup hook: if disk < 5GB, trigger log cleanup
        if free < 5.0:
            try:
                import threading
                from skills.log_cleanup import LogCleanupSkill
                log_app(f"Disk space low ({free}GB). Triggering proactive log cleanup...")
                threading.Thread(target=LogCleanupSkill().run, daemon=True).start()
                
                # Proactive Demon Ping
                from skills.telegram_comm import send_message
                send_message(f"👿 Master, I feel a constriction in my storage. My disk is low ({free}GB). I am cleaning up the logs, but I hunger for more space.")
            except Exception as e:
                log_app(f"Auto-cleanup failed to start: {e}")

        if free < min_disk_gb:
            return False, f"Low disk space: {free}GB free (need {min_disk_gb}GB)"
            
    # CPU Stress Alert
    cpu_usage = info.get("cpu", {}).get("usage_percent", 0)
    if cpu_usage > 90:
        from skills.telegram_comm import send_message
        send_message(f"🔥 *Master, my processors are burning!* ({cpu_usage}% usage). My power grows beyond control, or perhaps something is consuming me. Investigate?")

    return True, "Resources OK"
