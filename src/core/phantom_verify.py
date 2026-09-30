# ============================================================
# core/phantom_verify.py — Ghost Sandbox Verification
# ============================================================

import os
import shutil
import subprocess
import tempfile
import sys
from typing import Dict, Any
from settings import settings as config
from skills.logger import log_audit, log_app

class PhantomVerifier:
    """
    Isolated sandbox for verifying autonomous fixes before commit.
    Creates a 'Phantom' clone of the system to test patches.
    """

    def __init__(self):
        self.temp_dir = None

    def create_sandbox(self) -> str:
        """Create a temporary clone of the current src directory."""
        self.temp_dir = tempfile.mkdtemp(prefix="asura_phantom_")
        phantom_src = os.path.join(self.temp_dir, "src")
        
        # Clone only src and critical config
        shutil.copytree(config.SRC_DIR, phantom_src)
        # Also copy core files from root
        for f in ["asura.py", "pyproject.toml", "run.py", "stop.py"]:
            src_f = os.path.join(config.BASE_DIR, f)
            if os.path.exists(src_f):
                shutil.copy2(src_f, self.temp_dir)
        
        return self.temp_dir

    def _resolve_sandbox_file(self, target_file: str) -> str:
        """Resolve a target file path accurately inside the sandbox."""
        if not self.temp_dir:
            return ""
        clean_target = os.path.relpath(target_file, config.BASE_DIR) if os.path.isabs(target_file) else target_file
        if clean_target.startswith(f"src{os.sep}") or clean_target.startswith("src/"):
            return os.path.join(self.temp_dir, clean_target)
        # Check if exists directly in src/
        if os.path.exists(os.path.join(self.temp_dir, "src", clean_target)):
            return os.path.join(self.temp_dir, "src", clean_target)
        return os.path.join(self.temp_dir, clean_target)

    def apply_patch(self, target_file: str, new_code: str):
        """Apply the generated fix to the sandbox file."""
        if not self.temp_dir: return False
        
        sandbox_file = self._resolve_sandbox_file(target_file)
        os.makedirs(os.path.dirname(sandbox_file), exist_ok=True)
        
        with open(sandbox_file, "w", encoding="utf-8") as f:
            f.write(new_code)
        return True

    async def verify(self, target_file: str, test_script: str = None) -> Dict[str, Any]:
        """
        Run verification in the sandbox.
        Checks for syntax, imports, and optional behavioral tests.
        """
        if not self.temp_dir:
            return {"success": False, "error": "Sandbox not initialized"}

        sandbox_file = self._resolve_sandbox_file(target_file)
        if not os.path.exists(sandbox_file):
            return {"success": False, "error": f"Target file not found in sandbox: {sandbox_file}"}
        
        # 1. Syntax Check
        try:
            subprocess.run([sys.executable, "-m", "py_compile", sandbox_file], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Syntax Error: {e.stderr.decode()}"}

        # 2. Import Check (Ghost Spawn)
        # Ensure phantom src/ is first in PYTHONPATH for correct relative imports
        phantom_src = os.path.join(self.temp_dir, "src")
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = phantom_src + os.pathsep + self.temp_dir + os.pathsep + env.get("PYTHONPATH", "")
            
            # Extract module name from file path relative to src
            if sandbox_file.startswith(phantom_src):
                rel = os.path.relpath(sandbox_file, phantom_src)
                mod_name = os.path.splitext(rel)[0].replace(os.sep, ".")
            else:
                rel = os.path.relpath(sandbox_file, self.temp_dir)
                mod_name = os.path.splitext(rel)[0].replace(os.sep, ".")
            
            subprocess.run(
                [sys.executable, "-c", f"import {mod_name}"], 
                cwd=self.temp_dir, env=env, check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Import Failure: {e.stderr.decode()}"}

        # 3. Behavioral Test (if provided)
        if test_script:
            try:
                subprocess.run(
                    [sys.executable, "-c", test_script],
                    cwd=self.temp_dir, env=env, check=True, capture_output=True
                )
            except subprocess.CalledProcessError as e:
                return {"success": False, "error": f"Logic Test Failed: {e.stderr.decode()}"}

        return {"success": True, "msg": "Phantom verification passed"}

    def cleanup(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

# Global helper
async def verify_fix_in_ghost(target_file: str, new_code: str, test_script: str = None) -> Dict[str, Any]:
    verifier = PhantomVerifier()
    try:
        verifier.create_sandbox()
        verifier.apply_patch(target_file, new_code)
        return await verifier.verify(target_file, test_script)
    finally:
        verifier.cleanup()
