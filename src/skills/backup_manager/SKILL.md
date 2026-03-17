---
name: backup_manager
description: "Provides a project snapshot and restore system with automatic rotation and safety checks."
entry_point: manager.py
---

# Backup Manager

A core safety skill that handles project-wide snapshots and restoration. It ensures system state can be recovered by creating timestamped backups, enforcing size limits, and automatically rotating old snapshots to save space.

### 🔧 Tools / Functions
- `create_snapshot(reason="")`: Generates a compressed ZIP archive of the project source, excluding heavy directories like `.git`, `node_modules`, and `.venv`.
- `restore_snapshot(snapshot_name)`: Replaces current project files with those from a named snapshot. Always creates a pre-restore safety backup.
- `list_snapshots()`: Returns a metadata list of all available snapshots currently stored in the backup directory.

### 📝 Examples
- "Create a backup before I change the core" -> `create_snapshot("Manual backup before core change")`
- "Show me my backups" -> `list_snapshots()`

### 🛠️ Requirements
- `shutil`, `zipfile`, `tempfile` (standard library)
- `BACKUP_DIR` and `MAX_BACKUPS` configured in `config.py`
