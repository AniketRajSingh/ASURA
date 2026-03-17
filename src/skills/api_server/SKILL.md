---
name: api_server
description: "FastAPI REST server that exposes ASURA's skills, chat, and management features as secure API endpoints."
entry_point: server.py
---

# API Server

Exposes the AI's capabilities through a robust REST API with SSE streaming support. Enables integration with web frontends, mobile apps, and external services.

### 🔧 Tools / Functions
- `start_api_server()`: Start the FastAPI/Uvicorn server in a background thread.

### 📝 Examples
- "Launch the API" -> Starts the server on the configured host and port (default 8000).

### 🛠️ Requirements
- `fastapi`, `uvicorn`, `httpx`.
- `X-ASURA-Key` for authenticated requests.
