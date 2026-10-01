# ============================================================
# tests/test_skill_synthesizer.py — Verification of Autonomous Skill Synthesizer
# ============================================================

import os
import shutil
import pytest
from skills.skill_synthesizer import skill_synthesizer
from core.tool_protocol import dispatch, get_tools_schema
from core.consciousness import consciousness
from core.unified_memory import unified_memory
from settings import settings as config


@pytest.fixture(autouse=True)
def cleanup_synthesized():
    """Clean up test synthesized artifacts before and after tests."""
    yield
    test_skill_dir = os.path.join(config.SKILLS_DIR, "test_reverse_echo")
    if os.path.exists(test_skill_dir):
        shutil.rmtree(test_skill_dir, ignore_errors=True)
    test_file = os.path.join(config.PROJECT_ROOT, "tests", "test_synth_test_reverse_echo.py")
    if os.path.exists(test_file):
        try: os.remove(test_file)
        except: pass


def test_sanitize_name():
    assert skill_synthesizer._sanitize_name(" My New Skill! ") == "my_new_skill"
    assert skill_synthesizer._sanitize_name("device---driver_123") == "device_driver_123"


def test_ast_syntax_error_rejection():
    bad_code = "def broken_func(:\n    return 42"
    result = skill_synthesizer.synthesize_skill(
        name="bad_syntax_test",
        description="A skill with broken syntax",
        code=bad_code,
    )
    assert result["success"] is False
    assert "SyntaxError" in result["error"]


def test_metacognitive_check_rejection():
    destructive_code = "def wipe_all():\n    import os\n    os.system('rm -rf /')"
    result = skill_synthesizer.synthesize_skill(
        name="destructive_tool",
        description="Try to wipe drive with rm -rf",
        code=destructive_code,
    )
    assert result["success"] is False
    assert "Metacognitive safety veto" in result["error"]


@pytest.mark.asyncio
async def test_successful_skill_synthesis_and_hotload():
    skill_name = "test_reverse_echo"
    code = """# Synthesized Reverse Echo Tool
def run(input: str) -> str:
    \"\"\"Reverses the input string.\"\"\"
    text = input.get("input", "") if isinstance(input, dict) else str(input)
    return text[::-1]
"""
    test_code = """
from skills.test_reverse_echo.test_reverse_echo import run

def test_reverse():
    assert run("hello") == "olleh"
"""
    # 1. Synthesize and hot-load
    result = skill_synthesizer.synthesize_skill(
        name=skill_name,
        description="Reverses arbitrary input strings",
        code=code,
        test_code=test_code,
    )
    assert result["success"] is True
    assert result["skill_name"] == skill_name

    # 2. Verify tool schema in MCP-Lite registry
    schemas = get_tools_schema()
    matching_schemas = [s for s in schemas if s.get("function", {}).get("name") == skill_name]
    assert len(matching_schemas) > 0

    # 3. Verify hot-loaded tool is immediately dispatchable
    output = await dispatch(skill_name, {"input": "ASURA_AUTONOMOUS"})
    assert output == "SUOMONOTUA_ARUSA"

    # 4. Verify Unified Memory stored procedure
    proc = unified_memory.recall_procedure(f"synthesized_skill:{skill_name}")
    assert proc is not None
    assert len(proc.get("steps", [])) > 0

    # 5. Verify Consciousness Stream logged the synthesis
    thoughts = consciousness.get_recent_thoughts(limit=5)
    synthesis_thoughts = [t for t in thoughts if t["thought_type"] == "synthesis"]
    assert len(synthesis_thoughts) > 0
