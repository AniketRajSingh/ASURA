# ============================================================
# skills/graceful_mode/offline.py — Graceful Degradation
# Continue operating when Ollama or services are down
# ============================================================
import os, json
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit

_CACHE_PATH = os.path.join(config.BASE_DIR, "response_cache.json")
_QUEUE_PATH = os.path.join(config.BASE_DIR, "offline_queue.json")

def _load_cache(): return json.load(open(_CACHE_PATH)) if os.path.isfile(_CACHE_PATH) else {}
def _save_cache(d): json.dump(d, open(_CACHE_PATH, "w"), indent=2)
def _load_queue(): return json.load(open(_QUEUE_PATH)) if os.path.isfile(_QUEUE_PATH) else []
def _save_queue(d): json.dump(d, open(_QUEUE_PATH, "w"), indent=2)

def cache_response(prompt_key: str, response: str):
    cache = _load_cache()
    cache[prompt_key[:100]] = {"response": response, "cached": datetime.now().isoformat()}
    if len(cache) > 100:
        oldest = sorted(cache.items(), key=lambda x: x[1]["cached"])[:50]
        cache = dict(oldest)
    _save_cache(cache)

def get_cached(prompt_key: str) -> str:
    cache = _load_cache()
    entry = cache.get(prompt_key[:100])
    return entry["response"] if entry else None

def queue_for_later(task: str, args: dict = None):
    q = _load_queue()
    q.append({"task": task, "args": args or {}, "queued": datetime.now().isoformat()})
    _save_queue(q)
    log_audit("OFFLINE", f"Queued: {task}")

def process_offline_queue() -> int:
    q = _load_queue()
    if not q: return 0
    processed = 0
    remaining = []
    for item in q:
        try:
            from core.resource_governor import get_governor
            if get_governor().check_health()["ollama_alive"]:
                log_audit("OFFLINE", f"Processing: {item['task']}")
                processed += 1
            else:
                remaining.append(item)
        except: remaining.append(item)
    _save_queue(remaining)
    return processed

def get_offline_status() -> str:
    q = _load_queue()
    cache = _load_cache()
    return f"🔌 *Offline Mode*\nCached responses: {len(cache)}\nQueued tasks: {len(q)}"
