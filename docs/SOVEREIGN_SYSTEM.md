# ASURA: Sovereign Autonomous Intelligence — System Master Authority

**ASURA (Autonomous Self-Updating Reasoning Agent)** is a recursive AI ecosystem built for high-fidelity engineering and local OS sovereignty.

---

## 🏗️ 1. Technical Architecture

ASURA is designed as a **Multi-Layered Sovereign Engine** that separates high-level reasoning from low-level system execution.

### The Reasoning Loop (ASURA-Zero)
Implemented in `src/core/reasoning.py`, the loop follows a **Think -> Plan -> Act -> Observe -> Reflect** cycle.
*   **Dual-Tier Intelligence**: Intent recognition is handled by a fast 0.8B model, while complex engineering is executed by a 35B Heavy model.
*   **Architect Protocol**: Every plan is verified by a metacognitive pass before execution to ensure architectural alignment.

### Memory Hierarchy
*   **Level 1 (Context)**: Managed in `src/core/context_manager.py`. Rolling session memory.
*   **Level 2 (Relational)**: Managed in `src/core/knowledge_graph.py`. A live, AST-scanned map of every file, function, and dependency.
*   **Level 3 (Semantic)**: Managed in `src/skills/memory/store.py`. FAISS vector store for episodic and procedural retrieval.
*   **Level 4 (Vault)**: Immutable facts and project-specific rules stored in the Sovereign Vault.

---

## 🛠️ 2. Core Modules (The Engine)

| File | Purpose | Logic |
|:---|:---|:---|
| `run.py` | **Sovereign Bootloader** | Process-level supervisor with Recursive Self-Repair (Ghost Recovery). |
| `src/main.py` | **Orchestrator** | Initializer for all background daemons and gateway handlers. |
| `src/settings.py` | **Config Master** | Type-safe Pydantic configuration replacing legacy `config.py`. |
| `src/core/gateway.py` | **Channel Router** | Unified entry point for TUI, Web, and Telegram traffic. |
| `src/core/tool_protocol.py` | **MCP-Lite** | Dynamic tool registry with AST-enriched technical signatures. |
| `src/core/ast_surgeon.py` | **Precision Mutation** | Modifies code via Abstract Syntax Trees rather than text replacement. |
| `src/core/self_healing.py` | **Guardian Drive** | Monitors audit logs for tracebacks and autonomously initiates repair. |
| `src/core/self_recovery.py` | **Recursive Repair** | Spawns isolated stable ASURA instances from backups to fix the core. |
| `src/core/resource_governor.py` | **Telemetry** | Throttles AI power based on real-time CPU/RAM/VRAM metrics. |
| `src/core/anesthesia.py` | **Surgical Lock** | Pauses background daemons during active codebase modifications. |

---

## 🧩 3. Functional Skills (Capabilities)

ASURA possesses 49+ modular skills. Key production groups include:

### 👁️ Visual & Vision
*   `src/skills/visual/vision.py`: Screenshot analysis and surgical UI debugging using 35B vision models.
*   `src/skills/browser/agent.py`: High-level web automation and interactive navigation.

### 🎙️ Voice & Audio
*   `src/skills/voice/interface.py`: Hybrid STT/TTS routing to local or remote Qwen servers.
*   `src/daemon/qwen_tts_server.py`: Background service for high-speed voice-to-voice streaming.

### 🧪 Validation & Self-Audit
*   `src/skills/auto_tester/tester.py`: Autonomous execution of Pytest and syntax verification.
*   `src/skills/skill_registry.py`: Deep AST indexing of all functional capabilities.

### 📦 OS & Infrastructure
*   `src/skills/shell_executor/executor.py`: PTY-based shell command execution with safety gates.
*   `src/skills/backup_manager/manager.py`: Snapshot and restoration engine for system safety.

---

## 📂 4. Production Directory Structure

```
ASURA/
├── src/
│   ├── core/           # Engine: Logic, Reasoning, Recovery
│   │   └── utils/      # Shared utilities (JSON, retry, time)
│   ├── skills/         # Capabilities: 50+ modular tools
│   ├── cli/            # Interface: TUI and CLI entry points
│   ├── agents/         # Personas: Markdown-defined specialists
│   └── daemon/         # Background: Persistent servers (Voice, Gateway)
├── tests/              # Verification: Benchmarks, audits, and unit tests
├── data/
│   ├── memory_store/   # FAISS Index
│   ├── backups/        # Stable system snapshots
│   └── logs/           # Unified audit and application traces
└── docs/               # Sovereignty: Master Documentation
```

---
*Last Verified: 2026-03-15 (Phase S - Absolute Restructuring Edition)*
