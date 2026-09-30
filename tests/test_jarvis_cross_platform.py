# ============================================================
# tests/test_jarvis_cross_platform.py — Tests for Consciousness,
# Unified Memory, and Cross-Platform Device Control
# ============================================================

import pytest
import asyncio
from core.consciousness import consciousness, Thought, MetacognitiveVerdict
from core.unified_memory import unified_memory
from skills.device_control.desktop_driver import desktop_driver
from skills.device_control.android_driver import android_driver
from core.tool_protocol import dispatch, _registry


def test_consciousness_engine_self_state():
    """Verify ConsciousnessEngine introspects hardware and environment."""
    state = consciousness.get_self_state()
    assert "environment" in state
    assert "vitals" in state
    assert "identity" in state
    assert state["identity"]["name"] == "ASURA"
    assert "system" in state["environment"]


def test_consciousness_stream_and_metacognition():
    """Verify inner monologue stream and pre-flight metacognitive checks."""
    # Inner monologue thought recording
    t = consciousness.record_thought("introspection", "Testing consciousness integrity", pulse="focused")
    assert isinstance(t, Thought)
    recent = consciousness.get_recent_thoughts(limit=5)
    assert any(th["content"] == "Testing consciousness integrity" for th in recent)

    # Safe action check
    verdict_safe = consciousness.metacognitive_check("read_file", {"path": "README.md"})
    assert isinstance(verdict_safe, MetacognitiveVerdict)
    assert verdict_safe.approved is True

    # Dangerous action check (must be rejected)
    verdict_danger = consciousness.metacognitive_check("shell", {"command": "rm -rf /"})
    assert verdict_danger.approved is False
    assert verdict_danger.risk_level == "critical"


def test_unified_memory_layers():
    """Verify all 4 memory layers function and persist."""
    # Layer 1: Identity Vault
    unified_memory.remember_fact("test_fact_key", "test_fact_val", category="test_cat")
    facts = unified_memory.recall_facts("test_cat")
    assert "test_fact_key" in facts
    assert facts["test_fact_key"]["value"] == "test_fact_val"

    # Layer 2: Working Memory Scratchpad
    unified_memory.set_working("active_test_task", "Running unit tests")
    assert unified_memory.get_working("active_test_task") == "Running unit tests"

    # Layer 3: Episodic Memory
    unified_memory.record_episode("unit_test_run", "testing memory", "passed", success=True)
    episodes = unified_memory.recall_recent_episodes(limit=3)
    assert len(episodes) > 0
    assert any(e["action"] == "unit_test_run" for e in episodes)

    # Layer 4: Procedural Memory
    unified_memory.store_procedure("test_recipe", ["step 1", "step 2"], "recipe description")
    recipe = unified_memory.recall_procedure("test_recipe")
    assert recipe is not None
    assert recipe["steps"] == ["step 1", "step 2"]


def test_cross_platform_device_drivers():
    """Verify pure cross-platform desktop capture and android driver."""
    # Desktop observation
    cap = desktop_driver.capture_screen()
    assert cap["success"] is True
    assert "base64_image" in cap
    assert len(cap["base64_image"]) > 0

    # Android driver discovery
    devices = android_driver.list_devices()
    assert isinstance(devices, list)


@pytest.mark.asyncio
async def test_jarvis_tool_protocol_dispatch():
    """Verify JARVIS tools are registered and dispatchable."""
    assert "device_task" in _registry
    assert "desktop_action" in _registry
    assert "android_action" in _registry

    # Dispatch desktop screen capture
    res_desk = await dispatch("desktop_action", {"action": "capture_screen"})
    assert "Captured screen" in res_desk

    # Dispatch android device listing
    res_android = await dispatch("android_action", {"action": "list_devices"})
    assert res_android is not None
