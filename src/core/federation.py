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

    async def sync_code(self):
        """
        Pull the latest updates from the shared Git remote.
        This allows one ASURA to 'teach' the other by pushing to Git.
        """
        log_app(f"🔄 Federation: Pulling updates from {config.SHARED_GIT_REMOTE}...")
        from skills.git_manager import git
        
        # 1. Fetch from shared remote
        res = git._git(f"fetch {config.SHARED_GIT_REMOTE}")
        if not res["success"]:
            log_audit("FEDERATION_ERROR", f"Git fetch failed: {res['stderr']}")
            return False

        # 2. Merge changes (assuming we use a stable branch like 'main')
        res = git._git(f"merge {config.SHARED_GIT_REMOTE}/main")
        if res["success"]:
            log_app("✨ Federation: Code synchronized with sibling.")
            # Trigger full system verification after code pull
            from core.startup_checks import run_startup_checks
            await run_startup_checks()
            return True
        else:
            log_audit("FEDERATION_WARN", f"Git merge conflict or failure: {res['stderr']}")
            return False

    async def broadcast_memory(self, fact: str):
        """Send a new learned fact to all siblings."""
        log_audit("FEDERATION", f"Broadcasting fact to {len(self.peers)} peers")
        for url in self.peers:
            try:
                await self.client.post(f"{url}/memory/learn", json={"fact": fact})
            except Exception as e:
                log_app(f"Failed to sync fact to {url}: {e}")

    async def remote_handoff(self, task: str, peer_url: str) -> Optional[str]:
        """Delegate a task to a sibling if local resources are high."""
        log_audit("FEDERATION", f"Delegating task to sibling: {peer_url}")
        try:
            resp = await self.client.post(f"{peer_url}/chat", json={
                "message": task,
                "user_id": "federated_master",
                "channel": "federation"
            })
            if resp.status_code == 200:
                return resp.json().get("reply")
        except Exception as e:
            log_app(f"Remote handoff failed: {e}")
        return None

# Singleton
federation = SovereignFederation()
