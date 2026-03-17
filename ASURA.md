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
- **HEAVY**: `Qwen3.5:35b` - Complex reasoning, code generation, architecture design

## Coding Style
- Use Python 3.12+ features
- Type hints on all public functions
- Docstrings on all classes and public functions
- Use f-strings, not .format() or %
- Max line length: 100 characters

## Architecture Rules
- **Async First**: Core logic MUST be asynchronous (`async def`). Avoid blocking I/O; use `httpx` or `asyncio.to_thread`.
- **Multitasking**: Long-running shell commands MUST use the `spawn_job` tool via the `JobManager`.
- **Sovereign Auth**: All new API/Dashboard routes MUST enforce JWT or `X-ASURA-Key` verification.
- **Internal VCS**: Every code application by the AI MUST be preceded by a VCS commit via `get_vcs().commit()`.
- **Tiered Intelligence**: Use `Qwen3.5:0.8b` for routing/JSON, `Qwen3.5:35b` for reasoning and complex tasks.
- All new tools MUST register via `core/tool_protocol.py`.
- All path handling MUST be OS-independent (use `os.path.join` or `pathlib.Path`).
- All logging via `skills.logger`.
- **Surgical Mutation**: Use the `surgical_edit` tool for ALL Python code modifications instead of `edit_file` or `write_file`. The AST Surgeon runs your code in an isolated Minimal Run Environment (Sovereign OT) to verify it works before saving. Avoid full-file rewrites.
- **Permanent Facts**: Use the `remember_fact` tool for all identity or high-priority user preferences.
- **Environment Guard**: `run.py` is the strictly enforced isolated entry point. Do not bypass venv checks.

## Phase 2: Declarative Agents & Security Interceptors

### Specialized Agents (src/agents/)
Load agent definitions from `.md` files with YAML frontmatter:
- `archistar` - Architecture design and system planning
- `explorer` - Codebase navigation and pattern discovery
- `reviewer` - Security and quality auditing
- `validator` - Configuration and structure verification
- `simplifier` - Code refactoring and clarity improvement

### Security Interceptors (src/core/interceptors.py)
Pre-execution validation hooks:
- Blocks dangerous commands (`rm -rf`, `dd`, etc.)
- Detects hardcoded secrets and credentials
- Flags production environment operations requiring confirmation

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
- Model: Tiered (20B Heavy/Review + 1.5B Fast)
- Execution: Non-blocking Async Runtime
