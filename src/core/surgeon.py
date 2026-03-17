"""
core/surgeon.py
============================================================
The Sovereign OT (Operating Table) Protocol.
Creates a functional Minimal Run Environment (MRE) where ASURA 
can experiment, run sub-agents, and use tools in total isolation.
"""

import os
import subprocess
import time
import shutil
import sys
from typing import Tuple, List
from settings import settings as config
from skills.logger import log_audit, log_app

# The "Vital Organs" needed for ASURA to function inside the OT
CORE_MRE_BLUEPRINT = [
    "src/core",
    "src/config.py",
    "src/settings.py",
    "src/skills/__init__.py",
    "src/skills/skill_registry.py",
    "src/skills/dynamic_tools.py",
    "src/skills/logger",
    "src/skills/web_intelligence",
    "src/skills/shell_executor",
    "requirements.txt",
    "pyproject.toml",
    "ASURA.md"
]

class SurgicalRoom:
    """
    The OT Sandbox. A functional environment where ASURA can 'live' 
    and test itself while being modified.
    """
    def __init__(self, operation_id: str):
        self.operation_id = f"ot_{operation_id}"
        self.root = config.PROJECT_ROOT
        self.sandbox_dir = os.path.join(config.DATA_DIR, "surgery", self.operation_id)
        self.is_functional = False

    def _run_in_sandbox(self, cmd: list, env_extra: dict = None) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(self.sandbox_dir, "src")
        if env_extra:
            env.update(env_extra)
        return subprocess.run(cmd, capture_output=True, text=True, cwd=self.sandbox_dir, env=env)

    def __enter__(self):
        log_audit("SURGEON", f"🏥 Preparing Sovereign OT: {self.operation_id}")
        
        if os.path.exists(self.sandbox_dir):
            shutil.rmtree(self.sandbox_dir)
        os.makedirs(self.sandbox_dir, exist_ok=True)
        
        # 1. Scaffold the Minimal Run Environment (MRE)
        # We copy core files so the sandbox can actually execute Python code.
        for rel_path in CORE_MRE_BLUEPRINT:
            src = os.path.join(self.root, rel_path)
            dst = os.path.join(self.sandbox_dir, rel_path)
            
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

        # 2. Initialize Private Git for the OT
        self._run_in_sandbox(["git", "init"])
        self._run_in_sandbox(["git", "config", "user.name", "ASURA Surgeon"])
        self._run_in_sandbox(["git", "config", "user.email", "surgeon@asura.local"])
        self._run_in_sandbox(["git", "add", "."])
        self._run_in_sandbox(["git", "commit", "-m", "OT Initialized: System Vitals Active"])
        
        self.is_functional = True
        return self

    def add_target(self, rel_path: str):
        """Dynamically adds a specific file/skill to the OT if not in blueprint."""
        src = os.path.join(self.root, rel_path)
        dst = os.path.join(self.sandbox_dir, rel_path)
        
        if os.path.exists(src) and not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            self._run_in_sandbox(["git", "add", rel_path])
            self._run_in_sandbox(["git", "commit", "-m", f"Imported patient module: {rel_path}"])

    def simulate_execution(self, script_content: str) -> Tuple[bool, str]:
        """
        Actually RUNS ASURA logic inside the OT.
        This is where the agent can use its own web tools to verify its state.
        """
        temp_script = os.path.join(self.sandbox_dir, "ot_test_run.py")
        with open(temp_script, "w") as f:
            f.write(script_content)
            
        res = self._run_in_sandbox([sys.executable, "ot_test_run.py"])
        if res.returncode == 0:
            return True, res.stdout
        return False, f"EXECUTION FAILED:\n{res.stdout}\n{res.stderr}"

    def internal_commit(self, message: str):
        self._run_in_sandbox(["git", "add", "."])
        self._run_in_sandbox(["git", "commit", "-m", message])

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Eventually we cleanup old OT sessions, but keep the current one for a bit.
        pass

def perform_surgery(target_file: str, symbol_name: str, new_code: str, test_script: str = None) -> bool:
    """
    Standard Surgical Workflow for ALL development:
    1. Scaffold OT (Core + Target)
    2. Suture (AST Replace)
    3. Unit Test (Pytest in OT)
    4. Functional Test (Simulate Execution in OT)
    5. Promotion (Overwrite Live file)
    """
    op_id = str(int(time.time()))
    try:
        with SurgicalRoom(op_id) as room:
            from core.ast_surgeon import surgical_replace
            
            # Ensure target is in OT
            room.add_target(target_file)
            sandbox_target = os.path.join(room.sandbox_dir, target_file)
            
            # 1. Apply Scalpel
            if not target_file.endswith(".py"):
                # Plaintext fallback for HTML/CSS/JS files
                with open(sandbox_target, "r") as f:
                    content = f.read()
                if symbol_name in content:
                    content = content.replace(symbol_name, new_code)
                    with open(sandbox_target, "w") as f:
                        f.write(content)
                    success = True
                    msg = "Plaintext replacement successful."
                else:
                    success = False
                    msg = f"Symbol '{symbol_name}' not found in {sandbox_target}"
            else:
                success, msg = surgical_replace(sandbox_target, symbol_name, new_code)
                
            if not success:
                log_app(f"❌ Scalpel failed in OT: {msg}")
                return False
            
            room.internal_commit(f"Applied {symbol_name} update")
            
            # 2. Standard Simulation (Pytest)
            # Check if any tests exist for this target
            test_target = f"tests/test_{os.path.basename(target_file)}"
            room.add_target("tests") # Ensure tests dir is available
            
            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.join(room.sandbox_dir, "src")
            res = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/"],
                capture_output=True, text=True, cwd=room.sandbox_dir, env=env
            )
            
            if res.returncode != 0:
                log_app(f"❌ OT Pytest failed. Aborting surgery.")
                log_audit("OT_PYTEST_LOG", res.stdout + res.stderr)
                return False

            # 3. Functional Simulation (If provided)
            if test_script:
                passed, logs = room.simulate_execution(test_script)
                if not passed:
                    log_app(f"❌ OT Functional Test failed.")
                    log_audit("OT_FUNC_LOG", logs)
                    return False

            # 4. Promotion to Live
            live_path = os.path.join(room.root, target_file)
            shutil.copy2(sandbox_target, live_path)
            
            log_app(f"✅ OT Surgery Passed & Promoted: {target_file}")
            return True
                
    except Exception as e:
        log_app(f"❌ OT Surgery Error: {e}")
        import traceback
        log_audit("OT_EXCEPTION", traceback.format_exc())
        return False
