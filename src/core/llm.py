import json
import httpx
import asyncio
from settings import settings as config
from skills.logger import log_audit, log_app
from core.model_manager import model_manager
from core.utils.retry import async_retry

async def call_llm(prompt: str, model: str = None, system_prompt: str = None, stream: bool = False, format: str = None, images: list[str] = None, temperature: float = 0.7, timeout: int = None):
    """
    Unified LLM call interface supporting Ollama, SGLang, and Groq.
    Supports multimodal inputs (images) and parameter tuning.
    """
    # ─── Auto-Model Routing ─────────────────────────────
    # If no model is specified, route based on complexity
    if not model and not images:
        model = await model_manager.route_by_complexity(prompt, system_prompt)
        log_audit("LLM_ROUTING", f"Auto-routed to {model}")
    # ──────────────────────────────────────────────────

    # Intelligent default timeout: 30s for fast models, 300s for heavy
    if timeout is None:
        timeout = 30 if "fast" in (model or "").lower() or "0.8b" in (model or "").lower() else 300

    provider = getattr(config, "LLM_PROVIDER", "ollama").lower()
    
    from core.resource_governor import get_governor
    gov = get_governor()
    
    if provider == "groq" and not gov.is_exhausted("groq"):
        try:
            # Map model to valid Groq models (openai/gpt-oss-20b, openai/gpt-oss-120b, qwen/qwen3.8-27b)
            if model and ("gpt-oss" in model or "qwen3.8" in model):
                groq_model = model
            elif model and any(k in model.lower() for k in ["heavy", "35b", "reasoning", "architect", "120b"]):
                groq_model = config.GROQ_MODEL_HEAVY
            else:
                groq_model = config.GROQ_MODEL_FAST
            res = await _call_groq(prompt, groq_model, system_prompt, stream, format, images, temperature, timeout=timeout)
            gov.record_usage("groq")
            return res
        except Exception as e:
            log_app(f"Primary Groq failed, trying fallback chain: {e}")

    if provider == "openrouter" and not gov.is_exhausted("openrouter"):
        try:
            res = await _call_openrouter(prompt, model or config.OPENROUTER_MODEL_FREE, system_prompt, stream, format, images, temperature, timeout=timeout)
            gov.record_usage("openrouter")
            return res
        except Exception as e:
            log_app(f"Primary OpenRouter failed, trying fallback chain: {e}")

    # Default/Fallback Chain
    try:
        return await _call_ollama(prompt, model or config.OLLAMA_MODEL, system_prompt, stream, format, images, temperature, timeout=timeout)
    except Exception as e:
        log_app(f"Ollama failed ({e.__class__.__name__}). Checking if daemon is alive before fallback...")
        
        # Ping Ollama daemon
        is_ollama_alive = False
        base_url = model_manager.get_ollama_url()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{base_url}/")
                if resp.status_code == 200:
                    is_ollama_alive = True
        except Exception:
            pass
            
        if is_ollama_alive:
            log_app("Ollama daemon is ALIVE. Checking VRAM state and aggressively retrying local model (No Cloud Fallback).")
            # Check currently loaded models
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    ps_resp = await client.get(f"{base_url}/api/ps")
                    loaded_models = [m.get("name") for m in ps_resp.json().get("models", [])]
                    log_app(f"Currently loaded in VRAM: {loaded_models}")
            except Exception as ps_e:
                log_app(f"Failed to fetch /api/ps: {ps_e}")
                
            # Retry forcefully with extreme timeout
            log_app("Asserting strict Ollama usage. Increasing timeout to 900s.")
            return await _call_ollama(prompt, model or config.OLLAMA_MODEL, system_prompt, stream, format, images, temperature, timeout=900)
            
        log_app("Ollama daemon is DEAD or unreachable. Proceeding to Cloud Fallbacks.")
        
        # Try Groq if not exhausted
        if not images and not gov.is_exhausted("groq"):
            try:
                # MAP to Groq-compatible model
                fallback_model = config.GROQ_MODEL_HEAVY if any(k in (model or "").lower() for k in ["35b", "heavy", "120b", "reasoning", "architect"]) else config.GROQ_MODEL_FAST
                # Handle JSON enforcement
                prompt_to_send = prompt + " Return strictly JSON." if format == "json" else prompt
                res = await _call_groq(prompt_to_send, fallback_model, system_prompt, stream, format, None, 0.5, timeout=timeout)
                gov.record_usage("groq")
                return res
            except Exception as ge:
                log_app(f"Groq fallback failed: {ge}")
        
        # Try OpenRouter if not exhausted
        if not gov.is_exhausted("openrouter"):
            try:
                # Auto-patch deprecated models
                or_model = config.OPENROUTER_MODEL_FREE
                if "gemini-2.0-flash-exp" in or_model:
                    or_model = "google/gemini-2.0-flash-lite-preview-02-05:free"
                res = await _call_openrouter(prompt, or_model, system_prompt, stream, format, images, 0.5, timeout=timeout)
                gov.record_usage("openrouter")
                return res
            except Exception as oe:
                log_app(f"OpenRouter fallback failed: {oe}")
                
        raise e # Re-raise if everything failed

async def _call_openrouter(prompt: str, model: str, system_prompt: str, stream: bool, format: str, images: list[str] = None, temperature: float = 0.5, timeout: int = 120):
    """Fallback caller for OpenRouter."""
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/asura-ai", # OpenRouter recommendation
        "X-Title": "ASURA Autonomous AI",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    if images:
        content = [{"type": "text", "text": prompt}]
        for img in images:
            if not img.startswith("data:"):
                img = f"data:image/jpeg;base64,{img}"
            content.append({"type": "image_url", "image_url": {"url": img}})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "temperature": temperature,
    }
    if format == "json":
        payload["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            log_app(f"OpenRouter call failed: {e}")
            raise

async def _call_groq(prompt: str, model: str, system_prompt: str, stream: bool, format: str, images: list[str] = None, temperature: float = 0.5, timeout: int = 120):
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    if images:
        content = [{"type": "text", "text": prompt}]
        for img in images:
            # Handle both raw b64 and data: URLs
            if not img.startswith("data:"):
                img = f"data:image/jpeg;base64,{img}"
            content.append({"type": "image_url", "image_url": {"url": img}})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "temperature": temperature,
    }
    if format == "json":
        payload["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            log_app(f"Groq call failed: {e}")
            raise

@async_retry(retries=3, delay=5.0, backoff=2.0, exceptions=(httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout))
async def _call_ollama(prompt: str, model: str, system_prompt: str, stream: bool, format: str, images: list[str] = None, temperature: float = 0.7, timeout: int = 300):
    # Use /api/chat (universal)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    user_msg = {"role": "user", "content": prompt}
    if images:
        user_msg["images"] = images # Ollama chat API supports 'images' list in the message
    
    messages.append(user_msg)

    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": temperature,
        },
    }
    if format == "json":
        payload["format"] = "json"

    # FORCE NO PROXY for local Ollama calls
    mounts = {"all://": None}
    base_url = model_manager.get_ollama_url()
    async with httpx.AsyncClient(mounts=mounts, timeout=timeout, trust_env=False) as client:
        try:
            resp = await client.post(f"{base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "").strip()
        except Exception as e:
            log_app(f"Ollama call failed: {e}")
            raise

async def _call_sglang(prompt: str, model: str, system_prompt: str, stream: bool, format: str, images: list[str] = None, temperature: float = 0.7):
    """SGLang high-throughput caller."""
    base_url = model_manager.get_sglang_url()
    url = f"{base_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    if images:
        content = [{"type": "text", "text": prompt}]
        for img in images:
            if not img.startswith("data:"):
                img = f"data:image/jpeg;base64,{img}"
            content.append({"type": "image_url", "image_url": {"url": img}})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": prompt})
        
    caps = model_manager.get_capabilities(model)
    
    payload = {
        "model": model, 
        "messages": messages,
        "stream": stream,
        "temperature": temperature,
        "top_p": 0.95,
        "max_tokens": caps.max_output_tokens,
    }
    
    if format == "json":
        payload["response_format"] = {"type": "json_object"}
        payload["temperature"] = 0.0 # Force deterministic for JSON

    async with httpx.AsyncClient(timeout=120, limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]
            # Qwen3 thinking mode: content has the answer, reasoning_content has CoT
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning_content") or ""
            # Prefer final content; fall back to reasoning if content is empty
            result = content.strip() if content.strip() else reasoning.strip()
            return result if result else "(Model produced no output)"
        except Exception as e:
            err_msg = str(e)
            if hasattr(e, "response") and e.response:
                err_msg += f" | {e.response.text[:200]}"
            log_app(f"SGLang Turbo-Call Error: {err_msg}")
            raise
async def list_models():
    """List available models for the current provider."""
    provider = getattr(config, "LLM_PROVIDER", "ollama").lower()
    
    if provider == "groq":
        return [config.GROQ_MODEL]
        
    if provider == "sglang":
        base_url = model_manager.get_sglang_url()
        url = f"{base_url}/v1/models"
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                return [m["id"] for m in data.get("data", [])]
            except Exception as e:
                log_app(f"SGLang model list failed: {e}")
                return [model_manager.get_model_for_task("reasoning")]

    # Default: Ollama
    base_url = model_manager.get_ollama_url()
    url = f"{base_url}/api/tags"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return [m["name"] for m in models]
        except Exception as e:
            log_app(f"Ollama model list failed: {e}")
            return []
