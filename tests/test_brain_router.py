# ============================================================
# tests/test_brain_router.py — Tests for ASURA Brain Router
# ============================================================

import pytest
import asyncio
import time
from core.brain_router import brain_router, OpenRouterModelMeta
from core.llm import call_llm


@pytest.mark.asyncio
async def test_brain_router_initialization_and_cache():
    """Verify brain_router initializes and has models loaded from cache or API."""
    models = await brain_router.fetch_openrouter_models()
    assert len(models) > 0
    assert any(m.is_free for m in models)


@pytest.mark.asyncio
async def test_brain_router_candidates_ranking():
    """Verify task classification yields appropriate candidate models."""
    # Vision candidates must be multimodal
    vision_candidates = await brain_router.get_candidates(task_type="vision", require_vision=True)
    assert len(vision_candidates) > 0
    vision_paid = ["google/gemini-2.0-flash-001", "openai/gpt-4o-mini", "anthropic/claude-3.5-haiku"]
    for cand in vision_candidates:
        if cand["provider"] == "openrouter":
            # Must be a vision model, openrouter/free, or recognized vision paid fallback
            assert cand["model"] == "openrouter/free" or cand["model"] in vision_paid or any(
                m.id == cand["model"] and m.is_vision for m in brain_router._cached_models
            )

    # Reasoning candidates
    reasoning_candidates = await brain_router.get_candidates(task_type="reasoning", require_vision=False)
    assert len(reasoning_candidates) > 0


@pytest.mark.asyncio
async def test_brain_router_exhaustion_and_backoff():
    """Verify mark_exhausted removes model from candidates and auto-recovers after expiry."""
    test_model = "test-provider/test-model-429"
    assert not brain_router.is_exhausted(test_model)

    # Mark exhausted for 2 seconds
    brain_router.mark_exhausted(test_model, reason="Rate limited 429", cooldown_seconds=2)
    assert brain_router.is_exhausted(test_model)
    exhausted_map = brain_router.get_exhausted_models()
    assert test_model in exhausted_map

    # Wait for cooldown to expire
    await asyncio.sleep(2.1)
    assert not brain_router.is_exhausted(test_model)


@pytest.mark.asyncio
async def test_brain_router_manual_switch_and_reset():
    """Verify manual brain model override and reset."""
    msg_switch = brain_router.switch_model("nvidia/nemotron-3.5-lightning:free", "openrouter")
    assert "nvidia/nemotron-3.5-lightning:free" in msg_switch
    assert brain_router._active_override == ("openrouter", "nvidia/nemotron-3.5-lightning:free")

    # Candidates should reflect override as first priority
    candidates = await brain_router.get_candidates()
    assert candidates[0]["model"] == "nvidia/nemotron-3.5-lightning:free"

    # Reset
    msg_reset = brain_router.reset_to_automatic()
    assert "Autonomous Dynamic Cascade" in msg_reset
    assert brain_router._active_override is None


@pytest.mark.asyncio
async def test_llm_automatic_failover_cascade(monkeypatch):
    """
    Test that when a candidate fails (e.g. 429 Rate Limit),
    call_llm marks it exhausted and cascades to the next candidate seamlessly.
    """
    import importlib.util
    import os
    src_llm_path = os.path.join(os.path.dirname(__file__), "..", "src", "core", "llm.py")
    spec = importlib.util.spec_from_file_location("real_core_llm", src_llm_path)
    real_llm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(real_llm)

    call_log = []

    async def mock_call_openrouter(prompt, model, system_prompt, stream, format, images=None, temperature=0.5, timeout=120):
        call_log.append(model)
        if "fail-model" in model:
            import httpx
            req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            resp = httpx.Response(429, request=req, text='{"error":{"message":"Rate limited"}}')
            raise httpx.HTTPStatusError("429 Rate Limit", request=req, response=resp)
        return "SUCCESS_FROM_FALLBACK"

    monkeypatch.setattr(real_llm, "_call_openrouter", mock_call_openrouter)

    # Set mock candidates
    async def mock_get_candidates(*args, **kwargs):
        return [
            {"provider": "openrouter", "model": "fail-model-1", "is_local": False},
            {"provider": "openrouter", "model": "success-model-2", "is_local": False},
        ]
    monkeypatch.setattr(brain_router, "get_candidates", mock_get_candidates)

    result = await real_llm.call_llm("Hello ASURA")
    assert result == "SUCCESS_FROM_FALLBACK"
    assert "fail-model-1" in call_log
    assert "success-model-2" in call_log
    assert brain_router.is_exhausted("fail-model-1")
