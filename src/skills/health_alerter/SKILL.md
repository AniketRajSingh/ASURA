---
name: health_alerter
description: "Proactive system health monitoring that alerts and triggers auto-remediation when resource thresholds are exceeded."
entry_point: alerter.py
---

# Health Alerter

Background monitor that keeps an eye on CPU, Memory, and Disk usage. It proactively notifies the user and can trigger the Resource Governor for auto-remediation.

### 🔧 Tools / Functions
- `HealthAlerter().start()`: Launch the monitoring thread.
- `HealthAlerter().stop()`: Gracefully shut down the monitor.

### 📝 Examples
- "Start system health monitoring" -> Begins background checks every 2 minutes.

### 🛠️ Requirements
- `psutil` library.
- `ResourceGovernor` for active remediation support.
