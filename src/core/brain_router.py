# ============================================================
# core/brain_router.py — Dynamic Brain Router & Failover Engine
#
# Fetches live model metadata from OpenRouter API.
# Discovers free, vision, reasoning, and fast models dynamically.
# Intelligently selects the best model for ASURA Brain tasks.
# Tracks exhausted models (HTTP 429, timeouts, errors) with
# automatic cooldown and seamless failover to the next best model.
# ============================================================

from __future__ import annotations
import os
import time
import json
import asyncio
from typing import Optional, Any
from dataclasses import dataclass, asdict

import httpx
from settings import settings as config
from skills.logger import log_audit, log_app


@dataclass
class OpenRouterModelMeta:
    """Normalized metadata for a model fetched from OpenRouter."""
    id: str
    name: str
    context_length: int
    is_free: bool
    is_vision: bool
    is_reasoning: bool
    is_code: bool
    is_fast: bool
    prompt_price: float
    completion_price: float
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OpenRouterModelMeta":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            context_length=data.get("context_length", 4096),
            is_free=data.get("is_free", False),
            is_vision=data.get("is_vision", False),
            is_reasoning=data.get("is_reasoning", False),
            is_code=data.get("is_code", False),
            is_fast=data.get("is_fast", False),
            prompt_price=data.get("prompt_price", 0.0),
            completion_price=data.get("completion_price", 0.0),
            description=data.get("description", ""),
        )


class BrainRouter:
    """
    Central Brain Router for ASURA.
    - Synchronizes live model registry from OpenRouter.
    - Categorizes models into functional tiers (Free, Vision, Reasoning, Fast).
    - Maintains failover order across Local (Ollama) -> Cloud (Groq) -> OpenRouter.
    - Implements dynamic 429 rate-limit backoff and automatic exhaustion recovery.
    """

    _instance: Optional[BrainRouter] = None

    def __new__(cls) -> BrainRouter:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._cache_file = os.path.join(
            getattr(config, "DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")),
            "openrouter_models_cache.json"
        )
        self._cache_ttl = 3600 * 6  # 6 hours TTL
        self._cached_models: list[OpenRouterModelMeta] = []
        self._last_fetch_time: float = 0.0

        # Model exhaustion state: model_id -> {"cooldown_until": float, "reason": str, "timestamp": float}
        self._cooldowns: dict[str, dict] = {}
        
        # Local daemon liveness cache: {"alive": bool, "checked_at": float}
        self._ollama_health: dict[str, Any] = {"alive": None, "checked_at": 0.0}

        # User-selected active model override: (provider, model_name)
        self._active_override: Optional[tuple[str, str]] = None

        # Failover audit history (last 50 events)
        self._failover_history: list[dict] = []

        # Load existing cache from disk if available
        self._load_cache_from_disk()

    # ─── Cache & Model Fetching ────────────────────────────────

    def _load_cache_from_disk(self):
        """Load cached models from local disk if valid."""
        if not os.path.exists(self._cache_file):
            return
        try:
            with open(self._cache_file, "r") as f:
                data = json.load(f)
            self._last_fetch_time = data.get("timestamp", 0.0)
            raw_models = data.get("models", [])
            self._cached_models = [OpenRouterModelMeta.from_dict(m) for m in raw_models]
            log_app(f"BrainRouter: Loaded {len(self._cached_models)} models from disk cache.")
        except Exception as e:
            log_app(f"BrainRouter: Failed reading disk cache: {e}")

    def _save_cache_to_disk(self):
        """Persist model cache to disk."""
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            payload = {
                "timestamp": self._last_fetch_time,
                "count": len(self._cached_models),
                "models": [m.to_dict() for m in self._cached_models],
            }
            with open(self._cache_file, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            log_app(f"BrainRouter: Failed saving disk cache: {e}")

    async def fetch_openrouter_models(self, force: bool = False) -> list[OpenRouterModelMeta]:
        """
        Fetch models from OpenRouter API and classify them.
        Uses cached models if under TTL unless force=True.
        """
        now = time.time()
        if not force and self._cached_models and (now - self._last_fetch_time < self._cache_ttl):
            return self._cached_models

        api_key = getattr(config, "OPENROUTER_API_KEY", None)
        if not api_key:
            log_app("BrainRouter: OPENROUTER_API_KEY not configured, using cached or empty models.")
            return self._cached_models

        url = "https://openrouter.ai/api/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/asura-ai",
            "X-Title": "ASURA Autonomous AI",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            raw_models = data.get("data", [])
            parsed_models: list[OpenRouterModelMeta] = []

            for m in raw_models:
                mid = m.get("id", "")
                if not mid:
                    continue

                pricing = m.get("pricing", {})
                try:
                    p_prompt = float(pricing.get("prompt", 0))
                    p_comp = float(pricing.get("completion", 0))
                except (ValueError, TypeError):
                    p_prompt, p_comp = 0.0, 0.0

                is_free = mid.endswith(":free") or (p_prompt == 0.0 and p_comp == 0.0)

                arch = m.get("architecture", {})
                input_modalities = arch.get("input_modalities", [])
                is_vision = "image" in input_modalities

                name_lower = (m.get("name") or "").lower()
                desc_lower = (m.get("description") or "").lower()
                id_lower = mid.lower()

                is_reasoning = any(
                    k in id_lower or k in name_lower or k in desc_lower
                    for k in ["reason", "r1", "coder", "code", "ultra", "70b", "72b", "120b", "550b", "deepseek", "qwen"]
                )

                is_code = any(
                    k in id_lower or k in name_lower
                    for k in ["code", "coder", "starcoder", "deepseek-coder", "north-mini-code"]
                )

                is_fast = any(
                    k in id_lower or k in name_lower
                    for k in ["lightning", "flash", "instant", "mini", "2.6b", "small", "lfm", "0.8b"]
                )

                parsed_models.append(
                    OpenRouterModelMeta(
                        id=mid,
                        name=m.get("name", mid),
                        context_length=m.get("context_length", 4096),
                        is_free=is_free,
                        is_vision=is_vision,
                        is_reasoning=is_reasoning,
                        is_code=is_code,
                        is_fast=is_fast,
                        prompt_price=p_prompt,
                        completion_price=p_comp,
                        description=m.get("description", "")[:200],
                    )
                )

            self._cached_models = parsed_models
            self._last_fetch_time = now
            self._save_cache_to_disk()
            log_audit("BRAIN_ROUTER_FETCH", f"Fetched {len(parsed_models)} models from OpenRouter (Free: {len([m for m in parsed_models if m.is_free])})")
            return self._cached_models

        except Exception as e:
            log_app(f"BrainRouter: Failed fetching models from OpenRouter ({e}). Falling back to disk cache.")
            return self._cached_models

    # ─── Exhaustion & Cooldown Tracking ────────────────────────

    def mark_exhausted(self, model_id: str, reason: str = "Rate limited (429)", cooldown_seconds: int = 180):
        """
        Mark a model as temporarily exhausted (e.g. on HTTP 429 or timeout).
        Sets an automatic cooldown timestamp.
        """
        until = time.time() + cooldown_seconds
        self._cooldowns[model_id] = {
            "cooldown_until": until,
            "reason": reason,
            "timestamp": time.time(),
        }
        log_audit("MODEL_EXHAUSTED", f"Model {model_id} marked EXHAUSTED: {reason}. Cooldown for {cooldown_seconds}s.")
        log_app(f"BrainRouter: Model {model_id} exhausted -> backoff for {cooldown_seconds}s ({reason})")

    def is_exhausted(self, model_id: str) -> bool:
        """Check if a model is currently exhausted and in backoff."""
        info = self._cooldowns.get(model_id)
        if not info:
            return False

        if time.time() >= info.get("cooldown_until", 0):
            # Cooldown expired! Re-enable model
            del self._cooldowns[model_id]
            log_app(f"BrainRouter: Model {model_id} recovered from cooldown. Re-enabled.")
            return False

        return True

    def get_exhausted_models(self) -> dict[str, dict]:
        """Return dict of currently exhausted models with remaining cooldown seconds."""
        now = time.time()
        active = {}
        for mid, info in list(self._cooldowns.items()):
            remaining = info.get("cooldown_until", 0) - now
            if remaining > 0:
                active[mid] = {
                    "remaining_seconds": round(remaining, 1),
                    "reason": info.get("reason", "Unknown"),
                }
            else:
                del self._cooldowns[mid]
        return active

    def clear_exhaustion(self, model_id: Optional[str] = None):
        """Clear exhaustion cooldown for a specific model or all models."""
        if model_id:
            if model_id in self._cooldowns:
                del self._cooldowns[model_id]
                log_app(f"BrainRouter: Cleared exhaustion for {model_id}")
        else:
            self._cooldowns.clear()
            log_app("BrainRouter: Cleared all model exhaustion cooldowns.")

    def record_failover(self, from_model: str, to_model: str, reason: str):
        """Record a failover transition in history."""
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "from_model": from_model,
            "to_model": to_model,
            "reason": reason,
        }
        self._failover_history.append(entry)
        if len(self._failover_history) > 50:
            self._failover_history = self._failover_history[-50:]
        log_audit("BRAIN_FAILOVER", f"Switched from {from_model} to {to_model}: {reason}")

    # ─── Local Daemon Health ───────────────────────────────────

    async def is_ollama_alive(self, force_check: bool = False) -> bool:
        """Check if local Ollama daemon is responsive with 15s cache."""
        now = time.time()
        if not force_check and (now - self._ollama_health["checked_at"] < 15.0) and self._ollama_health["alive"] is not None:
            return self._ollama_health["alive"]

        from core.model_manager import model_manager
        base_url = model_manager.get_ollama_url()
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                resp = await client.get(f"{base_url}/")
                alive = resp.status_code == 200
        except Exception:
            alive = False

        self._ollama_health = {"alive": alive, "checked_at": now}
        return alive

    # ─── Candidate Cascade Generation ──────────────────────────

    async def get_candidates(
        self,
        task_type: str = "default",
        require_vision: bool = False,
        requested_model: Optional[str] = None
    ) -> list[dict]:
        """
        Generate an ordered list of candidate models for execution.
        Follows priority:
        1. Requested Model or Active Override (if not exhausted)
        2. Local Ollama (if alive and responsive)
        3. Groq (if not vision, API key configured, not exhausted)
        4. OpenRouter Free Pool (matching vision/reasoning/speed, non-exhausted)
        5. OpenRouter Auto-Free ('openrouter/free')
        6. OpenRouter Paid / Flagship Tier
        """
        candidates: list[dict] = []
        from core.resource_governor import get_governor
        gov = get_governor()

        # 1. Manual Override or Explicit Requested Model
        target_model = requested_model or (self._active_override[1] if self._active_override else None)
        target_provider = self._active_override[0] if self._active_override else None

        if target_model and not self.is_exhausted(target_model):
            provider = target_provider or ("openrouter" if "/" in target_model else getattr(config, "LLM_PROVIDER", "ollama"))
            candidates.append({
                "provider": provider,
                "model": target_model,
                "tier": "user_override",
                "is_local": provider == "ollama",
                "description": f"Explicit/Override target ({target_model})",
            })

        # 2. Local Ollama (Zero Latency & Privacy)
        ollama_alive = await self.is_ollama_alive()
        from core.model_manager import model_manager
        local_model = model_manager.get_model_for_task(task_type)

        if ollama_alive and not self.is_exhausted(local_model):
            # If user explicitly requested another provider as primary, local might already be added
            if not any(c["model"] == local_model for c in candidates):
                candidates.append({
                    "provider": "ollama",
                    "model": local_model,
                    "tier": "local_daemon",
                    "is_local": True,
                    "description": f"Local Ollama ({local_model})",
                })

        # 3. Groq High-Speed Tier (for text tasks)
        groq_key = getattr(config, "GROQ_API_KEY", None)
        if groq_key and not require_vision and not gov.is_exhausted("groq"):
            is_heavy = task_type in ("heavy", "reasoning", "code", "review") or "120b" in (target_model or "")
            groq_model = getattr(config, "GROQ_MODEL_HEAVY", "openai/gpt-oss-120b") if is_heavy else getattr(config, "GROQ_MODEL_FAST", "openai/gpt-oss-20b")
            
            if not self.is_exhausted(groq_model) and not any(c["model"] == groq_model for c in candidates):
                candidates.append({
                    "provider": "groq",
                    "model": groq_model,
                    "tier": "cloud_groq",
                    "is_local": False,
                    "description": f"Groq Ultra-Fast Cloud ({groq_model})",
                })

        # 4. OpenRouter Dynamic Free Models Pool
        or_key = getattr(config, "OPENROUTER_API_KEY", None)
        if or_key and not gov.is_exhausted("openrouter"):
            models = await self.fetch_openrouter_models()
            free_models = [m for m in models if m.is_free and not self.is_exhausted(m.id)]

            if require_vision:
                # Filter for vision capable models
                vision_pool = [m for m in free_models if m.is_vision]
                # Sort: preferred high-capacity vision models first
                preferred_order = [
                    "qwen/qwen3.8-27b:free",
                    "google/gemma-4-31b-it:free",
                    "google/gemma-4-26b-a4b-it:free",
                    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
                    "dots-studio/dots-3-note-preview:free",
                    "thinkingmachines/inkling:free",
                ]
                vision_pool.sort(key=lambda m: (0 if m.id in preferred_order else 1, preferred_order.index(m.id) if m.id in preferred_order else -m.context_length))

                for vm in vision_pool:
                    if not any(c["model"] == vm.id for c in candidates):
                        candidates.append({
                            "provider": "openrouter",
                            "model": vm.id,
                            "tier": "openrouter_free_vision",
                            "is_local": False,
                            "description": f"OpenRouter Free Vision ({vm.name})",
                        })
            else:
                # Text tasks: categorize according to task_type
                if task_type in ("heavy", "reasoning", "code", "review"):
                    reasoning_pool = [m for m in free_models if m.is_reasoning or m.is_code]
                    preferred_order = [
                        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
                        "nvidia/nemotron-3-ultra-550b-a55b:free",
                        "nvidia/nemotron-3-super-120b-a12b:free",
                        "cohere/north-mini-code:free",
                        "qwen/qwen3.8-27b:free",
                        "google/gemma-4-31b-it:free",
                    ]
                    reasoning_pool.sort(key=lambda m: (0 if m.id in preferred_order else 1, preferred_order.index(m.id) if m.id in preferred_order else -m.context_length))
                    for rm in reasoning_pool:
                        if not any(c["model"] == rm.id for c in candidates):
                            candidates.append({
                                "provider": "openrouter",
                                "model": rm.id,
                                "tier": "openrouter_free_reasoning",
                                "is_local": False,
                                "description": f"OpenRouter Free Reasoning ({rm.name})",
                            })

                # Fast / default pool
                fast_pool = [m for m in free_models if m.is_fast or not m.is_reasoning]
                preferred_fast = [
                    "nvidia/nemotron-3.5-lightning:free",
                    "liquid/lfm-2.5-2.6b:free",
                    "inclusionai/ling-3.0-flash-sante:free",
                    "thinkingmachines/inkling-small:free",
                ]
                fast_pool.sort(key=lambda m: (0 if m.id in preferred_fast else 1, preferred_fast.index(m.id) if m.id in preferred_fast else -m.context_length))
                for fm in fast_pool:
                    if not any(c["model"] == fm.id for c in candidates):
                        candidates.append({
                            "provider": "openrouter",
                            "model": fm.id,
                            "tier": "openrouter_free_fast",
                            "is_local": False,
                            "description": f"OpenRouter Free Fast ({fm.name})",
                        })

                # Append any remaining free models not already included
                for om in free_models:
                    if not any(c["model"] == om.id for c in candidates):
                        candidates.append({
                            "provider": "openrouter",
                            "model": om.id,
                            "tier": "openrouter_free_general",
                            "is_local": False,
                            "description": f"OpenRouter Free General ({om.name})",
                        })

                # Universal OpenRouter dynamic router alias
                if not self.is_exhausted("openrouter/free") and not any(c["model"] == "openrouter/free" for c in candidates):
                    candidates.append({
                        "provider": "openrouter",
                        "model": "openrouter/free",
                        "tier": "openrouter_free_auto",
                        "is_local": False,
                        "description": "OpenRouter Free Auto-Router",
                    })

        # 5. OpenRouter Paid/Heavy Fallbacks (when free tier is completely exhausted)
        if or_key and not gov.is_exhausted("openrouter"):
            if require_vision:
                paid_fallbacks = ["google/gemini-2.0-flash-001", "openai/gpt-4o-mini", "anthropic/claude-3.5-haiku"]
            else:
                paid_fallbacks = ["deepseek/deepseek-r1", "qwen/qwen-2.5-72b-instruct", "meta-llama/llama-3.3-70b-instruct"]
            for pm in paid_fallbacks:
                if not self.is_exhausted(pm) and not any(c["model"] == pm for c in candidates):
                    candidates.append({
                        "provider": "openrouter",
                        "model": pm,
                        "tier": "openrouter_paid_fallback",
                        "is_local": False,
                        "description": f"OpenRouter Flagship ({pm})",
                    })

        return candidates

    # ─── Model Switching & Control ─────────────────────────────

    def switch_model(self, model_id: str, provider: Optional[str] = None) -> str:
        """Explicitly switch active brain model."""
        if not provider:
            provider = "openrouter" if "/" in model_id else "ollama"
        self._active_override = (provider, model_id)
        # Clear any exhaustion on manually selected model
        self.clear_exhaustion(model_id)
        log_audit("BRAIN_SWITCH", f"Brain manually switched to {provider}:{model_id}")
        return f"Brain active model switched to **{model_id}** (Provider: `{provider}`)."

    def reset_to_automatic(self) -> str:
        """Reset manual override and return to fully autonomous cascade."""
        self._active_override = None
        log_audit("BRAIN_RESET", "Brain reset to autonomous dynamic cascade")
        return "Brain reset to **Autonomous Dynamic Cascade** (Local Ollama -> Groq -> OpenRouter Free Pool)."

    def get_status_summary(self) -> dict:
        """Comprehensive status for Gateway, Telegram, or CLI."""
        exhausted = self.get_exhausted_models()
        free_models = [m for m in self._cached_models if m.is_free]
        vision_models = [m for m in free_models if m.is_vision]
        reasoning_models = [m for m in free_models if m.is_reasoning]

        return {
            "active_override": self._active_override,
            "ollama_alive": self._ollama_health.get("alive"),
            "cached_models_count": len(self._cached_models),
            "free_models_count": len(free_models),
            "vision_models_count": len(vision_models),
            "reasoning_models_count": len(reasoning_models),
            "exhausted_models": exhausted,
            "recent_failovers": self._failover_history[-5:],
        }


# Global singleton instance
brain_router = BrainRouter()
