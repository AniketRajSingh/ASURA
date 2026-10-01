# ============================================================
# skills/device_control/desktop_driver.py — Cross-Platform Desktop Driver
#
# Pure cross-platform desktop automation:
# - Screen capture via PIL.ImageGrab / mss
# - Mouse & Keyboard actuation via pyautogui / standard protocols
# - High-DPI coordinate scaling & Headless safety checks
# Runs identically on Linux, Windows, macOS, and Containers.
# ============================================================

from __future__ import annotations
import os
import time
import base64
from typing import Optional, Tuple, Dict, Any
from io import BytesIO

from PIL import Image, ImageGrab
from settings import settings as config
from skills.logger import log_audit, log_app


class CrossPlatformDesktopDriver:
    """
    Universal Desktop Automation Driver.
    Zero OS-specific locks. Runs on any platform with a display server,
    and degrades gracefully on headless servers/containers.
    """

    def __init__(self):
        self._has_display = self._check_display_availability()
        self._screen_width, self._screen_height = self._detect_screen_size()

    def _check_display_availability(self) -> bool:
        """Verify whether an active GUI display is available."""
        import platform
        system = platform.system().lower()
        if system == "linux":
            # On Linux, verify DISPLAY or WAYLAND_DISPLAY is set
            return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        return True

    def _detect_screen_size(self) -> Tuple[int, int]:
        """Detect screen width and height safely."""
        try:
            img = ImageGrab.grab()
            return img.size  # (width, height)
        except Exception:
            return (1920, 1080)

    # ─── Screen Observation ────────────────────────────────────

    def capture_screen(self, output_path: Optional[str] = None, max_dimension: int = 1280, add_grid: bool = False) -> Dict[str, Any]:
        """
        Capture the current desktop screen in a cross-platform manner.
        Downscales proportionally if width or height exceeds max_dimension to preserve token budget.
        Optionally overlays visual coordinate grid for grounded model reasoning.
        """
        try:
            img = None
            try:
                img = ImageGrab.grab()
            except Exception:
                pass

            if img is None:
                try:
                    from skills.visual.vision import take_screenshot
                    tmp_path = os.path.join(getattr(config, "DATA_DIR", "data"), "temp_capture.png")
                    take_screenshot(tmp_path)
                    if os.path.exists(tmp_path):
                        img = Image.open(tmp_path)
                except Exception:
                    pass

            if img is None:
                img = Image.new("RGB", (1280, 720), color=(30, 30, 30))

            orig_w, orig_h = img.size

            # Scale if larger than max_dimension
            ratio = 1.0
            if max(orig_w, orig_h) > max_dimension:
                ratio = max_dimension / max(orig_w, orig_h)
                new_w = int(orig_w * ratio)
                new_h = int(orig_h * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            else:
                new_w, new_h = orig_w, orig_h

            if add_grid:
                try:
                    from skills.device_control.visual_grounding import visual_grounding
                    img = visual_grounding.draw_coordinate_grid(img)
                except Exception:
                    pass

            if img.mode != "RGB":
                img = img.convert("RGB")

            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            if output_path:
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                img.save(output_path, format="JPEG", quality=85)

            log_audit("DESKTOP_CAPTURE", f"Screen captured: {orig_w}x{orig_h} (scaled: {new_w}x{new_h})")
            return {
                "success": True,
                "base64_image": img_b64,
                "original_size": (orig_w, orig_h),
                "scaled_size": (new_w, new_h),
                "scale_ratio": ratio,
            }
        except Exception as e:
            log_app(f"Desktop capture failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "has_display": self._has_display,
            }

    # ─── Actuation (Mouse & Keyboard) ──────────────────────────

    def mouse_move(self, x: int, y: int) -> Dict[str, Any]:
        """Move cursor to logical coordinates (x, y)."""
        try:
            import pyautogui
            pyautogui.moveTo(x, y)
            return {"success": True, "action": "mouse_move", "coordinates": (x, y)}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed in environment"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
        """Click at logical coordinates (x, y)."""
        try:
            import pyautogui
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            log_audit("DESKTOP_CLICK", f"{button.upper()} click at ({x}, {y}) [clicks={clicks}]")
            return {"success": True, "action": f"{button}_click", "coordinates": (x, y), "clicks": clicks}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed in environment"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> Dict[str, Any]:
        """Click and drag from (start_x, start_y) to (end_x, end_y)."""
        try:
            import pyautogui
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=duration, button="left")
            log_audit("DESKTOP_DRAG", f"Drag from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return {"success": True, "action": "drag", "from": (start_x, start_y), "to": (end_x, end_y)}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed in environment"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def type_text(self, text: str, interval: float = 0.02) -> Dict[str, Any]:
        """Type text into focused element with natural key interval."""
        try:
            import pyautogui
            pyautogui.write(text, interval=interval)
            log_audit("DESKTOP_TYPE", f"Typed {len(text)} characters")
            return {"success": True, "action": "type_text", "length": len(text)}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed in environment"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def press_key(self, key: str) -> Dict[str, Any]:
        """Press a key or key combination (e.g. 'enter', 'tab', 'esc', 'ctrl+c')."""
        try:
            import pyautogui
            if "+" in key:
                keys = [k.strip() for k in key.split("+")]
                pyautogui.hotkey(*keys)
            else:
                pyautogui.press(key)
            log_audit("DESKTOP_KEY", f"Pressed key/combo: {key}")
            return {"success": True, "action": "press_key", "key": key}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed in environment"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def scroll(self, clicks: int) -> Dict[str, Any]:
        """Scroll the mouse wheel (positive up, negative down)."""
        try:
            import pyautogui
            pyautogui.scroll(clicks)
            return {"success": True, "action": "scroll", "clicks": clicks}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed in environment"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global instance
desktop_driver = CrossPlatformDesktopDriver()
