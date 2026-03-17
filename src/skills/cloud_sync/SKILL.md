---
name: cloud_sync
description: "Cloud synchronization and backup skill. Supports local backups and rclone-based sync to Google Drive, S3, and other remotes."
entry_point: sync.py
---

# Cloud Sync

Provides automated backup and synchronization services for the ASURA project. It supports creating timestamped local backups and utilizes `rclone` for secure synchronization to various cloud storage providers like Google Drive and AWS S3.

### 🔧 Tools / Functions
- `sync_to_local_backup(dest)`: Create a local timestamped backup of the project directory, excluding environment and cache files.
- `sync_rclone(remote)`: Synchronize the project directory to a configured cloud remote using `rclone`.
- `get_sync_status()`: Retrieve a summary of existing local backups.

### 📝 Examples
- "Backup my project to the cloud" -> Executes `rclone sync` to the default remote.
- "Create a local backup" -> Creates a new timestamped folder in the `backups/` directory.

### 🛠️ Requirements
- `rclone` (optional, required for cloud synchronization)
