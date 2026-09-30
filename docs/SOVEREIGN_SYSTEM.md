# ASURA: Sovereign Autonomous Intelligence — System Master Authority

**ASURA (Autonomous Self-Updating Reasoning Agent)** is a recursive AI ecosystem built for high-fidelity engineering and local OS sovereignty.

---

## 🏗️ 1. Technical Architecture

ASURA is designed as a **Multi-Layered Sovereign Engine** that separates high-level reasoning from low-level system execution.

### The Reasoning Loop (ASURA-Zero)
Implemented in `src/core/reasoning.py`, the loop follows a **Think -> Plan -> Act -> Observe -> Reflect** cycle.
*   **Dual-Tier Intelligence**: Intent recognition is handled by a fast 0.8B model, while complex engineering is executed by a **GPT-OSS 20B** Heavy model.
*   **Architect Protocol**: Every plan is verified by a metacognitive pass before execution to ensure architectural alignment.

### Multi-Level Memory Hierarchy
*   **Level 1 (Context)**: Managed in `src/core/context_manager.py`. Rolling 50-turn session memory for immediate coherence.
*   **Level 2 (Relational)**: Managed in `src/core/knowledge_graph.py`. A live, AST-scanned map of every file, function, and dependency.
*   **Level 3 (Semantic)**: Managed in `src/skills/memory/store.py`. FAISS vector store using `nomic-embed-text` for episodic and procedural retrieval.
*   **Level 4 (Vault)**: Immutable facts, Master preferences, and project-specific rules stored in the Sovereign Vault.

---

## 🛠️ 2. The Engine (Core Modules)

| Component | Logic | Purpose |
|:---|:---|:---|
| **Sovereign Bootloader** | `run.py` | Process supervisor with **Ghost Repair** (Recursive Self-Repair from snapshots). |
| **Orchestrator** | `src/main.py` | Initializer for parallel services, daemons, and leader election. |
| **Config Master** | `src/settings.py` | Type-safe configuration and global system state flags. |
| **Channel Router** | `src/core/gateway.py` | Unified entry point for TUI, Web, and Telegram traffic. |
| **MCP-Lite** | `src/core/tool_protocol.py` | Dynamic tool registry with AST-enriched technical signatures. |
| **Precision Mutation** | `src/core/ast_surgeon.py` | Modifies code via Abstract Syntax Trees rather than text replacement. |
| **Immortal Sentinel** | `src/core/self_healing.py` | Multi-log surveillance with **Architect-Critic** repair loops. |
| **Recursive Repair** | `src/core/self_recovery.py` | Spawns isolated stable instances from backups to fix the core. |
| **Telemetry** | `src/core/resource_governor.py` | Throttles AI power based on real-time CPU/RAM/VRAM metrics. |
| **Surgical Lock** | `src/core/anesthesia.py` | Pauses background daemons during active codebase modifications. |

---

## 📱 3. Master Interaction (Administrative Suite)

ASURA features a mobile-first interaction hub on Telegram, providing absolute sovereign control from anywhere.

### 🛠️ Sovereign Control Panel
The Control Panel provides a central interface for managing the cluster's state, evolution, and health. It now supports **Multi-Node Selection** for all administrative tasks.

![Control Panel](img/control_panel.png)
*Figure 1: The interactive Control Panel featuring Evolution Logs, Topology, and Maintenance tools.*

### 📋 Interactive Task Orchestration
ASURA uses a **Summary-First** proactive model to eliminate conversational bloat.
*   **The "Expand" Pattern**: Multiple proactive insights are merged into a single "Insight Summary" with an **Expand** button.
*   **Actionable Queue**: View, edit, or cross-question AI recommendations before adding them to your **📋 Task Manager**.
*   **Autonomous Execution**: Approved tasks execute in the background when system resources are available.

### 🚦 ASURA Pulse (Live Vitals)
High-fidelity system diagnostics are delivered directly to Telegram. You can now toggle the Pulse between your **Local Node** and federated peers like **RNDPC**.

![ASURA Pulse](img/asura_pulse.png)
*Figure 2: Real-time system vitals and operational integrity report.*

---

## 🧩 4. Functional Skills (Capabilities)

ASURA possesses 49+ modular skills. Key production groups include:

### 👁️ Visual Intelligence & Vision
*   **screenshot**: Capture system screen using native macOS/Windows fallbacks.
*   `src/skills/visual/vision.py`: Screenshot analysis and surgical UI debugging using 20B vision models.
*   `src/skills/browser/agent.py`: High-level web automation and interactive navigation.
*   **ocr_image**: Fast text extraction from any visual source.

### 🎙️ Audio & Voice Stack
*   **voice_chat**: Direct voice-to-voice interaction using local Whisper and remote Qwen-TTS.
*   `src/skills/voice/interface.py`: Hybrid STT/TTS routing to local or remote Qwen servers.
*   `src/daemon/qwen_tts_server.py`: Background service for high-speed voice-to-voice streaming.
*   **audio_say**: Local system-level text-to-speech for alerts and notifications.

### 🧪 Validation, Audit & Integrity
*   `src/skills/auto_tester/tester.py`: Autonomous execution of Pytest and syntax verification.
*   `src/skills/skill_registry.py`: Deep AST indexing of all functional capabilities.
*   **system_health**: High-level telemetry monitoring and resource-aware throttling.

### 📦 OS, Files & Infrastructure
*   `src/skills/shell_executor/executor.py`: PTY-based shell command execution with safety gates.
*   `src/skills/backup_manager/manager.py`: Snapshot and restoration engine for system safety.
*   **file_organizer**: Autonomous directory hygiene, dead code detection, and statistics.
*   **git_manager**: Version control integration with auto-commits and branch logic.

### 🧠 Intelligence & Search
*   **web_intelligence**: Multi-engine web search and clean content scraping.
*   **doc_summarizer**: Recursive summarization of local files and URLs.
*   **codebase_investigator**: Deep static analysis, symbol finding, and import tracing.
*   **memory**: Semantic (FAISS), Episodic (JSONL), and Procedural storage layers.

---

## 🌐 5. Federated Cluster Synergy

ASURA instances collaborate across your network using the **Sovereign Federation** protocol.

*   **Live Intent Sharing**: When one node learns a new intent mapping, it is instantly broadcast to all peers.
*   **Sovereign Witness Protocol**: PC-1 requests validation from RNDPC before final commitment of autonomous repairs.
*   **Distributed Reasoning**: Specialists can be offloaded to peer nodes during high-load scenarios.

---

## 🖥️ 6. Sovereign Command Center (Web)

For deep architectural work, the Web Dashboard provides absolute visibility into ASURA's internal "Self."

![Command Center](img/command_center_web.png)
*Figure 3: The System Intelligence Monitor and active operation stack.*

### 🌐 Cluster-Aware Cockpit
*   **Node Selector**: Switch the entire dashboard view between your Local Mac and RNDPC Windows nodes.
*   **Process Orchestration**: A de-duplicated list of unique master processes (Core, Bot, Loader) with real-time **Terminate** and **Restart** controls.
*   **Witness Verification**: Real-time status of the cluster-wide "Immune System" and autonomous repair validation.

### 🕸️ Architectural Knowledge Graph
ASURA's self-awareness is powered by a live D3.js visualization of its entire source code.

![Knowledge Graph](img/knowledge_graph.png)
*Figure 4: Relational map of all files, functions, and dependencies.*

---

## 📂 7. Directory Structure

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
│   ├── memory_store/   # FAISS Vector Index
│   ├── recovery_cache/ # Persistent Golden Snapshots
│   └── logs/           # Unified audit and application traces
└── docs/               # Technical Documentation
```

---
*Last Verified: 2026-03-19 (Phase S.2 - Witness Architecture Edition)*
