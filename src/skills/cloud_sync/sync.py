# ============================================================
# skills/cloud_sync/sync.py — Cloud Sync (S3/GDrive backup)
# ============================================================
import os, subprocess, shutil
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit

def sync_to_local_backup(dest: str = None) -> str:
    dest = dest or os.path.join(config.BACKUP_DIR, f"cloud_sync_{datetime.now().strftime('%Y%m%d_%H%M')}")
    src = config.BASE_DIR
    try:
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "*.pyc", "memory_store", "backups", "venv"))
        log_audit("SYNC", f"Synced to: {dest}")
        return f"✅ Synced to {dest}"
    except Exception as e:
        return f"❌ Sync failed: {e}"

def sync_rclone(remote: str = "gdrive:TF_backup") -> str:
    """Sync to cloud using rclone (if installed)."""
    try:
        result = subprocess.run(
            ["rclone", "sync", config.BASE_DIR, remote,
             "--exclude", ".git/**", "--exclude", "__pycache__/**", "--exclude", "venv/**"],
            capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            log_audit("SYNC", f"Cloud synced to {remote}")
            return f"☁️ Synced to {remote}"
        return f"Sync error: {result.stderr[:200]}"
    except FileNotFoundError:
        return "rclone not installed. Install: `brew install rclone`"

def get_sync_status() -> str:
    backups = os.listdir(config.BACKUP_DIR) if os.path.isdir(config.BACKUP_DIR) else []
    return f"☁️ *Cloud Sync*\nLocal backups: {len(backups)}"
