# ASURA Usage & Interface Guide

ASURA provides multiple secure entry points for interaction, all governed by the Sovereign Auth Layer.

---

## 1. Unified CLI Tool (`asura`)

ASURA features a powerful, Claude Code-inspired command-line interface. The tool automatically manages its environment and provides three primary modes of operation.

### Execution Modes

| Flag | Mode | Purpose |
|:---|:---|:---|
| `-c "[task]"` | **Standalone** | Execute a single task and exit immediately. |
| `-i` | **Interactive** | Start a full REPL session with history and agent selection. |
| `-p "[task]"` | **Planning** | Generate recommendations and a step-by-step plan without executing. |
| `--agent [name]` | **Agent Force** | Manually specify a specialist agent for the current task. |
| `--web` | **Web Launch** | Launch the Sovereign Dashboard in your browser. |

### Interactive REPL Commands
While in the interactive mode (`asura -i`), use the following slash-commands:

- `/agents` — List active specialist agents and their models.
- `/select <agent>` — Switch to a specific persona (e.g., `bug_hunter`).
- `/model <name>` — Explicitly switch the active LLM for the session.
- `/skills` — Display all 50+ available functional capabilities.
- `/tools` — List the raw MCP tool registry with technical signatures.
- `/stats` — View real-time observability and execution metrics.
- `/diff` — Show Git differences for pending local changes.
- `/history` — View the current conversation thread.
- `/compress` — Manually trigger context compaction.
- `/exit` — Securely terminate the session.

---

## 2. Telegram Integration

ASURA's Telegram Bot provides a mobile-optimized experience using the `asura-telegram` specialist agent.

### Core Commands
- `/think <query>` — Trigger deep, multi-step reasoning using the Heavy model.
- `/run <cmd>` — Execute shell commands (Safe commands execute; Unsafe require approval).
- `/evolve` — Manually trigger a system self-update cycle.
- `/audit` — Perform a code quality and system health check.
- `/remind <fact>` — Lock a high-priority fact into the Sovereign Vault.
- `/system` — Real-time telemetry and resource usage summary.
- `/backup` — Full project snapshot management.

### Mobile Optimization
- **Concise Responses**: Automatic message splitting and punchy formatting.
- **Media Support**: Directly analyze photos (UI Debugging) and Voice Notes.

---

## 3. Sovereign Dashboard (Web)

Navigate to `http://127.0.0.1:8082` to access the high-fidelity Command Center.

- **PTY Multitasking**: Watch background tasks execute in real-time via streaming PTY terminals.
- **STT/TTS Voice**: Hands-free interaction via the integrated voice pipeline.
- **Knowledge Graph**: Interactive 3D visualization of ASURA's architecture. Toggle between "Files", "Skills", and "Agents" views to see real-time health nodes.

---

## 4. REST API Access

For programmatic control, ASURA exposes a FastAPI server. All requests must include the `X-ASURA-Key` header.

### Endpoints
- `POST /chat` — Send a message to the Sovereign Gateway.
- `GET /skills` — Retrieve the full capability registry.
- `GET /health` — Fetch detailed Resource Governor telemetry.
- `POST /execute` — Trigger specific MCP tools via JSON payload.

---
*Last Updated: 2026-03-15 (Phase S - Unified Interface Edition)*
