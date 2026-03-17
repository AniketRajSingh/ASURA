# ============================================================
# skills/browser/automation.py — Browser Automation (Playwright)
# ============================================================

import os
from settings import settings as config
from skills.logger import log_audit, log_app


def browse_url(url: str, screenshot: bool = False) -> dict:
    """
    Browse a URL using Playwright and extract content.
    Falls back to requests+BS4 if Playwright unavailable.
    """
    try:
        return _browse_playwright(url, screenshot)
    except ImportError:
        log_app("Playwright not installed, using fallback")
        return _browse_fallback(url)
    except Exception as e:
        log_audit("BROWSER_ERROR", f"Playwright failed: {e}, using fallback")
        return _browse_fallback(url)


def _browse_playwright(url: str, screenshot: bool = False) -> dict:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)

        title = page.title()
        content = page.inner_text("body")[:5000]

        screenshot_path = ""
        if screenshot:
            screenshot_path = os.path.join(config.BASE_DIR, "browser_screenshot.png")
            page.screenshot(path=screenshot_path, full_page=False)

        browser.close()

    log_audit("BROWSER", f"Browsed: {url} | Title: {title[:50]}")
    return {"title": title, "content": content, "screenshot": screenshot_path, "url": url}


def _browse_fallback(url: str) -> dict:
    from skills.web_intelligence import scrape_url
    content = scrape_url(url)
    return {"title": "", "content": content[:5000], "screenshot": "", "url": url}


def fill_form(url: str, fields: dict, submit_selector: str = None) -> dict:
    """Fill out a web form using Playwright."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)

            for selector, value in fields.items():
                page.fill(selector, value)

            if submit_selector:
                page.click(submit_selector)
                page.wait_for_load_state("networkidle")

            result_text = page.inner_text("body")[:3000]
            browser.close()

        log_audit("BROWSER", f"Form filled at {url}")
        return {"success": True, "result": result_text}

    except ImportError:
        return {"success": False, "result": "Playwright not installed. pip install playwright && playwright install"}
    except Exception as e:
        return {"success": False, "result": str(e)}


def take_screenshot(url: str) -> str:
    """Take a screenshot of a URL and return the file path."""
    result = browse_url(url, screenshot=True)
    return result.get("screenshot", "")
