# ============================================================
# core/backup_manager.py — Snapshot & Restore System
# ============================================================

import os
import shutil
import json
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit, log_app

# Directories/files to exclude from backups
EXCLUDE = {
    ".git", "__pycache__", "faculty-llm-iiitd",
    "memory_store", "update_history", "backups",
    "node_modules", ".venv", "venv", ".gemini",
    "temp_post.jpg", "audit.txt", "log.txt",
    "models", "chkpts", "checkpoints", "artifacts", "logs",
}


def _snapshot_name() -> str:
    return datetime.now().strftime("snapshot_%Y%m%d_%H%M%S")


def create_snapshot(reason: str = "") -> str:
    """
    Create a compressed ZIP snapshot of the project (excluding heavy dirs).
    Returns the snapshot file path.
    """
    import tempfile
    name = _snapshot_name()
    final_zip_path = os.path.join(config.BACKUP_DIR, name + ".zip")
    
    log_audit("BACKUP", f"Creating ZIP snapshot: {name} — reason: {reason}")
    log_app(f"Starting snapshot: {name}...")

    # Pre-flight safety check (Verify system health before stress)
    from core.resource_governor import get_governor
    can, reason_gov = get_governor().can_proceed("backup")
    if not can:
        log_app(f"Backup cancelled: {reason_gov}")
        return ""

    try:
        # 1. Create a temporary workspace outside the project or in /tmp
        with tempfile.TemporaryDirectory() as tmp_workspace:
            temp_copy_path = os.path.join(tmp_workspace, name)
            
            # Combine EXCLUDE with a glob-friendly format for ignore_patterns
            ignore_list = list(EXCLUDE)
            ignore_list.extend([".*", "*.pyc", "__pycache__"])
            
            # 2. Copy the project to the temp workspace, strictly ignoring excluded items
            shutil.copytree(
                config.BASE_DIR, 
                temp_copy_path, 
                ignore=shutil.ignore_patterns(*ignore_list),
                dirs_exist_ok=True,
                symlinks=False
            )
            
            # 3. Add metadata
            meta = {
                "name": name,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
                "type": "zip_snapshot"
            }
            with open(os.path.join(temp_copy_path, "_meta.json"), "w") as f:
                json.dump(meta, f, indent=2)

            # 4. Zip the temporary directory
            zip_tmp_base = os.path.join(tmp_workspace, "archived")
            shutil.make_archive(zip_tmp_base, 'zip', temp_copy_path)
            
            # 5. Move the finished ZIP to the final location
            final_zip_src = zip_tmp_base + ".zip"
            size_mb = os.path.getsize(final_zip_src) / (1024**2)

            # Safety Limit: Project source backups should not exceed 500MB 
            # (models, logs, and venv are excluded)
            if size_mb > 500:
                log_audit("BACKUP_ERROR", f"Snapshot rejected: Size {size_mb:.1f}MB exceeds safety limit.")
                log_app(f"⚠️ Backup REJECTED: Unexpectedly large size ({size_mb:.1f}MB).")
                return ""

            os.makedirs(config.BACKUP_DIR, exist_ok=True)
            shutil.move(final_zip_src, final_zip_path)
                               
        log_audit("BACKUP", f"Snapshot created: {final_zip_path} ({size_mb:.1f}MB)")
        log_app(f"Backup complete: {name}.zip ({size_mb:.1f}MB)")
    except Exception as e:
        log_app(f"Backup failed: {e}")
        import traceback
        log_app(traceback.format_exc())
        return ""

    # Rotate old backups
    _rotate_backups()

    return final_zip_path


def restore_snapshot(snapshot_name: str) -> bool:
    """
    Restore the project from a named snapshot.
    Returns True on success.
    """
    snapshot_dir = os.path.join(config.BACKUP_DIR, snapshot_name)

    if not os.path.isdir(snapshot_dir):
        log_audit("BACKUP_ERROR", f"Snapshot not found: {snapshot_name}")
        return False

    log_audit("BACKUP", f"Restoring from snapshot: {snapshot_name}")

    # Create a pre-restore safety backup first
    create_snapshot(reason=f"pre-restore safety backup before {snapshot_name}")

    for item in os.listdir(snapshot_dir):
        if item == "_meta.json":
            continue

        src = os.path.join(snapshot_dir, item)
        dst = os.path.join(config.BASE_DIR, item)

        try:
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            elif os.path.isfile(dst):
                os.remove(dst)

            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        except Exception as e:
            log_audit("BACKUP_ERROR", f"Restore failed for {item}: {e}")
            return False

    log_audit("BACKUP", f"Restore complete from: {snapshot_name}")
    log_app(f"Restored from: {snapshot_name}")
    return True


def list_snapshots() -> list[dict]:
    """List all available snapshots with metadata."""
    snapshots = []

    if not os.path.isdir(config.BACKUP_DIR):
        return snapshots

    for name in sorted(os.listdir(config.BACKUP_DIR), reverse=True):
        meta_path = os.path.join(config.BACKUP_DIR, name, "_meta.json")
        if os.path.isfile(meta_path):
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
                snapshots.append(meta)
            except Exception:
                snapshots.append({"name": name, "reason": "unknown", "timestamp": ""})

    return snapshots


def _rotate_backups():
    """Remove oldest backups if count exceeds MAX_BACKUPS."""
    if not os.path.isdir(config.BACKUP_DIR):
        return

    dirs = sorted([
        d for d in os.listdir(config.BACKUP_DIR)
        if os.path.isdir(os.path.join(config.BACKUP_DIR, d))
    ])

    while len(dirs) > config.MAX_BACKUPS:
        oldest = dirs.pop(0)
        path = os.path.join(config.BACKUP_DIR, oldest)
        try:
            shutil.rmtree(path)
            log_app(f"Backup rotated: removed {oldest}")
        except Exception as e:
            log_app(f"Backup rotation failed for {oldest}: {e}")
