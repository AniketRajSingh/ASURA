---
name: logger
description: "Core thread-safe logging system for audit trails and application lifecycle events."
entry_point: log.py
---

# Logger Skill

Provides a dual logging system that maintains both human-readable text logs and structured JSONL files. It supports thread-safe concurrent writes to ensure data integrity during parallel operations and allows for programmatic querying of system events.

### 🔧 Tools / Functions
- `log_audit(step, message, **extra)`: Logs security-sensitive events to `audit.txt` and `audit.jsonl` without console output.
- `log_app(message, **extra)`: Logs general application events to `log.txt`, `audit.jsonl`, and prints them to the console.
- `query_logs(step=None, since=None, limit=50)`: Retrieves a list of structured log entries filtered by step, timestamp, or limit.

### 📝 Examples
- "Log a successful login event" -> Records the event in the audit logs.
- "Show me the last 10 application logs" -> Queries the log files and returns the recent entries.

### 🛠️ Requirements
- `structlog` library
- Write permissions for log paths defined in `config`
