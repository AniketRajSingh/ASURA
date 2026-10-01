# ============================================================
# skills/device_control/jarvis_agent.py — Autonomous Computer-Use Agent Loop
#
# Implements Anthropic-spec Computer-Use & Device Control:
# 1. Capture screen observation (Desktop or Android)
# 2. Vision reasoning via ASURA Brain (auto-routed to multimodal models)
# 3. Metacognitive pre-flight safety check (ConsciousnessEngine)
# 4. Cross-platform actuation (Desktop or Android ADB)
# 5. Post-action visual reflection & episode storage (UnifiedMemory)
# 100% Cross-Platform: Runs on Linux, Windows, macOS, and Android.
# ============================================================

from __future__ import annotations
import re
import json
import asyncio
from typing import Optional, Dict, Any, List

from settings import settings as config
from skills.logger import log_audit, log_app
from core.llm import call_llm
from core.consciousness import consciousness
from core.unified_memory import unified_memory
from skills.device_control.desktop_driver import desktop_driver
from skills.device_control.android_driver import android_driver


async def run_device_task(
    goal: str,
    target: str = "desktop",
    device_id: Optional[str] = None,
    max_steps: int = 8
) -> Dict[str, Any]:
    """
    Autonomous goal-oriented device control loop.
    Supports both desktop GUI and mobile Android targets.
    """
    target = target.lower()
    consciousness.set_focus(f"Automating {target} device: {goal}", pulse="focused")
    log_audit("JARVIS_LOOP_START", f"Target: {target} | Goal: {goal}")

    step_history: List[Dict[str, Any]] = []

    for step in range(1, max_steps + 1):
        log_app(f"🤖 JARVIS Agent: Step {step}/{max_steps} for goal '{goal[:50]}'")

        # ── 1. Observation (Capture Screen / UI) ────────────────
        if target == "android":
            obs = android_driver.capture_screen(device_id=device_id)
            ui_nodes = android_driver.dump_ui_hierarchy(device_id=device_id)
            ui_context = "\n".join([f"- '{n['text'] or n['content_desc']}' at center {n['center']}" for n in ui_nodes[:20]])
        else:
            obs = desktop_driver.capture_screen(add_grid=True)
            ui_context = "Desktop graphical interface with indexed coordinate grid overlay"

        if not obs.get("success"):
            err = obs.get("error", "Screen observation failed")
            consciousness.record_thought("alert", f"Observation failed: {err}", pulse="cautious")
            return {"success": False, "error": err, "steps": step_history}

        b64_image = obs.get("base64_image")

        # ── 2. Visual Reasoning via ASURA Brain ──────────────────
        prompt = f"""You are the JARVIS Autonomous Device Controller for ASURA.
Current Target: {target.upper()}
User Goal: "{goal}"
Current Step: {step} of {max_steps}

Recent Action History:
{json.dumps(step_history[-3:], indent=2) if step_history else "No actions taken yet."}

Interactive UI Elements detected:
{ui_context}

Analyze the screen image and output the next logical action to achieve the goal.
Respond strictly in JSON with this schema:
{{
    "thought": "Brief visual analysis of current screen and why you are choosing this action",
    "action": "click | type | press_key | drag | swipe | complete | fail",
    "x": integer coordinate (if click, tap),
    "y": integer coordinate (if click, tap),
    "start_x": integer (if drag, swipe),
    "start_y": integer (if drag, swipe),
    "end_x": integer (if drag, swipe),
    "end_y": integer (if drag, swipe),
    "text": "string to type" (if type),
    "key": "key name e.g. enter, tab, esc, home, back" (if press_key),
    "result": "summary message" (if complete or fail)
}}"""

        try:
            # Send prompt and image to ASURA Brain (auto-routed to multimodal tier)
            raw_response = await call_llm(
                prompt=prompt,
                images=[b64_image] if b64_image else None,
                temperature=0.2,
                format="json"
            )
        except Exception as e:
            log_app(f"JARVIS Brain reasoning error: {e}")
            return {"success": False, "error": f"LLM reasoning failed: {e}", "steps": step_history}

        # ── 3. Parse Action Decision ─────────────────────────────
        try:
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            decision = json.loads(cleaned.strip())
        except Exception:
            decision = {"action": "fail", "result": f"Failed parsing action: {raw_response[:200]}"}

        action_type = decision.get("action", "fail").lower()
        thought = decision.get("thought", "")
        consciousness.record_thought("introspection", f"Step {step}: {thought}", pulse="focused")

        # ── 4. Completion Check ──────────────────────────────────
        if action_type == "complete":
            final_res = decision.get("result", "Goal accomplished successfully.")
            consciousness.record_thought("reflection", f"Goal accomplished: {final_res}", pulse="vigilant")
            unified_memory.record_episode(
                action=f"device_{target}_{goal[:30]}",
                context=goal,
                outcome=final_res,
                success=True
            )
            return {"success": True, "result": final_res, "steps_count": step, "steps": step_history}

        if action_type == "fail":
            fail_reason = decision.get("result", "Could not complete task.")
            consciousness.record_thought("reflection", f"Task failed: {fail_reason}", pulse="cautious")
            return {"success": False, "error": fail_reason, "steps": step_history}

        # ── 5. Metacognitive Pre-Flight Safety Check ─────────────
        verdict = consciousness.metacognitive_check(f"{target}_{action_type}", decision)
        if not verdict.approved:
            return {"success": False, "error": f"Vetoed by consciousness: {verdict.reasoning}", "steps": step_history}

        # ── 6. Actuation ─────────────────────────────────────────
        act_res = {"success": False}
        if target == "android":
            if action_type in ("click", "tap"):
                act_res = android_driver.tap(decision.get("x", 0), decision.get("y", 0), device_id=device_id)
            elif action_type == "type":
                act_res = android_driver.type_text(decision.get("text", ""), device_id=device_id)
            elif action_type == "press_key":
                act_res = android_driver.press_key(decision.get("key", "enter"), device_id=device_id)
            elif action_type in ("drag", "swipe"):
                act_res = android_driver.swipe(
                    decision.get("start_x", 0), decision.get("start_y", 0),
                    decision.get("end_x", 0), decision.get("end_y", 0),
                    device_id=device_id
                )
        else:
            # Desktop Actuation with physical coordinate unscaling
            from skills.device_control.visual_grounding import visual_grounding
            orig_size = obs.get("original_size", (1920, 1080))
            scaled_size = obs.get("scaled_size", orig_size)

            if action_type in ("click", "tap"):
                raw_x, raw_y = decision.get("x", 0), decision.get("y", 0)
                phys_x, phys_y = visual_grounding.unscale_coordinates((raw_x, raw_y), scaled_size, orig_size)
                act_res = desktop_driver.click(phys_x, phys_y)
            elif action_type == "type":
                act_res = desktop_driver.type_text(decision.get("text", ""))
            elif action_type == "press_key":
                act_res = desktop_driver.press_key(decision.get("key", "enter"))
            elif action_type in ("drag", "swipe"):
                sx, sy = visual_grounding.unscale_coordinates(
                    (decision.get("start_x", 0), decision.get("start_y", 0)), scaled_size, orig_size
                )
                ex, ey = visual_grounding.unscale_coordinates(
                    (decision.get("end_x", 0), decision.get("end_y", 0)), scaled_size, orig_size
                )
                act_res = desktop_driver.drag(sx, sy, ex, ey)

        step_record = {
            "step": step,
            "thought": thought,
            "decision": decision,
            "execution": act_res,
        }
        step_history.append(step_record)
        consciousness.reflect_on_outcome(
            f"{target}_{action_type}",
            decision,
            act_res,
            success=act_res.get("success", False)
        )

        # Brief pause for OS/Mobile animation to settle
        await asyncio.sleep(0.8)

    return {
        "success": False,
        "error": f"Reached maximum steps limit ({max_steps}) without completion.",
        "steps": step_history
    }
