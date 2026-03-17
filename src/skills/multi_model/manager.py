# ============================================================
# skills/multi_model/manager.py — Multi-Model LLM Manager
# Task-aware model selection, powered by ModelManager registry
# ============================================================

import asyncio
from settings import settings as config
from core.llm import call_llm, list_models
from core.model_manager import model_manager
from skills.logger import log_audit, log_app


def get_model(task_type: str = "default") -> str:
    """Get the appropriate model for a task type using ModelManager."""
    return model_manager.get_model_for_task(task_type)


def list_available_models() -> list[str]:
    """Query provider for available models."""
    try:
        return asyncio.run(list_models())
    except Exception as e:
        log_app(f"Failed to list models: {e}")
        return []


def generate(prompt: str, task_type: str = "default", 
              temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """Generate text using the appropriate model for the task type."""
    model = get_model(task_type)
    log_audit("LLM", f"[{task_type}] model={model}")

    try:
        return asyncio.run(call_llm(prompt, model=model, temperature=temperature))
    except Exception as e:
        log_audit("LLM_ERROR", f"[{task_type}] Generation failed: {e}")
        raise


def chat_completion(messages: list[dict], task_type: str = "chat") -> str:
    """Send a chat-style conversation to the provider."""
    model = get_model(task_type)

    try:
        prompt = messages[-1]["content"]
        system = messages[0]["content"] if messages[0]["role"] == "system" else None
        return asyncio.run(call_llm(prompt, model=model, system_prompt=system))
    except Exception as e:
        log_audit("LLM_ERROR", f"Chat completion failed: {e}")
        raise


def model_info(model: str = None) -> str:
    """Get detailed info about a model's capabilities."""
    return model_manager.get_model_info(model)


def format_models_summary() -> str:
    """Format available and configured models for display."""
    available = list_available_models()
    
    # Start with registry summary
    lines = [model_manager.format_registry_summary(), ""]
    
    # Add availability status
    lines.append("*Task Assignments:*")
    for task, model in config.OLLAMA_MODELS.items():
        status = "✅" if model in available else "⚠️"
        caps = model_manager.get_capabilities(model)
        flags = "👁️" if caps.is_multimodal else "📝"
        lines.append(f"  {status} {task}: `{model}` {flags}")

    if available:
        lines.append(f"\n*Available Models ({len(available)}):*")
        for m in available:
            lines.append(f"  • `{m}`")

    return "\n".join(lines)
