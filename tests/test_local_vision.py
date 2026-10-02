# ============================================================
# tests/test_local_vision.py — Verification of Local Multimodal Vision Engine
# ============================================================

import pytest
from skills.visual.local_vision import LocalVisionEngine, local_vision
from core.brain_router import brain_router


def test_local_vision_model_filtering(monkeypatch):
    engine = LocalVisionEngine()

    # Mock Ollama /api/tags response
    class MockResp:
        status_code = 200
        def json(self):
            return {
                "models": [
                    {"name": "llama3:latest"},
                    {"name": "qwen2-vl:7b"},
                    {"name": "mistral:latest"},
                    {"name": "llava:13b"},
                ]
            }

    class MockClient:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url): return MockResp()

    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: MockClient())

    models = engine.list_local_vision_models()
    assert "qwen2-vl:7b" in models
    assert "llava:13b" in models
    assert "llama3:latest" not in models
    assert engine.is_available() is True
    assert engine.get_active_model() == "qwen2-vl:7b"


def test_local_vision_analyze_mock(monkeypatch):
    engine = LocalVisionEngine()

    class MockResp:
        status_code = 200
        def json(self):
            return {"response": "Detected browser window and Submit button at (400, 320)."}

    class MockClient:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url):
            class R:
                status_code = 200
                def json(self): return {"models": [{"name": "qwen2-vl:7b"}]}
            return R()
        def post(self, url, json=None):
            return MockResp()

    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: MockClient())

    res = engine.analyze_image(
        image_source="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        prompt="Find Submit button",
    )
    assert res["success"] is True
    assert res["model"] == "qwen2-vl:7b"
    assert "Submit button" in res["analysis"]
    assert res["offline"] is True


@pytest.mark.asyncio
async def test_brain_router_incorporates_local_vision(monkeypatch):
    # Mock Ollama alive and local vision model available
    async def _mock_alive(*args, **kwargs):
        return True

    monkeypatch.setattr(brain_router, "is_ollama_alive", _mock_alive)
    monkeypatch.setattr(local_vision, "list_local_vision_models", lambda: ["qwen2-vl:latest"])

    candidates = await brain_router.get_candidates(require_vision=True)
    vision_tiers = [c for c in candidates if c.get("tier") == "local_offline_vision"]
    assert len(vision_tiers) > 0
    assert vision_tiers[0]["model"] == "qwen2-vl:latest"
    assert vision_tiers[0]["is_local"] is True
