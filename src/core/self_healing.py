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
        self._last_positions = {}  # {log_path: position}
        self._failure_counts = {}  # {error_signature: count}
        self._max_auto_attempts = 3
        
        # Surveillance list: Monitor both core and app-specific logs
        self.log_files = [config.AUDIT_LOG_PATH, config.APP_LOG_PATH]

    async def start(self):
        """Start the self-healing monitoring task."""
        self._running = True
        # Initialize log positions to end of file to avoid re-fixing old errors
        for log in self.log_files:
            if os.path.isfile(log):
                self._last_positions[log] = os.path.getsize(log)
            
        asyncio.create_task(self._loop())
        log_app("✨ Self-healing system initialized (Multi-Log Surveillance Active)")

    async def pre_start_check(self):
        """Check for crashes that happened during the LAST run."""
        # Check the primary audit log for session-ending crashes
        audit_log = config.AUDIT_LOG_PATH
        if not os.path.isfile(audit_log):
            return

        log_app("🛡️ Guardian Drive: Scanning for session-ending crashes...")
        
        file_size = os.path.getsize(audit_log)
        read_size = min(file_size, 10240)
        
        content = ""
        with open(audit_log, "r", encoding="utf-8") as f:
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
        """Pattern-agnostic log surveillance."""
        for log_path in self.log_files:
            if not os.path.isfile(log_path): continue
            current_size = os.path.getsize(log_path)
            last_pos = self._last_positions.get(log_path, 0)
            if current_size < last_pos: last_pos = 0 
            if current_size == last_pos: continue

            with open(log_path, "r", encoding="utf-8") as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                self._last_positions[log_path] = f.tell()

            # Broad Anomaly Detection: Look for 'error', 'exception', 'fail', 'traceback'
            for i, line in enumerate(new_lines):
                low_line = line.lower()
                if any(trigger in low_line for trigger in ["error", "exception", "fail", "traceback"]):
                    # Skip known benign warnings
                    if "ptbuserwarning" in low_line: continue
                    
                    # Capture context (3 lines before, 2 lines after)
                    start = max(0, i - 3)
                    end = min(len(new_lines), i + 3)
                    context = "".join(new_lines[start:end])
                    
                    log_audit("HEALING_SENSE", f"Anomaly detected in {os.path.basename(log_path)}")
                    await self._analyze_anomaly(context, log_path)

    async def _analyze_anomaly(self, context: str, source_log: str):
        """Use the LLM to determine if the log anomaly is a fixable bug."""
        # Avoid duplicate analysis for the same error in a short window
        error_hash = hash(context.strip())
        if error_hash in self._failure_counts and self._failure_counts[error_hash] > 5:
            return

        prompt = f"""[AGENT: bug_hunter]
You are the ASURA Sovereign Healer. You found this anomaly in {source_log}:
---
{context}
---

MISSION:
1. Is this a Python error or system failure that needs a code fix? (YES/NO)
2. If YES, identify the file and the error message.
3. Propose a surgical fix.

Return ONLY a JSON object:
{{"is_bug": bool, "file": "path/to/file.py", "error": "message", "fix_idea": "..."}}
"""
        try:
            raw = await call_llm(prompt, model=config.OLLAMA_MODEL_FAST)
            import json, re
            # Fix: Look for standard single-brace JSON
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if not match: 
                log_audit("HEALING_WARN", "LLM returned no valid JSON fix")
                return
            res = json.loads(match.group())
            
            if res.get("is_bug"):
                self._failure_counts[error_hash] = self._failure_counts.get(error_hash, 0) + 1
                await self._handle_crash(context, res["error"])
        except: pass

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
        """Invoke Architect-Critic loop to fix and verify the bug in a sandbox."""
        try:
            from core.resource_governor import get_governor
            from core.phantom_verify import verify_fix_in_ghost
            from core.self_updater import SelfUpdater
            
            can, reason = get_governor().can_proceed("llm")
            if not can: return

            from core.antigravity_bridge import antigravity_bridge
            incident = antigravity_bridge.record_incident(err_msg, tb, target_file, context_files)
            incident_id = incident.get("id")

            updater = SelfUpdater(telegram_notify_fn=self._notify)
            extra_context = ""
            if context_files:
                for cf in set(context_files):
                    try:
                        with open(os.path.join(config.BASE_DIR, cf), "r") as f:
                            extra_context += f"\n### File Content: {cf}\n{f.read()}\n"
                    except: pass

            # ─── 🧠 Phase 1: Architect (Heavy Reasoning) ───────────
            architect_prompt = f"""[AGENT: bug_hunter]
You are the ARCHITECT of the ASURA Sovereign Healer.
FAILURE: {err_msg}
TRACEBACK:
{tb}

TARGET: {target_file}
CONTEXT FILES:
{extra_context}

MISSION:
Plan a surgical fix. Provide the fix idea and the actual updated code for the target file.
Return ONLY a JSON object:
{{"summary": "Fix for {err_msg}", "code": "full updated content of {target_file}", "test_script": "python code to re-verify the fix (optional)"}}
"""
            # Prefer powerful Groq heavy model if available
            architect_model = config.GROQ_MODEL_HEAVY if (getattr(config, "GROQ_API_KEY", None) and not get_governor().is_exhausted("groq")) else config.OLLAMA_MODEL
            log_app(f"🧠 Self-Healing Architect using model: {architect_model}")
            raw_plan = await call_llm(architect_prompt, model=architect_model)
            plan = updater._extract_json(raw_plan)
            if not plan or "code" not in plan: raise ValueError("Architect failed to generate plan")

            # ─── 🛡️ Phase 2: Critic (Qwen-0.8B) ────────────
            critic_prompt = f"""[AGENT: reviewer]
Review this proposed fix for ASURA.
ERROR: {err_msg}
CODE CHANGE:
{plan['code']}

Check for:
1. Logic errors or obvious bugs.
2. Security risks or file-system violations.
3. Unnecessary bloat.

If perfect, respond 'APPROVED'. If not, explain WHY.
"""
            review = await call_llm(critic_prompt, model=config.OLLAMA_MODEL_FAST)
            if "APPROVED" not in review.upper():
                log_audit("HEALING_CRITIC", f"Critic rejected plan: {review[:100]}...")
                # Optional: Loop back to architect here
                return

            # ─── 👻 Phase 3: Phantom Verification ─────────
            log_app(f"👻 Spawning Ghost Sandbox for {target_file}...")
            v_res = await verify_fix_in_ghost(target_file, plan["code"], plan.get("test_script"))
            
            if not v_res["success"]:
                log_audit("HEALING_FAIL", f"Phantom verification failed: {v_res.get('error')}")
                if self._notify: self._notify(f"❌ <b>Heal Failed in Sandbox</b>\n{target_file}: {v_res.get('error')}")
                return

            # ─── ⚖️ Phase 4: Witness Protocol ────────────────
            from core.federation import federation
            witnessed = await federation.request_witness_verification(target_file, plan["code"], plan.get("test_script"))
            
            if not witnessed:
                log_audit("HEALING_FAIL", f"Witness verification failed for {target_file}. Discarding fix.")
                if self._notify: self._notify(f"⚖️ <b>Witness Veto</b>\nThe cluster rejected the fix for <code>{target_file}</code>. Searching for safer alternative.")
                return

            # Apply to production
            backup_path = updater.apply(plan["code"], target_file)
            if incident_id:
                antigravity_bridge.resolve_incident(incident_id, f"Healed {target_file}: {plan.get('summary', 'fix applied')}")
            log_app(f"✅ Successfully healed {target_file}")
            if self._notify:
                self._notify(f"✨ <b>Sovereign Heal!</b>\n\nI fixed <code>{target_file}</code> using the Architect-Critic loop, verified it in a Ghost Sandbox, and received cluster-wide <b>Witness Approval</b>.")

        except Exception as e:
            log_audit("HEALING_ERROR", f"Fix attempt failed: {e}")

    # _ask_ollama removed - handled by call_llm
