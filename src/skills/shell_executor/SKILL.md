---
name: shell_executor
description: "Core skill: Sandboxed shell execution. Runs commands inside the project freely, blocks/asks master for commands outside the project or destructive operations. File read/write/list helpers."
entry_point: executor.py
---

# Shell Executor Skill

## Safety Model
- **Inside project dir** → execute freely, log everything
- **Outside project dir** → BLOCK, ask master via Telegram
- **Destructive commands** (rm, sudo, kill, etc.) → BLOCK, ask master

## Capabilities
- `execute(cmd)` — Run shell command with safety analysis
- `execute_python(code)` — Run Python snippet
- `list_project_files(pattern)` — Find files by glob
- `read_file(path)` — Read file content
- `write_file(path, content)` — Write/create file
- `start_interactive_session(session_id, cmd)` — Start a long-running process
- `send_session_input(session_id, text)` — Send text to a process's stdin
- `get_session_status(session_id)` — Get output and status of a session
