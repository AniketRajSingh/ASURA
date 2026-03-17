---
name: dashboard
description: "Observability web dashboard. Shows system status, skills, TODOs, hardware metrics, and audit log."
entry_point: app.py
---

# Dashboard

The Sovereign Command Center for ASURA. It provides a real-time web interface to monitor system health, manage active skills, track ongoing tasks, and review audit logs. It includes a built-in JWT-based authentication layer and a robust template rendering engine.

### 🔧 Tools / Functions
- `start_dashboard()`: Initialize and start the multi-threaded HTTP dashboard server on the configured port.
- `render_template(template_name, context)`: Render HTML templates with support for recursive includes and context variable substitution.
- `_build_html()`: Internal helper to gather system state and render the main dashboard view.

### 📝 Examples
- "Open the dashboard" -> System starts the server on `http://localhost:DASHBOARD_PORT`.
- "Check system metrics via web" -> User can view CPU, RAM, and Disk usage in the browser.

### 🛠️ Requirements
- `http.server`, `http.cookies`
- `jwt` (configured in `core.auth` for secure access)
- `templates/` and `static/` directories must be present within the skill folder.
