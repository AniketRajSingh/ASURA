# ============================================================
# skills/skill_synthesizer.py — Autonomous Skill Synthesizer
#
# Enables ASURA to self-expand by:
# 1. Synthesizing new skill packages (SKILL.md + Python logic)
# 2. Enforcing syntax safety via AST parsing
# 3. Generating and executing automated verification tests
# 4. Dynamically registering tools into the MCP-Lite protocol
# 5. Storing synthesized capabilities in Unified Memory
# 100% Cross-Platform: Runs identically across Linux, Windows, macOS.
# ============================================================

from __future__ import annotations
import os
import re
import ast
import sys
import importlib
import subprocess
from typing import Optional, Dict, Any, List

from settings import settings as config
from skills.logger import log_audit, log_app
from core.tool_protocol import register_tool, dispatch
from core.consciousness import consciousness
from core.unified_memory import unified_memory


class SkillSynthesizer:
    """
    Autonomous capability generator and dynamic tool linker.
    Allows ASURA to write its own tools, verify them with tests, and load them live.
    """

    def __init__(self):
        self._skills_dir = config.SKILLS_DIR
        self._tests_dir = os.path.join(config.PROJECT_ROOT, "tests")

    def _sanitize_name(self, name: str) -> str:
        clean = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())
        clean = re.sub(r"_+", "_", clean).strip("_")
        return clean

    def synthesize_skill(
        self,
        name: str,
        description: str,
        code: str,
        tool_name: Optional[str] = None,
        test_code: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize, test, and hot-load a new skill.
        
        Args:
            name: Human or snake_case name of the skill.
            description: Concise description of what the skill does.
            code: Complete Python source code implementing the logic.
            tool_name: Unique tool name for MCP-Lite (defaults to name).
            test_code: Pytest test code to verify functionality.
            parameters: JSON schema parameters for the tool.
        """
        clean_name = self._sanitize_name(name)
        if not clean_name:
            return {"success": False, "error": "Invalid skill name."}

        active_tool_name = self._sanitize_name(tool_name or clean_name)

        # ── 1. Metacognitive Pre-Flight Safety Check ─────────
        verdict = consciousness.metacognitive_check(
            action_name=f"synthesize_skill:{clean_name}",
            parameters={"tool": active_tool_name, "description": description, "code": code}
        )
        if not verdict.approved:
            return {"success": False, "error": f"Metacognitive safety veto: {verdict.reasoning}"}

        # ── 2. Syntax Validation via AST ─────────────────────
        try:
            ast.parse(code)
        except SyntaxError as e:
            msg = f"SyntaxError in synthesized code: {e}"
            consciousness.record_thought("synthesis_error", msg, pulse="cautious")
            return {"success": False, "error": msg}

        if test_code:
            try:
                ast.parse(test_code)
            except SyntaxError as e:
                msg = f"SyntaxError in synthesized test code: {e}"
                consciousness.record_thought("synthesis_error", msg, pulse="cautious")
                return {"success": False, "error": msg}

        # ── 3. Scaffold Skill Directory ──────────────────────
        skill_path = os.path.join(self._skills_dir, clean_name)
        os.makedirs(skill_path, exist_ok=True)

        # Create SKILL.md
        skill_md_content = f"""---
name: {clean_name}
description: {description}
category: synthesized
tool_name: {active_tool_name}
---

# {clean_name.replace('_', ' ').title()}

{description}

## Usage
Synthesized autonomously by ASURA. Registered in MCP-Lite tool protocol as `{active_tool_name}`.
"""
        with open(os.path.join(skill_path, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(skill_md_content)

        # Create main implementation file
        impl_path = os.path.join(skill_path, f"{clean_name}.py")
        with open(impl_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Create __init__.py
        init_content = f"""# Autonomous Synthesized Skill: {clean_name}
from . import {clean_name}
"""
        with open(os.path.join(skill_path, "__init__.py"), "w", encoding="utf-8") as f:
            f.write(init_content)

        # ── 4. Automated Verification via Pytest ─────────────
        test_file_path = None
        if test_code:
            os.makedirs(self._tests_dir, exist_ok=True)
            test_file_path = os.path.join(self._tests_dir, f"test_synth_{clean_name}.py")
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", test_file_path, "-v"],
                    capture_output=True,
                    text=True,
                    cwd=config.PROJECT_ROOT,
                    timeout=30
                )
                if proc.returncode != 0:
                    err_out = proc.stderr or proc.stdout
                    log_app(f"❌ Synthesized test failed for {clean_name}:\n{err_out[:500]}")
                    consciousness.record_thought("synthesis_failed", f"Test failed for {clean_name}: {err_out[:100]}", pulse="cautious")
                    return {
                        "success": False,
                        "error": "Pytest verification failed",
                        "output": err_out[-1000:],
                        "skill_path": skill_path,
                    }
            except Exception as e:
                return {"success": False, "error": f"Test runner execution error: {e}"}

        # ── 5. Dynamic Hot-Loading & MCP-Lite Registration ───
        try:
            # Dynamically import module
            module_name = f"skills.{clean_name}.{clean_name}"
            if module_name in sys.modules:
                mod = importlib.reload(sys.modules[module_name])
            else:
                mod = importlib.import_module(module_name)

            # Discover entry callable (function named run, execute, main, or matching clean_name)
            candidate_fn = None
            for fn_name in [clean_name, "run", "execute", "handler", "main"]:
                if hasattr(mod, fn_name) and callable(getattr(mod, fn_name)):
                    candidate_fn = getattr(mod, fn_name)
                    break

            if not candidate_fn:
                # Find any public function defined in the module
                for attr_name in dir(mod):
                    if not attr_name.startswith("_"):
                        attr = getattr(mod, attr_name)
                        if callable(attr) and getattr(attr, "__module__", "") == module_name:
                            candidate_fn = attr
                            break

            if not candidate_fn:
                return {
                    "success": False,
                    "error": f"No callable function found in synthesized module {clean_name}.py",
                    "skill_path": skill_path,
                }

            # Register in MCP-Lite tool protocol
            register_tool(
                name=active_tool_name,
                function=candidate_fn,
                description=description,
                parameters=parameters or {
                    "type": "object",
                    "properties": {"input": {"type": "string", "description": "Input payload"}},
                    "required": ["input"],
                },
                category="synthesized",
            )
            log_audit("SKILL_SYNTHESIZED", f"Skill '{clean_name}' hot-loaded as tool '{active_tool_name}'")

        except Exception as e:
            return {"success": False, "error": f"Dynamic module load failed: {e}", "skill_path": skill_path}

        # ── 6. Unified Memory & Consciousness Update ─────────
        unified_memory.store_procedure(
            name=f"synthesized_skill:{clean_name}",
            description=description,
            steps=[
                f"Generated {clean_name} package in skills/{clean_name}",
                f"Verified AST syntax and schema",
                f"Passed test suite {os.path.basename(test_file_path)}" if test_file_path else "Verified syntax",
                f"Hot-loaded tool '{active_tool_name}' into tool protocol",
            ],
        )
        consciousness.record_thought(
            thought_type="synthesis",
            content=f"Successfully synthesized and hot-loaded new autonomous capability: '{active_tool_name}'",
            pulse="energized",
            metadata={"skill": clean_name, "tool": active_tool_name}
        )

        return {
            "success": True,
            "skill_name": clean_name,
            "tool_name": active_tool_name,
            "skill_path": skill_path,
            "test_file": test_file_path,
            "message": f"Skill '{clean_name}' successfully synthesized, tested, and registered as '{active_tool_name}'."
        }


# Global instance
skill_synthesizer = SkillSynthesizer()
