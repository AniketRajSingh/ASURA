---
name: visual
description: "Visual understanding skill optimized for Qwen3.5 Vision models, supporting image analysis, OCR, and UI debugging."
entry_point: vision.py
---

# Visual Intelligence

Multimodal vision capabilities optimized for **Qwen3.5 Vision (0.8B and 35B)**. Features direct routing to vision-capable LLMs for zero overhead.

### 🔧 Tools / Functions
- `analyze_image(image_path, question, heavy)`: Multi-purpose visual understanding and captioning.
- `ocr_image(image_path)`: Fast text extraction from any visual source.
- `describe_screenshot(image_path)`: Detailed UI element mapping and application identification.
- `take_screenshot(output_path)`: Capture the current system screen (macOS native).
- `debug_ui_screenshot(image_path, bug_description)`: Specialized 35B analysis for UI bug detection and CSS/HTML fix recommendations.

### 📝 Examples
- "What's in this screenshot?" -> Detailed breakdown of UI elements and content.
- "Find the bug in this UI" -> Analysis of visual glitches with suggested fixes.

### 🛠️ Requirements
- `screencapture` utility (macOS).
- Multimodal LLM (e.g., Qwen2-VL or Qwen2.5-VL).
