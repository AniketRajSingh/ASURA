---
name: disk_usage
description: "Monitors disk space utilization and provides detailed statistics for specified paths."
entry_point: skill.py
---

# Disk Usage

Specialized skill for monitoring disk space consumption. It provides detailed statistics including total, used, and free space in gigabytes, as well as the usage percentage for any given filesystem path.

### 🔧 Tools / Functions
- `get_usage(path)`: Retrieve detailed disk usage statistics (total_gb, used_gb, free_gb, percent) for a specific path.

### 📝 Examples
- "Check disk space on /" -> "Disk usage for '/': {'total_gb': 494.38, 'used_gb': 320.1, ...}"

### 🛠️ Requirements
- `psutil` (recommended; falls back to `os.statvfs` on Unix systems)
