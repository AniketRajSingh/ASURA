---
name: browser
description: "Autonomous web interaction skill using Playwright. Can navigate, click, type, and take screenshots for visual analysis."
entry_point: automation.py
---

# Browser

Enables autonomous web browsing and interaction. ASURA can navigate complex websites, fill out and submit forms, extract clean text content for analysis, and capture screenshots to facilitate visual reasoning.

### 🔧 Tools / Functions
- `browse_url(url, screenshot)`: Navigate to a URL using Playwright and extract the page title and body content.
- `fill_form(url, fields, submit_selector)`: Automatically populate form fields and trigger a submission.
- `take_screenshot(url)`: Capture a high-resolution screenshot of a webpage and save it to the local project directory.
- `_browse_fallback(url)`: Internal fallback to `requests` and `BeautifulSoup` if Playwright is unavailable.

### 📝 Examples
- "Search for the latest news on Google" -> Navigates to Google and extracts result summaries.
- "Take a screenshot of https://example.com" -> Saves `browser_screenshot.png` to the project root.

### 🛠️ Requirements
- `playwright`
- `chromium` (installed via `playwright install chromium`)
