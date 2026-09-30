# ============================================================
# core/observer.py — Proactive File System Observer
#
# Monitors src/ and tests/ for changes, triggers background
# linting/testing, and detects git branch changes.
# ============================================================

import os
import time
import asyncio
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import config
from skills.logger import log_audit, log_app

class ASURAFileHandler(FileSystemEventHandler):
    """Handles file system events for the ASURA workspace."""

    def __init__(self, loop, callback_fn=None, git_callback_fn=None):
        self.loop = loop
        self.callback = callback_fn
        self.git_callback = git_callback_fn
        self._last_event_time = {}
        self._cooldown = 2.0  # seconds

    def on_modified(self, event):
        if event.is_directory:
            return

        # ─── Git Branch Change Detection ───
        if ".git/HEAD" in event.src_path or "HEAD" == os.path.basename(event.src_path):
            if self.git_callback:
                self.loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self.git_callback())
                )
            return

        if not event.src_path.endswith((".py", ".md", ".json")):
            return

        # Simple debouncing
        now = time.time()
        if now - self._last_event_time.get(event.src_path, 0) < self._cooldown:
            return
        self._last_event_time[event.src_path] = now

        rel_path = os.path.relpath(event.src_path, config.BASE_DIR)
        log_audit("OBSERVER", f"Modified: {rel_path}")

        # Trigger proactive analysis in the main event loop
        if self.callback:
            self.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.callback(rel_path))
            )

class FileSystemObserver:
    """
    Background daemon that monitors the workspace for proactive intervention.
    Part of Phase S: Proactive Intelligence Expansion.
    """

    def __init__(self, notify_fn=None):
        self._notify = notify_fn
        self._observer = None
        self._running = False
        self._loop = None
        self._last_branch = None

    async def start(self):
        """Start the file system observer."""
        self._loop = asyncio.get_running_loop()
        self._handler = ASURAFileHandler(self._loop, self._handle_change, self._handle_git_change)
        self._observer = Observer()
        
        # Watch src/, tests/ and .git/
        watch_dirs = [
            os.path.join(config.BASE_DIR, "src"),
            os.path.join(config.BASE_DIR, "tests"),
            os.path.join(config.BASE_DIR, ".git")
        ]
        
        for d in watch_dirs:
            if os.path.isdir(d):
                # .git is not recursive to keep overhead low
                recursive = ".git" not in d
                self._observer.schedule(self._handler, d, recursive=recursive)
                log_app(f"👁️ Observer watching: {os.path.relpath(d, config.BASE_DIR)}")

        # Initialize current branch
        self._last_branch = self._get_current_branch()

        self._observer.start()
        self._running = True
        log_app("✨ File System Observer active (Proactive Surveillance)")

    def stop(self):
        """Stop the observer."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
        self._running = False

    def _get_current_branch(self) -> str:
        """Read the current branch from .git/HEAD."""
        head_path = os.path.join(config.BASE_DIR, ".git", "HEAD")
        if not os.path.isfile(head_path):
            return "unknown"
        try:
            with open(head_path, "r") as f:
                content = f.read().strip()
                if content.startswith("ref: "):
                    return content.split("/")[-1]
                return content[:8] # Detached head SHA
        except Exception:
            return "unknown"

    async def _handle_git_change(self):
        """Detect branch switch and trigger re-sync."""
        new_branch = self._get_current_branch()
        if new_branch != self._last_branch:
            log_app(f"🔀 Branch Switch: {self._last_branch} -> {new_branch}")
            log_audit("OBSERVER", f"Branch change detected: {new_branch}. Triggering context re-sync.")
            
            if self._notify:
                self._notify(f"🔀 <b>Context Shift</b>\n\nI detected a branch switch to <code>{new_branch}</code>.\nI'm re-scanning the codebase to update my Knowledge Graph.")
            
            # Update last branch
            self._last_branch = new_branch
            
            # Trigger Architectural Knowledge Graph Scan (Self-Discovery)
            try:
                from core.knowledge_scanner import knowledge_scanner
                asyncio.create_task(knowledge_scanner.scan_all())
            except Exception as e:
                log_app(f"Observer: KG re-scan failed: {e}")

    async def _handle_change(self, file_path: str):
        """Analyze the changed file and decide on proactive actions."""
        if file_path.endswith(".py"):
            await self._run_background_checks(file_path)

    async def _run_background_checks(self, file_path: str):
        """Execute syntax and test checks for the modified file."""
        log_audit("OBSERVER", f"Analyzing changes in {file_path}...")
        
        # Example: Trigger pytest for the file
        full_path = os.path.join(config.BASE_DIR, file_path)
        
        # Heuristic: Find associated test
        test_file = None
        if "tests/" in file_path:
            test_file = file_path
        else:
            # Try to find matching test in tests/
            base_name = os.path.basename(file_path)
            potential_test = os.path.join("tests", f"test_{base_name}")
            if os.path.isfile(os.path.join(config.BASE_DIR, potential_test)):
                test_file = potential_test

        if test_file and os.path.basename(test_file).startswith("test_"):
            log_audit("OBSERVER", f"Auto-running test: {test_file}")
            # Run test in background
            proc = await asyncio.create_subprocess_exec(
                "pytest", "-v", os.path.join(config.BASE_DIR, test_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                err_msg = stderr.decode() or stdout.decode()
                log_audit("OBSERVER", f"❌ Proactive test failure in {test_file}")
                
                # Report to Master if significant
                if self._notify:
                    self._notify(f"🚩 <b>Proactive Alert</b>\n\nI detected a test failure in <code>{test_file}</code> after your changes.\n\nI'm handing this over to the Self-Healing system.")
                
                # ALERT the Self-Healing system by injecting a virtual crash log
                # This leverages existing logic in SelfHealingDaemon
                from core.self_healing import SelfHealingDaemon
                # We can't easily call the singleton here if it's not exposed, 
                # but we can log a traceback-like format to the audit log
                with open(config.AUDIT_LOG_PATH, "a") as f:
                    f.write(f"\nTraceback (most recent call last):\n  File \"{full_path}\", line 0, in proactive_scan\nProactiveTestFailure: {err_msg[:500]}\n")
            else:
                log_audit("OBSERVER", f"✅ Proactive test passed: {test_file}")
