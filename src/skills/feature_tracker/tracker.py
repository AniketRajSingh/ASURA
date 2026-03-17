# ============================================================
# skills/feature_tracker/tracker.py — Feature Evolution Tracker
#
# Tracks all features, detects when a new skill can replace
# or improve an existing one, and auto-upgrades usage.
# ============================================================

import os
import json
from datetime import datetime
import requests
from settings import settings as config
from skills.logger import log_audit, log_app


_TRACKER_PATH = os.path.join(config.DATA_DIR, "feature_registry.json")


def _load_registry() -> dict:
    if os.path.isfile(_TRACKER_PATH):
        try:
            with open(_TRACKER_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"features": {}, "replacements": [], "last_check": None}


def _save_registry(reg: dict):
    with open(_TRACKER_PATH, "w") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)


def register_feature(name: str, category: str, capability: str,
                     implementation: str, version: str = "1.0") -> dict:
    """Register a feature with its capability description."""
    reg = _load_registry()
    feature = {
        "name": name,
        "category": category,
        "capability": capability,
        "implementation": implementation,
        "version": version,
        "registered": datetime.now().isoformat(),
        "replaced_by": None,
        "active": True,
    }
    reg["features"][name] = feature
    _save_registry(reg)
    log_audit("TRACKER", f"Registered: {name} v{version}")
    return feature


def check_for_upgrades() -> list[dict]:
    """
    Analyze all features and check if any can be replaced
    by a better alternative. Uses LLM reasoning.
    """
    reg = _load_registry()
    features = reg.get("features", {})

    if len(features) < 2:
        return []

    # Build feature list for LLM analysis
    feature_list = "\n".join(
        f"- {name}: {f['capability']} (impl: {f['implementation']}, v{f['version']})"
        for name, f in features.items() if f.get("active")
    )

    from core.resource_governor import get_governor
    stats = get_governor().format_status_minimal()

    prompt = f"""Analyze these AI system features and identify if any truly need replacement.
System Context (Current Resources): {stats}

Currently tracked features:
{feature_list}

RULES:
1. RESTRICT to FREE, LOCAL, and LIGHTWEIGHT tools only.
2. DO NOT suggest paid APIs (e.g., GPT-4o, Pinecone, Google Cloud) or heavy infrastructure like Docker.
3. If current resources are stressed, prioritize optimization over adding new tech.
4. DO NOT suggest things that are already the active implementation.
5. If the implementation is already solid (e.g., Playwright, gTTS, FAISS), keep it.

Respond ONLY with JSON:
{{"upgrades": [
    {{"old": "feature_name", "new": "replacement", "reason": "why better AND lightweight", "confidence": 0.8}},
]}}

If everything is optimal or no free/local alternatives are better, return: {{"upgrades": []}}"""

    try:
        resp = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()

        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            upgrades = result.get("upgrades", [])

            # Store results
            reg["replacements"].extend(upgrades)
            reg["last_check"] = datetime.now().isoformat()
            _save_registry(reg)

            if upgrades:
                log_audit("TRACKER", f"Found {len(upgrades)} potential upgrades")
            return upgrades

    except Exception as e:
        log_audit("TRACKER_ERROR", f"Upgrade check failed: {e}")

    return []


def apply_replacement(old_name: str, new_name: str, reason: str):
    """Mark a feature as replaced by another."""
    reg = _load_registry()

    if old_name in reg["features"]:
        reg["features"][old_name]["active"] = False
        reg["features"][old_name]["replaced_by"] = new_name

    reg["replacements"].append({
        "old": old_name,
        "new": new_name,
        "reason": reason,
        "applied": datetime.now().isoformat(),
    })
    _save_registry(reg)
    log_audit("TRACKER", f"Replaced: {old_name} → {new_name} ({reason})")


def get_active_features() -> list[dict]:
    reg = _load_registry()
    return [f for f in reg["features"].values() if f.get("active")]


def get_replacement_history() -> list[dict]:
    reg = _load_registry()
    return reg.get("replacements", [])


def format_tracker_summary() -> str:
    reg = _load_registry()
    features = reg.get("features", {})
    active = [f for f in features.values() if f.get("active")]
    replaced = [f for f in features.values() if not f.get("active")]

    lines = [f"🔄 *Feature Evolution Tracker*\n"]
    lines.append(f"Active: {len(active)} | Replaced: {len(replaced)}")

    if replaced:
        lines.append("\n*Upgrades Applied:*")
        for f in replaced[-5:]:
            lines.append(f"  ↗️ {f['name']} → {f.get('replaced_by', '?')}")

    last = reg.get("last_check")
    if last:
        lines.append(f"\nLast check: {last[:16]}")

    return "\n".join(lines)


def auto_register_existing_features():
    """Auto-register all current skills as features."""
    features = [
        ("html_renderer", "content", "Convert HTML/CSS to images", "playwright", "1.0"),
        ("image_upload", "content", "Upload images to cloud CDN", "cloudinary", "1.0"),
        ("web_search", "intelligence", "Search the web for information", "duckduckgo_search", "1.0"),
        ("web_scraping", "intelligence", "Extract content from web pages", "beautifulsoup4", "1.0"),
        ("rag_memory", "memory", "Semantic memory storage and recall", "faiss+sentence-transformers", "1.0"),
        ("llm_generation", "ai", "Generate text with LLM", "ollama", "1.0"),
        ("shell_execution", "system", "Execute shell commands safely", "subprocess", "1.0"),
        ("browser_automation", "automation", "Browse and interact with web pages", "playwright", "1.0"),
        ("voice_transcription", "voice", "Speech-to-text conversion", "whisper", "1.0"),
        ("tts_synthesis", "voice", "Text-to-speech conversion", "gTTS", "1.0"),
        ("encryption", "security", "Encrypt/decrypt files and data", "cryptography/fernet", "1.0"),
        ("code_review", "dev", "Review code for quality and bugs", "ollama+prompts", "1.0"),
        ("doc_summarization", "intelligence", "Summarize documents and URLs", "ollama+prompts", "1.0"),
    ]

    for name, cat, cap, impl, ver in features:
        register_feature(name, cat, cap, impl, ver)
