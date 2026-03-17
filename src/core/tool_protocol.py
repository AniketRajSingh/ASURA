# ============================================================
# core/tool_protocol.py — MCP-Lite: Dynamic Tool Protocol
#
# Replaces the hardcoded _dispatch_action() if/elif chain with
# a dynamic tool registry. Tools are registered by skills and
# looked up at runtime by name.
#
# Inspired by Anthropic's Model Context Protocol (MCP).
# ============================================================

from typing import Callable, Any, Coroutine
import asyncio
import httpx
import os
import json

from settings import settings as config
from skills.logger import log_audit, log_app
from core.utils import is_safe_path

# ─── Global Tool Registry ─────────────────────────────────
_registry: dict[str, dict] = {}


def register_tool(
    name: str,
    function: Callable,
    description: str,
    parameters: dict = None,
    category: str = "general",
    metadata: dict = None,
) -> None:
    """
    Register a tool in the MCP-Lite registry.

    Args:
        name: Unique tool name (e.g., "web_search", "shell")
        function: The callable that executes the tool
        description: Human-readable description for the LLM
        parameters: JSON schema for parameters
        category: Tool category for organization
        metadata: Optional deep AST metadata (signature, return types, etc.)
    """
    _registry[name] = {
        "name": name,
        "function": function,
        "description": description,
        "parameters": parameters or {
            "type": "object",
            "properties": {"input": {"type": "string"}},
            "required": ["input"],
        },
        "category": category,
        "metadata": metadata or {},
    }


async def dispatch(name: str, args: str | dict = "") -> str:
    """
    Execute a registered tool by name with full Claude Code-style pipeline:
    1. Permission check
    2. Pre-hooks
    3. Tool execution with observability tracing
    4. Retry with exponential backoff (3 attempts)
    5. Post-hooks
    """
    name = name.strip().lower()

    if name not in _registry:
        available = ", ".join(sorted(_registry.keys()))
        return f"Unknown tool: {name}. Available: {available}"

    # Normalize for permission check / logging
    input_summary = str(args) if isinstance(args, dict) else args

    # ── 1. Permission check ──────────────────────────────────
    try:
        from core.permissions import check_permission
        allowed, reason = check_permission(name, input_summary)
        if not allowed:
            log_audit("MCP_BLOCKED", f"{name}: {reason}")
            return reason
    except ImportError:
        pass

    # ── 2. Security Interceptor Check ────────────────────────
    try:
        from core.interceptors import check_tool_call
        blocked, intercept_reason = check_tool_call(name, args if isinstance(args, dict) else {"input": args})
        if blocked:
            log_audit("INTERCEPT_BLOCKED", f"{name}: {intercept_reason}")
            return f"BLOCKED BY SECURITY INTERCEPTOR: {intercept_reason}"
        elif intercept_reason:
            # It was a warning or confirmation request (confirmation not fully implemented in this sync flow, so we warn)
            log_audit("INTERCEPT_WARNING", f"{name}: {intercept_reason}")
            # We continue for now, but log the warning
    except ImportError:
        pass
    except Exception as e:
        log_audit("INTERCEPT_ERROR", f"Interceptor failure: {e}")

    # ── 3. Pre-hooks ─────────────────────────────────────────

    # ── 3. Execute with observability + retry ────────────────
    from core.utils.retry import async_retry
    tool = _registry[name]

    @async_retry(retries=3, delay=1.0, backoff=2.0)
    async def _execute_with_retry(tool_fn, tool_args):
        if asyncio.iscoroutinefunction(tool_fn):
            return await tool_fn(tool_args)
        else:
            return await asyncio.to_thread(tool_fn, tool_args)

    try:
        result = await _execute_with_retry(tool["function"], args)
        result = str(result) if result is not None else "Done."
    except Exception as e:
        log_audit("MCP_ERROR", f"{name} failed after retries: {e}")
        raise RuntimeError(f"TOOL_ERROR: {e}")

    # ── 4. Post-hooks ────────────────────────────────────────
    try:
        from core.hooks import run_post_hooks
        run_post_hooks(name, input_summary, result or "")
    except ImportError:
        pass

    return result or "Done."


def get_tools_schema() -> list[dict]:
    """
    Generate the JSON schema array for LLM tool calling.
    Injects deep AST metadata (signatures) into descriptions for higher precision.
    """
    schema = []
    for name, tool in _registry.items():
        desc = tool["description"]
        meta = tool.get("metadata", {})
        
        # If we have AST metadata, append the real signature to the description
        if meta and "name" in meta:
            args_str = ", ".join([f"{a['name']}: {a.get('type', 'Any')}" for a in meta.get("args", [])])
            sig = f"\nSignature: {meta['name']}({args_str}) -> {meta.get('return_type', 'Any')}"
            desc += sig
            if meta.get("docstring"):
                desc += f"\nDetails: {meta['docstring']}"

        schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": tool["parameters"],
            },
        })
    return schema


def list_tools() -> str:
    """Return a formatted list of all registered tools."""
    if not _registry:
        return "No tools registered."
    lines = ["📦 Registered Tools:\n"]
    for name, tool in sorted(_registry.items()):
        lines.append(f"  • {name} — {tool['description'][:60]}")
    return "\n".join(lines)


def get_tool_count() -> int:
    """Return the number of registered tools."""
    return len(_registry)


# ============================================================
# Built-in Tool Implementations
# ============================================================

async def _tool_shell(args: str | dict) -> str:
    """Run a shell command."""
    cmd = args.get("command", "") if isinstance(args, dict) else args
    from skills.shell_executor.executor import execute
    result = await execute(cmd, timeout=30)
    if result.get("needs_approval"):
        return f"BLOCKED: {result['stderr']} — Requires Master approval."
    out = result.get("stdout", "")
    err = result.get("stderr", "")
    return (out[:3000] if out else "") + (f"\nSTDERR: {err[:500]}" if err else "")


def _tool_system_info(args: str | dict) -> str:
    """Get CPU/RAM/disk info."""
    from skills.hardware_monitor.monitor import get_system_info
    info = get_system_info()
    if isinstance(info, dict):
        lines = []
        cpu = info.get('cpu_percent', info.get('cpu', 'N/A'))
        mem = info.get('memory', {})
        disk = info.get('disk', {})
        lines.append(f"CPU: {cpu}%" if not isinstance(cpu, dict) else f"CPU: {json.dumps(cpu)}")
        if isinstance(mem, dict):
            lines.append(f"RAM: {mem.get('percent', '?')}% used ({mem.get('used_gb', '?')}GB / {mem.get('total_gb', '?')}GB)")
        if isinstance(disk, dict):
            lines.append(f"Disk: {disk.get('percent', '?')}% used ({disk.get('used_gb', '?')}GB / {disk.get('total_gb', '?')}GB)")
        lines.append(f"Platform: {info.get('platform', 'N/A')}")
        lines.append(f"Python: {info.get('python_version', 'N/A')}")
        return "\n".join(lines)
    return str(info)


def _tool_screenshot(args: str | dict) -> str:
    """Capture a screenshot of the system."""
    from skills.visual.vision import take_screenshot
    # Use a temp directory
    temp_dir = os.path.join(config.PROJECT_ROOT, "data/temp")
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, "mcp_screenshot.png")
    return take_screenshot(path)


def _tool_browse(args: str | dict) -> str:

    """Read content from a URL."""
    url = args.get("url", "") if isinstance(args, dict) else args
    try:
        from skills.browser.automation import browse_url
        result = browse_url(url)
        title = result.get('title', 'N/A') if isinstance(result, dict) else 'N/A'
        content = result.get('content', '') if isinstance(result, dict) else str(result)
        return f"Title: {title}\n\n{content[:3000]}"
    except Exception:
        import requests as _req
        try:
            # Removed verify=False for security
            resp = _req.get(url, timeout=10,
                            headers={'User-Agent': 'ASURA/4.0'})
            return f"Title: (fetched)\n\n{resp.text[:3000]}"
        except Exception as e2:
            return f"Browse failed: {e2}"


def _tool_browser_snapshot(args: str | dict) -> str:
    """Take a screenshot of a URL."""
    url = args.get("url", "") if isinstance(args, dict) else args
    try:
        from skills.browser.automation import take_screenshot
        path = take_screenshot(url)
        return f"Screenshot saved to: {path}"
    except Exception as e:
        return f"Screenshot failed: {e}"


def _tool_analyze_image(args: str | dict) -> str:
    """Analyze an image using vision models."""
    if not isinstance(args, dict):
        return "ERROR: analyze_image requires a JSON dictionary with 'path' and 'question'."
    path = args.get("path", "")
    question = args.get("question", "Describe this image.")
    from skills.visual.vision import analyze_image
    return analyze_image(path, question)


def _tool_web_search(args: str | dict) -> str:
    """Search the web."""
    query = args.get("query", "") if isinstance(args, dict) else args
    from skills.web_intelligence import web_search
    results = web_search(query)
    return results[:3000] if isinstance(results, str) else json.dumps(results)[:3000]


def _tool_read_file(args: str | dict) -> str:
    """Read file contents. Accepts 'path', 'line_start', and 'line_end'."""
    path = args.get("path", "") if isinstance(args, dict) else args
    
    line_start = args.get("line_start") if isinstance(args, dict) else None
    line_end = args.get("line_end") if isinstance(args, dict) else None
    
    from skills.shell_executor.executor import read_file
    if not is_safe_path(path):
        return f"BLOCKED: Path traversal attempt detected: {path}"
    content = read_file(path)
    
    if line_start is not None and line_end is not None:
        try:
            start = int(line_start) - 1
            end = int(line_end)
            lines = content.splitlines()
            return "\n".join(lines[start:end])
        except (ValueError, TypeError):
            pass

    return content[:8000]


def _verify_python_syntax(path: str) -> str:
    """Run py_compile on a Python file. Returns empty string on success, error message on failure."""
    if not path.endswith('.py'):
        return ""
    import py_compile, traceback
    try:
        py_compile.compile(path, doraise=True)
        return ""
    except py_compile.PyCompileError as e:
        return f"\n⚠️ SYNTAX ERROR in {path}: {e}"
    except Exception as e:
        return f"\n⚠️ Compile check failed: {e}"


def _tool_write_file(args: str | dict) -> str:
    """Write content to a file. Requires JSON dict {path, content}."""
    if not isinstance(args, dict):
        return "ERROR: write_file requires a JSON dictionary with 'path' and 'content'."
    path = args.get("path", "")
    content = args.get("content", "")
    if not is_safe_path(path):
        return f"BLOCKED: Path traversal attempt detected: {path}"
        
    from core.anesthesia import Anesthesia
    with Anesthesia():
        try:
            if os.path.dirname(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            # ── VERIFY: Read back + syntax check ──────────────────
            with open(path, "r") as f:
                written = f.read()
            char_count = len(written)
            syntax_result = _verify_python_syntax(path)
            if syntax_result:
                return f"File written ({char_count} chars): {path}{syntax_result}"
            return f"File written and verified ({char_count} chars): {path}"
        except Exception as e:
            return f"FAILED to write {path}: {e}"


def _tool_edit_file(args: str | dict) -> str:
    """Edit a file. Requires JSON dict {filepath, old_text, new_text}."""
    if not isinstance(args, dict):
        return "ERROR: edit_file requires a JSON dictionary with 'filepath', 'old_text', and 'new_text'."
    filepath = args.get("filepath", "")
    old_text = args.get("old_text", "")
    new_text = args.get("new_text", "")
    if not is_safe_path(filepath):
        return f"BLOCKED: Path traversal attempt detected: {filepath}"
    if not os.path.exists(filepath):
        return f"File not found: {filepath}"
    
    from core.anesthesia import Anesthesia
    with Anesthesia():
        with open(filepath, "r") as f:
            content = f.read()
        if old_text not in content:
            return f"Target text not found in {filepath}. Read the file first."
        content = content.replace(old_text, new_text, 1)
        with open(filepath, "w") as f:
            f.write(content)
        log_audit("TOOL", f"Edited file: {filepath}")
        # ── VERIFY: Read back confirming change + syntax check ─────
        with open(filepath, "r") as f:
            final = f.read()
        if new_text not in final:
            return f"ERROR: Edit applied but verification FAILED — new text not found in {filepath}!"
        syntax_result = _verify_python_syntax(filepath)
        if syntax_result:
            return f"File edited: {filepath}{syntax_result}"
        return f"SUCCESS: File edited and verified: {filepath}"


def _tool_surgical_edit(args: str | dict) -> str:
    """Use Sovereign OT (Operational Transformation) to edit a Python file safely."""
    if not isinstance(args, dict):
        return "ERROR: surgical_edit requires JSON {filepath, symbol_name, new_code}."
    
    filepath = args.get("filepath", "")
    symbol_name = args.get("symbol_name", "")
    new_code = args.get("new_code", "")
    test_script = args.get("test_script", "")
    
    # Strip the leading slash if the AI gives an absolute path starting from PROJECT_ROOT
    if filepath.startswith(config.PROJECT_ROOT):
        tgt_rel = os.path.relpath(filepath, config.PROJECT_ROOT)
    else:
        tgt_rel = filepath.lstrip("/")

    from core.anesthesia import Anesthesia
    with Anesthesia():
        from core.surgeon import perform_surgery
        success = perform_surgery(tgt_rel, symbol_name, new_code, test_script=test_script if test_script else None)
        
        if success:
            log_audit("SURGEON", f"OT Surgery Successful on {tgt_rel} ({symbol_name})")
            return f"SUCCESS: Surgery applied cleanly to {tgt_rel}. Tests passed in sandbox."
        else:
            log_audit("SURGEON", f"OT Surgery FAILED on {tgt_rel} ({symbol_name})")
            return f"ERROR: Sandbox surgery failed for {tgt_rel}. The change was aborted and rolled back. Check the AST syntax and your tests."


async def _tool_memory_recall(args: str | dict) -> str:
    """Search past memories."""
    topic = args.get("topic", "") if isinstance(args, dict) else args
    from core.memory_manager import SovereignMemory
    return await SovereignMemory.recall(topic, limit=3)


def _tool_list_skills(args: str | dict) -> str:
    """Show all skills."""
    from skills.skill_registry import list_skills
    return list_skills()


def _tool_todos(args: str | dict) -> str:
    """View TODOs."""
    todo_path = config.TODO_PATH
    if os.path.exists(todo_path):
        with open(todo_path, "r") as f:
            return f.read()[:3000] or "No TODOs."
    return "No TODOs file found."


def _tool_create_skill(args: str | dict) -> str:
    """Create a new skill. Requires JSON dict {skill_name, description, code}."""
    if not isinstance(args, dict):
        return "ERROR: create_skill requires a JSON dictionary."
    skill_name = args.get("skill_name", "").strip().replace(" ", "_").lower()
    description = args.get("description", "")
    code = args.get("code", "")

    skill_dir = os.path.join(config.SKILLS_DIR, skill_name)
    if os.path.exists(skill_dir):
        return f"Skill '{skill_name}' already exists. Use edit_file to modify it."
    os.makedirs(skill_dir, exist_ok=True)

    skill_md = f"---\nname: {skill_name}\ndescription: \"{description}\"\nentry_point: {skill_name}.py\n---\n\n# {skill_name.replace('_', ' ').title()} Skill\n\n{description}\n"
    with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
        f.write(skill_md)
    with open(os.path.join(skill_dir, "__init__.py"), "w") as f:
        f.write(f"# {skill_name} skill\n")
    with open(os.path.join(skill_dir, f"{skill_name}.py"), "w") as f:
        f.write(code)

    log_audit("TOOL", f"Created new skill: {skill_name}")
    return f"SUCCESS: Skill '{skill_name}' created at {skill_dir}"


async def _tool_list_files(args: str | dict) -> str:
    """List files in a directory."""
    directory = args.get("directory", "") if isinstance(args, dict) else args
    from skills.shell_executor.executor import execute
    result = await execute(f"find {directory} -type f -maxdepth 2 | head -30", timeout=10)
    return result.get("stdout", "No files found.")[:3000]


async def _tool_episode_recall(args: str | dict) -> str:
    """Search episodic memory for past events."""
    query = args.get("query", "") if isinstance(args, dict) else args
    from core.memory_manager import SovereignMemory
    return await SovereignMemory.recall(query, limit=5)


async def _tool_procedure_recall(args: str | dict) -> str:
    """Recall learned action patterns."""
    situation = args.get("situation", "") if isinstance(args, dict) else args
    from core.memory_manager import SovereignMemory
    # Fallback to skills.memory for now as SovereignMemory doesn't have procedural yet
    from skills.memory.procedural import recall_procedures
    procs = recall_procedures(situation, limit=3)
    if not procs:
        return "No matching procedures found."
    return "\n".join(
        f"- [{p['success_rate']:.0%}] {p['trigger'][:60]} -> {', '.join(p['action_chain'][:3])}"
        for p in procs
    )


async def _tool_spawn_agents(args: str | dict) -> str:
    """Decompose a task into parallel sub-agents. Redirects to sub_agent_manager."""
    from skills.sub_agent_manager.manager import spawn_subagent
    try:
        if not isinstance(args, dict):
            return "ERROR: spawn_agents requires a JSON dictionary with 'task' and 'roles'."
        task = args.get("task", "")
        roles_str = args.get("roles", "")
        roles = [r.strip() for r in roles_str.split(",")] if roles_str else ["Explorer", "Reviewer"]
        
        results = []
        for role in roles:
            name = f"{role}_{os.urandom(2).hex()}"
            res = await spawn_subagent(name, f"Expert in {role} for task: {task}")
            results.append(res)
        
        return "Spawned parallel workforce:\n" + "\n".join(results)
    except Exception as e:
        return f"Redirected spawning failed: {e}"


def _tool_run_workflow(args: str | dict) -> str:
    """Execute a named YAML workflow."""
    workflow_name = args.get("workflow_name", "") if isinstance(args, dict) else str(args).strip()
    from core.workflow_engine import run_workflow
    result = run_workflow(workflow_name)
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        return f"Workflow '{workflow_name}' failed: {error}"
    lines = [f"Workflow '{result['name']}' completed successfully:"]
    for step_name, step_result in result.get("results", {}).items():
        status = "OK" if step_result.get("success") else "FAIL"
        output = step_result.get("output", "")[:200]
        lines.append(f"  {status} {step_name}: {output}")
    return "\n".join(lines)


def _tool_list_workflows(args: str | dict) -> str:
    """List available YAML workflows."""
    from core.workflow_engine import list_workflows
    return list_workflows()


def _tool_session_stats(args: str | dict) -> str:
    """Show session observability stats."""
    try:
        from core.observability import format_stats
        return format_stats()
    except Exception as e:
        return f"Stats unavailable: {e}"

# ─── Job Management ───────────────────────────────────────

def _tool_spawn_job(args: str | dict) -> str:
    """Run a long-running shell command in the background (Non-Blocking)."""
    if isinstance(args, dict):
        command = args.get("command", "")
        name = args.get("name", "background_job")
    else:
        command = str(args)
        name = "background_job"
    
    from core.job_manager import manager
    job_id = manager.spawn_job(command, name)
    if job_id.startswith("ERROR"):
        return job_id
    return f"SUCCESS: Job spawned. ID: {job_id}. Use get_job_output('{job_id}') to check status."

def _tool_list_jobs(args: str | dict) -> str:
    """List all background jobs and their statuses."""
    from core.job_manager import manager
    jobs = manager.list_jobs()
    if not jobs:
        return "No background jobs running."
    lines = ["📋 Background Jobs:"]
    for j in jobs:
        lines.append(f"  [{j['job_id']}] {j['name']} - {j['status']} | {j['command'][:40]}...")
    return "\n".join(lines)

def _tool_get_job_output(args: str | dict) -> str:
    """Get output from a background job."""
    job_id = args.get("job_id", "") if isinstance(args, dict) else str(args).strip()
    from core.job_manager import manager
    job = manager.get_job(job_id)
    if not job:
        return f"Job {job_id} not found."
    
    out = "\n".join(job.stdout[-50:])
    err = "\n".join(job.stderr[-20:])
    report = f"Job: {job.name} ({job.job_id})\nStatus: {job.status}\nCommand: {job.command}\n\nSTDOUT (last 50 lines):\n{out}\n"
    if err:
        report += f"\nSTDERR:\n{err}"
    return report

def _tool_kill_job(args: str | dict) -> str:
    """Terminate a running background job."""
    job_id = args.get("job_id", "") if isinstance(args, dict) else str(args).strip()
    from core.job_manager import manager
    if manager.kill_job(job_id):
        return f"SUCCESS: Job {job_id} terminated."
    return f"FAILED: Could not terminate job {job_id}."

def _tool_generate_key(args: str | dict) -> str:
    """Generate a new Sovereign API Key."""
    reason = args.get("reason", "External Access") if isinstance(args, dict) else "External Access"
    from core.auth import generate_api_key
    key = generate_api_key()
    try:
        from core.state_manager import get_state_manager
        sm = get_state_manager()
        state = sm.get_state()
        keys = state.get("api_keys", [])
        keys.append(key)
        state["api_keys"] = keys
        sm.save_state()
        return f"🔑 New Key: {key}\nReason: {reason}"
    except Exception as e:
        return f"Error: {e}"

def _tool_vcs_history(args: str | dict) -> str:
    """Show internal VCS history."""
    path = args.get("path") if isinstance(args, dict) else None
    from core.vcs import get_vcs
    history = get_vcs().list_history(path)
    return json.dumps(history, indent=2)

def _tool_code_inspector(args: str | dict) -> str:
    """Surgical AST-based code vision."""
    path = args.get("path", "") if isinstance(args, dict) else ""
    node_name = args.get("node", "") if isinstance(args, dict) else ""
    import ast
    full_path = os.path.join(config.PROJECT_ROOT, path)
    if not os.path.exists(full_path): return f"File {path} not found."
    try:
        with open(full_path, "r", encoding="utf-8") as f: source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.name == node_name:
                return "\n".join(source.splitlines()[node.lineno-1:node.end_lineno])
        return f"Node {node_name} not found."
    except Exception as e: return str(e)


# ── Codebase Intelligence Tools (Phase B/C/D) ────────────────

def _tool_investigate(args: str | dict) -> str:
    """Deep codebase investigation via grep, symbol finder, import tracer, or architecture report."""
    query = args.get("query", "") if isinstance(args, dict) else str(args)
    try:
        from skills.codebase_investigator.investigator import investigate
        return investigate(query)
    except Exception as e:
        return f"Investigation failed: {e}"


def _tool_grep_codebase(args: str | dict) -> str:
    """Search the entire codebase with a regex pattern."""
    if isinstance(args, dict):
        pattern = args.get("pattern", "")
        path = args.get("path", None)
    else:
        pattern = str(args)
        path = None
    try:
        from skills.codebase_investigator.investigator import grep
        return grep(pattern, path)
    except Exception as e:
        return f"grep failed: {e}"


def _tool_find_symbol(args: str | dict) -> str:
    """Find all definitions and call sites of a symbol across the codebase."""
    name = args.get("name", "") if isinstance(args, dict) else str(args)
    try:
        from skills.codebase_investigator.investigator import find_symbol
        return find_symbol(name)
    except Exception as e:
        return f"find_symbol failed: {e}"


def _tool_run_module_check(args: str | dict) -> str:
    """
    Verify a Python file can be imported with no errors.
    Catches syntax errors, missing dependencies, and import-time exceptions.
    """
    path = args.get("path", "") if isinstance(args, dict) else str(args)
    if not os.path.isabs(path):
        path = os.path.join(config.PROJECT_ROOT, path)
    if not os.path.exists(path):
        return f"File not found: {path}"
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", path],
        capture_output=True, text=True, timeout=15,
        cwd=config.PROJECT_ROOT
    )
    if result.returncode == 0:
        return f"✅ Syntax OK: {path}"
    else:
        err = result.stderr.strip() or result.stdout.strip()
        return f"❌ Syntax error in {path}:\n{err}"


def _tool_run_tests(args: str | dict) -> str:
    """Run all tests or a specific test file. Returns structured pass/fail output."""
    path = args.get("path", "tests/") if isinstance(args, dict) else str(args)
    if not os.path.isabs(path):
        from settings import settings as config
        path = os.path.join(config.PROJECT_ROOT, path)
    import subprocess, sys
    try:
        # Use pytest if available, fallback to unittest
        cmd = [sys.executable, "-m", "pytest", "-v", path] if __import__("util.find_spec")("pytest") else [sys.executable, "-m", "unittest", "discover", "-v", "-s", path if os.path.isdir(path) else os.path.dirname(path), "-p", os.path.basename(path) if not os.path.isdir(path) else "test*.py"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=config.PROJECT_ROOT)
        out = result.stdout + "\n" + result.stderr
        return f"--- TEST RESULTS ---\n{out[:4000]}"
    except Exception as e:
        return f"Test runner failed: {e}"


def _tool_find_files(args: str | dict) -> str:
    """Find files in the codebase by name pattern or extension."""
    if isinstance(args, dict):
        pattern = args.get("pattern", "*")
        ext = args.get("extension", "")
    else:
        pattern = str(args)
        ext = ""
    
    from settings import settings as config
    from pathlib import Path
    from core.utils import is_safe_path
    
    root = Path(config.PROJECT_ROOT)
    if not is_safe_path(str(root)):
        return "BLOCKED: Invalid root directory."
        
    results = []
    glob_pat = f"**/{pattern}"
    if ext:
        if not ext.startswith("."): ext = "." + ext
        glob_pat += ext
    
    for p in root.rglob(glob_pat):
        if "__pycache__" in str(p) or ".git" in str(p): continue
        try:
            results.append(str(p.relative_to(root)))
        except ValueError:
            results.append(str(p))
        if len(results) >= 100:
            return "\n".join(results) + "\n(Limit of 100 files reached)"
    
    return "\n".join(results) if results else "No files found matching criteria."


def _tool_run_self_audit(args: str | dict) -> str:
    """Legacy tool. Now handled by the 'Reviewer' and 'Validator' agents."""
    return "This tool is deprecated. Please ask the 'Reviewer' agent to perform an audit using codebase tools."


async def _tool_query_knowledge_graph(args: str | dict) -> str:
    """Query ASURA's architectural knowledge graph."""
    query = args.get("query", "") if isinstance(args, dict) else str(args)
    from core.knowledge_graph import knowledge_graph
    
    # Simple search for now
    nodes = [n for n in knowledge_graph.nodes.values() if query.lower() in n["id"].lower() or query.lower() in n["type"].lower()]
    if not nodes: return f"No nodes found matching '{query}'."
    
    report = ["🔍 Knowledge Graph Results:"]
    for n in nodes[:10]:
        status = "🟢" if n["health"] > 80 else "🟡" if n["health"] > 40 else "🔴"
        report.append(f"  {status} [{n['type'].upper()}] {n['id']} (Health: {n['health']}%)")
    
    return "\n".join(report)


async def _tool_run_system_health_probe(args: str | dict) -> str:
    """Trigger a full system-wide architectural health check."""
    from core.knowledge_scanner import knowledge_scanner
    await knowledge_scanner.scan_all()
    return "✅ Full system health probe and architectural scan complete. Results updated in Knowledge Graph."


async def _tool_remember_fact(args: str | dict) -> str:
    """Store a permanent fact in the Sovereign Vault."""
    if isinstance(args, dict):
        fact = args.get("fact", "")
        category = args.get("category", "permanent_facts")
    else:
        fact = str(args)
        category = "permanent_facts"
    
    from core.memory_manager import SovereignMemory
    return await SovereignMemory.remember_fact(fact, category)


# Auto-register built-in tools
# ============================================================
def _register_builtins():
    """Register all built-in tools on import."""
    tools = [
        ("shell", _tool_shell, "Run shell command", {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}),
        ("system_info", _tool_system_info, "Get CPU/RAM/disk info", {"type": "object", "properties": {"arg": {"type": "string"}}, "required": []}),
        ("screenshot", _tool_screenshot, "Capture a screenshot of the current system screen", {"type": "object", "properties": {}, "required": []}),
        ("browse", _tool_browse, "Read a URL", {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}),
        ("web_search", _tool_web_search, "Search the web", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        ("read_file", _tool_read_file, "Read file contents with optional line boundaries", {"type": "object", "properties": {"path": {"type": "string"}, "line_start": {"type": "integer"}, "line_end": {"type": "integer"}}, "required": ["path"]}),
        ("write_file", _tool_write_file, "Write a file", {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}),
        ("edit_file", _tool_edit_file, "Edit a file (direct string replacement). Prefer surgical_edit for code.", {"type": "object", "properties": {"filepath": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["filepath", "old_text", "new_text"]}),
        ("surgical_edit", _tool_surgical_edit, "Edit a Python file using the Sovereign OT Sandbox. Pre-tests AST and executes tests before saving.", {"type": "object", "properties": {"filepath": {"type": "string"}, "symbol_name": {"type": "string"}, "new_code": {"type": "string"}, "test_script": {"type": "string"}}, "required": ["filepath", "symbol_name", "new_code"]}),
        ("memory_recall", _tool_memory_recall, "Search past memories", {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]}),
        ("list_skills", _tool_list_skills, "Show all skills", {"type": "object", "properties": {}, "required": []}),
        ("todos", _tool_todos, "View TODOs", {"type": "object", "properties": {}, "required": []}),
        ("create_skill", _tool_create_skill, "Create a new skill", {"type": "object", "properties": {"skill_name": {"type": "string"}, "description": {"type": "string"}, "code": {"type": "string"}}, "required": ["skill_name", "description", "code"]}),
        ("list_files", _tool_list_files, "List files in directory", {"type": "object", "properties": {"directory": {"type": "string"}}, "required": ["directory"]}),
        ("episode_recall", _tool_episode_recall, "Search episodic memory for past events", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        ("procedure_recall", _tool_procedure_recall, "Recall learned action patterns", {"type": "object", "properties": {"situation": {"type": "string"}}, "required": ["situation"]}),
        ("spawn_agents", _tool_spawn_agents, "Decompose a complex task into parallel sub-agents (researcher, implementer, reviewer)", {"type": "object", "properties": {"task": {"type": "string"}, "roles": {"type": "string"}}, "required": ["task"]}),
        ("run_workflow", _tool_run_workflow, "Execute a named YAML workflow (e.g., health_check, backup)", {"type": "object", "properties": {"workflow_name": {"type": "string"}}, "required": ["workflow_name"]}),
        ("list_workflows", _tool_list_workflows, "List available automated workflows", {"type": "object", "properties": {}, "required": []}),
        ("session_stats", lambda _: _tool_session_stats(_), "Show tool execution stats, timing, and token estimates", {"type": "object", "properties": {}, "required": []}),
        ("spawn_job", _tool_spawn_job, "Run a command in the background", {"type": "object", "properties": {"command": {"type": "string"}, "name": {"type": "string"}}, "required": ["command"]}),
        ("list_jobs", _tool_list_jobs, "List all background jobs", {}),
        ("get_job_output", _tool_get_job_output, "Get job output", {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}),
        ("kill_job", _tool_kill_job, "Kill a background job", {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}),
        ("generate_key", _tool_generate_key, "Generate Sovereign API Key", {"type": "object", "properties": {"reason": {"type": "string"}}, "required": []}),
        ("vcs_history", _tool_vcs_history, "Show VCS history", {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}),
        ("code_inspector", _tool_code_inspector, "Surgical code vision", {"type": "object", "properties": {"path": {"type": "string"}, "node": {"type": "string"}}, "required": ["path", "node"]}),
        ("create_transient_tool", lambda args: __import__("skills.dynamic_tools", fromlist=["create_transient_tool"]).create_transient_tool(args.get("name"), args.get("code"), args.get("description")), "ASURA Zero: Create a temporary tool for complex one-off tasks.", {"type": "object", "properties": {"name": {"type": "string"}, "code": {"type": "string"}, "description": {"type": "string"}}, "required": ["name", "code", "description"]}),
        ("send_telegram_msg", lambda args: __import__("skills.telegram_comm", fromlist=["send_message"]).send_message(args.get("text")), "Proactively send a message to the Master.", {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
        # ── Codebase Intelligence (Phase B/C/D) ──────────────────────────────────
        ("investigate", _tool_investigate, "Deep codebase investigation: grep, symbol search, architecture report, issue detection. Query formats: 'grep:<pattern>', 'find:<symbol>', 'imports:<file>', 'architecture', 'issues'", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        ("grep_codebase", _tool_grep_codebase, "Search the entire codebase with a regex pattern. Returns file:line matches.", {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]}),
        ("find_symbol", _tool_find_symbol, "Find all definitions and call sites of a function, class, or variable across the codebase.", {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}),
        ("run_module_check", _tool_run_module_check, "Verify a Python module imports correctly (catches syntax errors, missing deps). Pass module path like 'src/skills/foo/bar.py'", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}),
        ("run_tests", _tool_run_tests, "Autonomous test runner. Runs pytest or unittest on a directory or file.", {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}),
        ("find_files", _tool_find_files, "Find files in the codebase by name pattern or extension.", {"type": "object", "properties": {"pattern": {"type": "string"}, "extension": {"type": "string"}}, "required": []}),
        ("run_self_audit", _tool_run_self_audit, "Autonomous code quality and security audit. Scope: all|core|skills|security.", {"type": "object", "properties": {"scope": {"type": "string"}}, "required": []}),
        ("remember_fact", _tool_remember_fact, "Permanently store a fact about the Master or a specific directive in the Sovereign Vault.", {"type": "object", "properties": {"fact": {"type": "string"}, "category": {"type": "string"}}, "required": ["fact"]}),
        ("browser_screenshot", _tool_browser_snapshot, "Take a screenshot of a URL. Returns the file path.", {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}),
        ("analyze_image", _tool_analyze_image, "Analyze an image or screenshot. Specify 'path' to the image and a 'question'.", {"type": "object", "properties": {"path": {"type": "string"}, "question": {"type": "string"}}, "required": ["path", "question"]}),
        ("query_knowledge_graph", _tool_query_knowledge_graph, "Consult ASURA's architectural self-knowledge. Query by name or type.", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        ("run_system_health_probe", _tool_run_system_health_probe, "Trigger ASURA to perform a self-audit of all code and agents. High-cost operation.", {"type": "object", "properties": {}, "required": []}),
        ("send_telegram_message", lambda args: __import__("skills.telegram_bot", fromlist=["send_telegram_message"]).send_telegram_message(args), "Send a message, report, or interactive menu [Choice 1] | [Choice 2] to the Master's Telegram.", {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
    ]

    for name, fn, desc, params in tools:
        register_tool(name, fn, desc, params)

    log_audit("MCP", f"Registered {len(_registry)} tools")


# Auto-register on import
_register_builtins()

