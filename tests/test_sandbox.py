# ============================================================
# tests/test_sandbox.py — Verification of Headless Sandbox Manager
# ============================================================

import pytest
from skills.sandbox.container_manager import sandbox_manager
from core.tool_protocol import dispatch


def test_sandbox_status_inspection():
    status = sandbox_manager.get_status()
    assert "available" in status
    assert "running" in status
    assert "virtual_display" in status
    assert status["virtual_display"] == ":99"


def test_sandbox_tool_dispatch():
    # Calling sandbox_status tool via MCP-Lite dispatch
    import asyncio
    output = asyncio.run(dispatch("sandbox_status", {}))
    assert ":99" in output or "available" in output


def test_sandbox_mock_isolated_execution(monkeypatch):
    # Test isolated command execution flow
    def _mock_is_docker():
        return True

    def _mock_get_status():
        return {"available": True, "running": True, "virtual_display": ":99"}

    class MockProc:
        returncode = 0
        stdout = "isolated_output_hello"
        stderr = ""

    def _mock_run(cmd, *args, **kwargs):
        return MockProc()

    monkeypatch.setattr(sandbox_manager, "is_docker_available", _mock_is_docker)
    monkeypatch.setattr(sandbox_manager, "get_status", _mock_get_status)
    monkeypatch.setattr("subprocess.run", _mock_run)

    res = sandbox_manager.execute_isolated_command("echo hello")
    assert res["success"] is True
    assert res["stdout"] == "isolated_output_hello"
    assert res["isolated"] is True
