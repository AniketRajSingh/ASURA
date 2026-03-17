# ============================================================
# core/doc_updater.py — Autonomous Documentation Daemon
#
# Automatically syncs SKILLS.md and ARCHITECTURE.md
# by inspecting the codebase and skill registry.
# ============================================================

import os
import time
import threading
from settings import settings as config
from skills.logger import log_audit, log_app
from skills.skill_registry import discover_skills


class DocUpdater:
    """
    Background daemon that keeps modular documentation in sync with code.
    Ensures ASURA's self-awareness stays up to date.
    """

    def __init__(self, notify_fn=None):
        self._notify = notify_fn
        self._running = False
        self._thread = None
        self.docs_dir = os.path.join(config.BASE_DIR, "docs")
        os.makedirs(self.docs_dir, exist_ok=True)

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="doc-updater"
        )
        self._thread.start()
        log_app("📚 DocUpdater daemon active")

    def stop(self):
        self._running = False

    def _loop(self):
        # Run immediately on startup
        try:
            self.update_all()
        except Exception as e:
            log_audit("DOC_ERROR", f"Initial sync failed: {e}")
        
        while self._running:
            time.sleep(12 * 3600)  # Sync every 12 hours
            if not self._running:
                break
            try:
                self.update_all()
            except Exception as e:
                log_audit("DOC_ERROR", f"Update loop failed: {e}")

    def update_all(self):
        """Perform a full documentation synchronization."""
        log_app("🔄 Syncing documentation...")
        self._sync_skills_registry()
        self._sync_core_reference_in_arch()
        log_app("✅ Documentation sync complete")

    def _sync_skills_registry(self):
        """Update docs/SKILLS.md with the latest tool registry."""
        registry = discover_skills()
        target = os.path.join(self.docs_dir, "SKILLS.md")
        
        # Read existing file to preserve headers if necessary, 
        # or just overwrite with a clean template since it's an arsenal doc.
        
        lines = [
            "# ASURA Capabilities Registry",
            f"> This file is autonomously maintained by the DocUpdater daemon.",
            f"> Last updated: {time.ctime()}\n",
            "ASURA possesses a modular 'Skill' architecture. Each skill is a self-contained capability that registers one or more tools into the MCP-Lite protocol.\n",
            "---",
            "\n## 🛠️ Active Skills Registry\n",
            "| Skill | Description | Path |",
            "|---|---|---|"
        ]

        # Table entries
        for name, info in sorted(registry.items()):
            desc = info.get('description', 'No description available.').replace("\n", " ")
            rel_path = os.path.relpath(info['path'], config.BASE_DIR)
            lines.append(f"| **{name}** | {desc} | `{rel_path}` |")

        lines.append("\n## 📦 Detailed Functional Breakdowns\n")

        # Detailed sections from SKILL.md files
        for name, info in sorted(registry.items()):
            lines.append(f"### {name.title().replace('_', ' ')}")
            lines.append(f"**Path:** `src/skills/{name}`  ")
            
            body = info.get('full_content', '')
            if "---" in body:
                parts = body.split("---")
                if len(parts) > 2:
                    body = parts[2].strip()
            lines.append(body + "\n")

        with open(target, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _sync_core_reference_in_arch(self):
        """Update the module table in ARCHITECTURE.md."""
        arch_path = os.path.join(self.docs_dir, "ARCHITECTURE.md")
        if not os.path.exists(arch_path):
            return

        core_dir = os.path.join(config.SRC_DIR, "core")
        if not os.path.isdir(core_dir):
            return

        module_lines = [
            "| Module | Purpose | File |",
            "|:---|:---|:---|"
        ]

        for fname in sorted(os.listdir(core_dir)):
            if fname.endswith(".py") and not fname.startswith("__"):
                fpath = os.path.join(core_dir, fname)
                purpose = "Unknown"
                
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        # Scan first 15 lines for a purpose
                        for _ in range(15):
                            line = f.readline()
                            if not line: break
                            if "—" in line:
                                purpose = line.split("—", 1)[1].strip()
                                break
                            elif "Purpose:" in line:
                                purpose = line.split("Purpose:", 1)[1].strip()
                                break
                except Exception: pass
                
                module_lines.append(f"| **{fname[:-3]}** | {purpose} | `src/core/{fname}` |")

        # Surgically replace the table in ARCHITECTURE.md
        with open(arch_path, "r", encoding="utf-8") as f:
            content = f.read()

        import re
        # Find the table between "## 3. Sovereign Core: Module Reference" and "---" or next header
        pattern = r"(## 3\. Sovereign Core: Module Reference\n\n)(.*?)(?=\n---|\n##)"
        new_table = "\n".join(module_lines)
        
        new_content = re.sub(pattern, r"\1" + new_table, content, flags=re.DOTALL)
        
        with open(arch_path, "w", encoding="utf-8") as f:
            f.write(new_content)
