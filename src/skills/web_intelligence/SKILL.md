---
name: web_intelligence
description: "Web search and scraping engine with multi-engine fallback and content extraction."
entry_point: intelligence.py
---

# Web Intelligence

Provides the AI with real-time access to the internet. Uses a tiered fallback system (DuckDuckGo HTML -> SearXNG -> DDG API) for maximum reliability.

### 🔧 Tools / Functions
- `web_search(query: str, max_results: int)`: Perform a search across multiple engines.
- `scrape_url(url: str)`: Extract clean, readable text from any webpage (removing scripts/styles).
- `research_topic(topic: str)`: High-level tool that searches and scrapes top results for deep analysis.

### 📝 Examples
- "Search for the latest NVIDIA stock price" -> Returns search snippets.
- "Research the Model Context Protocol" -> Aggregates content from multiple web sources.

### 🛠️ Requirements
- `beautifulsoup4` for HTML parsing.
- `duckduckgo_search` (optional fallback).
