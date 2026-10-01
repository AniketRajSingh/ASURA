# ============================================================
# skills/device_control/visual_grounding.py — Visual Coordinate Grounding
#
# OmniParser-inspired visual coordinate grounding:
# - Overlays a non-destructive, high-contrast coordinate grid
#   onto screen captures so vision models can target buttons,
#   text, and links with 100% precision.
# - Translates scaled image coordinates back to physical display resolution.
# 100% Cross-Platform: Uses standard PIL (Pillow).
# ============================================================

from __future__ import annotations
import base64
from io import BytesIO
from typing import Tuple, Dict, Any, Optional

from PIL import Image, ImageDraw, ImageFont


class VisualGrounding:
    """
    Visual Grounding & Coordinate Normalization Engine.
    Enables vision models to perceive exact screen coordinates without hallucination.
    """

    @staticmethod
    def draw_coordinate_grid(
        image: Image.Image,
        grid_step: int = 100,
        line_color: Tuple[int, int, int, int] = (255, 0, 0, 90),
        text_color: Tuple[int, int, int] = (255, 255, 0),
    ) -> Image.Image:
        """
        Overlay an indexed coordinate grid on the image.
        Draws subtle gridlines and coordinate labels at grid intersections.
        """
        canvas = image.copy().convert("RGBA")
        overlay = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        w, h = canvas.size

        # Draw vertical lines & X labels
        for x in range(0, w, grid_step):
            draw.line([(x, 0), (x, h)], fill=line_color, width=1)
            draw.text((x + 2, 2), str(x), fill=text_color)

        # Draw horizontal lines & Y labels
        for y in range(0, h, grid_step):
            draw.line([(0, y), (w, y)], fill=line_color, width=1)
            draw.text((2, y + 2), str(y), fill=text_color)

        combined = Image.alpha_composite(canvas, overlay).convert("RGB")
        return combined

    @staticmethod
    def unscale_coordinates(
        coord: Tuple[int, int],
        scaled_size: Tuple[int, int],
        original_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """
        Map coordinates from the downscaled model observation
        back to the physical screen coordinates.
        """
        x, y = coord
        sw, sh = scaled_size
        ow, oh = original_size

        if sw == 0 or sh == 0:
            return (x, y)

        scale_x = ow / sw
        scale_y = oh / sh

        return (int(x * scale_x), int(y * scale_y))

    @staticmethod
    def encode_grounded_image(image: Image.Image, add_grid: bool = True) -> str:
        """Encode image to base64 JPEG, optionally with coordinate grid."""
        target_img = VisualGrounding.draw_coordinate_grid(image) if add_grid else image
        if target_img.mode != "RGB":
            target_img = target_img.convert("RGB")

        buffered = BytesIO()
        target_img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")


visual_grounding = VisualGrounding()
