# ============================================================
# core/federation.py — Peer-to-Peer AI Synchronization
#
# Connects multiple ASURA instances across a network.
# Syncs code (via Git), memory (via RAG-Sync), and tasks.
# ============================================================

import os
import httpx
import asyncio
import json
from typing import List, Optional
from settings import settings as config
from skills.logger import log_audit, log_app

class SovereignFederation:
    """
    Manages communication and state sync with Sibling ASURA instances.
    """

    def __init__(self):
        self.peers = config.ASURA_PEERS
        self.auth_token = config.PEER_AUTH_TOKEN
        self.client = httpx.AsyncClient(headers={"X-ASURA-Peer-Token": self.auth_token}, timeout=30)
        self._sync_running = False

    def start_sync_daemon(self):
        """Start the background code-sync observer."""
        if self._sync_running:
            return
        self._sync_running = True
        import threading
        threading.Thread(target=self._sync_loop, daemon=True, name="federation-sync").start()
        log_app("🌐 Federation: Evolution Observer active (Auto-Sync enabled)")

    def _sync_loop(self):
        """Periodically check the shared remote for new code evolutions."""
        import time
        # Random offset to avoid simultaneous pulls
        import random
        time.sleep(15 + random.randint(0, 30))
        
        while self._sync_running:
            try:
                # Only sync if we are not currently busy with a task
                from core.task_queue import get_task_queue
                if get_task_queue().is_empty():
                    asyncio.run(self.sync_code())
            except Exception as e:
                log_app(f"Federation Sync Loop Error: {e}")
            
            # Check every 10 minutes
            time.sleep(600)

    async def ping_peers(self) -> List[dict]:
        """Check status of all siblings."""
        results = []
        for url in self.peers:
            try:
                resp = await self.client.get(f"{url}/health")
                results.append({"url": url, "status": "online", "data": resp.json()})
            except Exception as e:
                results.append({"url": url, "status": "offline", "error": str(e)})
        return results

    async def push_evolution(self, message: str = None):
        """
        Commit all local changes and push to the shared remote.
        Designed for autonomous self-evolution.
        """
        from skills.git_manager import git
        log_app("🚀 Federation: Preparing to push evolution to remote...")
        
        # 1. Stage all
        git._git("add .")
        
        # 2. Design Commit Message if not provided
        if not message:
            # Short summary of changes
            diff = git._git("diff --cached --stat")["stdout"]
            message = f"[EVOLUTION] ASURA Autonomous Sync\n\nChanges:\n{diff[:500]}"
            
        # 3. Commit
        git._git(f'commit -m "{message}"')
        
        # 4. Push to shared remote
        res = git._git(f"push {config.SHARED_GIT_REMOTE} main")
        if res["success"]:
            log_app(f"✅ Federation: Evolution pushed to {config.SHARED_GIT_REMOTE}")
            return True
        else:
            log_audit("FEDERATION_ERROR", f"Push failed: {res['stderr']}")
            return False

    async def sync_code(self):
        """
        Autonomous Pull & Merge Logic.
        Handles dirty worktrees via stashing.
        """
        from skills.git_manager import git
        log_app(f"🔄 Federation: Checking {config.SHARED_GIT_REMOTE} for evolutions...")
        
        # 1. Fetch
        git._git(f"fetch {config.SHARED_GIT_REMOTE}")
        
        # 2. Check if we are behind
        status = git._git("status -uno")["stdout"]
        if "is behind" not in status and "can be fast-forwarded" not in status:
            return # Already in sync
            
        log_app("⚡ New evolution detected on remote. Syncing...")
        
        # 3. Handle dirty state
        is_dirty = "Changes not staged" in status or "Changes to be committed" in status
        if is_dirty:
            log_app("📦 Worktree dirty. Stashing local changes...")
            git._git("stash")
            
        # 4. Pull
        res = git._git(f"pull {config.SHARED_GIT_REMOTE} main")
        
        # 5. Restore dirty state
        if is_dirty:
            log_app("📦 Re-applying local stashed changes...")
            git._git("stash pop")
            
        if res["success"]:
            log_app("✨ Federation: System successfully synchronized and evolved.")
            return True
        return False

    async def broadcast_memory(self, fact: str):
        """Send a new learned fact to all siblings."""
        log_audit("FEDERATION", f"Broadcasting fact to {len(self.peers)} peers")
        for url in self.peers:
            try:
                await self.client.post(f"{url}/memory/learn", json={"fact": fact})
            except Exception as e:
                log_app(f"Failed to sync fact to {url}: {e}")

    async def should_start_bot(self) -> bool:
        """
        Deteremine if this instance should be the 'Leader' (Telegram active).
        Checks if any peer is already online.
        """
        if not self.peers:
            return True # Solo mode
            
        log_app("🌐 Federation: Checking peer status for Bot Election...")
        for url in self.peers:
            try:
                resp = await self.client.get(f"{url}/health", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("telegram_active") is True:
                        log_app(f"📡 Peer {url} is already LEADER. Entering Follower Mode (Bot OFF).")
                        return False
            except Exception:
                continue
        
        log_app("👑 No active leaders found. Claiming Leader Role (Bot ON).")
        return True

# Singleton
federation = SovereignFederation()
