import asyncio
import os
import sys

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from skills.browser.agent import BrowserAgent
from skills.visual.vision import analyze_image, debug_ui_screenshot
from skills.logger import log_app, log_audit

class VisualNav:
    def __init__(self, headless=True):
        self.agent = BrowserAgent(headless=headless)

    async def start(self):
        await self.agent.start()

    async def stop(self):
        await self.agent.stop()

    async def see_and_act(self, url: str, goal: str):
        """
        Navigate to a URL, take a screenshot, and analyze it using Qwen 35B.
        """
        log_audit("VISUAL_NAV", f"Goal: {goal} | URL: {url}")
        await self.agent.navigate(url)
        
        # Capture current state
        import time
        screenshot_path = await self.agent.screenshot(f"nav_{int(time.time())}.png")
        
        # Analyze with Heavy Vision (35B)
        analysis = debug_ui_screenshot(screenshot_path, f"I need to accomplish this goal: {goal}")
        
        log_audit("VISUAL_NAV", f"Vision Analysis (35B): {analysis[:200]}...")
        return analysis, screenshot_path

async def test_visual_nav(url: str, goal: str):
    navigator = VisualNav()
    await navigator.start()
    try:
        analysis, path = await navigator.see_and_act(url, goal)
        return f"Analysis: {analysis}\nScreenshot: {path}"
    finally:
        await navigator.stop()

if __name__ == "__main__":
    import time
    asyncio.run(test_visual_nav("https://www.wikipedia.org", "Find the search bar and describe it."))
