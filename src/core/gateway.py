# ============================================================
# core/gateway.py — Interactive Gateway
#
# Unified routing layer for all ASURA interfaces.
# Telegram, Web Dashboard, API, and CLI all route through here.
#
# Provides: session management, channel-agnostic I/O,
# rate limiting, streaming dispatch, and permission checks.
# ============================================================

import os
import json
import time
import threading
from datetime import datetime, timezone
from typing import Optional, Generator, AsyncGenerator

import config
from skills.logger import log_audit, log_app
from core.context_manager import compact_history

# ─── Session Store ────────────────────────────────────────────
_sessions: dict[str, "GatewaySession"] = {}
_lock = threading.Lock()
_SESSIONS_DIR = os.path.join(config.DATA_DIR, "sessions")
os.makedirs(_SESSIONS_DIR, exist_ok=True)

# ─── Rate Limiter ─────────────────────────────────────────────
_rate_limits: dict[str, list[float]] = {}   # user_id -> [timestamps]
RATE_LIMIT_WINDOW = 60    # seconds
RATE_LIMIT_MAX = 30       # max messages per window


class GatewaySession:
    """
    Per-user session that persists across channels.

    Each session has:
    - Unique session ID (user_id based)
    - Message history (shared across channels)
    - Channel source tracking
    - Creation and last-active timestamps
    """

    def __init__(self, session_id: str, channel: str = "unknown"):
        self.session_id = session_id
        self.channel = channel
        self.history: list[dict] = []
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_active = self.created_at
        self.metadata: dict = {}
        self.tool_calls: int = 0
        self.total_messages: int = 0
        self.MAX_HISTORY = 100

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "channel": self.channel,
            "history": self.history,  # Preserve full history for smart persistence
            "created_at": self.created_at,
            "last_active": self.last_active,
            "metadata": self.metadata,
            "tool_calls": self.tool_calls,
            "total_messages": self.total_messages,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GatewaySession":
        session = cls(data["session_id"], data.get("channel", "unknown"))
        session.history = data.get("history", [])
        session.created_at = data.get("created_at", session.created_at)
        session.last_active = data.get("last_active", session.last_active)
        session.metadata = data.get("metadata", {})
        session.tool_calls = data.get("tool_calls", 0)
        session.total_messages = data.get("total_messages", 0)
        return session

    def save(self):
        """Persist session to disk."""
        # Truncate history before saving
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY:]
            
        path = os.path.join(_SESSIONS_DIR, f"{self.session_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            log_app(f"Session save failed: {e}")

    @classmethod
    def load(cls, session_id: str) -> Optional["GatewaySession"]:
        """Load session from disk."""
        path = os.path.join(_SESSIONS_DIR, f"{session_id}.json")
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    return cls.from_dict(json.load(f))
            except Exception:
                pass
        return None


# ============================================================
# Gateway Public API
# ============================================================

def get_or_create_session(user_id: str, channel: str = "api") -> GatewaySession:
    """
    Get existing session or create a new one.
    
    BRIDGE LOGIC: Redirect 'dashboard' and 'api' requests to the Master's 
    Telegram ID to ensure unified memory across all interfaces.
    """
    original_id = user_id
    if user_id in ["dashboard", "api", "web"]:
        # Map to Master's Telegram ID for identity unification
        user_id = str(config.TELEGRAM_ADMIN_CHAT_ID)
        if original_id != user_id:
            log_app(f"Gateway: Bridging session {original_id} -> Master ({user_id})")

    with _lock:
        if user_id in _sessions:
            session = _sessions[user_id]
            session.channel = channel
            session.last_active = datetime.now(timezone.utc).isoformat()
            return session

        # Try loading from disk
        session = GatewaySession.load(user_id)
        if session:
            session.channel = channel
            session.last_active = datetime.now(timezone.utc).isoformat()
            _sessions[user_id] = session
            return session

        # Create new
        session = GatewaySession(user_id, channel)
        _sessions[user_id] = session
        log_audit("GATEWAY", f"New session: {user_id} via {channel}")
        return session


async def handle_message(
    user_id: str,
    message: str,
    channel: str = "api",
    stream: bool = False,
    agent_name: str = None,
) -> str | AsyncGenerator:
    """
    Main gateway entry point. All channels route through here (Async).
    """
    # Rate limiting
    if not _check_rate_limit(user_id):
        return "⚠️ Rate limit exceeded. Please wait a moment."

    session = get_or_create_session(user_id, channel)
    session.total_messages += 1
    session.last_active = datetime.now(timezone.utc).isoformat()

    log_audit("GATEWAY", f"[{channel}] {user_id}: {message[:80]}...")

    # Intercept Gateway Commands first
    if message.startswith("/"):
        cmd_res = await handle_command(user_id, message, channel)
        if cmd_res:
            if stream:
                async def _gen_cmd(): yield cmd_res
                return _gen_cmd()
            return cmd_res

    if stream:
        return _handle_stream(session, message, agent_name=agent_name)
    return await _handle_sync(session, message, agent_name=agent_name)


async def handle_command(user_id: str, command: str, channel: str = "api") -> str:
    """Handle gateway-level commands (not routed to AI)."""
    cmd = command.strip().lower()

    if cmd == "/sessions":
        return list_sessions()
    # Support '!' and '/run' for shell execution
    elif command.startswith("!") or cmd.startswith("/run ") or cmd.startswith("/exec "):
        if command.startswith("!"):
            command_to_run = command[1:].strip()
        elif cmd.startswith("/run "):
            command_to_run = command[5:].strip()
        else:
            command_to_run = command[6:].strip()
            
        from skills.shell_executor.executor import execute
        try:
            res = await execute(command_to_run)
            if res.get("needs_approval"):
                return "🔒 **Elevation Required.** Please use an interactive channel to approve this command."
            
            output = res.get("stdout", "") or res.get("stderr", "") or "(no output)"
            return f"🐚 **Shell Execution:**\n```\n{output[:3000]}\n```"
        except Exception as e:
            return f"❌ Execution failed: {e}"

    elif cmd == "/debug":
        import config
        config.DEBUG_MODE = not getattr(config, "DEBUG_MODE", False)
        return f"🐛 Debug mode is now **{'ON' if config.DEBUG_MODE else 'OFF'}**."
    elif cmd.startswith("/model"):
        import config
        parts = command.split(" ", 1)
        if len(parts) > 1:
            config.GROQ_MODEL = parts[1].strip()
            return f"🧠 Active model explicitly set to **{config.GROQ_MODEL}**."
        return f"🧠 Current model configuration: **{getattr(config, 'GROQ_MODEL', 'Not Set')}**"
    elif cmd == "/cancel":
        from skills.ai_content.generator import cancel_current_task
        cancel_current_task()
        return "⚡ Task cancelled."
    elif cmd == "/history":
        session = get_or_create_session(user_id, channel)
        if not session.history:
            return "No history yet."
        lines = ["📜 **Recent Conversation History:**\n"]
        for m in session.history[-10:]:
            role = m.get("role", "?").upper()
            content = m.get("content", "")
            # Truncate content for TUI preview
            short_content = (content[:150] + "...") if len(content) > 150 else content
            lines.append(f"• **{role}**: {short_content}")
        return "\n".join(lines)
    elif cmd == "/clear":
        session = get_or_create_session(user_id, channel)
        session.history = []
        session.save()
        return "🗑️ Session history cleared."
    elif cmd.startswith("/resume "):
        session_id = command[8:].strip()
        if not session_id:
            sessions = list_all_session_files()
            return "📋 **Available Sessions:**\n" + "\n".join([f"  • {s}" for s in sessions])
        
        # Load the new session
        new_session = GatewaySession.load(session_id)
        if new_session:
            with _lock:
                _sessions[user_id] = new_session # Switch current user session to this one
            return f"🔄 **Resumed session:** `{session_id}`. Conversation history loaded."
        return f"❌ Session `{session_id}` not found."
    elif cmd.startswith("/rename "):
        parts = command[8:].strip().split(" ", 1)
        if len(parts) < 1:
            return "⚠️ Usage: `/rename <new_name>`"
        
        new_name = parts[0]
        session = get_or_create_session(user_id, channel)
        old_path = os.path.join(_SESSIONS_DIR, f"{session.session_id}.json")
        new_path = os.path.join(_SESSIONS_DIR, f"{new_name}.json")
        
        try:
            session.session_id = new_name
            session.save()
            if os.path.exists(old_path) and old_path != new_path:
                os.remove(old_path)
            return f"🏷️ Session renamed to `{new_name}`"
        except Exception as e:
            return f"❌ Rename failed: {e}"
    elif cmd == "/compress":
        session = get_or_create_session(user_id, channel)
        if len(session.history) > 4:
            session.history = await compact_history(session.history)
            session.save()
            return "🗜️ Context compressed using Smart Agentic Compaction. Key details preserved."
        return "🗜️ Context already minimal."
    elif cmd.startswith("/rewind"):
        session = get_or_create_session(user_id, channel)
        try:
            n = int(command[7:].strip() or 1)
        except ValueError:
            n = 1
        popped = 0
        for _ in range(n * 2): # user + assistant pairs
            if session.history:
                session.history.pop()
                popped += 1
        session.save()
        return f"⏪ Rewound {popped // 2} interaction(s)."
    elif cmd.startswith("/export"):
        session = get_or_create_session(user_id, channel)
        export_dir = os.path.join(config.DATA_DIR, "exports")
        os.makedirs(export_dir, exist_ok=True)
        path = os.path.join(export_dir, f"{session.session_id}_{int(time.time())}.json")
        try:
            with open(path, "w") as f:
                json.dump(session.history, f, indent=2)
            return f"💾 Session exported to `{path}`"
        except Exception as e:
            return f"❌ Export failed: {e}"
    elif cmd.startswith("/theme"):
        parts = command.split()
        if len(parts) > 1:
            theme = parts[1].lower()
            if theme in ["light", "dark"]:
                return f"🎨 Theme set to {theme}"
        return "🎨 Usage: `/theme light` or `/theme dark`. Current default is premium dark mode."
    
    elif cmd.startswith("/sandbox "):
        script = command[9:].strip()
        import subprocess
        sandbox_dir = "/tmp/asura_sandbox"
        os.makedirs(sandbox_dir, exist_ok=True)
        try:
            res = subprocess.run(script, shell=True, cwd=sandbox_dir, capture_output=True, text=True, timeout=10)
            out = res.stdout + res.stderr
            return f"📦 **Sandbox Execution:**\n```\n{out[:2000] or 'No output'}\n```"
        except subprocess.TimeoutExpired:
            return "⏳ Sandbox execution timed out."
        except Exception as e:
            return f"❌ Sandbox error: {e}"
    elif cmd.startswith("/plan "):
        task = command[6:].strip()
        from core.reasoning import recursive_think
        try:
            # Removed asyncio.run
            result = await recursive_think(task)
            return f"📋 **Implementation Plan:**\n\n{result['final_conclusion']}"
        except Exception as e:
            return f"❌ Planning failed: {e}"
    elif cmd.startswith("/remind "):
        parts = command[8:].strip().split(" ", 1)
        if len(parts) < 2:
            return "⚠️ Usage: `/remind <time> <message>` (e.g. `/remind 2026-03-08 14:00 Check logs`)"
        when, message = parts[0], parts[1]
        from skills.calendar_manager.calendar import add_event
        ev = add_event(title=message, when=when)
        return f"⏰ Reminder set for **{ev['when']}**: {message}"
    elif cmd == "/diff":
        from skills.git_manager.git import diff
        d = diff()
        if not d.strip():
            return "No unstaged changes."
        return f"📝 **Git Diff:**\n```diff\n{d[:3000]}\n```"
    elif cmd == "/init":
        init_dir = os.path.join(config.BASE_DIR, ".asura")
        os.makedirs(init_dir, exist_ok=True)
        conf_path = os.path.join(init_dir, "config.json")
        if not os.path.isfile(conf_path):
            with open(conf_path, "w") as f:
                json.dump({"project_name": os.path.basename(config.BASE_DIR), "initialized_at": datetime.now(timezone.utc).isoformat()}, f, indent=2)
            return "✅ Initialized ASURA project in current directory."
        return "⚠️ ASURA project already initialized here."
    elif cmd == "/help":
        cmds = {
            "/agents": "List active agents and their active models",
            "/compress": "Compress history context to the last 4 interactions",
            "/debug": "Toggle verbose debug mode",
            "/diff": "Show git differences for unstaged changes",
            "/export": "Export current session history to disk",
            "/help": "Show this help screen",
            "/history": "Show recent conversation history",
            "/init": "Initialize ASURA project in current directory",
            "/model <name>": "Switch the active LLM explicitly",
            "/plan <task>": "Generate a step-by-step implementation plan without executing",
            "/processes": "List running ASURA and AI processes",
            "/remind <time> <msg>": "Add a scheduled reminder",
            "/resume <id>": "Resume previous session (CLI only)",
            "/rewind [n]": "Revert the last `n` AI actions/messages",
            "/sandbox <cmd>": "Run code in safe sub-process environment",
            "/sessions": "List active gateway sessions",
            "/skills": "List available skills",
            "/stats": "View observability and timing metrics",
            "/status": "Show overall ASURA System Status",
            "/theme <color>": "Change CLI output color theme (CLI only)",
            "/tools": "List available raw MCP/Skill tools",
        }
        lines = ["📚 **ASURA Slash Commands:**\n"]
        for k, v in sorted(cmds.items()):
            lines.append(f"• **`{k}`**: {v}")
        return "\n".join(lines)
    elif cmd.startswith("/workflows"):
        from core.workflow_engine import list_workflows
        return list_workflows()
    elif cmd == "/evolve":
        from core.self_updater import updater
        threading.Thread(target=updater.run_cycle, daemon=True).start()
        return "🚀 ASURA Evolution initiated. Generating improvements..."
    elif cmd.startswith("/zero "):
        from core.reasoning import recursive_think
        task = command[6:].strip()
        try:
            result = await recursive_think(task)
            return f"🌀 **ASURA Zero Reasoning**:\n\n{result['final_conclusion']}"
        except Exception as e:
            return f"❌ Zero Reasoning failed: {e}"

    elif cmd.startswith("/notify "):
        msg = command[8:].strip()
        from skills.telegram_bot.bot import notify_master
        notify_master(f"🔔 <b>ASURA Gateway Alert</b>\n\n{msg}")
        return f"✅ Notification sent: {msg}"

    elif cmd.startswith("/review "):
        target = command[8:].strip()
        from skills.swarm_review import run_swarm_review_sync

        # Read the file to review
        filename = os.path.basename(target)
        try:
            with open(target, "r") as f:
                code_content = f.read()
            return run_swarm_review_sync(code_content, filename)
        except Exception as e:
            return f"❌ Review failed: {e}"

    elif cmd.startswith("/create-agent "):
        """Create a new declarative agent from user specification."""
        task = command[14:].strip()
        if not task:
            return "⚠️ Usage: `/create-agent <agent description>` (e.g., `/create-agent A code review specialist who checks for security vulnerabilities`)"

        try:
            import asyncio
            from core.reasoning import recursive_think

            # Generate a complete agent definition using AI
            template_prompt = f"""
Create a complete declarative ASURA agent based on this specification: "{task}"

Requirements:
1. Name: Use kebab-case, one word that best describes the agent's purpose
2. Model: Choose 'fast', 'heavy', or 'inherit' based on complexity
3. Description: Clear, concise one-line description
4. Instructions: Detailed step-by-step guidelines for how the agent should operate
5. Include <example> blocks with Context/query/response format (at least 2-3 different examples)

Output FORMAT as a valid markdown file content with YAML frontmatter exactly like this structure:

---
name: agent-name
description: What this agent does
model: fast|heavy|inherit
---

# Agent Name

[Full name and extended description]

## Purpose
[Why this agent exists, what problems it solves]

## Behavior
[Detailed operational guidelines, step-by-step processes, best practices]

## Output Format
[How the agent should structure its responses]

<example>
Context: [situation or context where this agent is relevant]

user: [specific query/example that would trigger this agent]

assistant: [example response showing expected behavior]
</example>

[Add more <example> blocks as needed...]
"""

            result = asyncio.run(recursive_think(template_prompt))
            agent_content = result['final_conclusion']

            # Extract name from YAML frontmatter or filename
            name_match = re.search(r'^name:\s*(\S+)', agent_content, re.MULTILINE)
            if name_match:
                agent_name = name_match.group(1)
            else:
                # Fallback: generate name from task
                agent_name = f"agent_{int(time.time())}"

            # Determine model preference
            model_match = re.search(r'^model:\s*(\S+)', agent_content, re.MULTILINE)
            if not model_match:
                return "❌ Failed to generate valid agent - missing model specification"

            # Save the agent file
            from pathlib import Path

            # Use src/agents directory for declarative agents
            agents_dir = Path("src/agents")
            agents_dir.mkdir(exist_ok=True)

            agent_file = agents_dir / f"{agent_name}.md"

            with open(agent_file, "w", encoding="utf-8") as f:
                f.write(agent_content + "\n")

            # Reload agents to register the new one
            from core.declarative_agent_loader import get_agent_loader, init_declarative_agents
            loader = get_agent_loader()
            loader._load_declarative_agent(agent_file)

            log_app(f"Created new agent: {agent_name} at {agent_file}")

            return f"""🎉 **Agent Created Successfully!**

**Name:** `{agent_name}`
**Model:** {model_match.group(1)}
**File:** `src/agents/{agent_name}.md`

The agent has been registered and is now active. Use its name to trigger it specifically, or let the routing system automatically assign queries."""
        except Exception as e:
            log_audit("CREATE_AGENT_ERROR", f"Failed to create agent: {e}")
            return f"❌ Failed to create agent: {e}"

    elif cmd.startswith("/create-skill "):
        """Create a new skill from user specification."""
        task = command[14:].strip()
        if not task:
            return "⚠️ Usage: `/create-skill <skill description>` (e.g., `/create-skill A skill to manage database migrations`)"

        try:
            import asyncio
            from core.reasoning import recursive_think

            # Generate a complete skill using AI
            template_prompt = f"""
Create a complete ASURA skill based on this specification: "{task}"

Requirements:
1. Name: Use kebab-case or snake_case describing the functionality
2. Description: Clear, concise description of what it does
3. Entry point: The Python function that will be called (usually defined in __init__.py)
4. Include practical example usage

Output FORMAT as a markdown file with YAML frontmatter exactly like this structure:

---
name: skill-name
description: What this skill does
entry_point: module.function_name
---

# Skill Name

[Full name and extended description]

## Features
[List what the skill can do]

## Usage Examples
[Show how users would invoke this skill with example queries]

## Installation/Setup
[Any setup requirements, dependencies, etc.]

## Implementation Details
[Optional technical notes for developers]
"""

            result = asyncio.run(recursive_think(template_prompt))
            skill_content = result['final_conclusion']

            # Extract name from YAML frontmatter or filename
            name_match = re.search(r'^name:\s*(\S+)', skill_content, re.MULTILINE)
            if name_match:
                skill_name = name_match.group(1)
            else:
                skill_name = f"skill_{int(time.time())}"

            # Determine entry point
            entry_match = re.search(r'^entry_point:\s*(\S+)', skill_content, re.MULTILINE)
            if not entry_match:
                return "❌ Failed to generate valid skill - missing entry_point specification"

            # Save the skill markdown file
            from pathlib import Path

            skills_dir = Path("skills") / skill_name
            skills_dir.mkdir(parents=True, exist_ok=True)

            skill_md_path = skills_dir / "SKILL.md"
            with open(skill_md_path, "w", encoding="utf-8") as f:
                f.write(skill_content + "\n")

            # Create a minimal __init__.py as placeholder
            init_path = skills_dir / "__init__.py"
            if not init_path.exists():
                with open(init_path, "w", encoding="utf-8") as f:
                    f.write(f"# {skill_name} skill package\n# Entry point defined in SKILL.md\n")

            # Reload skills to register the new one
            from skills.skill_registry import discover_skills
            registry = discover_skills()

            log_app(f"Created new skill: {skill_name} at {skills_dir}")

            return f"""🎉 **Skill Created Successfully!**

**Name:** `{skill_name}`
**Entry Point:** {entry_match.group(1)}
**Directory:** `skills/{skill_name}/`

The skill has been registered and is now available. ASURA will automatically discover and load it on next restart."""
        except Exception as e:
            log_audit("CREATE_SKILL_ERROR", f"Failed to create skill: {e}")
            return f"❌ Failed to create skill: {e}"

    elif cmd.startswith("/remember "):
        fact = command[10:].strip()
        from core.memory_manager import SovereignMemory
        return SovereignMemory.remember_fact(fact, "manual_recall")
    elif cmd.startswith("/forget "):
        return "⚠️ Identity Vault entries are currently 'Sovereign' (Immutable). Please use the Admin Dashboard to prune the Vault file manually for safety."
    elif cmd == "/vault":
        from core.memory_manager import SovereignMemory
        return SovereignMemory.recall("all", limit=20)

    # Fallback for unrecognized slash commands
    if cmd.startswith("/"):
        return f"⚠️ Command `{cmd.split()[0]}` not recognized. Type `/help` for available commands."

    return None  # Not a gateway command, pass to AI


def list_sessions() -> str:
    """List all active sessions."""
    with _lock:
        if not _sessions:
            return "No active sessions."
        lines = ["📋 **Active Gateway Sessions:**\n"]
        for sid, s in _sessions.items():
            lines.append(
                f"• **{sid}** [{s.channel}] — "
                f"{s.total_messages} msgs, last active: {s.last_active[:19]}"
            )
        return "\n".join(lines)


def get_session_count() -> int:
    with _lock:
        return len(_sessions)


def list_all_session_files() -> list[str]:
    """List all session IDs available on disk."""
    files = os.listdir(_SESSIONS_DIR)
    return [f[:-5] for f in files if f.endswith(".json")]


# ============================================================
# Internal Helpers
# ============================================================

async def _handle_sync(session: GatewaySession, message: str, agent_name: str = None) -> str:
    """Handle message synchronously (blocking) but as an async coroutine."""
    from skills.ai_content.generator import chat

    try:
        # Proactive Auto-Compaction
        if len(session.history) > 20:
             session.history = await compact_history(session.history)
             
        reply, updated_history = await chat(message, session.history, platform=session.channel, agent_name=agent_name)
        session.history = updated_history
        
        # ─── MCQ Button Detection ─────────────
        # If the reply contains [Choice 1] | [Choice 2]
        if "[" in reply and "|" in reply:
            import re
            choices = re.findall(r'\[(.*?)\]', reply)
            if choices:
                session.metadata["pending_choices"] = choices
                log_audit("GATEWAY", f"Detected {len(choices)} MCQ buttons")
        
        session.save()
        return reply or "(No response generated)"
    except Exception as e:
        log_audit("GATEWAY_ERROR", f"Chat failed: {e}")
        return f"⚠️ Error: {e}"


async def _handle_stream(session: GatewaySession, message: str, agent_name: str = None) -> AsyncGenerator:
    """Handle message with streaming (yields chunks)."""
    from skills.ai_content.generator import chat_stream

    try:
        # Proactive Auto-Compaction
        if len(session.history) > 20:
             session.history = await compact_history(session.history)

        full_reply = ""
        async for chunk in chat_stream(message, session.history, platform=session.channel, agent_name=agent_name):
            full_reply += chunk
            yield chunk

        # Update session after stream completes
        if full_reply.strip():
            session.history.append({"role": "user", "content": message})
            session.history.append({"role": "assistant", "content": full_reply})
            session.save()
    except Exception as e:
        yield f"\n⚠️ Stream error: {e}"


def _check_rate_limit(user_id: str) -> bool:
    """Check if user is within rate limits."""
    now = time.time()
    if user_id not in _rate_limits:
        _rate_limits[user_id] = []

    # Clean old timestamps
    _rate_limits[user_id] = [
        t for t in _rate_limits[user_id]
        if now - t < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limits[user_id]) >= RATE_LIMIT_MAX:
        log_audit("RATE_LIMIT", f"User {user_id} exceeded {RATE_LIMIT_MAX} msgs/{RATE_LIMIT_WINDOW}s")
        return False

    _rate_limits[user_id].append(now)
    return True


def _get_stats() -> str:
    """Get gateway statistics."""
    try:
        from core.observability import format_stats
        obs = format_stats()
    except Exception:
        obs = "Observability unavailable."

    return (
        f"🌐 **ASURA Gateway Statistics:**\n"
        f"• **Active sessions**: {get_session_count()}\n"
        f"• **Storage path**: `{_SESSIONS_DIR}`\n\n"
        f"{obs}"
    )

