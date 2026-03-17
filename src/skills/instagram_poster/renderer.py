# ============================================================
# skills/instagram_poster/renderer.py — HTML-to-Image Rendering
# ============================================================

import os
from html2image import Html2Image
from settings import settings as config
from skills.logger import log_audit, log_app


def render_post(topic: str) -> str:
    """
    Inject the topic into the HTML template and render a
    1080×1080 JPEG image at config.TEMP_IMAGE_PATH.

    Returns:
        Absolute path to the generated image.
    """
    log_audit("RENDER", f"Rendering post image for topic: {topic}")

    with open(config.TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    with open(config.STYLE_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    html = html.replace("{{TOPIC}}", topic)

    try:
        hti = Html2Image(
            output_path=config.BASE_DIR,
            size=(1080, 1080),
        )

        filename = os.path.basename(config.TEMP_IMAGE_PATH)
        hti.screenshot(
            html_str=html,
            css_str=css,
            save_as=filename,
        )

        log_audit("RENDER", f"Image saved to {config.TEMP_IMAGE_PATH}")
        log_app(f"Post image rendered: {config.TEMP_IMAGE_PATH}")
        return config.TEMP_IMAGE_PATH

    except Exception as e:
        log_audit("RENDER_ERROR", f"html2image rendering failed: {e}")
        log_app(f"Rendering error: {e}")
        raise
