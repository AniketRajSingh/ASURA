import json
import httpx
import asyncio
from settings import settings as config
from skills.logger import log_audit, log_app
from core.model_manager import model_manager
from core.utils.retry import async_retry

from core.brain_router import brain_router

async def call_llm(prompt: str, model: str = None, system_prompt: str = None, stream: bool = False, format: str = None, images: list[str] = None, temperature: float = 0.7, timeout: int = None):
    """
    Unified ASURA Brain call interface supporting Local Ollama, Groq, and OpenRouter.
    Features:
    - Dynamic OpenRouter model discovery and live metadata sync.
    - Automatic functional tier matching (Vision, Reasoning, Fast, Free).
    - Seamless cascade failover on HTTP 429 rate limit, 5xx server errors, or timeouts.
    - Automatic exhaustion tracking with temporary cooldown and recovery.
    """
    from core.resource_governor import get_governor
    gov = get_governor()

    # Determine task classification
    task_type = "default"
    if images:
        task_type = "vision"
    elif not model:
        prompt_lower = prompt.lower()
        fast_keywords = ["summary", "caption", "extract", "shorten", "list", "who", "what", "where", "translate", "greet", "hello", "hi"]
        heavy_keywords = ["reason", "think", "analyze", "debug", "fix", "code", "architect", "design", "refactor", "complex", "steps", "plan"]
        if len(prompt) < 200 and any(kw in prompt_lower for kw in fast_keywords):
            task_type = "fast"
        elif any(kw in prompt_lower for kw in heavy_keywords) or len(prompt) > 1000:
            task_type = "reasoning"

    # Intelligent default timeout
    if timeout is None:
        timeout = 35 if task_type == "fast" else 180

    # Obtain prioritized candidates from BrainRouter
    candidates = await brain_router.get_candidates(
        task_type=task_type,
        require_vision=bool(images),
        requested_model=model
    )

    if not candidates:
        log_app("BrainRouter: All candidate models currently exhausted. Resetting backoff cooldowns for emergency retry.")
        brain_router.clear_exhaustion()
        candidates = await brain_router.get_candidates(
            task_type=task_type,
            require_vision=bool(images),
            requested_model=model
        )

    log_audit("LLM_CASCADE_START", f"Task: {task_type} | Candidates ({len(candidates)}): {[c['model'] for c in candidates[:4]]}")

    cascade_errors = []

    for idx, cand in enumerate(candidates):
        prov = cand["provider"]
        cand_model = cand["model"]

        # Check governor limits for cloud providers
        if prov in ("groq", "openrouter") and gov.is_exhausted(prov):
            continue

        try:
            log_app(f"BrainRouter: Attempting [{prov}] {cand_model} (Candidate {idx+1}/{len(candidates)})")

            if prov == "ollama":
                res = await _call_ollama(prompt, cand_model, system_prompt, stream, format, images, temperature, timeout=timeout)
                return res
            elif prov == "groq":
                if images:
                    continue # Groq text endpoint does not accept images
                prompt_to_send = prompt + " Return strictly JSON." if format == "json" else prompt
                res = await _call_groq(prompt_to_send, cand_model, system_prompt, stream, format, None, temperature, timeout=timeout)
                gov.record_usage("groq")
                return res
            elif prov == "openrouter":
                res = await _call_openrouter(prompt, cand_model, system_prompt, stream, format, images, temperature, timeout=timeout)
                gov.record_usage("openrouter")
                return res
            elif prov == "sglang":
                res = await _call_sglang(prompt, cand_model, system_prompt, stream, format, images, temperature)
                return res
            else:
                log_app(f"BrainRouter: Unknown provider '{prov}', skipping candidate {cand_model}")
                continue

        except httpx.HTTPStatusError as hse:
            status_code = hse.response.status_code if hse.response else 0
            err_text = ""
            try:
                err_text = hse.response.text[:200]
            except Exception:
                pass

            # 429 Rate Limit (180s cooldown), 402/404 (300s cooldown), others (60s cooldown)
            cooldown = 180 if status_code == 429 else 300 if status_code in (402, 404) else 60
            reason = f"HTTP {status_code}: {err_text or hse}"
            brain_router.mark_exhausted(cand_model, reason=reason, cooldown_seconds=cooldown)

            next_model = candidates[idx + 1]["model"] if idx + 1 < len(candidates) else "NONE"
            brain_router.record_failover(cand_model, next_model, f"HTTP {status_code}")
            cascade_errors.append(f"[{prov}] {cand_model} -> HTTP {status_code}")
            log_app(f"BrainRouter: Model {cand_model} EXHAUSTED ({reason}). Cascading to next candidate {next_model}...")
            continue

        except (httpx.TimeoutException, httpx.ConnectError) as net_err:
            reason = f"Network/Timeout ({net_err.__class__.__name__})"
            brain_router.mark_exhausted(cand_model, reason=reason, cooldown_seconds=120)
            next_model = candidates[idx + 1]["model"] if idx + 1 < len(candidates) else "NONE"
            brain_router.record_failover(cand_model, next_model, reason)
            cascade_errors.append(f"[{prov}] {cand_model} -> {reason}")
            log_app(f"BrainRouter: Model {cand_model} unreachable/timed out. Cascading to next candidate {next_model}...")
            continue

        except Exception as e:
            reason = f"Execution error: {e}"
            brain_router.mark_exhausted(cand_model, reason=reason, cooldown_seconds=60)
            next_model = candidates[idx + 1]["model"] if idx + 1 < len(candidates) else "NONE"
            brain_router.record_failover(cand_model, next_model, str(e))
            cascade_errors.append(f"[{prov}] {cand_model} -> {e}")
            log_app(f"BrainRouter: Model {cand_model} failed ({e}). Cascading to next candidate {next_model}...")
            continue

    fail_msg = f"All ASURA Brain candidate models exhausted. Failures: {'; '.join(cascade_errors)}"
    log_audit("LLM_CASCADE_FAILED", fail_msg)
    raise RuntimeError(fail_msg)

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

    async with httpx.AsyncClient(timeout=timeout or 120) as client:
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

    async with httpx.AsyncClient(timeout=timeout or 120) as client:
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
        return [config.GROQ_MODEL, config.GROQ_MODEL_HEAVY]
        
    if provider == "openrouter":
        or_models = await brain_router.fetch_openrouter_models()
        return [m.id for m in or_models if m.is_free]
        
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
