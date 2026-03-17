# ============================================================
# skills/ai_content/image_gen.py — Groq-Powered Image Generation
# ============================================================
import os
import requests
from settings import settings as config
from skills.logger import log_audit

def generate_image(prompt: str, aspect_ratio: str = "1:1") -> str:
    """
    Generate an image using Groq for prompt engineering and a free provider for generation.
    Returns the path to the generated image.
    """
    api_key = config.GROQ_API_KEY
    if not api_key:
        log_audit("IMAGE_GEN_ERROR", "Groq API key not found in config.")
        return ""

    log_audit("IMAGE_GEN", f"Generating: {prompt}")

    # Step 1: Use local Ollama to 'dream' a high-fidelity Stable Diffusion prompt
    try:
        ollama_prompt = f"""You are a master prompt engineer for Stable Diffusion.
Target: {prompt}
Goal: Create an extremely detailed, high-fidelity technical prompt that results in a professional, premium aesthetic.
Include: Lighting, texture, style, perspective, and negative keywords.
Return ONLY the final prompt text, no explanations."""

        resp = requests.post(f"{config.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": ollama_prompt,
                "stream": False
            },
            timeout=120
        )
        if resp.status_code != 200:
            log_audit("OLLAMA_ERROR", f"Local prompt engineering failed: {resp.text}")
            vision_prompt = prompt # Fallback to original
        else:
            vision_prompt = resp.json().get("response", "").strip()
            # Clean up potential markdown fences if the model added them
            vision_prompt = vision_prompt.replace("```", "").replace("Stable Diffusion Prompt:", "").strip()
            log_audit("IMAGE_GEN", f"Ollama 'Dreamed' Prompt: {vision_prompt[:100]}...")

    except Exception as e:
        log_audit("OLLAMA_ERROR", f"Ollama request failed: {e}")
        vision_prompt = prompt

    # Step 2: Use a free provider like Pollinations.ai (No API key needed, high reliability)
    # Pollinations supports /prompt?width=X&height=Y&model=flux
    # sanitize prompt for URL
    import urllib.parse
    safe_prompt = urllib.parse.quote(vision_prompt)
    
    width, height = 1024, 1024
    if aspect_ratio == "16:9": width, height = 1280, 720
    elif aspect_ratio == "9:16": width, height = 720, 1280

    gen_url = f"https://pollinations.ai/p/{safe_prompt}?width={width}&height={height}&seed={int(time.time())}&model=flux"
    
    try:
        img_resp = requests.get(gen_url, timeout=120)
        if img_resp.status_code == 200:
            fpath = os.path.join(config.ASSETS_DIR, f"gen_{int(time.time())}.jpg")
            with open(fpath, "wb") as f:
                f.write(img_resp.content)
            log_audit("IMAGE_GEN_SUCCESS", f"Image saved to: {fpath}")
            return fpath
    except Exception as e:
        log_audit("IMAGE_GEN_ERROR", f"Generation failed: {e}")

    return ""

# Add missing import
import time
