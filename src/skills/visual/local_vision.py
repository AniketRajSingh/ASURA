# ============================================================
# skills/visual/local_vision.py — Local Offline Multimodal Vision Engine
#
# Provides 100% private, air-gapped visual grounding:
# 1. Autodetects local vision models in Ollama (qwen2-vl, llava, minicpm-v, moondream)
# 2. Streams base64 screen perceptions locally with zero cloud leakage
# 3. Integrates with BrainRouter as Tier 0 vision provider
# 100% Cross-Platform: Works on macOS, Linux, Windows, and Raspberry Pi.
# ============================================================

from __future__ import annotations
import os
import base64
import json
import httpx
from typing import Optional, Dict, Any, List

from settings import settings as config
from skills.logger import log_audit, log_app


class LocalVisionEngine:
    """
    Offline multimodal perception engine using local Ollama daemon.
    Zero API cost, zero cloud latency, 100% data sovereignty.
    """
    KNOWN_VISION_FAMILIES = (
        "qwen2-vl",
        "llava",
        "minicpm-v",
        "moondream",
        "bakllava",
        "llama3.2-vision",
    )

    def __init__(self, ollama_url: Optional[str] = None):
        self._ollama_url = (ollama_url or getattr(config, "OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")
        self._cached_vision_model: Optional[str] = None

    def list_local_vision_models(self) -> List[str]:
        """Query local Ollama instance for installed vision models."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self._ollama_url}/api/tags")
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    vision_models = []
                    for m in models:
                        name = m.get("name", "").lower()
                        if any(fam in name for fam in self.KNOWN_VISION_FAMILIES):
                            vision_models.append(m.get("name"))
                    return vision_models
        except Exception:
            pass
        return []

    def is_available(self) -> bool:
        """Check if local Ollama daemon has at least one vision model."""
        return len(self.list_local_vision_models()) > 0

    def get_active_model(self) -> Optional[str]:
        """Return the best available local vision model."""
        models = self.list_local_vision_models()
        if not models:
            return None
        # Prefer Qwen2-VL or MiniCPM-V for high-accuracy UI grounding
        for pref in ["qwen2-vl", "minicpm-v", "llava"]:
            for m in models:
                if pref in m.lower():
                    return m
        return models[0]

    def analyze_image(
        self,
        image_source: str,
        prompt: str = "Describe what is on this screen in detail and locate interactive UI elements.",
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze an image or screenshot locally via Ollama.
        
        Args:
            image_source: Filepath or base64 data string.
            prompt: Question or instruction for visual grounding.
            model: Optional specific model name.
        """
        chosen_model = model or self.get_active_model()
        if not chosen_model:
            return {
                "success": False,
                "error": "No local vision model found in Ollama. Run: `ollama run qwen2-vl` or `ollama run llava`.",
            }

        # Normalize to base64
        if os.path.isfile(image_source):
            with open(image_source, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")
        elif image_source.startswith("data:image"):
            b64_img = image_source.split(",", 1)[-1]
        else:
            b64_img = image_source

        payload = {
            "model": chosen_model,
            "prompt": prompt,
            "images": [b64_img],
            "stream": False,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(f"{self._ollama_url}/api/generate", json=payload)
                if res.status_code == 200:
                    text_resp = res.json().get("response", "")
                    log_audit("LOCAL_VISION", f"Visual perception completed via {chosen_model}")
                    return {
                        "success": True,
                        "model": chosen_model,
                        "analysis": text_resp,
                        "offline": True,
                    }
                else:
                    return {"success": False, "error": f"Ollama error {res.status_code}: {res.text}"}
        except Exception as e:
            return {"success": False, "error": f"Local vision request failed: {e}"}


# Global singleton instance
local_vision = LocalVisionEngine()
