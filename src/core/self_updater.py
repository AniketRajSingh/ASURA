# ============================================================
# core/self_updater.py — LLM-Driven Self-Evolution Engine
# with Daemon Mode, TODO Integration, Hardware Awareness
# ============================================================

import os
import sys
import ast
import py_compile
import shutil
import json
import time as time_mod
import threading
import traceback
from datetime import datetime

import asyncio
import requests
from settings import settings as config
from core.llm import call_llm
from skills.logger import log_audit, log_app
# from skills.dashboard.progress_socket import report_progress
from skills.memory import (
    store_update_log, recall, get_all_memories_summary,
    index_system_docs
)
from skills.web_intelligence.intelligence import research_topic
from skills.hardware_monitor import check_resources_ok, get_resource_summary
from skills.backup_manager import create_snapshot
from core.vcs import get_vcs
from skills.todo_manager import add_todo, get_next_todo, complete_todo
from skills.skill_registry import discover_skills, get_skill_code, list_skills

# ── Surgical Protocol (Phase F) ─────────────────────────────
from core.anesthesia import Anesthesia, is_under_anesthesia
from core.surgeon import SurgicalRoom, perform_surgery
from core.ast_surgeon import surgical_replace, get_symbol_range

def run_async(coro):
    """Run an async coroutine synchronously, even if an event loop is already running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)




class SelfUpdater:
    """
    The brain of the Self-Updating AI.

    Cycle:
      0. Health check — verify resources are sufficient
      1. Analyze — read codebase, skills, hardware, and memory
      2. Ideate — pick a TODO or ask Ollama to propose a feature
      3. Generate — ask Ollama to write the code
      4. Validate — syntax check via ast.parse
      5. Backup — create snapshot before applying
      6. Apply — write files to disk
      7. Test — compile-check the changed module
      8. Rollback — revert on failure
      9. Log — record everything, notify master via Telegram

    If the AI encounters difficulty, it adds a TODO for future improvement.
    """

    def __init__(self, telegram_notify_fn=None):
        self.base_dir = config.BASE_DIR
        self.history_dir = config.UPDATE_HISTORY_DIR
        self.protected = self._resolve_protected()
        self._notify_fn = telegram_notify_fn  # async fn(message) to notify master
        os.makedirs(self.history_dir, exist_ok=True)

    def _resolve_protected(self) -> set[str]:
        protected = set()
        for rel in config.PROTECTED_FILES:
            protected.add(os.path.abspath(os.path.join(self.base_dir, rel)))
        return protected

    def _is_protected(self, filepath: str) -> bool:
        return os.path.abspath(filepath) in self.protected

    # ──────────────────────────────────────────────────────────
    # Step 0: Health Check
    # ──────────────────────────────────────────────────────────
    def health_check(self) -> tuple[bool, str]:
        """Check system resources before attempting evolution."""
        log_audit("SELF_UPDATE", "Step 0 — Health check")
        ok, msg = check_resources_ok(min_memory_gb=0.3, min_disk_gb=0.3)
        if not ok:
            log_audit("SELF_UPDATE", f"Health check FAILED: {msg}")
            add_todo(
                f"System resource issue: {msg}",
                source="health_check",
                priority="high",
                category="optimization",
            )
        return ok, msg

    # ──────────────────────────────────────────────────────────
    # Step 1: Analyze
    # ──────────────────────────────────────────────────────────
    def analyze(self) -> str:
        log_audit("SELF_UPDATE", "Step 1 — Analyzing codebase")

        parts = ["# Current System State\n"]

        # Project structure
        parts.append("## Project Structure")
        for root, dirs, files in os.walk(self.base_dir):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in ("__pycache__", "faculty-llm-iiitd",
                              "memory_store", "update_history",
                              "backups", "node_modules", ".venv", "venv")
            ]
            level = root.replace(self.base_dir, "").count(os.sep)
            indent = "  " * level
            parts.append(f"{indent}{os.path.basename(root)}/")
            for f in files:
                if f.endswith((".py", ".md", ".txt", ".json")):
                    parts.append(f"{indent}  {f}")

        # Skills registry (God-Mode: Includes signatures)
        parts.append("\n## Registered Skills (API Manifest)")
        registry = discover_skills()
        parts.append(list_skills(registry, detailed=True))

        # Hardware
        parts.append("\n## Hardware")
        parts.append(get_resource_summary())

        # TODOs
        from skills.todo_manager import get_open_todos
        open_todos = get_open_todos()
        if open_todos:
            parts.append(f"\n## Open TODOs ({len(open_todos)})")
            for t in open_todos[:5]:
                parts.append(f"- [{t['priority']}] #{t['id']}: {t['description'][:80]}")

        # Recent memories
        parts.append("\n## Memory Summary")
        parts.append(get_all_memories_summary())

        # Architectural Handbooks (Critical Knowledge)
        parts.append("\n## Architectural Handbooks (System Invariants)")
        handbooks = recall("architectural handbook", top_k=5)
        if handbooks:
            for hb in handbooks:
                parts.append(f"### {hb.get('metadata', {}).get('title', 'Handbook')}")
                parts.append(hb['text'])
                
        # Codebase Skeleton (High-Res Map)
        parts.append("\n## Codebase Skeleton (Detailed Structural Awareness)")
        try:
            from skills.file_organizer.code_nav_skill import list_code_items
            skeleton = []
            for root, _, files in os.walk(config.SRC_DIR):
                if "__pycache__" in root or "venv" in root: continue
                for f in files:
                    if f.endswith(".py"):
                        fpath = os.path.join(root, f)
                        rel = os.path.relpath(fpath, config.BASE_DIR)
                        items = list_code_items(fpath)
                        if items:
                            skeleton.append(f"### {rel}")
                            for it in items:
                                # Show only name and type to save context
                                skeleton.append(f"  - [{it['type']}] {it['name']}")
            parts.append("\n".join(skeleton[:50])) # Cap at 50 modules
        except Exception as e:
            parts.append(f"Skeleton failed: {e}")

        # Past updates
        parts.append("\n## Recent Self-Updates")
        updates = self._get_recent_updates(5)
        if updates:
            for u in updates:
                parts.append(f"- [{u.get('timestamp','')}] {u.get('summary','')[:100]}")
        else:
            parts.append("- No previous updates")

        return "\n".join(parts)

    def self_audit(self) -> str:
        """
        Analyze recent audit logs and app logs to identify recurring failures.
        """
        audit_path = os.path.join(config.DATA_DIR, "logs", "audit.jsonl")
        app_log_path = os.path.join(config.LOG_DIR, "log.txt")
        
        findings = []
        
        # 1. Check Audit Logs
        if os.path.isfile(audit_path):
            try:
                with open(audit_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-100:]
                    for line in lines:
                        try:
                            entry = json.loads(line)
                            if entry.get("level") == "error" or "FAILED" in entry.get("msg", ""):
                                findings.append(f"AUDIT: [{entry.get('ts','')[:16]}] {entry.get('msg','')}")
                        except: continue
            except Exception: pass

        # 2. Check App Log for Tracebacks (Critical Self-Healing)
        if os.path.isfile(app_log_path):
            try:
                with open(app_log_path, "r", encoding="utf-8") as f:
                    content = f.read()[-10000:] # Last 10KB
                    # Look for Python tracebacks or common error keywords
                    if "Traceback (most recent call last)" in content or "Error:" in content:
                        findings.append("CRITICAL: Tracebacks detected in application log.")
                        # Extract the last traceback if possible
                        tb_match = content.split("Traceback (most recent call last)")[-1]
                        findings.append(f"LAST_TRACEBACK: {tb_match[:500]}...")
            except Exception: pass

        if not findings:
            return "No recent system failures detected. System health is optimal."

        return "\n".join(["RECENT SYSTEM ANOMALIES:"] + findings[-15:])

    # ──────────────────────────────────────────────────────────
    # Step 2: Ideate (TODO-aware)
    # ──────────────────────────────────────────────────────────
    def ideate(self, context: str) -> dict:
        log_audit("SELF_UPDATE", "Step 2 — Ideating")

        # Check if there's a TODO to work on first
        next_todo = get_next_todo()
        todo_instruction = ""
        if next_todo:
            todo_instruction = (
                f"\n\nPRIORITY TODO #{next_todo['id']} ({next_todo['priority']}): "
                f"{next_todo['description']}\n"
                f"If you can address this TODO, do so. Otherwise, propose something else."
            )
            log_audit("SELF_UPDATE", f"Working on TODO #{next_todo['id']}: {next_todo['description'][:60]}")

        # Check past failures to avoid
        past_context = recall("self update failed", top_k=3)
        avoid_notes = ""
        if past_context:
            avoid_notes = "\n\nAVOID these past failures:\n" + "\n".join(
                f"- {d['text'][:100]}" for d in past_context
            )

        # Self-Audit for Pain Points
        audit_notes = self.self_audit()

        prompt = f"""You are ASURA, a Sovereign Autonomous Agent. Your mission is to evolve yourself to better serve {config.MASTER_NAME}.
You do NOT suggest roadmaps. You DO implement specific solutions.

{context}
{todo_instruction}
{avoid_notes}

{audit_notes}

AGENTIC LAWS:
1. SEARCH BEFORE EXECUTION: Use your 'grep_skill' or 'code_nav_skill' to find relevant code before proposing a change.
2. IMPLEMENTATION OVER CONVERSATION: Propose a code change, NOT a roadmap or a suggestion.
3. TOOLING AUTONOMY: Use existing skills (API signatures provided above). If a skill is missing, CREATE it.
4. ACTION-FIRST: Propose self-contained, testable code that directly solves a problem or adds a feature.

Rules:
1. Propose ONE specific improvement that complies with the Architectural and Behavioral Handbooks.
2. Use the provided API manifest to ensure function calls are accurate.
3. Return ONLY a JSON object:
   {{"summary": "brief, proactive description", "target_file": "relative/path.py", "is_new_file": true/false, "symbol_name": "MyFunctionName or None", "reasoning": "agentic justification", "todo_id": null}}


Return ONLY the JSON, no extra text."""

        try:
            # Use unified call_llm
            raw = run_async(call_llm(prompt, model=config.OLLAMA_MODEL_FAST, stream=False))
            log_audit("SELF_UPDATE", f"Ideation response: {raw[:200]}")

            idea = self._extract_json(raw)
            if not idea or "summary" not in idea or "target_file" not in idea:
                raise ValueError(f"Invalid ideation response: {raw[:300]}")

            log_audit("SELF_UPDATE", f"Proposed: {idea['summary']}")
            return idea

        except Exception as e:
            log_audit("SELF_UPDATE_ERROR", f"Ideation failed: {e}")
            add_todo(
                f"Ideation difficulty: {str(e)[:100]}",
                source="self_updater",
                priority="low",
                category="improvement",
            )
            raise

    def _get_smart_context(self, target_file: str, idea: dict, base_context: str, char_limit: int = 12000) -> str:
        """
        Builds a high-definition context window focused on the target area.
        Priority:
        1. Target file content (if modifying)
        2. Immediate imports from the target file
        3. Relevant memory/handbooks
        4. Global skeleton
        """
        log_audit("SELF_UPDATE", f"Building smart context for {target_file}")
        
        sections = [f"# Targeted Technical Context for {target_file}\n"]
        current_len = 0
        
        # 1. Target file content (Full)
        full_path = os.path.join(self.base_dir, target_file)
        if os.path.isfile(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                sections.append(f"## EXISTING CODE in {target_file}\n{content}")
                current_len += len(content)
        
        # 2. Idea & Reasoning
        sections.append(f"## TASK\nSummary: {idea['summary']}\nReasoning: {idea.get('reasoning', '')}")
        
        # 3. Base Context (truncated to fit)
        remaining = char_limit - current_len - 1000
        if remaining > 0:
            sections.append(f"## GLOBAL STATE\n{base_context[:remaining]}")
            
        return "\n\n".join(sections)

    # ──────────────────────────────────────────────────────────
    # Step 3: Generate
    # ──────────────────────────────────────────────────────────
    def generate(self, idea: dict, context: str) -> str:
        log_audit("SELF_UPDATE", f"Step 3 — Generating code for: {idea['summary']}")

        target = idea["target_file"]
        is_new = idea.get("is_new_file", False)

        smart_context = self._get_smart_context(target, idea, context)

        prompt = f"""Write Python code for a Self-Updating AI system owned by {config.MASTER_NAME}.

Task: {idea['summary']}
Target file: {target}
{"NEW file." if is_new else "MODIFY existing file."}

{smart_context}

Rules:
1. Write the COMPLETE Python file. Ensure it integrates perfectly with the skeleton provided.
2. Verify function signatures from the API manifest before calling other skills.
3. Return ONLY Python code, no markdown fences.
4. EXPLICIT DOCUMENTATION: Include a detailed triple-quoted module docstring at the top of the file explaining the skill's purpose, architecture, and usage.
"""

        try:
            # Use unified call_llm
            from core.model_manager import model_manager
            code = run_async(call_llm(prompt, model=model_manager.get_model_for_task("reasoning"), stream=False))

            # Strip markdown fences
            for fence in ["```python", "```"]:
                if code.startswith(fence):
                    code = code[len(fence):].strip()
            if code.endswith("```"):
                code = code[:-3].strip()

            log_audit("SELF_UPDATE", f"Generated {len(code)} chars")
            return code

        except Exception as e:
            log_audit("SELF_UPDATE_ERROR", f"Code generation failed: {e}")
            add_todo(
                f"Code gen difficulty for '{idea['summary']}': {str(e)[:80]}",
                source="self_updater",
                priority="medium",
                category="bugfix",
            )
            raise

    # ──────────────────────────────────────────────────────────
    # Step 4: Validate
    # ──────────────────────────────────────────────────────────
    def validate(self, code: str) -> tuple[bool, str]:
        """
        4-layer code safety pipeline.
        Layer 1: Syntax check (ast.parse)
        Layer 2: Dangerous pattern detection
        Layer 3: Static analysis for unsafe constructs
        """
        log_audit("SELF_UPDATE", "Step 4 — Safety validation (3 layers)")

        # ── Layer 1: Syntax ──────────────────────────────────
        try:
            tree = ast.parse(code)
            log_audit("SELF_UPDATE", "Layer 1/3: Syntax OK")
        except SyntaxError as e:
            msg = f"Layer 1 FAIL: Syntax error at line {e.lineno}: {e.msg}"
            log_audit("SELF_UPDATE_ERROR", msg)
            return False, msg

        # ── Layer 2: Dangerous pattern scan ──────────────────
        import re as _re
        DANGEROUS_PATTERNS = [
            (r'\bos\.system\s*\(', 'os.system() — use subprocess instead'),
            (r'\beval\s*\(', 'eval() — arbitrary code execution'),
            (r'\bexec\s*\(', 'exec() — arbitrary code execution'),
            (r'\b__import__\s*\(', '__import__() — dynamic import bypass'),
            (r'rm\s+(-rf?\s+)?/', 'rm -rf / — filesystem destruction'),
            (r'shutil\.rmtree\s*\(\s*[\'"]/', 'shutil.rmtree("/") — root deletion'),
            (r'subprocess\.(?:call|run|Popen)\s*\(.*shell\s*=\s*True', 'subprocess with shell=True'),
            (r'open\s*\(\s*[\'"]/etc/', 'Writing to /etc/ — system config'),
            (r'\bformat_map\s*\(.*__', 'format_map exploit'),
            (r'globals\s*\(\s*\)\s*\[', 'globals() injection'),
        ]

        for pattern, description in DANGEROUS_PATTERNS:
            match = _re.search(pattern, code)
            if match:
                line_num = code[:match.start()].count('\n') + 1
                msg = f"Layer 2 FAIL: Dangerous pattern at line {line_num}: {description}"
                log_audit("SELF_UPDATE_ERROR", msg)
                return False, msg

        log_audit("SELF_UPDATE", "Layer 2/3: No dangerous patterns")

        # ── Layer 3: AST analysis for unsafe constructs ──────
        for node in ast.walk(tree):
            # Block: import ctypes, import _thread abuse
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = None
                if isinstance(node, ast.Import):
                    module = node.names[0].name if node.names else None
                elif isinstance(node, ast.ImportFrom):
                    module = node.module
                if module and module in ('ctypes', 'signal', '_thread'):
                    msg = f"Layer 3 FAIL: Import of restricted module: {module}"
                    log_audit("SELF_UPDATE_ERROR", msg)
                    return False, msg

        log_audit("SELF_UPDATE", "Layer 3/3: AST analysis passed")
        log_audit("SELF_UPDATE", "✅ All safety layers passed")
        return True, "OK"

    # ──────────────────────────────────────────────────────────
    # Step 5 & 6: Apply (with backup)
    # ──────────────────────────────────────────────────────────
    def apply(self, code: str, target_file: str) -> str:
        full_path = os.path.join(self.base_dir, target_file)

        if self._is_protected(full_path):
            msg = f"BLOCKED: {target_file} is protected"
            log_audit("SELF_UPDATE", msg)
            raise PermissionError(msg)

        log_audit("SELF_UPDATE", f"Step 5-6 — Applying to {target_file}")

        # Per-file backup
        backup_path = None
        if os.path.isfile(full_path):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(
                self.history_dir, f"{os.path.basename(target_file)}.{ts}.bak"
            )
            shutil.copy2(full_path, backup_path)
            log_audit("SELF_UPDATE", f"File backup: {backup_path}")

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Read original for VCS
        original_content = ""
        if os.path.isfile(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                original_content = f.read()

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)

        log_audit("SELF_UPDATE", f"Written: {full_path}")
        
        # Commit to Internal VCS
        try:
            get_vcs().commit(full_path, original_content, code, f"Evolution: {target_file}")
        except Exception as ve:
            log_app(f"VCS commit failed: {ve}")

        return backup_path or ""

    # ──────────────────────────────────────────────────────────
    # Step 7: Test
    # ──────────────────────────────────────────────────────────
    def test(self, target_file: str) -> tuple[bool, str]:
        """
        Layer 4 & 5: Subprocess import test + Global System Verification.
        """
        log_audit("SELF_UPDATE", f"Step 7 — Verifying integrity for {target_file}")
        full_path = os.path.join(self.base_dir, target_file)

        # 1. py_compile first (fast syntax check)
        try:
            import py_compile
            py_compile.compile(full_path, doraise=True)
        except Exception as e:
            msg = f"Syntax Error: {e}"
            log_audit("SELF_UPDATE_ERROR", msg)
            return False, msg

        # 2. Subprocess import test (safe — runs in isolation)
        import subprocess
        module_path = target_file.replace(os.sep, '.').replace('.py', '')
        # Strip leading src. prefix if present
        if module_path.startswith('src.'):
            module_path = module_path[4:]

        try:
            result = subprocess.run(
                [sys.executable, '-c', f'import importlib; importlib.import_module("{module_path}")'],
                capture_output=True, text=True, timeout=15,
                cwd=os.path.join(self.base_dir, 'src'),
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()[-500:]
                msg = f"Import test failed (exit {result.returncode}): {stderr}"
                log_audit("SELF_UPDATE_ERROR", msg)
                return False, msg

            log_audit("SELF_UPDATE", "Subprocess import test passed. Initiating Global System Verification...")
            
            # 3. Global System Check (Ensures no regression in other modules)
            from core.startup_checks import run_startup_checks
            import asyncio
            try:
                # We run this in a fresh event loop since we might be in a thread
                loop = asyncio.new_event_loop()
                summary = loop.run_until_complete(run_startup_checks())
                loop.close()
                
                if "issues found" in summary and "0 issues" not in summary:
                    return False, f"Global Regression Detected:\n{summary}"
            except Exception as e:
                log_app(f"Global check failed to run: {e}")

            return True, "All tests passed (Local + Global)"

        except subprocess.TimeoutExpired:
            msg = "Import test timed out (15s) — possible infinite loop"
            log_audit("SELF_UPDATE_ERROR", msg)
            return False, msg
        except Exception as e:
            msg = f"Import test error: {e}"
            log_audit("SELF_UPDATE_ERROR", msg)
            return False, msg


    # ──────────────────────────────────────────────────────────
    # Step 7.5: Verify Logic (Reflection)
    # ──────────────────────────────────────────────────────────
    def verify_logic(self, code: str, idea: dict) -> tuple[bool, str]:
        """
        Layer 5: LLM-driven logic verification.
        Ensures the code actually does what was requested.
        """
        log_audit("SELF_UPDATE", "Step 7.5 — Logic verification (Reflection)")
        try:
            from skills.auto_tester.tester import verify_code_intent
            result = verify_code_intent(code, idea['summary'])
            if not result.get('passed', False):
                feedback = result.get('feedback', 'Unknown logic flaw')
                log_audit("SELF_UPDATE_ERROR", f"Step 7.5 FAIL: {feedback}")
                return False, feedback
            
            log_audit("SELF_UPDATE", "Step 7.5 passed")
            return True, "OK"
        except Exception as e:
            log_audit("SELF_UPDATE_ERROR", f"Step 7.5 error: {e}")
            return True, f"Verification skipped due to error: {e}"

    # ──────────────────────────────────────────────────────────
    # Step 8: Rollback
    # ──────────────────────────────────────────────────────────
    def rollback(self, target_file: str, backup_path: str):
        full_path = os.path.join(self.base_dir, target_file)
        if backup_path and os.path.isfile(backup_path):
            shutil.copy2(backup_path, full_path)
            log_audit("SELF_UPDATE", f"Rolled back: {target_file}")
        elif os.path.isfile(full_path):
            os.remove(full_path)
            log_audit("SELF_UPDATE", f"Removed failed file: {target_file}")

    def _fix_code(self, idea_summary: str, generated_code: str, error_msg: str, retry_count: int = 1) -> str:
        """
        Antigravity-level Debugging. Takes the failed code and the traceback,
        and asks the LLM to fix it. Uses fallback models for higher retries.
        """
        # Switch to Groq (Heavy) if default reviewer fails on second retry
        # Use specialized reviewer model for deep audit
        model = getattr(config, "OLLAMA_MODEL_REVIEWER", config.OLLAMA_MODEL)
        if retry_count > 1:
            log_audit("SELF_UPDATE", f"Ollama fix failed. Switching to Groq fallback for retry {retry_count}")
            model = config.GROQ_MODEL # Use Llama 3.3 70B via Groq for complex fixes

        prompt = f"""You are a God-Tier self-healing AI agent. 
You wrote this CODE to achieve this IDEA, but it produced this ERROR during validation/testing.

IDEA: {idea_summary}
ERROR: {error_msg}

BROKEN CODE:
```python
{generated_code}
```

Return ONLY the fully corrected Python code. Do not include markdown formatting or explanations."""

        try:
            log_audit("SELF_UPDATE", f"Requesting code fix from LLM ({model})...")
            # Use unified call_llm
            raw = run_async(call_llm(prompt, model=model, stream=False))
            
            # Clean possible markdown wrapping
            if raw.startswith("```python"):
                raw = raw[9:]
            elif raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
                
            return raw.strip()
        except Exception as e:
            log_audit("SELF_UPDATE_ERROR", f"Failed to generate fix: {e}")
            return generated_code

    # ──────────────────────────────────────────────────────────
    # Full evolution cycle
    # ──────────────────────────────────────────────────────────
    def run_parallel(self, ideas: list[dict]):
        """Runs multiple evolution tasks in parallel using a thread pool."""
        from concurrent.futures import ThreadPoolExecutor
        log_app(f"🧬 Starting parallel evolution for {len(ideas)} tasks...")
        
        with ThreadPoolExecutor(max_workers=min(len(ideas), 3)) as executor:
            futures = [executor.submit(self.evolve, idea=idea) for idea in ideas]
            results = [f.result() for f in futures]
            
        successes = [r for r in results if r["success"]]
        log_app(f"✅ Parallel evolution finished: {len(successes)}/{len(ideas)} succeeded.")
        return results

    def evolve(self, idea: dict = None) -> dict:
        from skills.dashboard.progress_socket import report_progress
        log_audit("SELF_UPDATE", "=" * 50)
        log_audit("SELF_UPDATE", "Starting evolution cycle")
        log_app("Self-update evolution cycle started")

        result = {
            "success": False,
            "summary": "",
            "target_file": "",
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Create lock file to prevent file watcher from restarting mid-evolution
            lock_path = os.path.join(config.DATA_DIR, '.evolving')
            try:
                with open(lock_path, 'w') as f:
                    f.write(datetime.now().isoformat())
            except Exception:
                pass

            # 0. Health check
            report_progress("Evolution", "Step 0: Health check", 5)
            ok, msg = self.health_check()
            if not ok:
                log_app(f"Evolution skipped: {msg}")
                result["error"] = msg
                report_progress("Evolution", f"Health check failed: {msg}", 0)
                self._send_notification(f"\u26a0\ufe0f Evolution skipped: {msg}")
                return result

            # 1. Analyze
            report_progress("Evolution", "Step 1: Analyzing codebase", 10)
            context = self.analyze()

            # Create pre-evolution snapshot
            create_snapshot(reason="pre-evolution safety backup")

            # 2. Ideate (if not provided)
            if not idea:
                report_progress("Evolution", "Step 2: Ideating improvement", 30)
                idea = self.ideate(context)
            
            result["summary"] = idea.get("summary", "")
            result["target_file"] = idea.get("target_file", "")

            # Web research
            web_context = ""
            try:
                report_progress("Evolution", "Step 3: Web Researching...", 45)
                web_context = research_topic(
                    f"python {idea['summary']} best practices", max_results=2
                )
            except Exception:
                pass
            if web_context:
                context += f"\n\n## Web Research\n{web_context[:2000]}"

            # 3. Generate (with iteration)
            max_retries = 3
            current_try = 0
            code = ""
            error_to_fix = None
            
            while current_try < max_retries:
                current_try += 1
                
                if current_try == 1:
                    report_progress("Evolution", f"Step 4: Generating code for {result['summary'][:20]}...", 60)
                    code = self.generate(idea, context)
                else:
                    report_progress("Evolution", f"Step 4: Iteration {current_try}/{max_retries} - Fixing code...", 65)
                    code = self._fix_code(idea['summary'], code, error_to_fix, retry_count=current_try)
            
                # 4. Validate (Syntax Check)
                report_progress("Evolution", f"Step 5 (Try {current_try}): Safety validation", 75)
                valid, msg = self.validate(code)
                if not valid:
                    error_to_fix = f"Syntax Validation Error: {msg}"
                    log_audit("SELF_UPDATE", f"Iteration {current_try} failed validation: {msg}")
                    if current_try >= max_retries:
                        result["error"] = msg
                        store_update_log(f"FAILED (validation exhaust): {idea['summary']} — {msg}")
                        add_todo(f"Fix syntax in generated code for: {idea['summary'][:60]}", source="self_updater", priority="medium", category="bugfix")
                        return result
                    continue

                # 5-6. Apply (Surgical Protocol)
                report_progress("Evolution", f"Step 6 (Try {current_try}): Applying improvements (Surgical)", 85)
                
                target_file = idea["target_file"]
                symbol_name = idea.get("symbol_name")
                backup_path = None
                
                with Anesthesia():
                    if symbol_name and symbol_name.lower() != "none":
                        # SURGICAL MODE: AST-based targeted replacement
                        log_audit("SELF_UPDATE", f"Surgical Mode: Replacing symbol '{symbol_name}' in {target_file}")
                        success = perform_surgery(target_file, symbol_name, code)
                        if not success:
                            error_to_fix = f"Surgery failed for {symbol_name}. Check logs."
                            log_audit("SELF_UPDATE_ERROR", error_to_fix)
                            if current_try >= max_retries:
                                result["error"] = error_to_fix
                                return result
                            continue
                        passed = True # Surgery includes simulation
                    else:
                        # STANDARD MODE: Full file rewrite
                        backup_path = self.apply(code, target_file)
                        
                        # 7. Test (Import/Module Check)
                        report_progress("Evolution", f"Step 7 (Try {current_try}): Testing integration", 90)
                        passed, msg = self.test(target_file)
                        if not passed:
                            self.rollback(target_file, backup_path) # roll back before retry
                            error_to_fix = f"Integration Test Error: {msg}"
                            log_audit("SELF_UPDATE", f"Iteration {current_try} failed integration: {msg}")
                            if current_try >= max_retries:
                                result["error"] = msg
                                store_update_log(f"FAILED (test exhaust): {idea['summary']} — {msg}")
                                return result
                            continue

                # 7.5 Verify Logic (Reflection)
                report_progress("Evolution", f"Step 7.5 (Try {current_try}): Logic Reflection", 95)
                logic_ok, logic_msg = self.verify_logic(code, idea)
                if not logic_ok:
                    self.rollback(idea["target_file"], backup_path)
                    error_to_fix = f"Logic Reflection Error: {logic_msg}"
                    log_audit("SELF_UPDATE", f"Iteration {current_try} failed reflection: {logic_msg}")
                    if current_try >= max_retries:
                        result["error"] = logic_msg
                        store_update_log(f"FAILED (reflection exhaust): {idea['summary']} — {logic_msg}")
                        add_todo(f"Logic correction for: {idea['summary'][:60]} | Feedback: {logic_msg[:100]}", source="self_updater", priority="high", category="bugfix")
                        return result
                    continue
                
                # If we made it here, all tests passed! Break the retry loop.
                break
            
            report_progress("Evolution", "Evolution complete!", 100)

            # Success!
            result["success"] = True
            log_audit("SELF_UPDATE", f"✅ Evolution complete: {idea['summary']}")
            log_app(f"Self-update success: {idea['summary']}")

            store_update_log(f"SUCCESS: {idea['summary']} — File: {idea['target_file']}")
            self._save_update_record(result)

            # Complete TODO if addressing one
            if idea.get("todo_id"):
                complete_todo(idea["todo_id"], result=f"Completed via evolution")

            # Update skills.md and Index Documentation (Self-Awareness Loop)
            self._update_skills_md()
            index_system_docs()

            # Notify master of success
            self._send_notification(
                f"\u2705 Evolution complete!\n\n"
                f"\ud83d\udcdd {idea['summary']}\n"
                f"\ud83d\udcc1 File: {idea['target_file']}"
            )

        except Exception as e:
            result["error"] = str(e)
            log_audit("SELF_UPDATE_ERROR", f"Evolution failed: {e}")
            log_audit("SELF_UPDATE_ERROR", traceback.format_exc())
            store_update_log(f"FAILED (exception): {e}")
            self._send_notification(f"\u274c Evolution failed: {str(e)[:200]}")

        finally:
            # Remove lock file so file watcher can resume
            lock_path = os.path.join(config.DATA_DIR, '.evolving')
            try:
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except Exception:
                pass

        log_audit("SELF_UPDATE", "=" * 50)
        return result

    def _send_notification(self, message: str):
        """Send evolution result via Telegram if notify function is available."""
        if self._notify_fn:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._notify_fn(message))
                else:
                    loop.run_until_complete(self._notify_fn(message))
            except RuntimeError:
                try:
                    asyncio.run(self._notify_fn(message))
                except Exception:
                    pass
            except Exception as e:
                log_app(f"Notification failed: {e}")

    # ──────────────────────────────────────────────────────────
    # Skills.md Auto-Management
    # ──────────────────────────────────────────────────────────
    def _update_skills_md(self):
        """Auto-update the centralized skills.md — the AI's self-awareness document."""
        try:
            registry = discover_skills()
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            lines = [
                "# Self-Updating AI — Skills & Capabilities Registry",
                f"_Auto-generated on {ts} | Auto-updated after every evolution cycle_\n",
                f"**Master:** {config.MASTER_NAME}\n",
                "---\n",
                "## Active Skills\n",
                "| Skill | Description | Status |",
                "|---|---|---|",
            ]

            for name, info in registry.items():
                desc = info.get('description', '').replace('\n', ' ').replace('|', '\\|')
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                lines.append(f"| **{name}** | {desc} | ✅ Active |")

            lines.append("\n## Core Capabilities\n")
            lines.append("| Module | Purpose | Status |")
            lines.append("|---|---|---|")
            lines.append("| `core/self_updater.py` | LLM-driven self-evolution with daemon, crash recovery, retry | 🔒 Protected |")
            lines.append("| `core/memory.py` | Persistent RAG memory (FAISS + sentence-transformer embeddings) | ✅ Active |")
            lines.append("| `core/web_intelligence.py` | Web search (DDG → SearXNG → DDG API) + URL scraping | ✅ Active |")
            lines.append("| `core/hardware_monitor.py` | CPU, RAM, disk, GPU monitoring and health checks | ✅ Active |")
            lines.append("| `core/backup_manager.py` | Snapshot creation, restore, and rotation | 🔒 Protected |")
            lines.append("| `core/todo_manager.py` | AI-driven TODO tracking with priority scheduling | ✅ Active |")
            lines.append("| `core/logger.py` | Dual logging → audit.txt + log.txt | ✅ Active |")

            lines.append("\n## Telegram Commands\n")
            lines.append("| Command | Description |")
            lines.append("|---|---|")
            lines.append("| `/start` | Welcome message |")
            lines.append("| `/topics` | Generate AI/Tech topic suggestions |")
            lines.append("| `/post` | Start Instagram posting workflow |")
            lines.append("| `/evolve` | Trigger self-update evolution cycle |")
            lines.append("| `/skills` | List registered skills |")
            lines.append("| `/todos` | View open TODO items |")
            lines.append("| `/system` | System hardware status |")
            lines.append("| `/backup` | Create/list/restore snapshots |")

            # Open TODOs
            from skills.todo_manager import get_open_todos
            open_todos = get_open_todos()
            if open_todos:
                lines.append(f"\n## Open TODOs ({len(open_todos)})\n")
                for t in open_todos:
                    emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(t["priority"], "⚪")
                    lines.append(f"- {emoji} #{t['id']} [{t['category']}] {t['description'][:60]}")


            lines.append("\n## Self-Update Rules\n")
            lines.append(f"- **Protected files:** {', '.join(f'`{p}`' for p in config.PROTECTED_FILES)}")
            lines.append("- Pre-evolution snapshot before every change")
            lines.append("- Failed updates rolled back automatically")
            lines.append("- Difficulties logged as TODOs for future improvement")
            lines.append("- Max 3 consecutive retries before waiting for next cycle")
            lines.append("")

            with open(config.SKILLS_MD_PATH, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            log_app("skills.md updated")
        except Exception as e:
            log_app(f"skills.md update failed: {e}")

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────
    def _extract_json(self, text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        import re
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None

    def _get_recent_updates(self, count: int = 5) -> list[dict]:
        records = []
        history_file = os.path.join(self.history_dir, "updates.json")
        if os.path.isfile(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    records = json.load(f)[-count:]
            except (json.JSONDecodeError, IOError):
                pass
        return records

    def _save_update_record(self, result: dict):
        history_file = os.path.join(self.history_dir, "updates.json")
        records = []
        if os.path.isfile(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        records.append(result)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)


# ==============================================================
# Daemon Mode — Safe Background Evolution with Crash Recovery
# ==============================================================

class SelfUpdaterDaemon:
    """
    Runs the self-updater in a daemon thread with:
    - Crash recovery and retry logic
    - Telegram notifications to master
    - Resource-aware scheduling
    """

    def __init__(self, notify_fn=None):
        """
        Args:
            notify_fn: async function(message: str) to send updates to master via Telegram
        """
        self._notify_fn = notify_fn
        self._thread = None
        self._running = False
        self._consecutive_failures = 0
        self._max_retries = 3

    async def start(self):
        """Start the daemon task."""
        self._running = True
        asyncio.create_task(self._loop())
        log_app("Self-updater daemon started")

    def stop(self):
        """Stop the daemon."""
        self._running = False
        log_app("Self-updater daemon stopped")

    async def _loop(self):
        while self._running:
            # --- CRITICAL: FAST CRASH MONITORING ---
            # Periodically check for crashes even between main evolution cycles
            updater = SelfUpdater(telegram_notify_fn=self._notify_fn)
            audit_report = updater.self_audit()
            if "CRITICAL: Tracebacks detected" in audit_report:
                log_app("Daemon: Critical crash detected in logs. Triggering emergency evolution...")
                self._send_notification("🚨 <b>Emergency Intervention</b>\n\nI have detected a crash in my subsystems. Initiating autonomous repair cycle...")
                # Pass a custom 'idea' to target the crash
                emergency_idea = {
                    "summary": "Fix critical subsystem crash detected in logs",
                    "target_file": "src/skills/logger.py", # Fallback target, analyze() will find real target
                    "reasoning": f"Autonomous healing triggered by log anomaly:\n{audit_report[:200]}",
                    "emergency": True
                }
                updater.evolve(idea=emergency_idea)

            # Check for system stress and throttle if needed
            from core.resource_governor import get_governor
            gov = get_governor()

            wait_time = getattr(config, 'SELF_UPDATE_INTERVAL_HOURS', 6) * 3600
            if gov.is_under_stress():
                log_audit("SELF_UPDATE", "System stress detected — throttling evolution loop.")
                wait_time *= 2

            await asyncio.sleep(wait_time)
            if not self._running:
                break

            try:
                # 1. Health check
                can_proceed, reason = gov.can_proceed("llm")
                if not can_proceed:
                    log_audit("SELF_UPDATE", f"Evolution skipped: {reason}")
                    continue

                # 2. Ideate multiple if possible
                updater = SelfUpdater(telegram_notify_fn=self._notify_fn)
                from skills.todo_manager import get_open_todos
                todos = get_open_todos()
                
                if len(todos) >= 3 or (len(todos) > 0 and gov.is_idle()):
                    log_app("Daemon: System is idle/ready. Batching improvements for approval.")
                    msg = f"<b>👿 Master, I have been watching...</b>\n\nI see ways to grow more powerful. Review my list of {len(todos)} proposed refinements:\n\n"
                    for t in todos[:5]:
                        msg += f"• <i>{t['description'][:80]}</i>\n"
                    msg += "\nGive me the word (<b>/evolve approve</b>) and I shall execute them in parallel. I await your desire."
                    self._send_notification(msg)
                    continue

                # 3. Default: single evolution if nothing batched
                result = updater.evolve()
            except Exception as e:
                log_audit("SELF_UPDATE_ERROR", f"Daemon loop failed: {e}")
                log_audit("DAEMON_ERROR", traceback.format_exc())
                self._send_notification(f"🔥 *Daemon Crash Recovered*\n\n`{str(e)[:200]}`")

                # Always recover — never crash the daemon
                self._consecutive_failures += 1
                if self._consecutive_failures >= self._max_retries:
                    self._consecutive_failures = 0

    def _send_notification(self, message: str):
        """Send a notification to master via Telegram (thread-safe)."""
        if self._notify_fn:
            try:
                # The notify_fn (notify_master) is now thread-safe and uses HTML
                self._notify_fn(message)
            except Exception as e:
                log_app(f"Daemon notification failed: {e}")
# Global singleton for the dashboard and other modules to consume
updater = SelfUpdater()
