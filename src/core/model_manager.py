# ============================================================
# core/model_manager.py — Model Capability Registry & Router
#
# Loads model capabilities from data/models.json at startup.
# Enables intelligent routing: multimodal models receive
# images directly; text-only models use separate vision tools.
# The JSON registry is editable without touching code.
# ============================================================

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from typing import Optional

from settings import settings as config
from skills.logger import log_app


@dataclass(frozen=True)
class ModelCapabilities:
    """Describes what a specific model can do."""
    # Identity
    display_name: str = "Unknown"
    architecture: str = "dense"        # "dense" or "moe"
    total_params: Optional[str] = None
    active_params: Optional[str] = None
    context_window: int = 4096
    max_output_tokens: int = 4096
    languages: int = 1

    # Multimodal sub-capabilities
    is_multimodal: bool = False
    can_see_images: bool = False
    can_see_video: bool = False
    can_hear_audio: bool = False
    can_web_search: bool = False

    # Core capabilities
    supports_tool_calling: bool = False
    supports_thinking: bool = False
    supports_json_output: bool = False
    supports_code_generation: bool = False
    supports_agentic: bool = False

    # Provider-specific hints
    provider_hints: dict = field(default_factory=dict)


# Default capabilities for unknown models (conservative)
_DEFAULT_CAPS = ModelCapabilities()

# ─── JSON Loading ─────────────────────────────────────────────

def _load_registry(json_path: str) -> dict[str, ModelCapabilities]:
    """Load model capabilities from a JSON file."""
    registry = {}
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        log_app(f"ModelManager: models.json not found at {json_path}, using empty registry")
        return registry
    except json.JSONDecodeError as e:
        log_app(f"ModelManager: Failed to parse models.json: {e}")
        return registry

    for model_key, info in data.items():
        if model_key.startswith("_"):  # Skip meta fields (_comment, _version)
            continue

        mm = info.get("multimodal", {})
        caps_dict = info.get("capabilities", {})
        hints = info.get("provider_hints", {})

        registry[model_key] = ModelCapabilities(
            display_name=info.get("display_name", model_key),
            architecture=info.get("architecture", "dense"),
            total_params=info.get("total_params"),
            active_params=info.get("active_params"),
            context_window=info.get("context_window", 4096),
            max_output_tokens=info.get("max_output_tokens", 4096),
            languages=info.get("languages", 1),
            # Multimodal
            is_multimodal=mm.get("enabled", False),
            can_see_images=mm.get("image", False),
            can_see_video=mm.get("video", False),
            can_hear_audio=mm.get("audio", False),
            can_web_search=mm.get("web_search", False),
            # Capabilities
            supports_tool_calling=caps_dict.get("tool_calling", False),
            supports_thinking=caps_dict.get("thinking_mode", False),
            supports_json_output=caps_dict.get("json_output", False),
            supports_code_generation=caps_dict.get("code_generation", False),
            supports_agentic=caps_dict.get("agentic", False),
            # Provider hints
            provider_hints=hints,
        )

    log_app(f"ModelManager: Loaded {len(registry)} models from {os.path.basename(json_path)}")
    return registry


class ModelManager:
    """Singleton that manages model selection and capability queries."""

    _instance: Optional[ModelManager] = None

    def __new__(cls) -> ModelManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Load registry on first instantiation
            json_path = os.path.join(
                getattr(config, "DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")),
                "models.json"
            )
            cls._instance._registry = _load_registry(json_path)
            
            # Load endpoint metadata if present
            try:
                with open(json_path, "r") as f:
                    data = json.load(f)
                    cls._instance._providers = data.get("_providers", {})
                    cls._instance._embedding = data.get("_embedding", {})
            except Exception as e:
                log_app(f"ModelManager: failed to load _providers: {e}")
                cls._instance._providers = {}
                cls._instance._embedding = {}
                
        return cls._instance

    # ─── Capability Queries ───────────────────────────────

    def get_capabilities(self, model: str = None) -> ModelCapabilities:
        """Look up capabilities for a model. Returns defaults for unknown models."""
        model = model or self.get_active_model()
        key = model.lower().split("/")[-1]
        caps = self._registry.get(key)
        if caps:
            return caps

        # Check dynamic brain router cache for OpenRouter models
        try:
            from core.brain_router import brain_router
            for m in brain_router._cached_models:
                if m.id.lower() == model.lower() or m.id.lower().endswith(f"/{key}"):
                    return ModelCapabilities(
                        display_name=m.name,
                        context_window=m.context_length,
                        max_output_tokens=min(m.context_length, 8192),
                        is_multimodal=m.is_vision,
                        can_see_images=m.is_vision,
                        supports_thinking=m.is_reasoning,
                        supports_code_generation=m.is_code,
                    )
        except Exception:
            pass

        return _DEFAULT_CAPS

    def is_multimodal(self, model: str = None) -> bool:
        """Check if the model can process any non-text input."""
        return self.get_capabilities(model).is_multimodal

    def can_see_images(self, model: str = None) -> bool:
        """Check if the model can directly process images."""
        return self.get_capabilities(model).can_see_images

    def can_see_video(self, model: str = None) -> bool:
        """Check if the model can directly process video."""
        return self.get_capabilities(model).can_see_video

    def can_web_search(self, model: str = None) -> bool:
        """Check if the model has built-in web search."""
        return self.get_capabilities(model).can_web_search

    def supports_tool_calling(self, model: str = None) -> bool:
        """Check if the model supports native function/tool calling."""
        return self.get_capabilities(model).supports_tool_calling

    def supports_thinking(self, model: str = None) -> bool:
        """Check if the model has a thinking/reasoning mode."""
        return self.get_capabilities(model).supports_thinking

    def get_context_window(self, model: str = None) -> int:
        """Get the context window size for a model."""
        return self.get_capabilities(model).context_window

    def get_max_output_tokens(self, model: str = None) -> int:
        """Get the max output tokens for a model."""
        return self.get_capabilities(model).max_output_tokens

    # ─── Model Selection ─────────────────────────────────

    def get_active_model(self) -> str:
        """Get the currently active model name based on brain router or provider config."""
        try:
            from core.brain_router import brain_router
            if brain_router._active_override:
                return brain_router._active_override[1]
        except Exception:
            pass

        provider = getattr(config, "LLM_PROVIDER", "ollama").lower()
        if provider == "groq":
            return getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile")
        elif provider == "openrouter":
            return getattr(config, "OPENROUTER_MODEL_FREE", "nvidia/nemotron-3.5-lightning:free")
        else:
            return getattr(config, "OLLAMA_MODEL", "gpt-oss:20b")

    async def route_by_complexity(self, prompt: str, system_prompt: str = None) -> str:
        """
        Analyze prompt complexity and route to either FAST or HEAVY model.
        
        Uses a 1-step heuristic (length + keywords) and optionally 
        a fast-model (0.8B) evaluation if the heuristic is ambiguous.
        """
        # 1. Heuristic: Simple/Fast indicators
        fast_keywords = [
            "summary", "caption", "extract", "shorten", "list", 
            "who", "what", "where", "translate", "greet", "hello", "hi"
        ]
        
        # Heuristic: Complex indicators
        heavy_keywords = [
            "reason", "think", "analyze", "debug", "fix", "code", 
            "architect", "design", "refactor", "complex", "steps", "plan"
        ]
        
        prompt_lower = prompt.lower()
        
        # Simple Length/Keyword Heuristic (Zero Latency)
        if len(prompt) < 200 and any(kw in prompt_lower for kw in fast_keywords):
            log_app("ModelManager: Heuristic Fast-Path (Small prompt + keywords)")
            return self.get_model_for_task("fast")

        if any(kw in prompt_lower for kw in heavy_keywords) or len(prompt) > 1000:
            log_app("ModelManager: Heuristic Heavy-Path (Large prompt or heavy keywords)")
            return self.get_model_for_task("reasoning")

        # 2. Dynamic Analysis: Use the 0.8B model to classify if still ambiguous
        # This adds ~200-500ms but prevents massive token waste on 35B
        log_app("ModelManager: Ambiguous complexity — requesting 0.8B evaluation")
        
        analysis_prompt = f"""Task: "{prompt[:300]}..."
Classification Rules:
- 'fast': Simple extraction, facts, greetings, or basic summaries.
- 'heavy': Logic, coding, multi-step planning, or deep analysis.

Respond with ONLY one word: fast OR heavy."""

        from core.llm import _call_ollama # Avoid circular import by using internal caller
        try:
            # We use a 2s timeout for classification to ensure it doesn't block
            decision = await _call_ollama(
                analysis_prompt, 
                model=self.get_model_for_task("fast"), 
                system_prompt="You are a task classifier.", 
                stream=False
            )
            
            if "heavy" in decision.lower():
                log_app("ModelManager: Classification Result -> HEAVY")
                return self.get_model_for_task("reasoning")
            else:
                log_app("ModelManager: Classification Result -> FAST")
                return self.get_model_for_task("fast")
                
        except Exception as e:
            log_app(f"ModelManager: Complexity analysis failed ({e}), defaulting to HEAVY for safety")
            return self.get_model_for_task("reasoning")

    def get_model_for_task(self, task_type: str = "default") -> str:
        """Get the best model for a specific task type."""
        provider = getattr(config, "LLM_PROVIDER", "ollama").lower()

        if provider == "groq":
            return {
                "default": getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile"),
                "heavy": getattr(config, "GROQ_MODEL_HEAVY", "llama-3.3-70b-versatile"),
                "reasoning": getattr(config, "GROQ_MODEL_HEAVY", "llama-3.3-70b-versatile"),
                "fast": getattr(config, "GROQ_MODEL_FAST", "llama-3.3-70b-specdec"),
                "summary": getattr(config, "GROQ_MODEL_FAST", "llama-3.1-8b-instant"),
                "review": getattr(config, "GROQ_MODEL_HEAVY", "llama-3.3-70b-versatile"),
                "caption": getattr(config, "GROQ_MODEL_FAST", "llama-3.1-8b-instant"),
                "code": getattr(config, "GROQ_MODEL_HEAVY", "llama-3.3-70b-versatile"),
            }.get(task_type, getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile"))

        # Map task types to standardized OLLAMA config variables
        model_map = {
            "default": getattr(config, "OLLAMA_MODEL", "gpt-oss:20b"),
            "reasoning": getattr(config, "OLLAMA_MODEL_REASONING", "gpt-oss:20b"),
            "vision": getattr(config, "OLLAMA_MODEL_VISION", "qwen3.5:0.8b"),
            "heavy_vision": getattr(config, "OLLAMA_MODEL", "gpt-oss:20b"),
            "caption": getattr(config, "OLLAMA_MODEL_CAPTION", "qwen3.5:0.8b"),
            "summary": getattr(config, "OLLAMA_MODEL_SUMMARY", "qwen3.5:0.8b"),
            "code": getattr(config, "OLLAMA_MODEL_CODE", "gpt-oss:20b"),
            "review": getattr(config, "OLLAMA_MODEL_REVIEWER", "gpt-oss:20b"),
            "intent": getattr(config, "OLLAMA_MODEL_INTENT", "qwen3.5:0.8b"),
            "fast": getattr(config, "OLLAMA_MODEL_FAST", "qwen3.5:0.8b"),
        }
        
        active_ollama = model_map.get(task_type, model_map["default"])
        
        # Dynamic Vision Routing (Contextual override)
        if task_type in ("vision", "caption", "heavy_vision"):
            # Use 20b for heavy vision tasks or if default is already 20b and multimodal
            if task_type == "heavy_vision":
                return model_map["default"] if "20b" in model_map["default"].lower() else "gpt-oss:20b"

            main_model = model_map["default"]
            if self.is_multimodal(main_model) and "20b" in main_model.lower():
                return main_model
            # Otherwise use the designated vision/caption model
            return active_ollama

        return active_ollama

    def can_handle_images(self, model: str = None) -> bool:
        """Should images be sent directly to the LLM?
        
        True = model is multimodal, send images inline (zero overhead).
        False = use separate vision tool pipeline.
        """
        model = model or self.get_active_model()
        can = self.can_see_images(model)
        if can:
            log_app(f"ModelManager: {model} can see images — routing directly")
        return can

    # ─── Endpoints & Resolution ───────────────────────────

    def get_ollama_url(self) -> str:
        """Get the base URL for Ollama."""
        # Check registry first
        if "ollama" in self._providers:
            registry_url = self._providers["ollama"].get("base_url")
            if registry_url:
                return getattr(config, "OLLAMA_BASE_URL", registry_url)
        return getattr(config, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    def get_sglang_url(self) -> str:
        """Get the base URL for SGLang."""
        if "sglang" in self._providers:
            registry_url = self._providers["sglang"].get("base_url")
            if registry_url:
                return getattr(config, "SGLANG_BASE_URL", registry_url)
        return getattr(config, "SGLANG_BASE_URL", "http://127.0.0.1:11435")

    def get_llm_url(self) -> str:
        """Get the base URL for the active LLM provider."""
        provider = getattr(config, "LLM_PROVIDER", "ollama").lower()
        
        if provider == "groq":
            return "https://api.groq.com/openai/v1"
        if provider == "sglang":
            return self.get_sglang_url()
        if provider == "openrouter":
            return "https://openrouter.ai/api/v1"
        
        return self.get_ollama_url()

    def get_embed_model(self) -> str:
        """Get the name of the embedding model to use."""
        return self._embedding.get("model", getattr(config, "EMBED_MODEL", "nomic-embed-text"))

    def get_embed_url(self) -> str:
        """Get the fully qualified URL for embeddings."""
        provider = self._embedding.get("provider", "ollama")
        endpoint = self._embedding.get("endpoint", "/api/embed")
        
        base_url = self.get_ollama_url()
        if provider == "sglang":
            base_url = self.get_sglang_url()

        return f"{base_url.rstrip('/')}{endpoint}"

    # ─── Registry Management ──────────────────────────────

    def reload_registry(self):
        """Hot-reload the models.json file without restarting."""
        json_path = os.path.join(config.DATA_DIR, "models.json")
        self._registry = _load_registry(json_path)

    def list_models(self) -> list[str]:
        """List all registered model names."""
        return list(self._registry.keys())

    # ─── Info & Debug ─────────────────────────────────────

    def get_model_info(self, model: str = None) -> str:
        """Human-readable summary of model capabilities."""
        model = model or self.get_active_model()
        caps = self.get_capabilities(model)
        
        flags = []
        if caps.can_see_images: flags.append("👁️ Image")
        if caps.can_see_video: flags.append("🎥 Video")
        if caps.can_hear_audio: flags.append("🎵 Audio")
        if caps.can_web_search: flags.append("🌐 Search")
        if caps.supports_tool_calling: flags.append("🔧 Tools")
        if caps.supports_thinking: flags.append("🧠 Thinking")
        if caps.supports_agentic: flags.append("🤖 Agentic")

        params = caps.total_params or "?"
        if caps.active_params:
            params = f"{caps.active_params} active / {caps.total_params} total"

        return (
            f"**{caps.display_name}** ({caps.architecture.upper()})\n"
            f"  Params: {params}\n"
            f"  Context: {caps.context_window:,} tokens\n"
            f"  Languages: {caps.languages}\n"
            f"  Capabilities: {' | '.join(flags) if flags else 'Basic'}"
        )

    def format_registry_summary(self) -> str:
        """Format all registered models for display."""
        lines = ["🤖 **Model Registry**\n"]
        active = self.get_active_model()
        for name in self._registry:
            caps = self._registry[name]
            marker = "▶️" if name == active else "  "
            flags = []
            if caps.can_see_images: flags.append("👁️")
            if caps.can_see_video: flags.append("🎥")
            if caps.supports_tool_calling: flags.append("🔧")
            if caps.supports_thinking: flags.append("🧠")
            if caps.supports_agentic: flags.append("🤖")
            params = f"{caps.active_params}/{caps.total_params}" if caps.active_params else caps.total_params
            lines.append(f"{marker} `{name}` ({params}) {' '.join(flags)}")
        return "\n".join(lines)


# ─── Singleton Instance ───────────────────────────────────────
model_manager = ModelManager()
