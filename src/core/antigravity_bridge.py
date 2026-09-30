# ============================================================
# core/antigravity_bridge.py — Antigravity Agent & IDE Bridge
# Connects ASURA self-healing to Antigravity IDE / SWE-agent harness
# ============================================================

import os
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from settings import settings as config
from skills.logger import log_audit, log_app

INCIDENTS_DIR = os.path.join(config.BASE_DIR, ".agents", "incidents")
os.makedirs(INCIDENTS_DIR, exist_ok=True)


class AntigravityBridge:
    """
    Bridge connecting ASURA's internal autonomous runtime to
    Google Antigravity IDE / external agent harnesses.
    Enables Antigravity to autonomously discover, reproduce, and fix ASURA incidents.
    """

    def __init__(self):
        self.incidents_dir = INCIDENTS_DIR

    def record_incident(
        self,
        err_msg: str,
        tb: str,
        target_file: str,
        context_files: Optional[List[str]] = None,
        test_script: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a structured incident that Antigravity IDE can consume.
        """
        incident_id = f"inc_{int(time.time())}_{str(uuid.uuid4())[:6]}"
        incident_file = os.path.join(self.incidents_dir, f"{incident_id}.json")
        
        payload = {
            "id": incident_id,
            "timestamp": time.time(),
            "status": "OPEN",
            "error_message": err_msg,
            "traceback": tb,
            "target_file": target_file,
            "context_files": context_files or [],
            "test_script": test_script or "",
            "environment": {
                "base_dir": config.BASE_DIR,
                "python_executable": os.sys.executable,
                "llm_provider": getattr(config, "LLM_PROVIDER", "ollama"),
            }
        }

        try:
            with open(incident_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            log_audit("ANTIGRAVITY_INCIDENT", f"Incident recorded: {incident_id} ({target_file})")
            log_app(f"🛰️ Antigravity Incident recorded: {incident_id}. Ready for agentic repair.")
        except Exception as e:
            log_app(f"Failed to record Antigravity incident: {e}")

        # Also scaffold an automated test reproduction harness
        self._scaffold_reproduction_test(incident_id, target_file, err_msg, test_script)
        return payload

    def _scaffold_reproduction_test(self, incident_id: str, target_file: str, err_msg: str, test_script: Optional[str]):
        """Create a pytest reproduction test for SWE-bench-style verification."""
        inc_tests_dir = os.path.join(config.BASE_DIR, "tests", "incidents")
        os.makedirs(inc_tests_dir, exist_ok=True)
        test_file = os.path.join(inc_tests_dir, f"test_{incident_id}.py")
        
        content = f'''"""
Reproduction Harness for Incident {incident_id}
Target File: {target_file}
Error: {err_msg}
"""
import pytest
import subprocess
import sys
import os

def test_incident_resolution():
    """Verify that {target_file} compiles and imports without {err_msg[:40]}."""
    target_path = os.path.join("{config.BASE_DIR}", "{target_file}")
    assert os.path.exists(target_path), f"Target file missing: {{target_path}}"
    
    # 1. Syntax check
    res = subprocess.run([sys.executable, "-m", "py_compile", target_path], capture_output=True, text=True)
    assert res.returncode == 0, f"Syntax Error: {{res.stderr}}"
'''
        if test_script:
            content += f'''
    # 2. Behavioral verification
    test_code = """{test_script}"""
    res_b = subprocess.run([sys.executable, "-c", test_code], capture_output=True, text=True)
    assert res_b.returncode == 0, f"Behavioral test failed: {{res_b.stderr}}"
'''
        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

    def list_open_incidents(self) -> List[Dict[str, Any]]:
        """List all pending incidents awaiting agentic repair."""
        incidents = []
        if not os.path.isdir(self.incidents_dir):
            return []
        for fname in sorted(os.listdir(self.incidents_dir), reverse=True):
            if fname.endswith(".json"):
                fpath = os.path.join(self.incidents_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("status") == "OPEN":
                            incidents.append(data)
                except Exception:
                    pass
        return incidents

    def resolve_incident(self, incident_id: str, resolution_summary: str = "Resolved via agent"):
        """Mark an incident as resolved."""
        incident_file = os.path.join(self.incidents_dir, f"{incident_id}.json")
        if os.path.exists(incident_file):
            try:
                with open(incident_file, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    data["status"] = "RESOLVED"
                    data["resolved_at"] = time.time()
                    data["resolution"] = resolution_summary
                    f.seek(0)
                    json.dump(data, f, indent=2)
                    f.truncate()
                log_audit("ANTIGRAVITY_INCIDENT", f"Incident {incident_id} marked RESOLVED.")
            except Exception as e:
                log_app(f"Error marking incident {incident_id} resolved: {e}")


# Singleton
antigravity_bridge = AntigravityBridge()
