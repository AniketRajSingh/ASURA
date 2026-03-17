---
name: system_health
description: "Generates a concise, human-readable report of system health metrics including CPU, memory, disk, and uptime."
entry_point: system_health.py
---

# System Health

Provides a high-level overview of the system's vital signs, including CPU load, memory utilization, disk space, and system uptime.

### 🔧 Tools / Functions
- `run() -> str`: Generates and returns a formatted system health report.

### 📝 Examples
- "How is the system doing?" -> "CPU Usage: 15.4% | Memory: 45.2% used (7.2 GB / 16.0 GB) | Disk: 60.1% used | Uptime: 2d 5h"

### 🛠️ Requirements
- `psutil` library.
