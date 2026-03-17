---
name: log_cleanup
description: "Automatically rotate and prune old log entries to prevent storage bloat and maintain system performance."
entry_point: __init__.py
---

# Log Cleanup

Keep the system's audit trail and application logs healthy by pruning old entries and preventing massive file growth.

### 🔧 Tools / Functions
- `LogCleanupSkill().run()`: Prunes `audit.txt`, `log.txt`, and `audit.jsonl` based on retention settings.

### 📝 Examples
- "Clean up my logs" -> Removes log entries older than the configured retention period (default 7 days).

### 🛠️ Requirements
- `LOG_RETENTION_DAYS` in `config.py`.
- `psutil` for emergency truncation of large log files.
