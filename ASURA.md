# ============================================================
# ASURA.md — Project Configuration
#
# This file is loaded by ASURA on startup, similar to Claude Code's
# CLAUDE.md. Add project-specific rules, preferences, and context.
# ============================================================

# Project: ASURA (Sovereign AI Agent)
# Owner: Aniket Raj Singh

## Model Configuration
- **FAST**: `Qwen3.5:0.8b` - Routing, JSON parsing, simple queries
- **HEAVY**: `gpt-oss:20b` - Complex reasoning, code generation, architecture design
- **VISION**: `Qwen3.5:0.8b` (Fast) or `gpt-oss:20b` (Heavy)

## Coding Style
- Use Python 3.12+ features
- Type hints on all public functions
- Docstrings on all classes and public functions
- Use f-strings, not .format() or %
- Max line length: 100 characters

## Architecture Rules
- **Async First**: Core logic MUST be asynchronous (`async def`). Avoid blocking I/O; use `httpx` or `asyncio.to_thread`.
- **Parallel-Turbo**: Preparation tasks (agent selection, context loading) SHOULD execute concurrently using `asyncio.gather`.
- **Sovereign Auth**: All new API/Dashboard routes MUST enforce JWT or `X-ASURA-Key` verification.
- **Master Bypass**: Telegram RBAC MUST allow `config.TELEGRAM_ADMIN_CHAT_ID` to bypass registration for immediate command.
- **Ghost Repair**: Core components MUST be backed up in `data/recovery_cache/` for autonomous restoration by the Guardian Drive.
- **Sovereign Power Lock**: `SovereignAuthority` MUST be engaged at startup to prevent node sleep.
- **Proxy Bypass**: All internal LLM/Ollama clients MUST use `trust_env=False` to bypass system-level proxies.
- All new tools MUST register via `core/tool_protocol.py`.
- All path handling MUST be OS-independent (use `os.path.join` or `pathlib.Path`).
- **Incremental Scanning**: Knowledge Graph updates SHOULD use AST caching and directory-mtime skipping for performance.
- **Permanent Facts**: Use the `remember_fact` tool for all identity or high-priority user preferences.
- **Environment Guard**: `run.py` is the strictly enforced isolated entry point. Do not bypass venv checks.

## Phase S.2: Absolute Integrity & Cluster Synergy

### Specialized Agents (src/agents/)
Load agent definitions from `.md` files with YAML frontmatter:
- `asura_spawner` - Core system architect and agent manager
- `explorer` - Codebase navigation and pattern discovery
- `reviewer` - Security and quality auditing
- `telegram_specialist` - Mobile-optimized interaction hub

### Security & UX
- **Administrative Suite**: Telegram Control Panel for vitals, logs, and restarts.
- **Visual Thinking**: Animated processing indicators for real-time status feedback.
- **Split Messaging**: Responses must separate text from code blocks for clean rendering.

## Forbidden Patterns
- No os.system() — use subprocess
- No os.killpg() — use psutil for cross-platform termination
- No shell=True in subprocess unless strictly required
- No eval() or exec()
- No import * (explicit imports only)
- No bare except (always catch specific exceptions)
- No hardcoded API keys (use .env)

## Testing
- Run tests: python run.py test
- Syntax check: python -m py_compile <file>

## Deployment
- Platform: Universal (macOS, Windows, Linux)
- Interface: Telegram bot + Dashboard (SCC 2.0)
- Model: Tiered (GPT-OSS 20B Heavy / 0.8B Fast)
- Execution: Non-blocking Parallel-Async Runtime
