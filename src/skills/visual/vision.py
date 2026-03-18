# ============================================================
# skills/visual/vision.py — Visual Understanding (Qwen-Optimized)
# Smart routing: multimodal Qwen models get images directly.
# 0.8B for fast captioning, 35B for complex UI debugging.
# ============================================================
import os
import base64
import asyncio
from typing import Optional

from settings import settings as config
from skills.logger import log_audit
from core.model_manager import model_manager

"""
⚙️ **Vision Skill – Visual Understanding**

Optimized for Qwen3.5 Vision (0.8B and 35B). 
Routes images directly to the LLM for zero overhead.
"""

__all__ = ["analyze_image", "ocr_image", "describe_screenshot", "take_screenshot", "debug_ui_screenshot"]

def take_screenshot(output_path: str = "screenshot.png") -> str:
    """Capture the current system screen using native OS commands or pyautogui.
    
    Returns:
        Absolute path to the captured screenshot.
    """
    import platform, subprocess
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    abs_path = os.path.abspath(output_path)
    system = platform.system().lower()

    try:
        # 1. Try Native OS Commands (Zero-Dependency)
        if system == "darwin":
            # Mac Native
            subprocess.run(["screencapture", "-x", abs_path], check=True)
            return abs_path
        elif system == "windows":
            # Windows Native via PowerShell
            ps_cmd = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('%{{PRTSC}}'); $img = [System.Windows.Forms.Clipboard]::GetImage(); if($img) {{ $img.Save('{abs_path}', [System.Drawing.Imaging.ImageFormat]::Png) }}"
            subprocess.run(["powershell", "-Command", ps_cmd], check=True)
            if os.path.exists(abs_path): return abs_path
        elif system == "linux":
            # Linux Native (requires scrot or gnome-screenshot)
            for cmd in ["scrot", "gnome-screenshot", "import"]:
                try:
                    if cmd == "import": subprocess.run([cmd, "-window", "root", abs_path], check=True)
                    else: subprocess.run([cmd, abs_path], check=True)
                    return abs_path
                except: continue

        # 2. Fallback to PyAutoGUI if native fails
        import pyautogui
        ss = pyautogui.screenshot()
        ss.save(output_path)
        log_audit("VISION", f"Screenshot captured via pyautogui: {abs_path}")
        return abs_path

    except Exception as e:
        log_audit("VISION", f"Screenshot capture failed: {e}")
        return f"Error: {e}"


def _image_to_base64(path: str) -> Optional[str]:
    """Encode an image file to a base-64 string."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

def analyze_image(image_path: str, question: str = "Describe this image in detail.", heavy: bool = False) -> str:
    """Analyze an image using Qwen3.5 Vision.
    
    Args:
        image_path: Path to the image file.
        question: Prompt for the model.
        heavy: If True, uses the 35B model for deep reasoning.
    """
    if not os.path.isfile(image_path):
        return f"Image not found: {image_path}"

    img_b64 = _image_to_base64(image_path)
    if img_b64 is None:
        return f"Failed to read image: {image_path}"

    from core.llm import call_llm

    # ─── Qwen Vision Routing ────────────
    task_type = "heavy_vision" if heavy else "vision"
    vision_model = model_manager.get_model_for_task(task_type)
    
    try:
        log_audit("VISION", f"Routing to {vision_model} (heavy={heavy})")
        result = asyncio.run(call_llm(
            question, model=vision_model,
            images=[img_b64], stream=False
        ))
        if result:
            return result
    except Exception as e:
        log_audit("VISION", f"Vision call failed ({vision_model}): {e}")
        return f"Vision Error: {e}"

    return "No response from vision model."

def ocr_image(image_path: str) -> str:
    """Extract and list ALL text visible in this image."""
    return analyze_image(
        image_path, 
        "Extract and list ALL text visible in this image. Return only the text.",
        heavy=False
    )

def describe_screenshot(image_path: str) -> str:
    """Produce a detailed, UI-aware description of a screenshot using 35B."""
    ui_prompt = (
        "Describe this screenshot in detail. Identify all UI elements such as "
        "buttons, input fields, dropdowns, check-boxes, radio buttons, menus, "
        "and any interactive components. For each element, provide its label, "
        "position (if visible), and inferred purpose. Also describe the "
        "application being displayed and what the user is likely doing."
    )
    return analyze_image(image_path, ui_prompt, heavy=True)

def debug_ui_screenshot(image_path: str, bug_description: str = "Look for visual glitches or broken UI.") -> str:
    """Analyze a screenshot specifically for UI bugs and fixes using Qwen 35B."""
    debug_prompt = (
        f"CONTEXT: The user is reporting a UI issue: '{bug_description}'\n\n"
        "TASK: Analyze this screenshot carefully. \n"
        "1. Identify the specific UI component mentioned or any visible glitches.\n"
        "2. Check for layout shifts, overlapping elements, or broken styles.\n"
        "3. Provide a 'Surgical Fix' recommendation: Tell me exactly what CSS or HTML "
        "might be causing this and how to fix it."
    )
    return analyze_image(image_path, debug_prompt, heavy=True)
