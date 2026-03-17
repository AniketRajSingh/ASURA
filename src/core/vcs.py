import os
import difflib
import json
import time
from datetime import datetime
from typing import Optional
from settings import settings as config
from skills.logger import log_audit, log_app

VCS_DIR = os.path.join(config.PROJECT_ROOT, ".tf_vcs")
os.makedirs(VCS_DIR, exist_ok=True)

class InternalVCS:
    """
    Lightweight, patch-based version control for internal ASURA modifications.
    Uses difflib to store incremental changes instead of full copies.
    """
    
    def __init__(self):
        self.history_file = os.path.join(VCS_DIR, "history.json")
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w") as f:
                json.dump([], f)

    def _get_history(self):
        with open(self.history_file, "r") as f:
            return json.load(f)

    def _save_history(self, history):
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)

    def commit(self, filepath: str, original_content: str, new_content: str, message: str):
        """Record a change as a unified diff patch."""
        rel_path = os.path.relpath(filepath, config.PROJECT_ROOT)
        
        # Generate diff
        diff = list(difflib.unified_diff(
            original_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}"
        ))
        
        if not diff:
            return None # No change
            
        commit_id = f"tf_{int(time.time())}"
        patch_file = os.path.join(VCS_DIR, f"{commit_id}.patch")
        
        with open(patch_file, "w") as f:
            f.writelines(diff)
            
        entry = {
            "id": commit_id,
            "timestamp": datetime.now().isoformat(),
            "file": rel_path,
            "message": message,
            "patch": f"{commit_id}.patch"
        }
        
        history = self._get_history()
        history.append(entry)
        self._save_history(history)
        
        log_audit("VCS", f"Committed {commit_id}: {message} ({rel_path})")
        return commit_id

    def list_history(self, filepath: Optional[str] = None):
        history = self._get_history()
        if filepath:
            rel_path = os.path.relpath(filepath, config.PROJECT_ROOT)
            return [e for e in history if e["file"] == rel_path]
        return history

    def get_patch(self, commit_id: str) -> Optional[str]:
        """Read the patch content for a specific commit."""
        patch_path = os.path.join(VCS_DIR, f"{commit_id}.patch")
        if os.path.exists(patch_path):
            with open(patch_path, "r") as f:
                return f.read()
        return None

    def rollback(self, commit_id: str):
        """Apply the inverse of a patch to rollback a change."""
        # TODO: Implement proper patch application
        # For now, we mainly use this for tracking.
        pass

_vcs = InternalVCS()

def get_vcs():
    return _vcs
