# ============================================================
# core/self_healing.py — Autonomous Self-Healing Daemon
#
# Monitors audit logs for Python tracebacks, analyzes them,
# and invokes the Self-Updater to autonomously fix bugs.
# ============================================================

import os
import time
import threading
import traceback
import re
import asyncio
from settings import settings as config
from core.llm import call_llm
from skills.logger import log_audit, log_app
from core.self_updater import SelfUpdater
from core.handoff import create_handoff
from core.anesthesia import wait_for_consciousness


class SelfHealingDaemon:
    """
    Background daemon that monitors logs for crashes and fixes them.
    The "Antibodies" of the system.
    """

    def __init__(self, notify_fn=None):
        self._notify = notify_fn
        self._running = False
        self._thread = None
        self._last_position = 0
        self._failure_counts = {}  # {error_signature: count}
        self._max_auto_attempts = 3
        
        # signature = hash(error_message + target_file)
        self.log_file = config.AUDIT_LOG_PATH

    async def start(self):
        """Start the self-healing monitoring task."""
        self._running = True
        # Initialize log position to end of file to avoid re-fixing old errors
        if os.path.isfile(self.log_file):
            self._last_position = os.path.getsize(self.log_file)
            
        asyncio.create_task(self._loop())
        log_app("✨ Self-healing system initialized (Antibodies Active)")

    async def pre_start_check(self):
        """
        Check for crashes that happened during the LAST run.
        This handles the "Main Thread" crash scenario where the daemon
        stopped because the whole process died.
        """
        if not os.path.isfile(self.log_file):
            return

        log_app("🛡️ Guardian Drive: Scanning for session-ending crashes...")
        
        # Read last 10KB of logs (enough for a few tracebacks)
        file_size = os.path.getsize(self.log_file)
        read_size = min(file_size, 10240)
        
        content = ""
        with open(self.log_file, "r", encoding="utf-8") as f:
            f.seek(file_size - read_size)
            content = f.read()

        # Find the very LAST traceback in the file
        matches = re.findall(
            r"(Traceback \(most recent call last\):.*?)\n([a-zA-Z0-9_.]+: .*?)\n", 
            content, 
            re.DOTALL
        )

        if not matches:
            log_app("✅ No prior crashes detected. System is clean.")
            return

        tb, err_msg = matches[-1] # Get the most recent one
        log_audit("GUARDIAN", f"Found prior crash: {err_msg}")
        
        # Only try to fix if it hasn't been fixed yet or if we are in recovery mode
        # We use a smaller attempt limit but prioritize this fix
        await self._handle_crash(tb.strip(), err_msg.strip())

    def stop(self):
        self._running = False

    async def _loop(self):
        while self._running:
            # Wait for any active surgery to complete
            wait_for_consciousness()
            
            await asyncio.sleep(30)  # Check logs every 30 seconds
            if not self._running:
                break
                
            try:
                await self._scan_logs()
            except Exception as e:
                log_audit("HEALING_ERROR", f"Daemon loop failed: {e}")

    async def _scan_logs(self):
        """Scan audit log for new tracebacks."""
        if not os.path.isfile(self.log_file):
            return

        current_size = os.path.getsize(self.log_file)
        if current_size < self._last_position:
            self._last_position = 0  # Log rotated

        if current_size == self._last_position:
            return

        new_content = ""
        with open(self.log_file, "r", encoding="utf-8") as f:
            f.seek(self._last_position)
            new_content = f.read()
            self._last_position = f.tell()

        # Look for tracebacks
        matches = re.findall(
            r"(Traceback \(most recent call last\):.*?)\n([a-zA-Z0-9_.]+: .*?)\n", 
            new_content, 
            re.DOTALL
        )

        for tb, err_msg in matches:
            await self._handle_crash(tb.strip(), err_msg.strip())

        # ─── Detect Telegram Conflict (Duplicate Instance) ───
        if "terminated by other getUpdates request" in new_content:
            log_audit("HEALING", "Detected Telegram Conflict (Multi-instance). Initiating cleanup.")
            await self._handle_telegram_conflict()

    async def _handle_telegram_conflict(self):
        """Emergency cleanup for duplicate bot instances."""
        log_app("🛠️ Self-Healing: Cleaning up duplicate Telegram bot instances...")
        try:
            import psutil
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = " ".join(proc.info['cmdline'] or [])
                    # If it's a python process running ASURA but NOT our current PID
                    if ("main.py" in cmdline or "run.py" in cmdline) and proc.info['pid'] != current_pid:
                        log_audit("HEALING", f"Terminating zombie process: {proc.info['pid']}")
                        # psutil.Process.terminate() is cross-platform (SIGTERM on Unix, TerminateProcess on Win)
                        p = psutil.Process(proc.info['pid'])
                        p.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if self._notify:
                self._notify("🛠️ <b>Self-Healed: Bot Conflict</b>\n\nI detected and terminated a duplicate instance that was causing a Telegram conflict.")
        except Exception as e:
            log_audit("HEALING_ERROR", f"Conflict resolution failed: {e}")

    async def _handle_crash(self, tb: str, err_msg: str):
        """Analyze crash and attempt a fix."""
        # Find the target file from the traceback
        file_matches = re.findall(r'File "([^"]+)", line (\d+)', tb)
        if not file_matches:
            return

        target_file_abs, line_no = file_matches[-1]
        target_file = target_file_abs.replace(config.BASE_DIR, "").strip(os.sep)

        # Ignore interactive or streaming input which aren't actual files
        if target_file in ("<stdin>", "<string>") or target_file.startswith("<"):
            return

        # 🩺 SMART UPGRADE: ImportError awareness
        # If it's an ImportError, we might need to fix the SOURCE of the missing symbol
        # instead of the file that failed to import it.
        context_files = [target_file]
        if "ImportError" in err_msg or "ModuleNotFoundError" in err_msg:
            # Try to identify the missing symbol and source module
            # Pattern: cannot import name 'get_recent_context' from 'skills.conversation.history'
            missing_sym = re.search(r"import name '([^']+)'", err_msg)
            source_module = re.search(r"from '([^']+)'", err_msg)
            
            if source_module:
                mod_str = source_module.group(1)
                # Resolve module to path
                mod_path = mod_str.replace(".", os.sep) + ".py"
                # Check if it's in src
                full_mod_path = os.path.join(config.BASE_DIR, "src", mod_path)
                if not os.path.isfile(full_mod_path):
                    # Try direct path
                    full_mod_path = os.path.join(config.BASE_DIR, mod_path)
                
                if os.path.isfile(full_mod_path):
                    rel_mod_path = full_mod_path.replace(config.BASE_DIR, "").strip(os.sep)
                    log_audit("HEALING", f"Pivot: ImportError source identified as {rel_mod_path}")
                    # Pivot the target of the fix to the source module
                    target_file = rel_mod_path
                    # But keep the original crash site in context
                    context_files.append(rel_mod_path)
        
        # Don't try to auto-code-fix protected files
        if target_file in config.PROTECTED_FILES:
            log_audit("HEALING", f"Protected file crash detected: {target_file}. Initiating Ghost Restore...")
            try:
                # ─── GHOST RESTORE ────────────
                # Instead of code-fixing, we copy from the recovery cache
                recovery_path = os.path.join(config.DATA_DIR, "recovery_cache", target_file)
                if os.path.isfile(recovery_path):
                    import shutil
                    shutil.copy2(recovery_path, os.path.join(config.BASE_DIR, target_file))
                    log_app(f"👻 Ghost Repair: Restored {target_file} from recovery cache.")
                    if self._notify:
                        self._notify(f"👻 <b>Ghost Repair Successful</b>\n\nCore file <code>{target_file}</code> was corrupted and has been restored from a stable snapshot.")
                    return
                else:
                    log_audit("HEALING_FAIL", f"Recovery cache missing for {target_file}")
            except Exception as e:
                log_audit("HEALING_ERROR", f"Ghost Repair failed: {e}")
            return

        signature = f"{err_msg}|{target_file}"
        count = self._failure_counts.get(signature, 0) + 1
        self._failure_counts[signature] = count

        log_app(f"🩺 Detected crash relating to {target_file}: {err_msg}")
        log_audit("HEALING", f"Attempt {count}/{self._max_auto_attempts} for {signature}")

        import html
        esc_err = html.escape(err_msg)
        esc_target = html.escape(target_file)

        if count > self._max_auto_attempts:
            # Persistent bug — initiate handoff
            if self._notify:
                self._notify(f"🚩 <b>Persistent Bug Detected</b>\n\nI failed to fix <code>{esc_target}</code> after {self._max_auto_attempts} attempts.\nI've created a handoff for Antigravity.")
            create_handoff(err_msg, tb, target_file, count)
            return

        # Attempt healing
        if self._notify:
            self._notify(f"🩺 <b>Self-Healing Attempt {count}</b>\n\nI detected a crash in <code>{esc_target}</code>:\n<code>{esc_err}</code>\n\nI'm attempting an autonomous fix...")

        await self._apply_fix(target_file, err_msg, tb, context_files)

    async def _apply_fix(self, target_file: str, err_msg: str, tb: str, context_files: list[str] = None):
        """Invoke SelfUpdater to fix the bug."""
        try:
            from core.resource_governor import get_governor
            can, reason = get_governor().can_proceed("llm")
            if not can:
                log_audit("HEALING", f"Deferred: {reason}")
                return

            updater = SelfUpdater(telegram_notify_fn=self._notify)
            
            # Read context from all relevant files
            extra_context = ""
            if context_files:
                for cf in set(context_files):
                    try:
                        with open(os.path.join(config.BASE_DIR, cf), "r") as f:
                            extra_context += f"\n### File Content: {cf}\n{f.read()}\n"
                    except Exception:
                        pass

            # Specialized analysis prompt for healing
            prompt = f"""You are fixing a BUG in a Self-Updating AI system.
Crash Traceback:
{tb}

Error: {err_msg}
Target File to Fix: {target_file}

{extra_context}

Rules:
1. Return ONLY a JSON object:
   {{"summary": "Fix for {err_msg}", "target_file": "{target_file}", "is_new_file": false, "reasoning": "Root cause analysis: ...", "todo_id": null}}
2. Ensure you resolve the ROOT CAUSE (e.g., if a symbol is missing, add it to the target file).
3. Do not just patch the traceback file if the error indicates a missing symbol in an imported module.
"""
            # Use unified call_llm wrapper
            raw_idea = await call_llm(prompt, model=config.OLLAMA_MODEL, stream=False)
            idea = updater._extract_json(raw_idea)
            if not idea:
                raise ValueError("LLM failed to generate fix idea")

            # Proceed with generation and application
            context = updater.analyze()
            code = updater.generate(idea, context)
            valid, msg = updater.validate(code)
            if valid:
                backup_path = updater.apply(code, target_file)
                passed, msg = updater.test(target_file)
                if passed:
                    log_app(f"✅ Successfully healed {target_file}")
                    if self._notify:
                        self._notify(f"✨ <b>Healed!</b>\n\nI fixed the bug in <code>{target_file}</code> and verified the code.")
                else:
                    log_audit("HEALING", f"Test failed after apply: {msg}. Rolling back.")
                    updater.rollback(target_file, backup_path)
            else:
                log_audit("HEALING", f"LLM generated invalid code: {msg}")

        except Exception as e:
            log_audit("HEALING_ERROR", f"Fix attempt failed: {e}")

    # _ask_ollama removed - handled by call_llm
