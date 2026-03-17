import os
import time
import asyncio
from playwright.async_api import async_playwright
try:
    from settings import settings as config
    from skills.logger import log_app, log_audit
except ImportError:
    # Support direct execution
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from settings import settings as config
    from skills.logger import log_app, log_audit

class BrowserAgent:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    async def start(self, user_mode=False):
        log_app("Starting BrowserAgent...")
        self.playwright = await async_playwright().start()
        
        # Use persistent context to store cookies/sessions
        # If user_mode is True, we force headless=False so the user can see/log in
        headless = self.headless if not user_mode else False
        
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=config.BROWSER_PROFILE_DIR,
            headless=headless,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # launch_persistent_context returns a context that already has a page
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
            
        log_app(f"BrowserAgent started (headless={headless}).")

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        log_app("BrowserAgent stopped.")

    async def navigate(self, url: str):
        log_audit("BROWSER", f"Navigating to {url}")
        await self.page.goto(url, wait_until="networkidle")
        return f"Navigated to {url}"

    async def click(self, selector: str, retry_with_vision=True):
        log_audit("BROWSER", f"Clicking {selector}")
        try:
            await self.page.click(selector, timeout=5000)
            return f"Clicked {selector}"
        except Exception as e:
            if not retry_with_vision:
                raise e
            log_app(f"Click failed: {e}. Attempting vision-based self-correction...")
            return await self._action_with_vision("click", selector)

    async def type(self, selector: str, text: str, retry_with_vision=True):
        log_audit("BROWSER", f"Typing '{text}' into {selector}")
        try:
            await self.page.fill(selector, text, timeout=5000)
            return f"Typed into {selector}"
        except Exception as e:
            if not retry_with_vision:
                raise e
            log_app(f"Type failed: {e}. Attempting vision-based self-correction...")
            return await self._action_with_vision("type", selector, text)

    async def _action_with_vision(self, action: str, target: str, value: str = None):
        """Internal helper to use vision model to find a target when selector fails."""
        fpath = await self.screenshot("correction_needed.png")
        log_app("Analyzing screenshot for self-correction...")
        
        prompt = f"I tried to {action} on '{target}' but the selector failed. Look at this screenshot of the web page. "
        prompt += f"Find the coordinates (X, Y) of the element that looks like '{target}' or is most relevant. "
        prompt += "Return ONLY JSON: {'x': int, 'y': int, 'found': bool}"
        
        try:
            from skills.visual.vision import analyze_image
            res_str = analyze_image(fpath, prompt)
            import json
            # Extract JSON from response
            import re
            match = re.search(r"\{.*\}", res_str, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if data.get("found"):
                    x, y = data["x"], data["y"]
                    log_app(f"Vision found element at {x}, {y}. Retrying action...")
                    await self.page.mouse.click(x, y)
                    if action == "type" and value:
                        await self.page.keyboard.type(value)
                    return f"Vision-corrected {action} success at {x},{y}"
        except Exception as ve:
            log_app(f"Vision correction failed: {ve}")
        
        return f"Failed {action} on {target} even with vision."

    async def screenshot(self, filename: str = None):
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        fpath = os.path.join(config.ASSETS_DIR, filename)
        await self.page.screenshot(path=fpath)
        log_audit("BROWSER", f"Screenshot saved to {fpath}")
        return fpath

    async def get_content(self):
        content = await self.page.content()
        # Basic text extraction
        text = await self.page.evaluate("() => document.body.innerText")
        return text[:5000] # Limit to 5000 chars for context

async def run_browser_task(url: str, task_desc: str):
    """
    Convenience function to run a single browser task.
    """
    agent = BrowserAgent()
    await agent.start()
    try:
        await agent.navigate(url)
        # This is where the autonomous loop would go
        # For now, just take a screenshot
        fpath = await agent.screenshot()
        return f"Task completed. Screenshot: {fpath}"
    finally:
        await agent.stop()

if __name__ == "__main__":
    # Test script
    asyncio.run(run_browser_task("https://www.google.com", "Testing browser agent"))
