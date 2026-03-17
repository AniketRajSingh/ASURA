from settings import settings as config
from skills.logger import log_app, log_audit
import os

# Try importing psutil for disk usage; fall back to os.statvfs if unavailable
try:
    import psutil  # type: ignore
    _USE_PSUTIL = True
except ImportError:
    _USE_PSUTIL = False
    log_audit("psutil module not available; disk usage will use os.statvfs fallback")

class DiskUsageSkill:
    """
    DiskUsageSkill provides disk usage statistics for a specified path.
    """

    name: str = "disk_usage"
    description: str = "Reports disk usage statistics for a given path or root directory."

    def __init__(self) -> None:
        """
        Initialize the DiskUsageSkill.
        """
        log_app(f"Initializing {self.name} skill")

    def get_usage(self, path: str = "/") -> dict | None:
        """
        Retrieve disk usage information for the given path.
        """
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Path '{path}' does not exist")

            if _USE_PSUTIL:
                usage = psutil.disk_usage(path)
                total_gb = usage.total / (1024 ** 3)
                used_gb = usage.used / (1024 ** 3)
                free_gb = usage.free / (1024 ** 3)
                percent = usage.percent
            else:
                stat = os.statvfs(path)
                block_size = stat.f_frsize or stat.f_bsize
                total = stat.f_blocks * block_size
                free = stat.f_bfree * block_size
                used = total - free
                percent = (used / total) * 100 if total else 0.0
                total_gb = total / (1024 ** 3)
                used_gb = used / (1024 ** 3)
                free_gb = free / (1024 ** 3)

            result = {
                "path": path,
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "percent": round(percent, 2),
            }

            log_app(f"Disk usage for '{path}': {result}")
            return result

        except Exception as exc:
            log_audit(f"Error retrieving disk usage for '{path}': {exc}")
            return None


# Instantiate the skill at import time
_disk_usage_skill_instance = DiskUsageSkill()
__all__ = ["DiskUsageSkill", "_disk_usage_skill_instance"]
