# ============================================================
# skills/device_control/android_driver.py — Cross-Platform Android ADB Driver
#
# Standard ADB mobile device automation:
# - Device discovery over USB or Wi-Fi (TCP/IP)
# - Screen capture & UI Automator XML hierarchy parsing
# - Element finding by text, content-desc, or resource ID
# - Touch actuation: tap, swipe, type, key events, app launch
# 100% Cross-Platform: Works on Linux, Windows, macOS via ADB protocol.
# ============================================================

from __future__ import annotations
import os
import re
import shutil
import base64
import subprocess
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any, Tuple

from settings import settings as config
from skills.logger import log_audit, log_app


class AndroidDriver:
    """
    Universal Android ADB Automation Driver.
    Connects to physical Android phones or emulators via USB or Wi-Fi.
    """

    def __init__(self):
        self._adb_bin = self._find_adb()

    def _find_adb(self) -> str:
        """Find ADB executable across Linux, Windows, and macOS."""
        custom_path = getattr(config, "ADB_PATH", None)
        if custom_path and os.path.exists(custom_path):
            return custom_path
        
        found = shutil.which("adb")
        if found:
            return found

        # Common fallback paths
        fallbacks = [
            "/opt/homebrew/bin/adb",
            "/usr/local/bin/adb",
            "/usr/bin/adb",
            os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
            os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
            "C:\\platform-tools\\adb.exe",
        ]
        for fb in fallbacks:
            if os.path.exists(fb):
                return fb
        return "adb"

    def _run_cmd(self, args: List[str], timeout: int = 15) -> Tuple[int, bytes, str]:
        """Execute an ADB command safely."""
        cmd = [self._adb_bin] + args
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            return proc.returncode, proc.stdout, proc.stderr.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return -1, b"", "Command timed out"
        except Exception as e:
            return -1, b"", str(e)

    # ─── Device Discovery ──────────────────────────────────────

    def list_devices(self) -> List[Dict[str, str]]:
        """List all connected Android devices (USB & Wi-Fi)."""
        code, stdout, stderr = self._run_cmd(["devices"])
        devices = []
        if code != 0:
            log_app(f"ADB devices call failed: {stderr}")
            return devices

        lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
        for line in lines[1:]:
            parts = line.strip().split()
            if len(parts) >= 2:
                devices.append({
                    "device_id": parts[0],
                    "status": parts[1],
                })
        return devices

    def connect_wifi(self, ip_port: str) -> Dict[str, Any]:
        """Connect to an Android device over Wi-Fi (e.g. '192.168.1.150:5555')."""
        code, stdout, stderr = self._run_cmd(["connect", ip_port])
        out_str = stdout.decode("utf-8", errors="replace")
        success = "connected" in out_str.lower()
        log_audit("ADB_CONNECT", f"Wi-Fi connection to {ip_port}: {'Success' if success else 'Failed'}")
        return {"success": success, "output": out_str.strip()}

    # ─── Screen Observation ────────────────────────────────────

    def capture_screen(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Capture screenshot from Android device as base64 JPEG."""
        args = ["-s", device_id] if device_id else []
        args.extend(["exec-out", "screencap", "-p"])

        code, raw_bytes, err = self._run_cmd(args, timeout=10)
        if code != 0 or not raw_bytes:
            return {"success": False, "error": err or "Failed capturing screen"}

        try:
            from io import BytesIO
            from PIL import Image
            img = Image.open(BytesIO(raw_bytes))
            orig_w, orig_h = img.size

            # Downscale proportionally for token efficiency
            max_dim = 1280
            if max(orig_w, orig_h) > max_dim:
                ratio = max_dim / max(orig_w, orig_h)
                new_w, new_h = int(orig_w * ratio), int(orig_h * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            else:
                new_w, new_h = orig_w, orig_h

            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=80)
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            return {
                "success": True,
                "base64_image": img_b64,
                "dimensions": (orig_w, orig_h),
                "scaled_dimensions": (new_w, new_h),
            }
        except Exception as e:
            return {"success": False, "error": f"Image processing failed: {e}"}

    def dump_ui_hierarchy(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Dump and parse UI Automator XML hierarchy into structured UI nodes.
        Enables 100% reliable element finding without visual hallucination.
        """
        args = ["-s", device_id] if device_id else []
        args.extend(["exec-out", "uiautomator", "dump", "/dev/tty"])

        code, stdout, err = self._run_cmd(args, timeout=10)
        if code != 0 or not stdout:
            return []

        xml_str = stdout.decode("utf-8", errors="replace")
        nodes = []

        try:
            # Clean possible preamble
            start_idx = xml_str.find("<?xml")
            if start_idx != -1:
                xml_str = xml_str[start_idx:]
            
            root = ET.fromstring(xml_str)
            for elem in root.iter("node"):
                text = elem.attrib.get("text", "")
                desc = elem.attrib.get("content-desc", "")
                res_id = elem.attrib.get("resource-id", "")
                bounds = elem.attrib.get("bounds", "")

                if bounds:
                    # Parse bounds e.g. "[0,0][1080,2400]"
                    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                    if m:
                        x1, y1, x2, y2 = map(int, m.groups())
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2

                        if text or desc or res_id:
                            nodes.append({
                                "text": text,
                                "content_desc": desc,
                                "resource_id": res_id,
                                "bounds": (x1, y1, x2, y2),
                                "center": (center_x, center_y),
                                "clickable": elem.attrib.get("clickable") == "true",
                            })
        except Exception as e:
            log_app(f"UI hierarchy parse error: {e}")

        return nodes

    def find_element(self, text_or_pattern: str, device_id: Optional[str] = None) -> Optional[Tuple[int, int]]:
        """Find the center coordinates of an element by text, description, or resource ID."""
        nodes = self.dump_ui_hierarchy(device_id)
        target = text_or_pattern.lower()

        for n in nodes:
            if target in n["text"].lower() or target in n["content_desc"].lower() or target in n["resource_id"].lower():
                return n["center"]
        return None

    # ─── Touch & Input Actuation ───────────────────────────────

    def tap(self, x: int, y: int, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Tap at screen coordinates (x, y)."""
        args = ["-s", device_id] if device_id else []
        args.extend(["shell", "input", "tap", str(x), str(y)])
        code, _, err = self._run_cmd(args)
        log_audit("ANDROID_TAP", f"Tap at ({x}, {y}) on device {device_id or 'default'}")
        return {"success": code == 0, "action": "tap", "coordinates": (x, y), "error": err if code != 0 else None}

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Swipe from (x1, y1) to (x2, y2)."""
        args = ["-s", device_id] if device_id else []
        args.extend(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])
        code, _, err = self._run_cmd(args)
        log_audit("ANDROID_SWIPE", f"Swipe ({x1},{y1}) -> ({x2},{y2})")
        return {"success": code == 0, "action": "swipe", "from": (x1, y1), "to": (x2, y2), "error": err if code != 0 else None}

    def type_text(self, text: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Type text into focused element."""
        # Spaces in ADB text must be escaped as %s
        escaped = text.replace(" ", "%s")
        args = ["-s", device_id] if device_id else []
        args.extend(["shell", "input", "text", escaped])
        code, _, err = self._run_cmd(args)
        log_audit("ANDROID_TYPE", f"Typed {len(text)} chars on mobile device")
        return {"success": code == 0, "action": "type_text", "error": err if code != 0 else None}

    def press_key(self, key_name: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Press an Android system key.
        Supports: HOME, BACK, ENTER, APP_SWITCH, VOLUME_UP, VOLUME_DOWN, POWER.
        """
        key_map = {
            "home": 3,
            "back": 4,
            "enter": 66,
            "return": 66,
            "app_switch": 187,
            "recent": 187,
            "volume_up": 24,
            "volume_down": 25,
            "power": 26,
            "delete": 67,
            "backspace": 67,
        }
        key_code = key_map.get(key_name.lower())
        if not key_code:
            try:
                key_code = int(key_name)
            except ValueError:
                return {"success": False, "error": f"Unknown key name: {key_name}"}

        args = ["-s", device_id] if device_id else []
        args.extend(["shell", "input", "keyevent", str(key_code)])
        code, _, err = self._run_cmd(args)
        log_audit("ANDROID_KEY", f"Keyevent {key_name} ({key_code})")
        return {"success": code == 0, "action": "press_key", "key": key_name, "error": err if code != 0 else None}

    def open_app(self, package_name: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Launch an application by package name using Android Monkey launcher."""
        args = ["-s", device_id] if device_id else []
        args.extend(["shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"])
        code, stdout, err = self._run_cmd(args)
        success = code == 0 and "Events injected: 1" in stdout.decode("utf-8", errors="replace")
        log_audit("ANDROID_APP", f"Launch {package_name}: {'Success' if success else 'Failed'}")
        return {"success": success, "package": package_name, "output": stdout.decode("utf-8", errors="replace")[:200]}


# Global instance
android_driver = AndroidDriver()
