---
name: hardware_monitor
description: "System resource monitoring. Tracks CPU, RAM, disk, and GPU (Apple Silicon + NVIDIA) for resource-aware operations."
entry_point: monitor.py
---

# Hardware Monitor

Monitors system health and resource utilization. It provides real-time data on CPU usage, memory availability, disk space, and GPU performance, enabling ASURA to make resource-aware decisions and trigger proactive maintenance.

### 🔧 Tools / Functions
- `get_system_info()`: Gather comprehensive system information (CPU cores/usage, RAM, disk, GPU details).
- `get_resource_summary()`: Generate a human-readable Markdown summary of current system resources.
- `check_resources_ok(min_memory_gb, min_disk_gb)`: Verify if the system meets the minimum resource requirements for an operation.

### 📝 Examples
- "Check system health" -> Returns a summary of CPU, RAM, and Disk usage.
- "Is there enough space for an update?" -> Returns True/False based on disk availability.

### 🛠️ Requirements
- `psutil` (recommended for accurate resource tracking)
- `nvidia-smi` (optional, for NVIDIA GPU monitoring)
- `system_profiler` (on macOS for Apple Silicon GPU details)
