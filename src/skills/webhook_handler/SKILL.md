---
name: webhook_handler
description: "Incoming webhook handler. Accepts GitHub or generic webhooks, verifies signatures, and triggers appropriate system actions."
entry_point: handler.py
---

# Webhook Handler

Allows ASURA to receive and respond to external events via HTTP webhooks. It supports GitHub-style HMAC-SHA256 signature verification, processes incoming event payloads (like push, issues, or PRs), and notifies the master of relevant activity.

### 🔧 Tools / Functions
- `verify_signature(payload, signature, secret)`: Verify the authenticity of an incoming webhook using HMAC-SHA256.
- `process_webhook(event_type, payload)`: Parse incoming event data and trigger internal notifications or actions.
- `get_webhook_log(limit)`: Retrieve a history of recently received webhook events.
- `start_webhook_server()`: Initialize and start a background HTTP server to listen for incoming webhooks on the configured port.

### 📝 Examples
- "Listen for GitHub pushes" -> Starts the server and begins logging repository activity.
- "Show me recent webhooks" -> Displays a list of the last 10 received events.

### 🛠️ Requirements
- None (Uses standard `http.server` and `hmac` libraries)
- Configured `WEBHOOK_PORT` and `WEBHOOK_SECRET` in `config.py`
